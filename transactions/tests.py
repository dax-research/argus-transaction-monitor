"""
Tests to verify fraud flow is logically correct:
- Signal runs on Transaction create and updates risk_score, fraud_decision, status.
- ALLOW -> SUCCESS, CHALLENGE -> OTP_REQUIRED, DENY -> BLOCKED.
"""
import unittest
from unittest.mock import patch

from django.apps import apps
from django.test import TestCase

from transactions.models import Transaction
from users.models import User


class FraudSignalLogicTests(TestCase):
    """Verify post_save signal applies ML decision to transaction status."""

    def setUp(self):
        self.user = User.objects.create(
            user_id="testuser1",
            phone="+919876543210",
            account_balance=10_000.0,
        )

    @patch("transactions.signals.evaluate_transaction")
    def test_allow_sets_success(self, mock_evaluate):
        mock_evaluate.return_value = (0.2, "ALLOW")
        txn = Transaction.objects.create(
            user=self.user,
            amount=100,
            device_type="Mobile",
        )
        txn.refresh_from_db()
        self.assertEqual(txn.fraud_decision, "ALLOW")
        self.assertEqual(txn.status, "SUCCESS")
        self.assertFalse(txn.otp_required)
        self.assertAlmostEqual(float(txn.risk_score), 0.2, places=4)

    @patch("transactions.signals.evaluate_transaction")
    def test_challenge_sets_otp_required(self, mock_evaluate):
        mock_evaluate.return_value = (0.5, "CHALLENGE")
        txn = Transaction.objects.create(
            user=self.user,
            amount=5000,
            device_type="Laptop",
        )
        txn.refresh_from_db()
        self.assertEqual(txn.fraud_decision, "CHALLENGE")
        self.assertEqual(txn.status, "OTP_REQUIRED")
        self.assertTrue(txn.otp_required)

    @patch("transactions.signals.evaluate_transaction")
    def test_deny_sets_blocked(self, mock_evaluate):
        mock_evaluate.return_value = (0.9, "DENY")
        txn = Transaction.objects.create(
            user=self.user,
            amount=50_000,
            device_type="Mobile",
        )
        txn.refresh_from_db()
        self.assertEqual(txn.fraud_decision, "DENY")
        self.assertEqual(txn.status, "BLOCKED")
        self.assertFalse(txn.otp_required)

    @patch("transactions.signals.evaluate_transaction")
    def test_fraud_failure_fallback_to_challenge(self, mock_evaluate):
        mock_evaluate.side_effect = RuntimeError("Model missing")
        txn = Transaction.objects.create(
            user=self.user,
            amount=100,
            device_type="Mobile",
        )
        txn.refresh_from_db()
        self.assertEqual(txn.fraud_decision, "CHALLENGE")
        self.assertEqual(txn.status, "OTP_REQUIRED")
        self.assertTrue(txn.otp_required)


class FraudRulesTests(TestCase):
    """Verify rule-based evaluator flags hard blocks and passes safe traffic."""

    def setUp(self):
        self.user = User.objects.create(
            user_id="ruleuser1",
            phone="+919999999999",
            account_balance=5_000.0,
        )

    def test_high_amount_rule_blocks(self):
        """
        Amounts >= HIGH_AMOUNT_THRESHOLD should trigger a hard block rule.
        """
        from transactions.fraud.evaluator import evaluate_rules
        from transactions.fraud.constant import HIGH_AMOUNT_THRESHOLD

        txn = Transaction.objects.create(
            user=self.user,
            amount=HIGH_AMOUNT_THRESHOLD,
            device_type="Mobile",
        )
        result = evaluate_rules(txn)

        self.assertTrue(result["hard_block"])
        self.assertIn("high_amount_rule", result["triggered_rules"])

    def test_low_amount_rules_pass(self):
        """
        Safe, low-value transactions should not hard block or add risk boost.
        """
        from transactions.fraud.evaluator import evaluate_rules
        from transactions.fraud.constant import HIGH_AMOUNT_THRESHOLD

        txn = Transaction.objects.create(
            user=self.user,
            amount=HIGH_AMOUNT_THRESHOLD / 10,
            device_type="Mobile",
        )
        result = evaluate_rules(txn)

        self.assertFalse(result["hard_block"])
        self.assertEqual(result["risk_boost"], 0.0)
        self.assertEqual(result["triggered_rules"], [])
