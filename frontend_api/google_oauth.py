"""
frontend_api/google_oauth.py

Server-side Google id_token verifier.

The frontend uses the Google Identity Services (GIS) popup — the user
clicks "Sign in with Google", Google returns a signed JWT (id_token) to
the browser, the browser POSTs that id_token to our backend, and we
verify it here using Google's public keys.

No server-side redirect / client-secret is needed.
"""
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings


def verify_google_id_token(credential: str) -> dict:
    """
    Verify a Google id_token string and return its decoded claims.

    Parameters
    ----------
    credential : str
        The raw id_token JWT string sent by the frontend.

    Returns
    -------
    dict with keys: sub, email, name, given_name, family_name, picture, email_verified

    Raises
    ------
    ValueError  — token is invalid, expired, or the audience doesn't match
    """
    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    if not client_id:
        raise ValueError(
            "GOOGLE_OAUTH_CLIENT_ID is not configured in settings. "
            "Add it to your .env file and load it in settings.py."
        )

    # This makes an HTTPS call to Google's public-key endpoint to verify the
    # JWT signature. The request is cached by google-auth between calls.
    id_info = id_token.verify_oauth2_token(
        credential,
        google_requests.Request(),
        client_id,
    )

    if not id_info.get("email_verified"):
        raise ValueError("Google account email is not verified.")

    return {
        "sub":          id_info["sub"],          # unique Google account ID
        "email":        id_info["email"],
        "name":         id_info.get("name", ""),
        "given_name":   id_info.get("given_name", ""),
        "family_name":  id_info.get("family_name", ""),
        "picture":      id_info.get("picture", ""),
        "email_verified": id_info.get("email_verified", False),
    }
