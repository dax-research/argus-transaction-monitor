"""
retrain_models.py  (v2 — uses pre-computed features from CSV directly)
Retrain RF + XGBoost + Meta-LR models using local library versions.
Run: python retrain_models.py
"""
import os, warnings
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import roc_auc_score, classification_report
from xgboost import XGBClassifier
import joblib

warnings.filterwarnings("ignore")

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "ml_assests")

MODEL_PATH   = os.path.join(ASSETS_DIR, "argus_rf_model.joblib")
XGB_PATH     = os.path.join(ASSETS_DIR, "argus_xgb_model.joblib")
ENCODER_PATH = os.path.join(ASSETS_DIR, "argus_encoder.joblib")
META_PATH    = os.path.join(ASSETS_DIR, "argus_meta_lr_model.joblib")
DATASET_PATH = os.path.join(BASE_DIR, "Fraud_dataset.csv")

FEATURE_COLS = [
    "Transaction_Amount", "Account_Balance", "Daily_Transaction_Count",
    "Avg_Transaction_Amount_7d", "Failed_Transaction_Count_7d",
    "Is_Weekend", "New_Device", "Device_Type_Enc",
]

# ── 1. Load ───────────────────────────────────────────────────────────────────
print("Loading dataset...")
df = pd.read_csv(DATASET_PATH)
print(f"  Shape: {df.shape}")
print(f"  Columns: {list(df.columns)}")
print(f"  Fraud_Label: {df['Fraud_Label'].value_counts().to_dict()}")

# ── 2. Encode Device_Type ─────────────────────────────────────────────────────
print("\nEncoding Device_Type...")
df["Device_Type"] = df["Device_Type"].astype(str).str.strip()
le = LabelEncoder()
df["Device_Type_Enc"] = le.fit_transform(df["Device_Type"])
print(f"  Known device classes: {list(le.classes_)}")
joblib.dump(le, ENCODER_PATH)
print(f"  Saved encoder -> {ENCODER_PATH}")

# ── 3. Compute Is_Weekend if not present ──────────────────────────────────────
if "Is_Weekend" not in df.columns:
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df["Is_Weekend"] = (df["Timestamp"].dt.dayofweek >= 5).astype(int)

# ── 4. Compute New_Device if not present ──────────────────────────────────────
# 1 = this is the first time this user used this device type; 0 = seen before
if "New_Device" not in df.columns:
    print("  Computing New_Device per user...")
    if "User_ID" in df.columns:
        df = df.sort_values(["User_ID", "Timestamp"]).reset_index(drop=True) \
               if "Timestamp" in df.columns else df.sort_values("User_ID").reset_index(drop=True)
        # Mark first occurrence of each (user, device) pair as New_Device=1
        df["New_Device"] = (~df.duplicated(subset=["User_ID", "Device_Type_Enc"], keep="first")).astype(int)
    else:
        df["New_Device"] = 0  # No user info — assume all known

# ── 4. Verify all feature cols exist and fill nulls ───────────────────────────
missing = [c for c in FEATURE_COLS if c not in df.columns]
if missing:
    print(f"ERROR: Missing columns: {missing}")
    raise SystemExit(1)

X = df[FEATURE_COLS].fillna(0).astype(float)
y = df["Fraud_Label"].astype(int)

print(f"\nFeature matrix: {X.shape}")
print(f"Label dist:\n{y.value_counts()}")

# ── 5. Train/test split ───────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\nTrain: {X_train.shape}  Test: {X_test.shape}")

# ── 6. Random Forest ──────────────────────────────────────────────────────────
print("\nTraining Random Forest...")
rf = RandomForestClassifier(
    n_estimators=150, class_weight="balanced", random_state=42, n_jobs=-1
)
rf.fit(X_train, y_train)
rf_auc = roc_auc_score(y_test, rf.predict_proba(X_test)[:, 1])
print(f"  RF ROC-AUC: {rf_auc:.4f}")
print(classification_report(y_test, rf.predict(X_test), digits=3))
joblib.dump(rf, MODEL_PATH)
print(f"  Saved -> {MODEL_PATH}")

# ── 7. XGBoost ────────────────────────────────────────────────────────────────
print("\nTraining XGBoost...")
scale_pos = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
xgb = XGBClassifier(
    n_estimators=200, learning_rate=0.1, max_depth=5,
    scale_pos_weight=scale_pos, random_state=42,
    eval_metric="logloss", verbosity=0,
)
xgb.fit(X_train, y_train)
xgb_auc = roc_auc_score(y_test, xgb.predict_proba(X_test)[:, 1])
print(f"  XGB ROC-AUC: {xgb_auc:.4f}")
print(classification_report(y_test, xgb.predict(X_test), digits=3))
joblib.dump(xgb, XGB_PATH)
print(f"  Saved -> {XGB_PATH}")

# ── 8. Meta Logistic Regression (stacking) ───────────────────────────────────
print("\nTraining Meta-LR (stacking)...")
X_meta_train = np.column_stack([
    rf.predict_proba(X_train)[:, 1],
    xgb.predict_proba(X_train)[:, 1],
])
X_meta_test = np.column_stack([
    rf.predict_proba(X_test)[:, 1],
    xgb.predict_proba(X_test)[:, 1],
])
meta = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
meta.fit(X_meta_train, y_train)
meta_auc = roc_auc_score(y_test, meta.predict_proba(X_meta_test)[:, 1])
print(f"  Meta-LR ROC-AUC: {meta_auc:.4f}")
joblib.dump(meta, META_PATH)
print(f"  Saved -> {META_PATH}")

# ── 9. Summary ────────────────────────────────────────────────────────────────
print("\n===== TRAINING COMPLETE =====")
print(f"  RF      ROC-AUC: {rf_auc:.4f}")
print(f"  XGB     ROC-AUC: {xgb_auc:.4f}")
print(f"  Meta-LR ROC-AUC: {meta_auc:.4f}")
print("\nRestart Django server to load new models: press Ctrl+C, then run: python manage.py runserver 8001")
