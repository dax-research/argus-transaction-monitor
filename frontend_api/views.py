"""
frontend_api/views.py
All API endpoints needed by the frontend analyst dashboard.
"""
import json
import jwt as pyjwt
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User as DjangoUser
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from frontend_api.throttles import (
    LoginRateThrottle,
    RegisterRateThrottle,
    RefreshRateThrottle,
    GoogleAuthThrottle,
    AuthenticatedBurstThrottle,
)
from django.db.models import Count, Avg, Q

from transactions.models import Transaction
from frontend_api.models import Investigation
from frontend_api.google_oauth import verify_google_id_token


# ── OAuth2 helpers ──────────────────────────────────────────────────────
CLIENT_ID = "argus-frontend-client"
DEFAULT_SCOPE = "read write"


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload WITHOUT verifying signature (already verified upstream)."""
    try:
        return pyjwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_exp": False},   # expiry already enforced by DOT
        )
    except Exception:
        return {}


def _user_payload_from_jwt(token: str) -> dict:
    """Extract the {id, email, full_name, role} dict the frontend expects."""
    claims = _decode_jwt_payload(token)
    return {
        "id":        claims.get("sub"),
        "email":     claims.get("email", ""),
        "full_name": claims.get("full_name", ""),
        "role":      claims.get("role", "AUDITOR"),
    }


def _do_password_grant(request, username: str, password: str, scope: str = DEFAULT_SCOPE) -> dict:
    """
    Issue an OAuth2 JWT access + refresh token pair for the given user.

    We generate the JWT directly using our custom generator and create the
    DOT AccessToken / RefreshToken database records so that revocation and
    introspection still work.

    Returns: { "access_token": str, "refresh_token": str, "token_type": "Bearer",
                "expires_in": int, "scope": str }
    """
    import secrets
    from datetime import datetime, timedelta, timezone as dt_timezone
    from django.utils import timezone

    from oauth2_provider.models import Application, AccessToken, RefreshToken as OAuthRefreshToken
    from oauth2_provider.settings import oauth2_settings
    from argus_transaction_monitor.oauth_jwt import generate_jwt_token

    # Verify the application exists
    try:
        app = Application.objects.get(client_id=CLIENT_ID)
    except Application.DoesNotExist:
        raise ValueError(
            "OAuth2 application not configured. Run: python manage.py seed_oauth_app"
        )

    user = request.user  # already authenticated by the calling view

    # Generate the JWT access token string
    jwt_token = generate_jwt_token(request, app, scope)

    # Create (or update) the DOT AccessToken record storing the JWT string as the token
    expires = timezone.now() + timedelta(
        seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS
    )
    access_obj = AccessToken.objects.create(
        user=user,
        application=app,
        token=jwt_token,
        expires=expires,
        scope=scope,
    )

    # Create a DOT RefreshToken (opaque, random — used for rotation & revocation)
    refresh_token_str = secrets.token_urlsafe(40)
    OAuthRefreshToken.objects.create(
        user=user,
        application=app,
        token=refresh_token_str,
        access_token=access_obj,
    )

    return {
        "access_token":  jwt_token,
        "refresh_token": refresh_token_str,
        "token_type":    "Bearer",
        "expires_in":    oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS,
        "scope":         scope,
    }



def _legacy_user_payload(user) -> dict:
    """Fallback: build user payload from the Django user object directly."""
    role = "ANALYST" if user.is_staff else "AUDITOR"
    return {
        "id":        user.id,
        "email":     user.email,
        "full_name": f"{user.first_name} {user.last_name}".strip() or user.username,
        "role":      role,
    }

# ── AUTH ENDPOINTS ──────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
    """
    POST /api/auth/login/
    Body: { email, password }
    Returns: { access, refresh, user: { id, email, full_name, role } }

    Internally runs the OAuth2 Resource Owner Password Credentials grant
    against django-oauth-toolkit and returns a JWT access token.
    """
    email    = request.data.get("email", "").strip().lower()
    password = request.data.get("password", "")

    if not email or not password:
        return Response({"detail": "Email and password are required."}, status=400)

    # Look up username from email (Django auth needs username)
    try:
        django_user = DjangoUser.objects.get(email__iexact=email)
        username = django_user.username
    except DjangoUser.DoesNotExist:
        return Response({"detail": "Invalid credentials."}, status=401)

    if not django_user.is_active:
        return Response({"detail": "Account is disabled."}, status=401)

    # Attach user to request so the JWT generator can embed user claims
    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({"detail": "Invalid credentials."}, status=401)
    request.user = user

    try:
        token_data = _do_password_grant(request, username=username, password=password)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=401)

    access_token  = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")

    return Response({
        "access":  access_token,
        "refresh": refresh_token,
        "user":    _user_payload_from_jwt(access_token) or _legacy_user_payload(user),
    })


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([RegisterRateThrottle])
def register_view(request):
    """
    POST /api/auth/register/
    Body: { full_name, email, password, confirm_password, role }
    Returns: { access, refresh, user }

    In a realistic setup:
    - Auditors may self-register.
    - Analyst (staff) accounts must be provisioned by an administrator.
    """
    full_name = request.data.get("full_name", "").strip()
    email     = request.data.get("email", "").strip().lower()
    password  = request.data.get("password", "")
    confirm   = request.data.get("confirm_password", "")
    requested_role = request.data.get("role", "AUDITOR").upper()

    # Determine effective role:
    # - Self-service (not superuser): always AUDITOR
    # - Admins can explicitly choose ANALYST or AUDITOR
    is_admin = bool(request.user and request.user.is_authenticated and request.user.is_superuser)
    if is_admin:
        role = requested_role if requested_role in ("ANALYST", "AUDITOR") else "AUDITOR"
    else:
        role = "AUDITOR"

    errors = {}
    if not full_name:
        errors["full_name"] = ["Full name is required."]
    if not email:
        errors["email"] = ["Email is required."]
    elif DjangoUser.objects.filter(email__iexact=email).exists():
        errors["email"] = ["An account with this email already exists."]
    if not password:
        errors["password"] = ["Password is required."]
    elif len(password) < 8:
        errors["password"] = ["Password must be at least 8 characters."]
    elif password != confirm:
        errors["confirm_password"] = ["Passwords do not match."]
    if errors:
        return Response(errors, status=400)

    first_name, *rest = full_name.split(" ", 1)
    last_name = rest[0] if rest else ""

    # Derive unique username from email prefix
    username = email.split("@")[0]
    base, idx = username, 1
    while DjangoUser.objects.filter(username=username).exists():
        username = f"{base}{idx}"
        idx += 1

    user = DjangoUser.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_staff=(role == "ANALYST"),
    )

    # Authenticate and issue OAuth2 tokens immediately
    request.user = user
    try:
        token_data = _do_password_grant(request, username=username, password=password)
    except ValueError as exc:
        # User was created; return a minimal success without tokens
        return Response(
            {"detail": str(exc), "user": _legacy_user_payload(user)},
            status=201,
        )

    access_token  = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")

    return Response({
        "access":  access_token,
        "refresh": refresh_token,
        "user":    _user_payload_from_jwt(access_token) or _legacy_user_payload(user),
    }, status=201)


@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):  # logout tokens are consumed on use; no throttle required
    """
    POST /api/auth/logout/
    Body: { refresh }  (the refresh token string)
    Revokes the token via DOT's revocation endpoint.
    """
    refresh_token = request.data.get("refresh") or request.data.get("token")
    if refresh_token:
        try:
            from oauth2_provider.models import RefreshToken as OAuthRefreshToken
            rt = OAuthRefreshToken.objects.filter(token=refresh_token).first()
            if rt:
                rt.revoke()
        except Exception:
            pass  # best-effort revocation
    return Response({"detail": "Logged out."})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([RefreshRateThrottle])
def refresh_view(request):
    """
    POST /api/auth/refresh/
    Body: { refresh }
    Returns: { access }  — a new JWT access token.
    """
    refresh_token = request.data.get("refresh", "")
    if not refresh_token:
        return Response({"detail": "refresh token is required."}, status=400)

    from oauth2_provider.models import RefreshToken as OAuthRefreshToken
    from oauth2_provider.settings import oauth2_settings

    try:
        rt = OAuthRefreshToken.objects.select_related("application", "user").get(
            token=refresh_token, revoked__isnull=True
        )
    except OAuthRefreshToken.DoesNotExist:
        return Response({"detail": "Invalid or expired refresh token."}, status=401)

    # Generate a new access token using our custom JWT generator
    from argus_transaction_monitor.oauth_jwt import generate_jwt_token
    request.user = rt.user
    new_access = generate_jwt_token(request, rt.application, rt.access_token.scope)

    # Update the stored access token string
    rt.access_token.token = new_access
    rt.access_token.save(update_fields=["token"])

    # Rotate refresh token if configured
    if oauth2_settings.ROTATE_REFRESH_TOKEN:
        import secrets
        rt.token = secrets.token_urlsafe(40)
        rt.save(update_fields=["token"])

    return Response({"access": new_access, "refresh": rt.token})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([GoogleAuthThrottle])
def google_auth_view(request):
    """
    POST /api/auth/google/
    Body: { credential: "<Google id_token JWT>" }
    Returns: { access, refresh, user: { id, email, full_name, role } }

    The frontend uses the Google Identity Services (GIS) popup which returns
    a signed id_token. We verify it server-side, get-or-create a Django user,
    and issue the same Argus JWT/refresh-token pair as the password grant.
    """
    credential = request.data.get("credential", "").strip()
    requested_role = request.data.get("role", "AUDITOR").upper()
    if not credential:
        return Response({"detail": "Google credential (id_token) is required."}, status=400)

    # ── 1. Verify the id_token with Google ────────────────────────────────
    try:
        google_user = verify_google_id_token(credential)
    except ValueError as exc:
        return Response({"detail": f"Google token verification failed: {exc}"}, status=401)
    except Exception as exc:
        return Response({"detail": f"Unexpected error verifying Google token: {exc}"}, status=500)

    email      = google_user["email"].lower()
    given_name = google_user.get("given_name", "")
    family_name = google_user.get("family_name", "")
    full_name  = google_user.get("name", "").strip() or email.split("@")[0]

    # ── 2. Get or create the Django user ──────────────────────────────────
    user, created = DjangoUser.objects.get_or_create(
        email__iexact=email,
        defaults={"email": email},
    )

    if created:
        # Derive a unique username from the email prefix
        base_username = email.split("@")[0]
        username = base_username
        idx = 1
        while DjangoUser.objects.filter(username=username).exists():
            username = f"{base_username}{idx}"
            idx += 1

        user.username   = username
        user.first_name = given_name or full_name.split(" ")[0]
        user.last_name  = family_name or (" ".join(full_name.split(" ")[1:]) if " " in full_name else "")
        # Self-service Google sign-in always creates an AUDITOR account.
        # Analyst (staff) access must be granted separately by an admin.
        user.is_staff   = False
        user.set_unusable_password()   # Prevent password-based login
        user.save()
    elif not user.is_active:
        return Response({"detail": "Account is disabled."}, status=401)

    # ── 3. Issue Argus JWT + refresh token (same as password grant) ───────
    request.user = user
    try:
        token_data = _do_password_grant(request, username=user.username, password="")
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=500)

    access_token  = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")

    return Response({
        "access":  access_token,
        "refresh": refresh_token,
        "user":    _user_payload_from_jwt(access_token) or _legacy_user_payload(user),
    })


# ── DASHBOARD ENDPOINTS ────────────────────────────────────────────────────────

def _is_analyst_or_auditor(user):
    return user and user.is_authenticated


@api_view(["GET"])
@throttle_classes([AuthenticatedBurstThrottle])
def stats_view(request):
    """
    GET /api/dashboard/stats/
    Returns KPI counts and chart data the analyst dashboard expects.
    """
    if not _is_analyst_or_auditor(request.user):
        return Response({"detail": "Authentication required."}, status=401)

    txns = Transaction.objects.all()
    total = txns.count()

    # Map our statuses to frontend statuses
    blocked = txns.filter(status="BLOCKED").count()
    success = txns.filter(status="SUCCESS").count()
    otp = txns.filter(status="OTP_REQUIRED").count()
    initiated = txns.filter(status="INITIATED").count()

    # Frontend expects: total, flagged, high_risk, approved, open_investigations, fraud_rate, pending, rejected
    # Map: BLOCKED → flagged+rejected, OTP_REQUIRED → pending, SUCCESS → approved
    # High risk: risk_score >= 0.7
    high_risk = txns.filter(risk_score__gte=0.7).count()
    fraud_rate = round((blocked / total * 100), 1) if total else 0

    # Daily transactions for last 7 days
    today = timezone.now().date()
    daily = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = txns.filter(created_at__date=day).count()
        daily.append({"date": day.strftime("%b %d"), "count": count})

    # Risk distribution  LOW < 0.3, HIGH >= 0.7, OTP_REQUIRED 0.3-0.7
    low_risk = txns.filter(risk_score__lt=0.3).count()
    mid_risk = txns.filter(risk_score__gte=0.3, risk_score__lt=0.7).count()

    return Response({
        "total_transactions": total,
        "flagged": blocked,
        "high_risk": high_risk,
        "approved": success,
        "pending": otp + initiated,
        "rejected": blocked,
        "open_investigations": Investigation.objects.filter(status="OPEN").count(),
        "fraud_rate": fraud_rate,
        "risk_distribution": {
            "LOW": low_risk,
            "HIGH": high_risk,
            "OTP_REQUIRED": mid_risk,
        },
        "daily_transactions": daily,
    })


@api_view(["GET"])
@throttle_classes([AuthenticatedBurstThrottle])
def transactions_view(request):
    """
    GET /api/dashboard/transactions/?status=&risk_level=
    Returns list of transactions in the format dashboard_analyst.js expects.
    """
    if not _is_analyst_or_auditor(request.user):
        return Response({"detail": "Authentication required."}, status=401)

    txns = Transaction.objects.all().order_by("-created_at")

    # Filter by status (frontend uses PENDING/APPROVED/FLAGGED/REJECTED)
    status_filter = request.query_params.get("status", "")
    status_map = {
        "PENDING": ["OTP_REQUIRED", "INITIATED"],
        "APPROVED": ["SUCCESS"],
        "FLAGGED": ["BLOCKED"],
        "REJECTED": ["BLOCKED"],
    }
    if status_filter and status_filter in status_map:
        txns = txns.filter(status__in=status_map[status_filter])

    # Filter by risk_level
    risk_filter = request.query_params.get("risk_level", "")
    if risk_filter == "LOW":
        txns = txns.filter(risk_score__lt=0.3)
    elif risk_filter == "HIGH":
        txns = txns.filter(risk_score__gte=0.7)
    elif risk_filter == "OTP_REQUIRED":
        txns = txns.filter(risk_score__gte=0.3, risk_score__lt=0.7)

    def _frontend_status(t):
        if t.status == "SUCCESS":
            return "APPROVED"
        elif t.status in ("OTP_REQUIRED", "INITIATED"):
            return "PENDING"
        elif t.status == "BLOCKED":
            return "FLAGGED"
        return t.status

    def _risk_level(t):
        if t.risk_score is None:
            return "LOW"
        if t.risk_score >= 0.7:
            return "HIGH"
        elif t.risk_score >= 0.3:
            return "OTP_REQUIRED"
        return "LOW"

    results = []
    for t in txns[:200]:   # cap at 200 for performance
        results.append({
            "id": t.txn_id,
            "amount": float(t.amount),
            "merchant_name": t.payment_type or "—",
            "merchant_category": t.city or "—",
            "status": _frontend_status(t),
            "risk_level": _risk_level(t),
            "fraud_score": float(t.risk_score) if t.risk_score is not None else None,
            "created_at": t.created_at.isoformat(),
            "device_type": t.device_type,
            "fraud_decision": t.fraud_decision,
            "fraud_reason": t.failure_reason,
        })

    return Response(results)


@api_view(["GET"])
@throttle_classes([AuthenticatedBurstThrottle])
def investigations_view(request):
    """
    GET /api/dashboard/investigations/
    Auto-creates Investigation rows for blocked transactions and returns real DB data.
    """
    if not _is_analyst_or_auditor(request.user):
        return Response({"detail": "Authentication required."}, status=401)

    blocked = Transaction.objects.filter(status="BLOCKED").order_by("-created_at")[:50]

    # Auto-create investigation rows for any newly blocked transactions
    for t in blocked:
        Investigation.objects.get_or_create(
            txn_id=t.txn_id,
            defaults={
                "notes": t.failure_reason or "Blocked by fraud engine",
                "status": "OPEN",
            }
        )

    # Return real investigation records
    investigations = Investigation.objects.filter(
        txn_id__in=[t.txn_id for t in blocked]
    ).order_by("-created_at")

    results = []
    for inv in investigations:
        results.append({
            "id": inv.id,
            "transaction": inv.txn_id,
            "status": inv.status,
            "analyst_name": inv.analyst_name,
            "notes": inv.notes,
            "resolution": inv.resolution,
            "created_at": inv.created_at.isoformat(),
        })
    return Response(results)


@api_view(["PATCH"])
@throttle_classes([AuthenticatedBurstThrottle])
def investigation_update_view(request, pk):
    """PATCH /api/dashboard/investigations/<pk>/ — persist status, notes, resolution."""
    if not _is_analyst_or_auditor(request.user):
        return Response({"detail": "Authentication required."}, status=401)

    try:
        inv = Investigation.objects.get(pk=pk)
    except Investigation.DoesNotExist:
        return Response({"detail": "Investigation not found."}, status=404)

    if "status" in request.data:
        inv.status = request.data["status"]
    if "notes" in request.data:
        inv.notes = request.data["notes"]
    if "resolution" in request.data:
        inv.resolution = request.data["resolution"]
    if request.user and request.user.is_authenticated:
        full_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
        inv.analyst_name = full_name

    inv.save()

    return Response({
        "id": inv.id,
        "transaction": inv.txn_id,
        "status": inv.status,
        "notes": inv.notes,
        "resolution": inv.resolution,
        "analyst_name": inv.analyst_name,
    })


@api_view(["GET"])
@throttle_classes([AuthenticatedBurstThrottle])
def audit_log_view(request):
    """
    GET /api/dashboard/audit-log/
    Returns recent transaction events as an audit trail.
    """
    if not _is_analyst_or_auditor(request.user):
        return Response({"detail": "Authentication required."}, status=401)

    recent = Transaction.objects.all().order_by("-created_at")[:100]
    results = []
    for t in recent:
        results.append({
            "timestamp": t.created_at.isoformat(),
            "actor_name": str(t.user) if t.user else "System",
            "action": t.fraud_decision or t.status,
            "entity_type": "Transaction",
            "entity_id": t.txn_id,
            "detail": f"Amount: \u20b9{t.amount} | Risk: {round(float(t.risk_score or 0)*100)}% | {t.failure_reason or 'OK'}",
        })
    return Response(results)


@api_view(["POST"])
@throttle_classes([AuthenticatedBurstThrottle])
def flag_transaction_view(request, txn_id):
    """
    POST /api/dashboard/transactions/<txn_id>/flag/
    Manually flag a transaction for investigation.

    Called by:
    - Analysts from the analyst dashboard (Flag button)
    - Auditors from the auditor dashboard ("Report suspicious" action)

    Creates an Investigation row (status=OPEN) if none exists, and records
    who flagged it and an optional message:
      - Analysts → "ANALYST_FLAGGED: <note>"
      - Auditors → "AUDITOR_FLAGGED: <note>"
    """
    if not _is_analyst_or_auditor(request.user):
        return Response({"detail": "Authentication required."}, status=401)

    try:
        Transaction.objects.get(txn_id=txn_id)
    except Transaction.DoesNotExist:
        return Response({"detail": "Transaction not found."}, status=404)

    analyst = ""
    if request.user and request.user.is_authenticated:
        analyst = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username

    # Determine who is flagging and build note
    is_analyst = bool(request.user and request.user.is_authenticated and request.user.is_staff)
    base_tag = "ANALYST_FLAGGED" if is_analyst else "AUDITOR_FLAGGED"
    note_text = (request.data.get("note") or "").strip()
    new_entry = f"{base_tag}: {note_text}" if note_text else base_tag

    inv, created = Investigation.objects.get_or_create(
        txn_id=txn_id,
        defaults={
            "notes": new_entry,
            "status": "OPEN",
            "analyst_name": analyst or "Unassigned",
        }
    )
    if not created:
        # Append a new line with the latest flag details
        existing = (inv.notes or "").strip()
        inv.notes = (existing + "\n\n" + new_entry) if existing else new_entry
        if is_analyst:
            inv.analyst_name = analyst or inv.analyst_name
        inv.save(update_fields=["notes", "analyst_name"])

    return Response({
        "id": inv.id,
        "txn_id": txn_id,
        "status": inv.status,
        "flagged": True,
    }, status=201 if created else 200)

@api_view(["POST"])
@throttle_classes([AuthenticatedBurstThrottle])
def simulate_fraud_view(request):
    """
    POST /simulate
    Input JSON: { "amount": float, "location": "string", "hour": int }
    Returns: { "probability": float, "risk_level": "LOW" | "MEDIUM" | "HIGH" }
    """
    if not _is_analyst_or_auditor(request.user):
        return Response({"detail": "Authentication required."}, status=401)

    try:
        amount = float(request.data.get("amount", 0))
        location = str(request.data.get("location", "")).strip()
        hour = int(request.data.get("hour", 0))
    except (ValueError, TypeError):
        return Response({"error": "Invalid input format"}, status=400)

    from django.apps import apps
    import pandas as pd
    from django.utils import timezone
    from datetime import timedelta
    from transactions.views import _normalize_fraud_output

    fraud_engine_app = apps.get_app_config("fraud_engine")
    detector = getattr(fraud_engine_app, "detector", None)

    if detector is None:
        return Response({"error": "ML model not available"}, status=503)

    # ── 1. Create Mock Environment ──────────────────────────────────────────
    now = timezone.now().replace(hour=hour, minute=0, second=0, microsecond=0)
    
    # Fake user history of 5 small, successful transactions in India.
    # This provides a baseline so the ML model can calculate averages
    # and recognize anomalous volume.
    history_records = []
    for i in range(1, 6):
        history_records.append({
            "Transaction_Amount": 500.0,
            "Device_Type": "Browser",
            "Timestamp": now - timedelta(days=i),
            "City": "India",
            "Payment_Type": "CARD",
            "status": "SUCCESS"
        })
    history_df = pd.DataFrame(history_records)

    txn_data = {
        "Transaction_Amount": amount,
        "Account_Balance": 20000.0,
        "Device_Type": "Browser",
        "Timestamp": pd.Timestamp(now),
        "City": location,
        "Payment_Type": "CARD"
    }

    # ── 2. Run ML Model ─────────────────────────────────────────────────────
    try:
        raw_prediction = detector.predict_fraud(txn_data, history_df)
        ml_risk, _ = _normalize_fraud_output(raw_prediction)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"error": f"ML Model error: {str(e)}"}, status=500)

    # ── 3. Apply Rule-based Boosts (from evaluator.py) ──────────────────────
    risk_boost = 0.0
    
    # Location anomaly boost (+0.35)
    if location.lower() != "india":
        risk_boost += 0.35
        
    # High Amount Hard Block rule -> caps at 100%
    if amount >= 100000:
        ml_risk = 1.0

    probability = min(ml_risk + risk_boost, 1.0)

    # ── 4. Risk Thresholds ──────────────────────────────────────────────────
    if probability < 0.3:
        risk_level = "LOW"
    elif probability <= 0.7:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    return Response({
        "probability": round(probability, 3),
        "risk_level": risk_level
    })


@api_view(["POST"])
@throttle_classes([AuthenticatedBurstThrottle])
def explain_fraud_view(request):
    """
    POST /explain/
    Returns human readable SHAP descriptions of what caused the score.
    """
    if not _is_analyst_or_auditor(request.user):
        return Response({"detail": "Authentication required."}, status=401)

    try:
        amount = float(request.data.get("amount", 0))
        location = str(request.data.get("location", "")).strip()
        hour = int(request.data.get("hour", 0))
    except (ValueError, TypeError):
        return Response({"error": "Invalid input format"}, status=400)

    from django.apps import apps
    import pandas as pd
    from django.utils import timezone
    from datetime import timedelta
    from transactions.views import _normalize_fraud_output

    fraud_engine_app = apps.get_app_config("fraud_engine")
    detector = getattr(fraud_engine_app, "detector", None)
    if detector is None:
        return Response({"error": "ML model not available"}, status=503)

    now = timezone.now().replace(hour=hour, minute=0, second=0, microsecond=0)
    
    history_records = []
    for i in range(1, 6):
        history_records.append({
            "Transaction_Amount": 500.0,
            "Device_Type": "Browser",
            "Timestamp": now - timedelta(days=i),
            "City": "India",
            "Payment_Type": "CARD",
            "status": "SUCCESS"
        })
    history_df = pd.DataFrame(history_records)

    txn_data = {
        "Transaction_Amount": amount,
        "Account_Balance": 20000.0,
        "Device_Type": "Browser",
        "Timestamp": pd.Timestamp(now),
        "City": location,
        "Payment_Type": "CARD"
    }

    try:
        raw_prediction = detector.predict_fraud(txn_data, history_df)
        ml_risk, _ = _normalize_fraud_output(raw_prediction)
        
        # SHAP
        ml_impacts = detector.explain_transaction(txn_data, history_df)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"error": f"ML Model error: {str(e)}"}, status=500)

    # Manual Rule Boosts (mirroring simulate_fraud_view behavior)
    location_boost = 0.0
    if location.lower() != "india":
        location_boost = 0.35
        
    ml_risk_override = False
    if amount >= 100000:
        ml_risk_override = True

    probability = min(ml_risk + location_boost if not ml_risk_override else 1.0, 1.0)

    impact_dict = {}
    for imp in ml_impacts:
        name = imp["feature"]
        score = imp["impact"]
        if name == "Transaction_Amount":
            impact_dict["amount"] = score
            if ml_risk_override:
                impact_dict["amount"] += 1.0  # Force to top
        elif name == "Is_Weekend":
            impact_dict["time"] = score
        elif name == "New_Device":
            impact_dict["device"] = score
        elif name == "Daily_Transaction_Count":
            impact_dict["frequency"] = score
        else:
            impact_dict[name.lower()] = score

    if location_boost > 0:
        impact_dict["location"] = impact_dict.get("location", 0) + location_boost

    sorted_features = sorted([{"feature": k, "impact": v} for k, v in impact_dict.items()], 
                             key=lambda x: abs(x["impact"]), reverse=True)[:3]

    text_mapping = {
        "amount": "Transaction amount is unusually high",
        "location": "Transaction from unfamiliar location",
        "time": "Transaction at unusual time",
        "device": "Transaction from a new unrecognized device",
        "frequency": "Unusual transaction frequency",
    }

    reasons = []
    for f in sorted_features:
        if f["impact"] > 0:
            reason = text_mapping.get(f["feature"], f"Unusual {f['feature']} pattern")
            reasons.append(reason)
            
    if not reasons:
        explanation = "Transaction pattern matches normal behavior."
    else:
        # Lowercase starting character for inline joining
        formatted_reasons = []
        for r in reasons:
            txt = r.lower()
            if txt.startswith("transaction"):
                txt = txt.replace("transaction", "", 1).strip()
            formatted_reasons.append(txt)
            
        if len(formatted_reasons) == 1:
            explanation = f"Transaction flagged because {formatted_reasons[0]}."
        elif len(formatted_reasons) == 2:
            explanation = f"Transaction flagged because {formatted_reasons[0]} and {formatted_reasons[1]}."
        else:
            explanation = f"Transaction flagged because {formatted_reasons[0]}, {formatted_reasons[1]}, and {formatted_reasons[2]}."

    if probability < 0.3:
        risk_level = "LOW"
    elif probability < 0.7:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    return Response({
        "probability": round(probability, 3),
        "risk_level": risk_level,
        "top_features": sorted_features,
        "explanation": explanation
    })
