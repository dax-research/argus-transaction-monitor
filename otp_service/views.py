from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from frontend_api.throttles import OtpVerifyThrottle
from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone
from transactions.models import Transaction
from users.models import User
from .models import TransactionOTP

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([OtpVerifyThrottle])
def verify_otp(request):
    txn_id = request.data.get("txn_id")
    entered_otp = request.data.get("otp")

    if not txn_id or not entered_otp:
        return Response({"error": "txn_id and otp required"}, status=HTTP_400_BAD_REQUEST)

    try:
        txn = Transaction.objects.get(txn_id=txn_id)
        otp_obj = txn.otp
    except Transaction.DoesNotExist:
        return Response({"error": "Transaction not found"}, status=HTTP_400_BAD_REQUEST)
    except TransactionOTP.DoesNotExist:
        return Response({"error": "OTP not generated for this transaction"}, status=HTTP_400_BAD_REQUEST)

    # Expiry check
    if otp_obj.is_expired():
        txn.status = "FAILED"
        txn.save()
        return Response({"status": "FAILED", "reason": "OTP expired"})

    # Attempt limit check
    if otp_obj.attempts >= TransactionOTP.MAX_ATTEMPTS:
        txn.status = "BLOCKED"
        txn.save()
        return Response({"status": "BLOCKED", "reason": "Too many attempts"})

    # Verify OTP
    if entered_otp == otp_obj.otp:
        # Use a DB transaction so balance deduction + status update are atomic
        with db_transaction.atomic():
            user = User.objects.select_for_update().get(pk=txn.user_id)

            # Guard: re-check balance hasn't dropped since OTP was issued
            if user.account_balance < float(txn.amount):
                txn.status = "FAILED"
                txn.failure_reason = "Insufficient balance at time of OTP verification"
                txn.save()
                return Response({
                    "status": "FAILED",
                    "reason": "Insufficient balance",
                    "balance": user.account_balance,
                })

            # Deduct balance
            user.account_balance = max(0, user.account_balance - float(txn.amount))
            user.save(update_fields=["account_balance"])

            # Approve transaction
            txn.status = "SUCCESS"
            txn.otp_verified = True
            txn.save()

            otp_obj.is_verified = True
            otp_obj.save()

        return Response({
            "status": "SUCCESS",
            "balance": user.account_balance,
        })

    else:
        otp_obj.attempts += 1
        otp_obj.save()

        remaining = TransactionOTP.MAX_ATTEMPTS - otp_obj.attempts
        if remaining <= 0:
            txn.status = "BLOCKED"
            txn.save()
            return Response({"status": "BLOCKED", "reason": "Too many incorrect attempts"})

        return Response({"status": "FAILED", "reason": "Incorrect OTP", "attempts_remaining": remaining})



@api_view(["GET"])
@permission_classes([AllowAny])
def debug_get_otp(request, txn_id):
    """
    DEBUG ONLY — returns the OTP for a given txn_id.
    Remove this endpoint before going to production!
    """
    if not settings.DEBUG:
        from rest_framework.status import HTTP_403_FORBIDDEN
        return Response({"error": "Not available in production"}, status=HTTP_403_FORBIDDEN)

    try:
        txn = Transaction.objects.get(txn_id=txn_id)
        otp_obj = txn.otp
    except Transaction.DoesNotExist:
        return Response({"error": "Transaction not found"}, status=HTTP_400_BAD_REQUEST)
    except TransactionOTP.DoesNotExist:
        return Response({"error": "No OTP for this transaction"}, status=HTTP_400_BAD_REQUEST)

    return Response({
        "txn_id": txn_id,
        "otp": otp_obj.otp,
        "is_expired": otp_obj.is_expired(),
        "is_verified": otp_obj.is_verified,
        "expires_at": otp_obj.expires_at,
    })