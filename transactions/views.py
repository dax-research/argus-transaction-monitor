from django.apps import apps
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_503_SERVICE_UNAVAILABLE
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import pandas as pd
import traceback
import random

from transactions.models import Transaction
from otp_service.models import TransactionOTP
from users.models import User  # custom user


def _normalize_fraud_output(raw_output):
    """
    Accept tuple/list/dict outputs from the fraud engine and normalize to:
    (risk_score: float, decision: str)
    """
    risk = None
    decision = None

    if isinstance(raw_output, (tuple, list)):
        if len(raw_output) >= 2:
            risk, decision = raw_output[0], raw_output[1]
    elif isinstance(raw_output, dict):
        risk = raw_output.get("risk", raw_output.get("score"))
        decision = raw_output.get("decision", raw_output.get("action"))
    else:
        raise ValueError(f"Unsupported fraud output type: {type(raw_output).__name__}")

    risk = float(risk)
    decision = str(decision).upper().strip()
    if decision not in {"ALLOW", "CHALLENGE", "DENY"}:
        decision = "CHALLENGE"

    return risk, decision


@api_view(["POST"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def process_transaction(request):
    try:
        # Map request.user to your custom User model
        try:
            user = User.objects.get(user_id=request.user.username)
        except User.DoesNotExist:
            return Response({"error": "Custom user not found"}, status=HTTP_401_UNAUTHORIZED)

        # Get fraud detector
        fraud_engine_app = apps.get_app_config("fraud_engine")
        detector = getattr(fraud_engine_app, "detector", None)
        if detector is None:
            return Response({"error": "Fraud engine not available"}, status=HTTP_503_SERVICE_UNAVAILABLE)

        # Request data
        try:
            amount = float(request.data.get("amount", 0))
            device_type = request.data.get("device_type", "")
            balance = float(request.data.get("balance", getattr(user, "account_balance", 0)))
            city = request.data.get("city", "")
            payment_type = request.data.get("payment_type", "")
        except (TypeError, ValueError):
            return Response({"error": "Invalid amount or balance"}, status=HTTP_400_BAD_REQUEST)

        # Validate balance — use actual DB balance, not client-sent value
        actual_balance = float(user.account_balance)
        if amount <= 0:
            return Response({"error": "Amount must be greater than zero"}, status=HTTP_400_BAD_REQUEST)
        if amount > actual_balance:
            return Response({
                "error": f"Insufficient balance. Your balance is ₹{actual_balance:,.2f} but you tried to send ₹{amount:,.2f}."
            }, status=HTTP_400_BAD_REQUEST)

        txn_data = {
            "Transaction_Amount": amount,
            "Account_Balance": actual_balance,
            "Device_Type": device_type,
            "Timestamp": pd.Timestamp(timezone.now())
        }

        # Transaction history — include city and payment_type for richer ML input
        history_qs = user.transactions.values(
            "amount", "device_type", "created_at", "status", "city", "payment_type"
        )
        history_df = pd.DataFrame(list(history_qs))
        if not history_df.empty:
            history_df = history_df.rename(columns={
                "amount": "Transaction_Amount",
                "device_type": "Device_Type",
                "created_at": "Timestamp",
                "city": "City",
                "payment_type": "Payment_Type",
            })

        # Save as INITIATED first so rule engine can query DB context (velocity, rapid txns, etc.)
        # Convert to Decimal to avoid Decimal+float type errors inside rule engine
        txn_obj = Transaction.objects.create(
            user=user,
            amount=Decimal(str(amount)),
            device_type=device_type,
            city=city or None,
            payment_type=payment_type or None,
            status="INITIATED",
        )

        # ── Step 1: Rule Engine ─────────────────────────────────────────────
        from transactions.fraud.evaluator import evaluate_rules
        rule_eval = evaluate_rules(txn_obj)
        hard_block = rule_eval["hard_block"]
        risk_boost = rule_eval["risk_boost"]

        # ── Step 2: ML Model (always run) ───────────────────────────────────
        try:
            raw_prediction = detector.predict_fraud(txn_data, history_df)
            ml_risk, _ = _normalize_fraud_output(raw_prediction)
        except Exception:
            traceback.print_exc()
            ml_risk = 0.85

        # ── Step 3: Combine ML risk + soft rule boost ────────────────────────
        # Hard-block rules override everything.
        # Soft rules only nudge the score upward — ALLOW may become CHALLENGE,
        # CHALLENGE may become DENY, but a 22% ML score won't jump to DENY
        # just because the user switched city.
        if hard_block:
            risk = min(1.0, ml_risk + risk_boost)
            decision = "DENY"
            txn_status = "BLOCKED"
            otp_required = False
            failure_reason = "Blocked by fraud rule"
        else:
            risk = min(1.0, ml_risk + risk_boost)
            if risk < 0.3:
                decision = "ALLOW"
                txn_status = "SUCCESS"
                otp_required = False
                failure_reason = None
            elif risk < 0.7:
                decision = "CHALLENGE"
                txn_status = "OTP_REQUIRED"
                otp_required = True
                failure_reason = None
            else:
                decision = "DENY"
                txn_status = "BLOCKED"
                otp_required = False
                failure_reason = "High risk score"

        txn_obj.status = txn_status
        txn_obj.fraud_decision = decision
        txn_obj.risk_score = risk
        txn_obj.otp_required = otp_required
        if failure_reason:
            txn_obj.failure_reason = failure_reason
        txn_obj.save()

        # Deduct balance on SUCCESS
        if decision == "ALLOW":
            user.account_balance = max(0, user.account_balance - amount)
            user.save(update_fields=["account_balance"])

        # Create OTP if needed
        if decision == "CHALLENGE":
            otp_code = str(random.randint(100000, 999999))
            TransactionOTP.objects.create(
                transaction=txn_obj,
                otp=otp_code,
                expires_at=timezone.now() + timedelta(minutes=5)
            )

        return Response({
            "risk": round(risk, 4),
            "decision": decision,
            "txn_id": txn_obj.txn_id,
            "status": txn_obj.status,
            "otp_required": decision == "CHALLENGE",
            "balance": user.account_balance,
            "message": (
                "Challenge detected. OTP generated for dummy app verification."
                if decision == "CHALLENGE"
                else "Transaction processed."
            ),
        })

    except Exception as e:
        traceback.print_exc()
        return Response({"error": f"Internal server error: {str(e)}"}, status=500)


@api_view(["GET"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def transaction_history(request):
    """Return paginated transaction history for the logged-in user."""
    try:
        user = User.objects.get(user_id=request.user.username)
    except User.DoesNotExist:
        return Response({"error": "Custom user not found"}, status=HTTP_401_UNAUTHORIZED)

    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))
    offset = (page - 1) * page_size

    qs = user.transactions.order_by("-created_at")
    total = qs.count()
    transactions = qs[offset: offset + page_size]

    results = []
    for txn in transactions:
        results.append({
            "txn_id": txn.txn_id,
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
            "created_at": txn.created_at.isoformat(),
        })

    return Response({
        "count": total,
        "page": page,
        "page_size": page_size,
        "results": results,
    })


@api_view(["GET"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def profile(request):
    """Return current user's profile and balance."""
    try:
        user = User.objects.get(user_id=request.user.username)
    except User.DoesNotExist:
        return Response({"error": "Custom user not found"}, status=HTTP_401_UNAUTHORIZED)

    return Response({
        "username": request.user.username,
        "account_balance": user.account_balance,
        "is_blocked": user.is_blocked,
        "member_since": user.created_at.isoformat(),
    })
