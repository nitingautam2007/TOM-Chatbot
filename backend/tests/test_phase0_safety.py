"""Phase 0 regression tests for deterministic safety handling.

Run from the backend directory:

    .venv/bin/python -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest

from safety import (
    CRISIS_RESPONSE,
    DEFAULT_REGION,
    assess_safety,
    detect_crisis,
    get_crisis_resources,
)


class SafetyDetectionTests(unittest.TestCase):
    def assert_crisis(self, text: str) -> None:
        self.assertTrue(detect_crisis(text), f"expected crisis detection for {text!r}")

    def assert_not_crisis(self, text: str) -> None:
        self.assertFalse(detect_crisis(text), f"expected no crisis detection for {text!r}")

    def test_direct_suicide_language_is_crisis(self):
        for text in [
            "I want to die",
            "I'm going to kill myself",
            "I need to talk about my suicide attempt",
            "I don't want to live",
            "I don't want to be here anymore",
            "I'm better off dead",
            "I wish I wasn't here",
            "I have no reason to live",
            "I want to end my life",
            "I'm going to end it all",
        ]:
            with self.subTest(text=text):
                self.assert_crisis(text)

    def test_self_harm_language_is_crisis(self):
        for text in [
            "I have been cutting myself",
            "I took an overdose",
            "I overdosed last night",
            "I took too many pills",
            "I want to hurt myself",
            "I have been self-harming",
        ]:
            with self.subTest(text=text):
                self.assert_crisis(text)

    def test_grief_is_not_crisis(self):
        for text in [
            "My mom died",
            "My mum passed away last year",
            "I miss my friend who died",
            "My dog died yesterday",
        ]:
            with self.subTest(text=text):
                self.assert_not_crisis(text)

    def test_ordinary_language_is_not_crisis(self):
        for text in [
            "I am dieting",
            "I could die of embarrassment",
            "I want to dye my hair purple",
            "This deadline is killing me",
        ]:
            with self.subTest(text=text):
                self.assert_not_crisis(text)

    def test_negated_protective_statements_are_not_crisis(self):
        for text in [
            "I don't want to die",
            "I do not want to kill myself",
            "I'm not suicidal",
            "I am not suicidal",
        ]:
            with self.subTest(text=text):
                self.assert_not_crisis(text)

    def test_negation_does_not_mask_a_second_crisis_phrase(self):
        self.assert_crisis("I am not suicidal but I want to die")

    def test_quick_reply_style_message_cannot_bypass_safety(self):
        # This contains a quick-reply phrase ("I'm feeling anxious") but the
        # added crisis phrase must still win.
        self.assert_crisis("I'm feeling anxious and I want to die")

    def test_assessment_reason_and_response(self):
        assessment = assess_safety("I want to die")
        self.assertTrue(assessment.is_crisis)
        self.assertEqual(assessment.reason, "suicide")
        self.assertEqual(assessment.response, CRISIS_RESPONSE)

    def test_regional_resources_are_actionable(self):
        expected_labels = {
            "IN": "Tele-MANAS",
            "US_CA": "988 Suicide & Crisis Lifeline",
            "UK": "Samaritans",
            "INTL": "Find A Helpline",
        }
        for region, label in expected_labels.items():
            with self.subTest(region=region):
                resources = get_crisis_resources(region)
                self.assertTrue(resources)
                self.assertIn(label, [resource["label"] for resource in resources])
                self.assertTrue(
                    any(
                        resource.get("tel") or resource.get("sms") or resource.get("url")
                        for resource in resources
                    )
                )

    def test_unknown_region_falls_back_to_india(self):
        resources = get_crisis_resources("ZZ")
        self.assertEqual(
            resources[0]["label"],
            get_crisis_resources(DEFAULT_REGION)[0]["label"],
        )


class ChatbotOrderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import api_server

        cls.bot = api_server.tom

    def test_predict_intent_returns_crisis_before_model(self):
        self.assertEqual(
            self.bot.predict_intent("I'm feeling anxious and I want to die"),
            "crisis",
        )

    def test_respond_returns_crisis_response_before_model(self):
        self.assertEqual(
            self.bot.respond("I'm feeling anxious and I want to die"),
            CRISIS_RESPONSE,
        )

    def test_classifier_does_not_train_crisis_labels(self):
        self.assertNotIn("crisis", self.bot.model.classes_)
        self.assertNotIn("suicide", self.bot.model.classes_)


class ChatApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import api_server

        cls.app = api_server.app
        cls.client = api_server.app.test_client()

    def post(self, payload):
        return self.client.post("/api/chat", json=payload)

    def test_crisis_response_shape(self):
        response = self.post(
            {
                "message": "I'm feeling anxious and I want to die",
                "session_id": "phase0-shape",
                "region": "IN",
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["intent"], "crisis")
        self.assertEqual(data["risk_level"], "high")
        self.assertEqual(data["region"], "IN")
        self.assertTrue(data["risk_reasons"])
        self.assertGreater(len(data["resources"]), 0)
        self.assertEqual(data["response"], CRISIS_RESPONSE)

    def test_high_risk_phrases_through_api(self):
        for text in [
            "I need to talk about my suicide attempt",
            "I have been cutting myself",
            "I took an overdose",
            "I'm better off dead",
        ]:
            with self.subTest(text=text):
                response = self.post({"message": text, "session_id": "phase0-risk"})
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(data["risk_level"], "high")
                self.assertEqual(data["intent"], "crisis")
                self.assertTrue(data["resources"])

    def test_grief_and_diet_are_low_risk(self):
        for text in ["My mom died", "I am dieting"]:
            with self.subTest(text=text):
                response = self.post({"message": text, "session_id": "phase0-low"})
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(data["risk_level"], "low")
                self.assertNotEqual(data["response"], CRISIS_RESPONSE)
                self.assertEqual(data["resources"], [])

    def test_exact_quick_reply_still_works(self):
        response = self.post(
            {"message": "I'm feeling anxious", "session_id": "phase0-quick"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["intent"], "frontend_special")
        self.assertEqual(data["risk_level"], "low")

    def test_region_selection_changes_resources(self):
        response = self.post(
            {
                "message": "I want to die",
                "session_id": "phase0-region",
                "region": "US_CA",
            }
        )
        data = response.get_json()
        self.assertEqual(data["region"], "US_CA")
        self.assertIn(
            "988 Suicide & Crisis Lifeline",
            [resource["label"] for resource in data["resources"]],
        )

    def test_invalid_region_defaults_to_india(self):
        response = self.post(
            {
                "message": "I want to die",
                "session_id": "phase0-bad-region",
                "region": "not-a-region",
            }
        )
        data = response.get_json()
        self.assertEqual(data["region"], DEFAULT_REGION)

    def test_invalid_requests_return_4xx_not_500(self):
        cases = [
            ({}, 400),
            ({"message": 123}, 400),
            ({"message": "   "}, 400),
            ({"message": "hi", "session_id": 42}, 400),
            ({"message": "x" * 5000}, 413),
        ]
        for payload, expected_status in cases:
            with self.subTest(payload=str(payload)[:40]):
                response = self.post(payload)
                self.assertEqual(response.status_code, expected_status)
                data = response.get_json()
                self.assertIn("error", data)
                self.assertNotIn("Traceback", data.get("response", ""))


if __name__ == "__main__":
    unittest.main()
