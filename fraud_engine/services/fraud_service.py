from django.apps import apps


def evaluate_transaction(transaction, user_history):
    detector = apps.get_app_config("fraud_engine").detector
    if detector is None:
        raise RuntimeError("Fraud engine detector not initialized. Check that fraud_engine is in INSTALLED_APPS.")

    txn_data = {
        "Transaction_Amount": float(transaction.amount),
        "Account_Balance": getattr(transaction.user, "account_balance", 0.0) or 0.0,
        "Device_Type": (transaction.device_type or "").strip() or "Unknown",
        "Timestamp": transaction.created_at,
    }

    risk, decision = detector.predict_fraud(txn_data, user_history)
    return risk, decision
