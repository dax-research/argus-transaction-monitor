from django.utils import timezone
from datetime import timedelta
from .constant import *
from ..models import Transaction
from django.db.models import Sum


#1.High Transaction Amount
def high_amount_rule(txn):
    if txn.amount >= HIGH_AMOUNT_THRESHOLD:
        return "BLOCK"
    return 1

#2.Rapid Multiple Transactions
def rapid_transactions_rule(txn):
    time_window = timezone.now()-timedelta(minutes=5)

    count = Transaction.objects.filter(
        user=txn.user,
        created_at__gte = time_window
    ).count()

    if count >= 3:
        return "BLOCK"
    
    return 1

#3.Mulitple failed attempts
def failed_attempts_rule(txn):
    time_window = timezone.now()-timedelta(minutes=30)

    count = Transaction.objects.filter(
        user=txn.user,
        status = "FAILED",
        created_at__gte = time_window
    ).count()

    if count >= 5:
        return "BLOCK"
    
    return 1

#4.Location Anomaly
def location_anomaly(txn):
    if not txn.city:
        return 1
    last_txn = Transaction.objects.filter(
        user=txn.user,
    ).exclude(pk=txn.pk).order_by("-created_at").first()
    if not last_txn or not last_txn.city:
        return 1
    if last_txn.city != txn.city:
        return "BLOCK"
    return 1

#5.Device change
def device_change_rule(txn):
    known_devices = (
        Transaction.objects.filter(user=txn.user)
        .exclude(pk=txn.pk)
        .values_list("device_type", flat=True)
        .distinct()
    )
    known_devices = [d for d in known_devices if d]
    if txn.device_type and txn.device_type not in known_devices:
        return "BLOCK"
    return 1

# #6.Merchant History
# def merchant_risk_rule(txn):
#     if txn.merchant.risk_score > 80:
#         return "BLOCK"
#     return 1

#7.Payment Type Risk
def payment_type_risk_rule(txn):
    risky_methods = ["UPI", "WALLET"]

    if txn.payment_type in risky_methods and txn.amount > 5000:
        return "BLOCK"

    return 1

#8.Velocity Rule (Amount
def daily_velocity_rule(txn):
    today = timezone.now().date()

    total = Transaction.objects.filter(
        user=txn.user,
        created_at__date=today,
        status="SUCCESS"
    ).aggregate(total=Sum("amount"))["total"] or 0

    if total + txn.amount > 50000:
        return "BLOCK"

    return 1

