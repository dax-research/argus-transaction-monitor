import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'argus_transaction_monitor.settings')
django.setup()

import pandas as pd
from transactions.models import Transaction
from django.apps import apps

fraud_engine_app = apps.get_app_config("fraud_engine")
detector = fraud_engine_app.detector

def generate_explanation(t):
    txn_data = {
        "Transaction_Amount": float(t.amount),
        "Account_Balance": 10000.0, # dummy context
        "Device_Type": t.device_type or "Mobile",
        "Timestamp": pd.Timestamp(t.created_at),
        "City": t.city or "India",
        "Payment_Type": t.payment_type or "CARD"
    }
    
    try:
        from frontend_api.views import _normalize_fraud_output
        raw_prediction = detector.predict_fraud(txn_data, pd.DataFrame())
        ml_risk, _ = _normalize_fraud_output(raw_prediction)
        ml_impacts = detector.explain_transaction(txn_data, pd.DataFrame())
    except Exception as e:
        return "Explanation unavailable."

    location = (t.city or "India").lower()
    location_boost = 0.0
    if location != "india":
        location_boost = 0.35
        
    ml_risk_override = False
    if float(t.amount) >= 100000:
        ml_risk_override = True

    impact_dict = {}
    for imp in ml_impacts:
        name = imp["feature"]
        score = imp["impact"]
        if name == "Transaction_Amount":
            impact_dict["amount"] = score
            if ml_risk_override:
                impact_dict["amount"] += 1.0
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
        if t.status == "SUCCESS":
            return "Transaction pattern matches normal behavior."
        return "Transaction flagged by manual rules."
    else:
        formatted_reasons = []
        for r in reasons:
            txt = r.lower()
            if txt.startswith("transaction"):
                txt = txt.replace("transaction", "", 1).strip()
            formatted_reasons.append(txt)
            
        if len(formatted_reasons) == 1:
            explanation = f"Flagged because {formatted_reasons[0]}."
        elif len(formatted_reasons) == 2:
            explanation = f"Flagged because {formatted_reasons[0]} and {formatted_reasons[1]}."
        else:
            explanation = f"Flagged because {formatted_reasons[0]}, {formatted_reasons[1]}, and {formatted_reasons[2]}."
        return explanation

txns = Transaction.objects.all()
for txn in txns:
    if txn.failure_reason in [None, "", "High risk score"]:
        txn.failure_reason = generate_explanation(txn)
        txn.save(update_fields=['failure_reason'])
print("Backfill complete.")
