"""
argus_transaction_monitor/oauth_validator.py

Custom OAuth2 validator for django-oauth-toolkit.

Two responsibilities:
1. validate_user()  — called by OAuthLib during the ROPC password grant to
   authenticate username+password via Django's auth backend. Sets
   oauthlib_request.user (a Django User) so the JWT generator can embed claims.

2. validate_bearer_token() — called on every protected API request to verify
   a JWT bearer token (signature + expiry) without a DB lookup.
"""
import jwt
import logging
from datetime import datetime, timezone

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User as DjangoUser
from oauth2_provider.oauth2_validators import OAuth2Validator

logger = logging.getLogger(__name__)


def _signing_key() -> str:
    return settings.SECRET_KEY


class ArgusOAuth2Validator(OAuth2Validator):
    """
    Extends the default DOT validator with:
    - JWT bearer validation (no DB lookup for access tokens)
    - Django-backed user authentication for the ROPC grant
    """

    # ── Password grant: user authentication ──────────────────────────────────

    def validate_user(self, username, password, client, request, *args, **kwargs):
        """
        Called by OAuthLib during the Resource Owner Password Credentials grant.
        Authenticates the user via Django's auth backend and, on success,
        attaches the Django User object to the oauthlib request so the JWT
        generator can embed user claims.
        """
        user = authenticate(username=username, password=password)
        if user is not None and user.is_active:
            request.user = user   # oauthlib Request — picked up by the JWT generator
            return True
        return False

    # ── Bearer token: JWT validation ─────────────────────────────────────────

    def validate_bearer_token(self, token, scopes, request):
        """
        Validate a JWT bearer token presented on a protected API endpoint.
        Returns True if the token is valid, and populates request.user with
        the corresponding Django User.
        """
        if not token:
            return False

        try:
            payload = jwt.decode(
                token,
                _signing_key(),
                algorithms=["HS256"],
                options={"verify_exp": True},
            )
        except jwt.ExpiredSignatureError:
            logger.debug("JWT token has expired.")
            return False
        except jwt.InvalidTokenError as exc:
            logger.debug("JWT token invalid: %s", exc)
            return False

        # Attach user to the DRF request
        user_id = payload.get("sub")
        if user_id:
            try:
                user = DjangoUser.objects.get(pk=user_id, is_active=True)
                request.user = user
            except DjangoUser.DoesNotExist:
                logger.debug("JWT sub=%s not found or inactive.", user_id)
                return False
        else:
            return False

        # Store decoded claims for downstream use
        request.access_token = payload  # type: ignore[assignment]

        # Scope validation
        token_scopes = set(payload.get("scope", "").split())
        for required_scope in (scopes or []):
            if required_scope not in token_scopes:
                logger.debug(
                    "Required scope %r not in token scopes %r.",
                    required_scope,
                    token_scopes,
                )
                return False

        return True

