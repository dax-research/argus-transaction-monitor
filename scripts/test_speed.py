import os
import sys
import django
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'argus_transaction_monitor.settings')
django.setup()

from transactions.models import Transaction
from frontend_api.views import explain_fraud_view
from django.apps import apps
import pandas as pd

fraud_engine_app = apps.get_app_config("fraud_engine")
detector = fraud_engine_app.detector

txns = Transaction.objects.all()[:90]

start = time.time()
for t in txns:
    txn_data = {
        "Transaction_Amount": float(t.amount),
        "Account_Balance": 10000.0,
        "Device_Type": "Browser",
        "Timestamp": t.created_at,
        "City": "USA",
        "Payment_Type": "CARD"
    }
    # detector.explain_transaction(txn_data, pd.DataFrame())
    # calling tree explainer takes ~20ms each?
    detector.explain_transaction(txn_data, pd.DataFrame())
    
print("Total time for 90 txns:", time.time() - start)
