"""
frontend_api/throttles.py

Named DRF throttle classes for critical Argus endpoints.
Rates are configured in settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].

All anonymous throttles key by IP address.
AuthenticatedBurstThrottle keys by authenticated user ID.
"""
from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """
    Limits login attempts to prevent credential brute-forcing.
    Rate: settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login_anon']
    Default: 5/min per IP.
    """
    scope = "login_anon"

    def get_cache_key(self, request, view):
        # Always key by IP — even authenticated callers hitting /login/ should be rate-limited
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class RegisterRateThrottle(SimpleRateThrottle):
    """
    Limits account-registration attempts to prevent account-spam.
    Rate: settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['register_anon']
    Default: 3/min per IP.
    """
    scope = "register_anon"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class OtpVerifyThrottle(SimpleRateThrottle):
    """
    Limits OTP verification attempts to prevent OTP brute-forcing.
    Rate: settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['otp_verify']
    Default: 5/min per IP.
    """
    scope = "otp_verify"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class RefreshRateThrottle(SimpleRateThrottle):
    """
    Limits token-refresh calls.
    Rate: settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['refresh_anon']
    Default: 10/min per IP.
    """
    scope = "refresh_anon"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class GoogleAuthThrottle(SimpleRateThrottle):
    """
    Limits Google OAuth endpoint calls.
    Rate: settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['google_auth_anon']
    Default: 10/min per IP.
    """
    scope = "google_auth_anon"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class AuthenticatedBurstThrottle(UserRateThrottle):
    """
    Broad burst limit for all authenticated dashboard endpoints.
    Keys by user ID (not IP), so heavy users don't starve each other.
    Rate: settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['burst']
    Default: 60/min per user.
    """
    scope = "burst"
