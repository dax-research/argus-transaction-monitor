import joblib
import pandas as pd
import shap
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'argus_transaction_monitor.settings')
django.setup()

from django.conf import settings
MODEL_PATH = os.path.join(settings.BASE_DIR, "ml_assests", "argus_rf_model.joblib")
rf = joblib.load(MODEL_PATH)

X_pred = pd.DataFrame([{
    'Transaction_Amount': 10000.0,
    'Account_Balance': 20000.0,
    'Daily_Transaction_Count': 5,
    'Avg_Transaction_Amount_7d': 500.0,
    'Failed_Transaction_Count_7d': 0,
    'Is_Weekend': 0,
    'New_Device': 0,
    'Device_Type_Enc': 1
}])

explainer = shap.TreeExplainer(rf)
shap_values = explainer.shap_values(X_pred)

print(type(shap_values))
if isinstance(shap_values, list):
    print("List length:", len(shap_values))
    print("Shape of class 1:", shap_values[1].shape)
else:
    print("Array shape:", shap_values.shape)
