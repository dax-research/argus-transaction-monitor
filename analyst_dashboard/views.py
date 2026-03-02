from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from transactions.models import Transaction
from users.models import User


def _require_staff(request):
    """Returns a Response error if the user is not staff, else None."""
    if not request.user.is_staff:
        return Response({"error": "Staff access required"}, status=HTTP_403_FORBIDDEN)
    return None


@api_view(["GET"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def analyst_transactions(request):
    """
    GET /api/analyst/transactions/
    Returns all transactions (staff only), with optional filters:
      ?status=SUCCESS|BLOCKED|OTP_REQUIRED
      ?decision=ALLOW|CHALLENGE|DENY
      ?user_id=<user_id>
      ?page=1&page_size=30
    """
    err = _require_staff(request)
    if err:
        return err

    qs = Transaction.objects.select_related("user").order_by("-created_at")

    # Filters
    status_filter = request.query_params.get("status")
    decision_filter = request.query_params.get("decision")
    user_filter = request.query_params.get("user_id")

    if status_filter:
        qs = qs.filter(status=status_filter)
    if decision_filter:
        qs = qs.filter(fraud_decision=decision_filter)
    if user_filter:
        qs = qs.filter(user__user_id=user_filter)

    page = int(request.query_params.get("page", 1))
    page_size = min(int(request.query_params.get("page_size", 30)), 100)
    offset = (page - 1) * page_size

    total = qs.count()
    transactions = qs[offset: offset + page_size]

    results = []
    for txn in transactions:
        results.append({
            "txn_id": txn.txn_id,
            "user_id": txn.user.user_id,
            "amount": str(txn.amount),
            "currency": txn.currency,
            "status": txn.status,
            "fraud_decision": txn.fraud_decision,
            "risk_score": txn.risk_score,
            "device_type": txn.device_type,
            "city": txn.city,
            "payment_type": txn.payment_type,
            "otp_required": txn.otp_required,
            "otp_verified": txn.otp_verified,
            "is_flagged": txn.failure_reason == "ANALYST_FLAGGED",
            "created_at": txn.created_at.isoformat(),
        })

    return Response({
        "count": total,
        "page": page,
        "page_size": page_size,
        "results": results,
    })


@api_view(["POST"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def flag_transaction(request, txn_id):
    """
    POST /api/analyst/flag/<txn_id>/
    Allows a staff analyst to flag a transaction as fraudulent.
    Body: { "reason": "optional explanation" }
    """
    err = _require_staff(request)
    if err:
        return err

    try:
        txn = Transaction.objects.get(txn_id=txn_id)
    except Transaction.DoesNotExist:
        return Response({"error": "Transaction not found"}, status=HTTP_404_NOT_FOUND)

    reason = request.data.get("reason", "Manually flagged by analyst")
    txn.failure_reason = "ANALYST_FLAGGED"
    txn.status = "BLOCKED"
    txn.save(update_fields=["failure_reason", "status"])

    return Response({
        "txn_id": txn_id,
        "status": "BLOCKED",
        "flagged_reason": reason,
        "message": "Transaction flagged successfully.",
    })


@api_view(["GET"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def analyst_stats(request):
    """
    GET /api/analyst/stats/
    Returns aggregate stats for the analyst dashboard.
    """
    err = _require_staff(request)
    if err:
        return err

    total = Transaction.objects.count()
    success = Transaction.objects.filter(status="SUCCESS").count()
    blocked = Transaction.objects.filter(status="BLOCKED").count()
    otp_pending = Transaction.objects.filter(status="OTP_REQUIRED").count()
    flagged = Transaction.objects.filter(failure_reason="ANALYST_FLAGGED").count()

    # Risk score distribution buckets
    low_risk = Transaction.objects.filter(risk_score__lt=0.3).count()
    med_risk = Transaction.objects.filter(risk_score__gte=0.3, risk_score__lt=0.65).count()
    high_risk = Transaction.objects.filter(risk_score__gte=0.65).count()

    return Response({
        "total": total,
        "success": success,
        "blocked": blocked,
        "otp_pending": otp_pending,
        "flagged": flagged,
        "risk_distribution": {
            "low": low_risk,
            "medium": med_risk,
            "high": high_risk,
        }
    })
