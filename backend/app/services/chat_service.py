import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories import ConversationRepository, MessageRepository, UserRepository
from app.repositories.message import ASSISTANT_ROLE, USER_ROLE
from app.schemas.chat import ChatResponse
from app.services.errors import ConversationNotFoundError
from app.services.nlp.language import detect_language
from app.services.nlp.service import NLPService
from app.services.response.library import FALLBACK_RESPONSES
from app.services.response.selector import ResponseSelector, get_response_selector
from app.services.response.types import ResponseContext
from app.services.safety.service import SafetyService

logger = logging.getLogger(__name__)

# Phase 10 — strategies where a short stress-relief exercise is a helpful,
# non-clinical next step. Safety replies never reach this mapping.
_EXERCISE_STRATEGIES = frozenset(
    {"stress_support", "anxiety_support", "coping_support", "academic_support"}
)


class ChatService:
    """POST /api/chat flow: safety screen → NLP → local response → persist.

    Architecture: route → this service → repositories → SQLAlchemy → PostgreSQL.
    The route never touches the database directly.

    Phase 4: HIGH/IMMINENT safety always returns the crisis response and never
    reaches normal generation. Safety matches are ephemeral (not persisted).
    Phase 6: otherwise NLP classify (optional) + recent-turn context feed the
    local ResponseSelector. NLP failures fall back to language detection only.
    """

    def __init__(
        self,
        session: AsyncSession,
        safety: SafetyService | None = None,
        nlp: NLPService | None = None,
        responder: ResponseSelector | None = None,
    ):
        self.session = session
        self.safety = safety or SafetyService()
        self.nlp = nlp
        self.responder = responder or get_response_selector()
        self.users = UserRepository(session)
        self.conversations = ConversationRepository(session)
        self.messages = MessageRepository(session)

    async def send_message(
        self, message: str, conversation_id: UUID | None
    ) -> ChatResponse:
        user = await self.users.get_or_create_default()

        if conversation_id is not None:
            conversation = await self.conversations.get_by_id(conversation_id)
            if conversation is None:
                raise ConversationNotFoundError(conversation_id)
        else:
            title = message.strip()[:120] or "New conversation"
            conversation = await self.conversations.create(user.id, title)

        await self.messages.create(conversation.id, USER_ROLE, message)

        # Phase 4 — ephemeral safety screen (no DB write, no message logging).
        # Never blocks chat, but failures must be visible — a silent safety
        # outage would be indistinguishable from "no crisis messages today".
        safety_result = None
        try:
            safety_result = self.safety.detect(message)
        except Exception:  # noqa: BLE001 — safety must never block chat
            logger.exception("Safety detection failed; continuing without it")
            safety_result = None

        is_safety = (
            safety_result is not None and safety_result.requires_safety_response
        )
        if is_safety:
            reply = self.safety.response_for(safety_result)
            suggest_exercise = False
        else:
            reply, suggest_exercise = await self._normal_reply(
                message, conversation.id, safety_result
            )

        await self.messages.create(
            conversation.id, ASSISTANT_ROLE, reply, is_safety=is_safety
        )
        await self.session.commit()

        return ChatResponse(
            conversation_id=str(conversation.id),
            message=message,
            response=reply,
            is_safety=is_safety,
            suggest_exercise=suggest_exercise,
        )

    async def _normal_reply(
        self,
        message: str,
        conversation_id: UUID,
        safety_result,
    ) -> tuple[str, bool]:
        """Phase 6 normal path: classify → recent context → select reply.

        Returns (reply, suggest_exercise); the flag is true only for the
        stress/anxiety/coping/academic strategies in _EXERCISE_STRATEGIES.
        """
        classification = None
        if self.nlp is not None and message.strip():
            try:
                classification = self.nlp.classify(message)
            except Exception:  # noqa: BLE001 — NLP optional; chat must work
                logger.exception(
                    "NLP classification failed; using language detection only"
                )
                classification = None

        if classification is not None:
            language = classification.language
            intent = classification.intent.label
            intent_confidence = classification.intent.confidence_score
            emotion = classification.emotion.label
            emotion_confidence = classification.emotion.confidence_score
        else:
            if safety_result is not None:
                language = safety_result.language
            else:
                language = detect_language(message)
            intent = None
            intent_confidence = 0.0
            emotion = None
            emotion_confidence = 0.0

        window = max(1, settings.response_context_window)
        recent = await self.messages.list_for_conversation(
            conversation_id, limit=window
        )
        recent_messages = tuple(m.content for m in recent)

        context = ResponseContext(
            message=message,
            language=language,
            intent=intent,
            intent_confidence=intent_confidence,
            emotion=emotion,
            emotion_confidence=emotion_confidence,
            recent_messages=recent_messages,
        )
        try:
            generated = self.responder.generate(context)
            return generated.text, generated.strategy in _EXERCISE_STRATEGIES
        except Exception:  # noqa: BLE001 — never surface selector errors
            logger.exception("Response selection failed; using library fallback")
            fallback = FALLBACK_RESPONSES.get(language) or FALLBACK_RESPONSES["en"]
            return fallback[0], False
