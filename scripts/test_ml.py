import os
import sys
import django
import pandas as pd
from datetime import timedelta
from django.utils import timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'argus_transaction_monitor.settings')
django.setup()

from django.apps import apps
fraud_engine_app = apps.get_app_config("fraud_engine")
detector = getattr(fraud_engine_app, "detector", None)

hour = 23
now = timezone.now().replace(hour=hour, minute=0, second=0, microsecond=0)

history_records = []
for i in range(1, 6):
    history_records.append({
        "Transaction_Amount": 500.0,
        "Device_Type": "Browser",
        "Timestamp": now - timedelta(days=i),
        "City": "India",
        "Payment_Type": "CARD",
        "status": "SUCCESS"
    })
history_df = pd.DataFrame(history_records)

txn_data = {
    "Transaction_Amount": 10000.0,
    "Account_Balance": 20000.0,
    "Device_Type": "Browser",
    "Timestamp": pd.Timestamp(now),
    "City": "USA",
    "Payment_Type": "CARD"
}

print("Running detector...")
try:
    res = detector.predict_fraud(txn_data, history_df)
    print("Result:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
