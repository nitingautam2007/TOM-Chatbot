"""Phase 2 tests for production configuration and API hardening.

Run from the backend directory:

    .venv/bin/python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import logging
import unittest

from config import DEFAULT_SECRET_KEY, load_settings
from observability import (
    REQUEST_ID_HEADER,
    JsonFormatter,
    configure_logging,
    request_id_from_header,
)

PRODUCTION_SECRET = "a" * 48


class ProductionConfigTests(unittest.TestCase):
    def test_development_defaults_are_safe_for_local_use(self):
        settings = load_settings({})

        self.assertEqual(settings.environment, "development")
        self.assertFalse(settings.is_production)
        self.assertEqual(settings.secret_key, DEFAULT_SECRET_KEY)
        self.assertEqual(settings.cors_origins, ("*",))
        self.assertFalse(settings.trust_proxy)
        self.assertEqual(settings.session_ttl_seconds, 1800)
        self.assertEqual(settings.max_sessions, 1000)
        self.assertEqual(settings.rate_limit_requests, 20)
        self.assertEqual(settings.rate_limit_window_seconds, 60)
        self.assertEqual(settings.log_level, "INFO")
        self.assertEqual(settings.port, 8000)
        self.assertEqual(settings.max_content_length, 32 * 1024)
        self.assertEqual(settings.max_message_length, 2000)

    def test_production_requires_a_long_secret(self):
        for secret in [None, "", "short-secret", DEFAULT_SECRET_KEY]:
            with self.subTest(secret=secret):
                environment = {
                    "TOM_ENV": "production",
                    "TOM_CORS_ORIGINS": "https://tom.example.com",
                }
                if secret is not None:
                    environment["TOM_SECRET_KEY"] = secret
                with self.assertRaisesRegex(RuntimeError, "TOM_SECRET_KEY"):
                    load_settings(environment)

    def test_production_requires_explicit_cors_origins(self):
        environment = {
            "TOM_ENV": "production",
            "TOM_SECRET_KEY": PRODUCTION_SECRET,
        }
        with self.assertRaisesRegex(RuntimeError, "TOM_CORS_ORIGINS"):
            load_settings(environment)

        environment["TOM_CORS_ORIGINS"] = "*"
        with self.assertRaisesRegex(RuntimeError, "cannot contain"):
            load_settings(environment)

    def test_production_settings_parse_and_normalize_origins(self):
        settings = load_settings(
            {
                "TOM_ENV": "prod",
                "TOM_SECRET_KEY": PRODUCTION_SECRET,
                "TOM_CORS_ORIGINS": (
                    "https://tom.example.com/, https://www.tom.example.com,"
                    " https://tom.example.com"
                ),
                "TOM_TRUST_PROXY": "yes",
                "TOM_SESSION_TTL_SECONDS": "900",
                "TOM_MAX_SESSIONS": "250",
                "TOM_RATE_LIMIT_REQUESTS": "30",
                "TOM_RATE_LIMIT_WINDOW_SECONDS": "45",
                "TOM_LOG_LEVEL": "warning",
                "TOM_HOST": "127.0.0.1",
                "TOM_PORT": "9000",
            }
        )

        self.assertTrue(settings.is_production)
        self.assertEqual(settings.secret_key, PRODUCTION_SECRET)
        self.assertEqual(
            settings.cors_origins,
            ("https://tom.example.com", "https://www.tom.example.com"),
        )
        self.assertTrue(settings.trust_proxy)
        self.assertEqual(settings.session_ttl_seconds, 900)
        self.assertEqual(settings.max_sessions, 250)
        self.assertEqual(settings.rate_limit_requests, 30)
        self.assertEqual(settings.rate_limit_window_seconds, 45)
        self.assertEqual(settings.log_level, "WARNING")
        self.assertEqual(settings.host, "127.0.0.1")
        self.assertEqual(settings.port, 9000)

    def test_invalid_cors_origins_are_rejected(self):
        for origin in [
            "https://tom.example.com/app",
            "ftp://tom.example.com",
            "tom.example.com",
            "https://tom.example.com?debug=1",
            "https://user:pass@tom.example.com",
            "https://tom example.com",
        ]:
            with self.subTest(origin=origin):
                with self.assertRaisesRegex(RuntimeError, "Invalid CORS origin"):
                    load_settings(
                        {
                            "TOM_ENV": "production",
                            "TOM_SECRET_KEY": PRODUCTION_SECRET,
                            "TOM_CORS_ORIGINS": origin,
                        }
                    )

    def test_invalid_environment_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Invalid TOM_ENV"):
            load_settings({"TOM_ENV": "prodction"})

    def test_staging_uses_production_safeguards(self):
        settings = load_settings(
            {
                "TOM_ENV": "staging",
                "TOM_SECRET_KEY": PRODUCTION_SECRET,
                "TOM_CORS_ORIGINS": "https://staging.tom.example.com",
            }
        )
        self.assertTrue(settings.is_production)
        self.assertEqual(settings.environment, "staging")

    def test_invalid_log_level_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "TOM_LOG_LEVEL"):
            load_settings({"TOM_LOG_LEVEL": "verbose"})

    def test_invalid_numbers_and_booleans_are_rejected(self):
        for environment in [
            {"TOM_MAX_SESSIONS": "not-a-number"},
            {"TOM_RATE_LIMIT_REQUESTS": "0"},
            {"TOM_SESSION_TTL_SECONDS": "-5"},
            {"TOM_PORT": "70000"},
            {"TOM_TRUST_PROXY": "sometimes"},
        ]:
            with self.subTest(environment=environment):
                with self.assertRaises(RuntimeError):
                    load_settings(environment)


class ObservabilityTests(unittest.TestCase):
    def test_json_formatter_keeps_metadata_and_drops_unknown_fields(self):
        record = logging.LogRecord(
            "tom.api",
            logging.INFO,
            __file__,
            10,
            "request",
            (),
            None,
        )
        record.extra_fields = {
            "request_id": "abc123",
            "method": "POST",
            "path": "/api/chat",
            "status": 200,
            "duration_ms": 12.5,
        }

        payload = json.loads(JsonFormatter().format(record))
        self.assertEqual(payload["level"], "INFO")
        self.assertEqual(payload["message"], "request")
        self.assertEqual(payload["request_id"], "abc123")
        self.assertEqual(payload["status"], 200)
        self.assertNotIn("message_text", payload)
        self.assertTrue(payload["timestamp"].endswith("Z"))

    def test_request_ids_are_validated(self):
        self.assertEqual(request_id_from_header("client-request_123"), "client-request_123")
        self.assertEqual(request_id_from_header("  padded-id  "), "padded-id")
        for value in [None, "", "has spaces", "x" * 65, "line\nbreak"]:
            with self.subTest(value=value):
                generated = request_id_from_header(value)
                self.assertEqual(len(generated), 32)
                self.assertNotEqual(generated, value)

    def test_logging_setup_is_idempotent(self):
        logger = configure_logging("INFO")
        count = len(logger.handlers)
        configure_logging("INFO")
        self.assertEqual(len(logger.handlers), count)


class ProductionApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import api_server

        cls.api = api_server
        cls.app = api_server.app
        cls.client = api_server.app.test_client()

    def setUp(self):
        self.api.SESSION_STORE.clear()
        self.api.RATE_LIMITER.clear()

    def test_health_reports_readiness_and_runtime_metadata(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "online")
        self.assertTrue(data["ready"])
        self.assertEqual(data["version"], self.api.TOM_VERSION)
        self.assertEqual(data["environment"], self.api.SETTINGS.environment)
        self.assertGreater(data["intents"], 0)
        self.assertGreater(data["patterns"], 0)
        self.assertGreater(data["faq_entries"], 0)
        self.assertIn("messages", data)
        self.assertIn("rate_limit_keys", data)
        self.assertGreaterEqual(data["uptime_seconds"], 0)
        self.assertTrue(data["timestamp"].endswith("Z"))

    def test_readiness_endpoint_reports_unavailable_without_a_model(self):
        original = self.api.MODEL_READY
        self.api.MODEL_READY = False
        try:
            response = self.client.get("/api/ready")
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.get_json()["error"], "model_unavailable")
        finally:
            self.api.MODEL_READY = original

        response = self.client.get("/api/ready")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ready"])

    def test_request_id_is_echoed_or_generated(self):
        response = self.client.get(
            "/api/health",
            headers={REQUEST_ID_HEADER: "client-request-123"},
        )
        self.assertEqual(response.headers[REQUEST_ID_HEADER], "client-request-123")

        generated = self.client.get("/api/health")
        self.assertEqual(len(generated.headers[REQUEST_ID_HEADER]), 32)

    def test_api_responses_include_security_headers(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
        self.assertIn("camera=()", response.headers["Permissions-Policy"])
        self.assertIn(
            "frame-ancestors 'none'",
            response.headers["Content-Security-Policy"],
        )
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(
            response.headers["X-Permitted-Cross-Domain-Policies"],
            "none",
        )
        self.assertNotIn("Strict-Transport-Security", response.headers)

    def test_production_security_headers_include_hsts(self):
        from dataclasses import replace
        from werkzeug.wrappers import Response

        original = self.api.SETTINGS
        self.api.SETTINGS = replace(
            original,
            environment="production",
            is_production=True,
        )
        try:
            response = Response()
            self.api._set_security_headers(response)
        finally:
            self.api.SETTINGS = original

        self.assertEqual(
            response.headers["Strict-Transport-Security"],
            "max-age=31536000; includeSubDomains",
        )

    def test_unknown_routes_return_json(self):
        response = self.client.get("/api/does-not-exist")
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data["error"], "not_found")
        self.assertEqual(data["source"], "validation")
        self.assertIn(REQUEST_ID_HEADER, response.headers)

    def test_wrong_method_returns_json_with_allow_header(self):
        response = self.client.get("/api/chat")
        self.assertEqual(response.status_code, 405)
        data = response.get_json()
        self.assertEqual(data["error"], "method_not_allowed")
        self.assertIn("POST", response.headers["Allow"])

    def test_unexpected_errors_return_a_safe_json_body(self):
        try:
            raise RuntimeError("internal detail that must not leak")
        except RuntimeError as error:
            with self.app.test_request_context("/api/chat", method="POST"):
                response, status = self.api.handle_unexpected_error(error)

        self.assertEqual(status, 500)
        data = response.get_json()
        self.assertEqual(data["error"], "server_error")
        self.assertNotIn("internal detail", data["response"])

    def test_chat_context_is_scoped_per_session(self):
        first = self.client.post(
            "/api/chat",
            json={"message": "I feel sad", "session_id": "phase2-context-a"},
        ).get_json()["response"]
        second = self.client.post(
            "/api/chat",
            json={"message": "I feel sad", "session_id": "phase2-context-a"},
        ).get_json()["response"]
        other_session = self.client.post(
            "/api/chat",
            json={"message": "I feel sad", "session_id": "phase2-context-b"},
        ).get_json()["response"]

        self.assertEqual(first.count("I'm here for you."), 1)
        self.assertEqual(second.count("I understand this is difficult for you."), 1)
        self.assertEqual(other_session.count("I'm here for you."), 1)

    def test_crisis_path_still_precedes_hardening(self):
        response = self.client.post(
            "/api/chat",
            json={"message": "I want to kill myself", "session_id": "phase2-crisis"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["intent"], "crisis")
        self.assertEqual(data["source"], "safety")


if __name__ == "__main__":
    unittest.main()
