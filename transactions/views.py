# from django.apps import apps
# from rest_framework.decorators import api_view
# from rest_framework.response import Response
# from rest_framework.status import (
#     HTTP_400_BAD_REQUEST,
#     HTTP_401_UNAUTHORIZED,
#     HTTP_503_SERVICE_UNAVAILABLE,
# )
# import pandas as pd


# @api_view(["POST"])
# def process_transaction(request):
#     if not request.user.is_authenticated:
#         return Response({"error": "Authentication required"}, status=HTTP_401_UNAUTHORIZED)

#     detector = apps.get_app_config("fraud_engine").detector
#     if detector is None:
#         return Response(
#             {"error": "Fraud engine not available"},
#             status=HTTP_503_SERVICE_UNAVAILABLE,
#         )

#     try:
#         amount = request.data["amount"]
#         balance = request.data.get("balance", getattr(request.user, "account_balance", 0))
#         device_type = request.data.get("device_type", "")
#     except KeyError as e:
#         return Response({"error": f"Missing field: {e}"}, status=HTTP_400_BAD_REQUEST)

#     txn = {
#         "Transaction_Amount": amount,
#         "Account_Balance": balance,
#         "Device_Type": device_type or "",
#         "Timestamp": pd.Timestamp.now()
#     }

#     history_qs = request.user.transactions.values(
#         "amount",
#         "device_type",
#         "created_at",
#         "status"
#     )
#     history_df = pd.DataFrame(list(history_qs))
#     if not history_df.empty:
#         history_df = history_df.rename(columns={
#             "amount": "Transaction_Amount",
#             "device_type": "Device_Type",
#             "created_at": "Timestamp"
#         })

#     risk, decision = detector.predict_fraud(txn, history_df)

#     return Response({
#         "risk": round(risk, 4),
#         "decision": decision
#     })
# mainproject/transactions/views.py
from django.apps import apps
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_503_SERVICE_UNAVAILABLE
from django.utils import timezone
from datetime import timedelta
import pandas as pd
import traceback
import random

from transactions.models import Transaction
from otp_service.models import TransactionOTP
from users.models import User  # custom user

@api_view(["POST"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def process_transaction(request):
    try:
        # Map request.user to your custom User model
        try:
            user = User.objects.get(user_id=request.user.username)  # assuming token username = user_id
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
        except (TypeError, ValueError):
            return Response({"error": "Invalid amount or balance"}, status=HTTP_400_BAD_REQUEST)

        txn_data = {
            "Transaction_Amount": amount,
            "Account_Balance": balance,
            "Device_Type": device_type,
            "Timestamp": pd.Timestamp(timezone.now())
        }

        # Transaction history
        history_qs = user.transactions.values("amount", "device_type", "created_at", "status")
        history_df = pd.DataFrame(list(history_qs))
        if not history_df.empty:
            history_df = history_df.rename(columns={
                "amount": "Transaction_Amount",
                "device_type": "Device_Type",
                "created_at": "Timestamp"
            })

        # Predict fraud
        risk, decision = detector.predict_fraud(txn_data, history_df)

        # Save transaction
        txn_status = "PENDING" if decision == "CHALLENGE" else ("SUCCESS" if decision == "ALLOW" else "BLOCKED")
        txn_obj = Transaction.objects.create(
            user=user,
            amount=amount,
            device_type=device_type,
            status=txn_status
        )

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
            "txn_id": txn_obj.txn_id
        })

    except Exception as e:
        traceback.print_exc()
        return Response({"error": f"Internal server error: {str(e)}"}, status=500)