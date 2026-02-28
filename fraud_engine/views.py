from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from transactions.models import Transaction


@api_view(["POST"])
def verify_otp(request):

    txn_id = request.data.get("txn_id")
    entered_otp = request.data.get("otp")

    if not txn_id or not entered_otp:
        return Response(
            {"error": "txn_id and otp required"},
            status=HTTP_400_BAD_REQUEST
        )

    try:
        txn = Transaction.objects.get(txn_id=txn_id)
    except Transaction.DoesNotExist:
        return Response(
            {"error": "Transaction not found"},
            status=HTTP_400_BAD_REQUEST
        )

    if not txn.otp_required:
        return Response({"error": "OTP not required"})

    if txn.otp == entered_otp:
        txn.status = "SUCCESS"
        txn.otp_required = False
        txn.save()

        return Response({"status": "SUCCESS"})

    else:
        txn.status = "BLOCKED"
        txn.save()

        return Response({"status": "BLOCKED"})