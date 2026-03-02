"""
frontend_api/views.py
All API endpoints needed by the frontend analyst dashboard.
"""
from django.contrib.auth import authenticate
from django.contrib.auth.models import User as DjangoUser
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import BasicAuthentication
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.db.models import Count, Avg, Q

from transactions.models import Transaction
from frontend_api.models import Investigation


# ── Helpers ────────────────────────────────────────────────────────────────────

def _user_payload(user):
    """Return the minimal user dict the frontend expects."""
    role = "ANALYST" if user.is_staff else "AUDITOR"
    return {
        "id": user.id,
        "email": user.email,
        "full_name": f"{user.first_name} {user.last_name}".strip() or user.username,
        "role": role,
    }


def _tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": _user_payload(user),
    }


# ── AUTH ENDPOINTS ─────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """
    POST /api/auth/login/
    Body: { email, password }
    Returns: { access, refresh, user: { id, email, full_name, role } }
    """
    email = request.data.get("email", "").strip().lower()
    password = request.data.get("password", "")

    if not email or not password:
        return Response({"detail": "Email and password are required."}, status=400)

    # Django auth uses username; look up by email
    try:
        django_user = DjangoUser.objects.get(email__iexact=email)
        username = django_user.username
    except DjangoUser.DoesNotExist:
        return Response({"detail": "Invalid credentials."}, status=401)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({"detail": "Invalid credentials."}, status=401)
    if not user.is_active:
        return Response({"detail": "Account is disabled."}, status=401)

    return Response(_tokens_for(user))


@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    """
    POST /api/auth/register/
    Body: { full_name, email, password, confirm_password, role }
    Returns: { access, refresh, user }
    """
    full_name = request.data.get("full_name", "").strip()
    email = request.data.get("email", "").strip().lower()
    password = request.data.get("password", "")
    confirm = request.data.get("confirm_password", "")
    role = request.data.get("role", "AUDITOR").upper()

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

    # Use email as username (unique)
    username = email.split("@")[0]
    base = username
    idx = 1
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

    return Response(_tokens_for(user), status=201)


@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):
    """POST /api/auth/logout/ — blacklist the refresh token if provided."""
    refresh_token = request.data.get("refresh")
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass
    return Response({"detail": "Logged out."})


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_view(request):
    """
    POST /api/auth/refresh/
    Body: { refresh }
    Returns: { access }
    """
    from rest_framework_simplejwt.serializers import TokenRefreshSerializer
    serializer = TokenRefreshSerializer(data=request.data)
    try:
        serializer.is_valid(raise_exception=True)
    except (TokenError, InvalidToken) as e:
        return Response({"detail": str(e)}, status=401)
    return Response(serializer.validated_data)


# ── DASHBOARD ENDPOINTS ────────────────────────────────────────────────────────

def _is_analyst_or_auditor(user):
    return user and user.is_authenticated


@api_view(["GET"])
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
        })

    return Response(results)


@api_view(["GET"])
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
def flag_transaction_view(request, txn_id):
    """
    POST /api/dashboard/transactions/<txn_id>/flag/
    Manually flag a transaction for investigation.
    Creates an Investigation row (status=OPEN) if none exists,
    or marks an existing one as ANALYST_FLAGGED.
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

    inv, created = Investigation.objects.get_or_create(
        txn_id=txn_id,
        defaults={
            "notes": "ANALYST_FLAGGED",
            "status": "OPEN",
            "analyst_name": analyst or "Unassigned",
        }
    )
    if not created:
        inv.notes = "ANALYST_FLAGGED"
        inv.analyst_name = analyst or inv.analyst_name
        inv.save(update_fields=["notes", "analyst_name"])

    return Response({
        "id": inv.id,
        "txn_id": txn_id,
        "status": inv.status,
        "flagged": True,
    }, status=201 if created else 200)
