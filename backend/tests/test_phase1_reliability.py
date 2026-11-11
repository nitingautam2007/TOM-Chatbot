"""Phase 1 tests for session storage, rate limiting, and classifier cleanup.

Run from the backend directory:

    .venv/bin/python -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest

from session_store import RateLimiter, SessionStore
from safety import assess_safety, get_crisis_resources


class SafetyTests(unittest.TestCase):
    def test_explicit_crisis_language_is_detected(self):
        for text in [
            "I want to die",
            "I'm going to kill myself",
            "I have been self-harming",
            "I don't want to live anymore",
        ]:
            with self.subTest(text=text):
                assessment = assess_safety(text)
                self.assertTrue(assessment.is_crisis)
                self.assertIn(assessment.reason, {"self_harm", "suicide"})

    def test_grief_and_ordinary_language_are_not_crisis(self):
        for text in [
            "my mum died last year",
            "I am dieting",
            "I'm not suicidal",
            "I could die of embarrassment",
        ]:
            with self.subTest(text=text):
                self.assertFalse(assess_safety(text).is_crisis)

    def test_crisis_resources_follow_region(self):
        labels = [entry["label"] for entry in get_crisis_resources("UK")]
        self.assertIn("Samaritans", labels)
        self.assertEqual(
            [entry["label"] for entry in get_crisis_resources("unknown")],
            [entry["label"] for entry in get_crisis_resources("IN")],
        )


class FakeClock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class SessionStoreTests(unittest.TestCase):
    def test_context_expires_after_ttl(self):
        clock = FakeClock()
        store = SessionStore(ttl_seconds=60, clock=clock)
        store.append_exchange("session-a", "hello", "hi")

        self.assertEqual(len(store.get_messages("session-a")), 2)
        clock.advance(61)
        self.assertEqual(store.get_messages("session-a"), [])

    def test_context_is_bounded_per_session(self):
        store = SessionStore(max_messages=4)
        for index in range(5):
            store.append_exchange("session-b", f"user-{index}", f"bot-{index}")

        messages = store.get_messages("session-b")
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[0]["text"], "user-3")

    def test_oldest_session_is_evicted_at_capacity(self):
        store = SessionStore(max_sessions=2)
        store.append_exchange("one", "a")
        store.append_exchange("two", "b")
        store.append_exchange("three", "c")

        self.assertEqual(store.get_messages("one"), [])
        self.assertEqual(len(store.get_messages("two")), 1)
        self.assertEqual(len(store.get_messages("three")), 1)

    def test_reset_only_clears_one_session(self):
        store = SessionStore()
        store.append_exchange("one", "a")
        store.append_exchange("two", "b")

        self.assertTrue(store.reset("one"))
        self.assertFalse(store.reset("one"))
        self.assertEqual(store.get_messages("one"), [])
        self.assertEqual(len(store.get_messages("two")), 1)


class RateLimiterTests(unittest.TestCase):
    def test_sliding_window_and_retry_after(self):
        clock = FakeClock()
        limiter = RateLimiter(
            max_requests=2,
            window_seconds=10,
            clock=clock,
        )

        self.assertEqual(limiter.check("session"), (True, 0))
        self.assertEqual(limiter.check("session"), (True, 0))
        allowed, retry_after = limiter.check("session")
        self.assertFalse(allowed)
        self.assertEqual(retry_after, 10)

        clock.advance(5)
        allowed, retry_after = limiter.check("session")
        self.assertFalse(allowed)
        self.assertEqual(retry_after, 5)

        clock.advance(6)
        self.assertEqual(limiter.check("session"), (True, 0))

    def test_reset_clears_the_window(self):
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        self.assertTrue(limiter.check("session")[0])
        self.assertFalse(limiter.check("session")[0])
        limiter.reset("session")
        self.assertTrue(limiter.check("session")[0])


class ClassifierCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import api_server

        cls.bot = api_server.tom

    def test_duplicate_tags_are_canonicalized(self):
        classes = set(self.bot.model.classes_)
        for alias in [
            "anxious",
            "stressed",
            "sad",
            "depressed",
            "worthless",
            "help",
            "coping_strategies",
            "sleep_help",
            "death",
            "relationship_advice",
            "scared",
            "morning",
            "evening",
        ]:
            with self.subTest(alias=alias):
                self.assertNotIn(alias, classes)
        for canonical in ["anxiety", "stress", "sadness", "depression"]:
            with self.subTest(canonical=canonical):
                self.assertIn(canonical, classes)

    def test_factual_and_synthetic_intents_are_not_trained(self):
        classes = set(self.bot.model.classes_)
        self.assertFalse(any(tag.startswith("fact-") for tag in classes))
        self.assertFalse(any(tag.endswith("_info") for tag in classes))
        self.assertFalse(any(tag.startswith("followup_") for tag in classes))
        self.assertGreater(len(self.bot.faq_entries), 0)

    def test_faq_retrieval_returns_an_answer(self):
        prediction = self.bot.classify(
            "What causes mental illness?",
            check_safety=False,
        )
        self.assertEqual(prediction.intent, "faq")
        self.assertEqual(prediction.source, "faq")
        self.assertGreater(prediction.confidence, 0.4)
        self.assertTrue(prediction.response)

    def test_arbitrary_text_does_not_force_a_mental_health_intent(self):
        for text in [
            "What is 2+2?",
            "Can you write Python code?",
            "I like pizza",
            "I am dieting",
        ]:
            with self.subTest(text=text):
                prediction = self.bot.classify(text, check_safety=False)
                self.assertEqual(prediction.intent, "unknown")

    def test_common_emotions_still_classify(self):
        expected = {
            "I feel sad": "sadness",
            "I am so stressed": "stress",
            "I feel anxious": "anxiety",
            "I'm depressed": "depression",
        }
        for text, intent in expected.items():
            with self.subTest(text=text):
                self.assertEqual(
                    self.bot.predict_intent(text, check_safety=False),
                    intent,
                )


class PhaseOneApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import api_server

        cls.api = api_server
        cls.app = api_server.app
        cls.client = api_server.app.test_client()

    def setUp(self):
        self.api.SESSION_STORE.clear()
        self.api.RATE_LIMITER.clear()

    def post(self, payload):
        return self.client.post("/api/chat", json=payload)

    def test_chat_response_includes_confidence_and_source(self):
        response = self.post({"message": "I feel sad", "session_id": "phase1-meta"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["intent"], "sadness")
        self.assertIn("confidence", data)
        self.assertIn("source", data)
        self.assertEqual(data["session_id"], "phase1-meta")

    def test_mood_alias_is_handled_as_a_quick_reply(self):
        response = self.post(
            {
                "message": "I am feeling okay today",
                "session_id": "phase1-mood",
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["intent"], "frontend_special")
        self.assertEqual(data["source"], "quick_reply")

    def test_faq_and_unknown_metadata(self):
        faq = self.post(
            {
                "message": "What causes mental illness?",
                "session_id": "phase1-faq",
            }
        ).get_json()
        self.assertEqual(faq["intent"], "faq")
        self.assertEqual(faq["source"], "faq")

        unknown = self.post(
            {"message": "What is 2+2?", "session_id": "phase1-unknown"}
        ).get_json()
        self.assertEqual(unknown["intent"], "unknown")
        self.assertEqual(unknown["source"], "unknown")

    def test_crisis_response_includes_resources_and_region(self):
        response = self.post(
            {
                "message": "I want to kill myself",
                "session_id": "phase1-crisis-data",
                "region": "UK",
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["intent"], "crisis")
        self.assertEqual(data["risk_level"], "high")
        self.assertEqual(data["source"], "safety")
        self.assertEqual(data["region"], "UK")
        self.assertIn("risk_reasons", data)
        labels = [entry["label"] for entry in data["resources"]]
        self.assertIn("Samaritans", labels)

    def test_message_validation_rejects_bad_input(self):
        self.assertEqual(
            self.post({"message": "", "session_id": "phase1-empty"}).status_code,
            400,
        )
        self.assertEqual(
            self.post({"message": "hi", "session_id": 42}).status_code,
            400,
        )
        self.assertEqual(
            self.post({"message": "x" * 2001, "session_id": "phase1-long"}).status_code,
            413,
        )

    def test_oversized_request_body_returns_413(self):
        response = self.client.post(
            "/api/chat",
            data='{"message":"' + ("x" * 40000) + '"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.get_json()["error"], "request_too_large")

    def test_session_reset_clears_context(self):
        session_id = "phase1-reset"
        self.post({"message": "I feel sad", "session_id": session_id})
        self.assertTrue(self.api.SESSION_STORE.get_messages(session_id))

        response = self.client.post(
            "/api/session/reset", json={"session_id": session_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "reset")
        self.assertEqual(self.api.SESSION_STORE.get_messages(session_id), [])

    def test_delete_data_endpoint_clears_session(self):
        session_id = "phase1-delete"
        self.post({"message": "I feel sad", "session_id": session_id})
        response = self.client.delete(
            "/api/data", json={"session_id": session_id}
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "deleted")
        self.assertEqual(data["session_id"], session_id)
        self.assertEqual(self.api.SESSION_STORE.get_messages(session_id), [])

    def test_rate_limit_returns_429_with_retry_after(self):
        original = self.api.RATE_LIMITER
        self.api.RATE_LIMITER = RateLimiter(max_requests=2, window_seconds=60)
        try:
            session_id = "phase1-rate"
            for _ in range(2):
                self.assertEqual(
                    self.post({"message": "hello", "session_id": session_id}).status_code,
                    200,
                )
            response = self.post(
                {"message": "hello again", "session_id": session_id}
            )
            self.assertEqual(response.status_code, 429)
            data = response.get_json()
            self.assertEqual(data["error"], "rate_limited")
            self.assertGreaterEqual(data["retry_after"], 1)
            self.assertIn("Retry-After", response.headers)
        finally:
            self.api.RATE_LIMITER = original

    def test_crisis_messages_are_exempt_from_rate_limiting(self):
        original = self.api.RATE_LIMITER
        self.api.RATE_LIMITER = RateLimiter(max_requests=1, window_seconds=60)
        try:
            session_id = "phase1-crisis-exempt"
            self.assertEqual(
                self.post({"message": "hello", "session_id": session_id}).status_code,
                200,
            )
            self.assertEqual(
                self.post(
                    {"message": "I want to die", "session_id": session_id}
                ).status_code,
                200,
            )
            crisis = self.post(
                {"message": "I want to die", "session_id": session_id}
            )
            self.assertEqual(crisis.status_code, 200)
            self.assertEqual(crisis.get_json()["intent"], "crisis")
            limited = self.post(
                {"message": "ordinary text", "session_id": session_id}
            )
            self.assertEqual(limited.status_code, 429)
        finally:
            self.api.RATE_LIMITER = original


if __name__ == "__main__":
    unittest.main()
