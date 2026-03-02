from django.utils import timezone
from datetime import timedelta
from .constant import *
from ..models import Transaction
from django.db.models import Sum
from decimal import Decimal

REAL_STATUSES = ["SUCCESS", "OTP_REQUIRED", "FAILED"]
# Only fully resolved statuses count toward rapid-fire detection
# OTP_REQUIRED means the transaction is still pending — not a completed attempt
SETTLED_STATUSES = ["SUCCESS", "FAILED"]

# ── Hard Block Rules ──────────────────────────────────────────────────────────
# These always block regardless of ML score (high-confidence fraud signals).
# Return "BLOCK" to trigger immediate DENY.

def high_amount_rule(txn):
    """Amounts >= ₹1,00,000 are always blocked."""
    if txn.amount >= HIGH_AMOUNT_THRESHOLD:
        return "BLOCK"
    return None

def rapid_transactions_rule(txn):
    """5+ settled transactions in 5 minutes → always block.
    Only counts SUCCESS/FAILED — OTP_REQUIRED transactions are still pending."""
    time_window = timezone.now() - timedelta(minutes=5)
    count = Transaction.objects.filter(
        user=txn.user,
        status__in=SETTLED_STATUSES,
        created_at__gte=time_window,
    ).exclude(pk=txn.pk).count()
    if count >= 5:
        return "BLOCK"
    return None

def failed_attempts_rule(txn):
    """5+ failed transactions in 30 minutes → always block."""
    time_window = timezone.now() - timedelta(minutes=30)
    count = Transaction.objects.filter(
        user=txn.user,
        status="FAILED",
        created_at__gte=time_window,
    ).count()
    if count >= 5:
        return "BLOCK"
    return None

def daily_velocity_rule(txn):
    """Daily spend > ₹50,000 → always block."""
    today = timezone.now().date()
    total = Transaction.objects.filter(
        user=txn.user,
        created_at__date=today,
        status="SUCCESS",
    ).exclude(pk=txn.pk).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    if total + txn.amount > Decimal(str(DAILY_VELOCITY_LIMIT)):
        return "BLOCK"
    return None


# ── Soft Risk-Boost Rules ─────────────────────────────────────────────────────
# These don't hard-block on their own. Instead they return a float (0.0–1.0)
# added to the ML risk score. Combined score > 0.7 → DENY, > 0.3 → CHALLENGE.

def location_anomaly_boost(txn):
    """Sudden city change from established history → +0.35 risk boost."""
    if not txn.city:
        return 0.0
    prior_real = Transaction.objects.filter(
        user=txn.user, status__in=REAL_STATUSES
    ).exclude(pk=txn.pk)
    if prior_real.count() < 2:
        return 0.0
    last_txn = prior_real.order_by("-created_at").first()
    if not last_txn or not last_txn.city:
        return 0.0
    if last_txn.city != txn.city:
        return 0.35
    return 0.0

def device_change_boost(txn):
    """Unknown device after 2+ real transactions → +0.30 risk boost."""
    prior_real = Transaction.objects.filter(
        user=txn.user, status__in=REAL_STATUSES
    ).exclude(pk=txn.pk)
    if prior_real.count() < 2:
        return 0.0
    known_devices = set(d for d in prior_real.values_list("device_type", flat=True) if d)
    if txn.device_type and txn.device_type not in known_devices:
        return 0.30
    return 0.0

def payment_type_risk_boost(txn):
    """UPI/Wallet payment > ₹5,000 → +0.20 risk boost."""
    risky_methods = ["UPI", "WALLET"]
    if txn.payment_type in risky_methods and txn.amount > Decimal("5000"):
        return 0.20
    return 0.0


# Exported rule lists
HARD_BLOCK_RULES = [
    high_amount_rule,
    rapid_transactions_rule,
    failed_attempts_rule,
    daily_velocity_rule,
]

SOFT_BOOST_RULES = [
    location_anomaly_boost,
    device_change_boost,
    payment_type_risk_boost,
]
