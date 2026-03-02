from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from django.conf import settings
from django.utils import timezone
from transactions.models import Transaction
from .models import TransactionOTP

@api_view(["POST"])
@permission_classes([AllowAny])
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
        txn.status = "BLOCKED"
        txn.save()
        return Response({"status": "BLOCKED", "reason": "OTP expired"})

    # Verify OTP
    if entered_otp == otp_obj.otp:
        txn.status = "SUCCESS"
        txn.otp_verified = True
        txn.save()
        otp_obj.is_verified = True
        otp_obj.save()
        return Response({"status": "SUCCESS"})
    else:
        txn.status = "BLOCKED"
        txn.save()
        return Response({"status": "BLOCKED", "reason": "Incorrect OTP"})


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