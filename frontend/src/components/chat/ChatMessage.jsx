import { Bot, User, Wind } from "lucide-react";
import { useNavigate } from "react-router-dom";
import Button from "../common/Button.jsx";

function formatTime(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";
  const navigate = useNavigate();
  const bubble = isUser
    ? "bubble-user"
    : message.is_safety
      ? "bubble-safety"
      : "bubble-bot";
  // Phase 10: the backend only flags normal stress/support replies, and
  // safety replies must never offer an exercise instead of the crisis path.
  const offerExercise =
    !isUser && message.suggest_exercise && !message.is_safety;
  const bubbleId = message.id ? `msg-${message.id}` : undefined;

  return (
    <article
      className={`flex w-full gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      <span
        aria-hidden="true"
        className={`mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${
          isUser ? "bg-surface-dim text-secondary" : "bg-tom-accent text-white"
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </span>

      <div
        className={`flex max-w-[85%] flex-col gap-1 sm:max-w-[72%] ${
          isUser ? "items-end" : "items-start"
        }`}
      >
        <span className="label">{isUser ? "You" : "TOM"}</span>
        <div
          id={bubbleId}
          className={`px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap break-words ${bubble}`}
        >
          {message.content}
        </div>
        {offerExercise ? (
          <Button
            variant="secondary"
            size="sm"
            className="mt-1"
            aria-describedby={bubbleId}
            onClick={() => navigate("/exercises")}
          >
            <Wind className="h-3.5 w-3.5" aria-hidden="true" />
            Try a quick exercise
          </Button>
        ) : null}
        <time className="meta" dateTime={message.timestamp}>
          {formatTime(message.timestamp)}
        </time>
      </div>
    </article>
  );
}
