"""
argus_transaction_monitor/oauth_jwt.py

Custom JWT access-token generator for django-oauth-toolkit.

DOT calls ACCESS_TOKEN_GENERATOR(request, client, scope) to produce the
access-token string. We return a signed JWT that encodes the user's identity,
role, and scope so the frontend can decode it client-side without an extra
/me API call.

The token is also stored in DOT's AccessToken table (the JWT string is the
"token" column), so introspection and revocation still work.
"""
import uuid
import time
import jwt
from django.conf import settings


def _get_signing_key() -> str:
    """Return the HMAC-SHA256 signing key (Django's SECRET_KEY is fine for dev)."""
    return settings.SECRET_KEY


def _user_claims(user) -> dict:
    """Extra claims we embed in the JWT payload."""
    role = "ANALYST" if user.is_staff else "AUDITOR"
    full_name = f"{user.first_name} {user.last_name}".strip() or user.username
    return {
        "sub":       str(user.pk),
        "email":     user.email,
        "full_name": full_name,
        "role":      role,
    }


def generate_jwt_token(request, client, scope) -> str:
    """
    Called by DOT to produce the access-token string.

    Parameters
    ----------
    request : django.http.HttpRequest
        The current HTTP request (the ROPC /o/token/ POST).
    client  : oauth2_provider.models.Application
        The OAuth2 client app.
    scope   : str
        Space-separated scope string granted to this token.

    Returns
    -------
    str
        A signed JWT that will be stored as the access token and sent to the
        client in the `access_token` field of the DOT response.
    """
    expire_seconds = getattr(settings, "OAUTH2_PROVIDER", {}).get(
        "ACCESS_TOKEN_EXPIRE_SECONDS", 8 * 3600
    )

    now = int(time.time())
    payload = {
        "jti":       str(uuid.uuid4()),
        "iat":       now,
        "exp":       now + expire_seconds,
        "iss":       "argus-transaction-monitor",
        "client_id": client.client_id,
        "scope":     scope,
    }

    # Attach user claims when we have a real user (password grant always does)
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        payload.update(_user_claims(user))

    return jwt.encode(payload, _get_signing_key(), algorithm="HS256")
