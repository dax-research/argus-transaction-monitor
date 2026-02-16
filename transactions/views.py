from django.apps import apps
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_503_SERVICE_UNAVAILABLE,
)
import pandas as pd


@api_view(["POST"])
def process_transaction(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=HTTP_401_UNAUTHORIZED)

    detector = apps.get_app_config("fraud_engine").detector
    if detector is None:
        return Response(
            {"error": "Fraud engine not available"},
            status=HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        amount = request.data["amount"]
        balance = request.data.get("balance", getattr(request.user, "account_balance", 0))
        device_type = request.data.get("device_type", "")
    except KeyError as e:
        return Response({"error": f"Missing field: {e}"}, status=HTTP_400_BAD_REQUEST)

    txn = {
        "Transaction_Amount": amount,
        "Account_Balance": balance,
        "Device_Type": device_type or "",
        "Timestamp": pd.Timestamp.now()
    }

    history_qs = request.user.transactions.values(
        "amount",
        "device_type",
        "created_at",
        "status"
    )
    history_df = pd.DataFrame(list(history_qs))
    if not history_df.empty:
        history_df = history_df.rename(columns={
            "amount": "Transaction_Amount",
            "device_type": "Device_Type",
            "created_at": "Timestamp"
        })

    risk, decision = detector.predict_fraud(txn, history_df)

    return Response({
        "risk": round(risk, 4),
        "decision": decision
    })
