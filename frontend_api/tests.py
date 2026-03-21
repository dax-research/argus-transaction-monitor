"""
frontend_api/tests.py

Tests for DRF API rate limiting (throttling) on critical Argus endpoints.

Strategy:
  - Use override_settings at the class level combining CACHES + REST_FRAMEWORK
    so both settings coexist in the same context.  Nesting them at different
    decorator levels (class vs method) caused the wrong cache backend to be
    active when the throttle checked its rate, which is why tests were failing.
  - Tight per-scope rates (2–3/min) so we hit the limit in milliseconds,
    not after a real clock-minute waits.
  - Each class uses a unique LOCATION string for its LocMemCache so throttle
    history does not bleed between test classes.
"""
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status


# ── Shared throttle rate overrides ───────────────────────────────────────────
_TIGHT_RATES = {
    "login_anon":       "3/min",
    "register_anon":    "2/min",
    "otp_verify":       "3/min",
    "refresh_anon":     "10/min",
    "google_auth_anon": "10/min",
    "burst":            "60/min",
    "anon":             "100/min",
    "user":             "1000/min",
}

_BASE_DRF = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": _TIGHT_RATES,
}


def _fresh_cache(location: str) -> dict:
    """Return a CACHES dict backed by a named LocMemCache at the given location."""
    return {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": location,
        }
    }


# ── Login throttle ────────────────────────────────────────────────────────────
@override_settings(CACHES=_fresh_cache("test-login"), REST_FRAMEWORK=_BASE_DRF)
class LoginThrottleTests(APITestCase):
    """
    POST /api/auth/login/ is limited to 3/min (in tests) per IP.
    Requests 1–3 should pass (returning 401 for bad credentials);
    request 4 should return HTTP 429.
    """

    URL = "/api/auth/login/"

    def _post(self):
        return self.client.post(
            self.URL,
            {"email": "nobody@example.com", "password": "wrongpassword"},
            format="json",
        )

    def test_login_throttle_triggers(self):
        """After exceeding the login throttle limit, the server returns 429."""
        for i in range(3):
            resp = self._post()
            self.assertNotEqual(
                resp.status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
                msg=f"Request {i + 1} was unexpectedly throttled.",
            )
        # 4th request must be throttled
        resp = self._post()
        self.assertEqual(
            resp.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
            msg=f"Expected 429 on 4th login attempt, got {resp.status_code}.",
        )

    def test_throttled_response_has_retry_after(self):
        """The 429 response must include a Retry-After header."""
        for _ in range(4):
            resp = self._post()
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn(
            "Retry-After", resp,
            msg="HTTP 429 response is missing the Retry-After header.",
        )


# ── Register throttle ─────────────────────────────────────────────────────────
@override_settings(CACHES=_fresh_cache("test-register"), REST_FRAMEWORK=_BASE_DRF)
class RegisterThrottleTests(APITestCase):
    """
    POST /api/auth/register/ is limited to 2/min (in tests) per IP.
    Requests 1–2 may succeed or fail for business reasons; request 3 → 429.
    """

    URL = "/api/auth/register/"

    def _post(self, suffix: str):
        return self.client.post(
            self.URL,
            {
                "full_name": "Test User",
                "email": f"throttletest{suffix}@example.com",
                "password": "TestPass1234",
                "confirm_password": "TestPass1234",
            },
            format="json",
        )

    def test_register_throttle_triggers(self):
        """After exceeding the register throttle limit, the server returns 429."""
        for i in range(2):
            resp = self._post(suffix=str(i))
            self.assertNotEqual(
                resp.status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
                msg=f"Request {i + 1} was unexpectedly throttled.",
            )
        # 3rd request must be throttled
        resp = self._post(suffix="extra")
        self.assertEqual(
            resp.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
            msg=f"Expected 429 on 3rd register attempt, got {resp.status_code}.",
        )


# ── OTP verify throttle ───────────────────────────────────────────────────────
@override_settings(CACHES=_fresh_cache("test-otp"), REST_FRAMEWORK=_BASE_DRF)
class OtpVerifyThrottleTests(APITestCase):
    """
    POST /api/verify-otp/ is limited to 3/min (in tests) per IP.
    Requests 1–3 get 400 (invalid txn_id); request 4 → 429.
    """

    URL = "/api/verify-otp/"

    def _post(self):
        return self.client.post(
            self.URL,
            {"txn_id": "TXN-FAKE-0000", "otp": "000000"},
            format="json",
        )

    def test_otp_verify_throttle_triggers(self):
        """After exceeding OTP verify throttle limit, the server returns 429."""
        for i in range(3):
            resp = self._post()
            self.assertNotEqual(
                resp.status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
                msg=f"Request {i + 1} was unexpectedly throttled.",
            )
        # 4th request must be throttled
        resp = self._post()
        self.assertEqual(
            resp.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
            msg=f"Expected 429 on 4th OTP attempt, got {resp.status_code}.",
        )
