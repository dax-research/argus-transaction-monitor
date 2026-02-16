"""
Tests to verify ML fraud detector is logically correct:
- predict_fraud returns (float risk, str decision).
- risk in [0, 1], decision in ALLOW | CHALLENGE | DENY.
- Thresholds: <0.3 ALLOW, <0.7 CHALLENGE, else DENY.
"""
import os
import unittest

import pandas as pd
from django.test import TestCase

from fraud_engine.services.ml_rf_v1 import (
    ENCODER_PATH,
    ArgusFraudDetector,
    MODEL_PATH,
    XGB_MODEL_PATH,
)


def _ml_assets_exist():
    return all(os.path.exists(p) for p in (MODEL_PATH, XGB_MODEL_PATH, ENCODER_PATH))


class DetectorOutputTests(TestCase):
    """Verify detector output shape and decision values. Skip if model files missing."""

    @unittest.skipIf(not _ml_assets_exist(), "ML model files not found (run training first)")
    def test_predict_fraud_returns_tuple(self):
        detector = ArgusFraudDetector()
        txn = {
            "Transaction_Amount": 200,
            "Account_Balance": 5000,
            "Device_Type": "Mobile",
            "Timestamp": pd.Timestamp.now(),
        }
        risk, decision = detector.predict_fraud(txn, pd.DataFrame())
        self.assertIsInstance(risk, float)
        self.assertIsInstance(decision, str)
        self.assertGreaterEqual(risk, 0.0)
        self.assertLessEqual(risk, 1.0)
        self.assertIn(decision, ("ALLOW", "CHALLENGE", "DENY"))

    @unittest.skipIf(not _ml_assets_exist(), "ML model files not found")
    def test_decision_follows_thresholds(self):
        detector = ArgusFraudDetector()
        risk, decision = detector.predict_fraud(
            {
                "Transaction_Amount": 100,
                "Account_Balance": 10_000,
                "Device_Type": "Mobile",
                "Timestamp": pd.Timestamp.now(),
            },
            pd.DataFrame(),
        )
        if risk < 0.3:
            self.assertEqual(decision, "ALLOW")
        elif risk < 0.7:
            self.assertEqual(decision, "CHALLENGE")
        else:
            self.assertEqual(decision, "DENY")
