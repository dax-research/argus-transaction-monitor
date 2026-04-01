import logging

import pandas as pd
from django.db.models.signals import post_save
from django.dispatch import receiver

from transactions.models import Transaction
from fraud_engine.services.fraud_service import evaluate_transaction

logger = logging.getLogger(__name__)


# @receiver(post_save, sender=Transaction)
# def run_fraud_check(sender, instance, created, **kwargs):
#     if not created:
#         return
@receiver(post_save, sender=Transaction)
def run_fraud_check(sender, instance, created, raw, **kwargs):
    if raw:
        return   # 🚨 VERY IMPORTANT

    # your existing logic
    # Get user's past transactions (exclude current one)
    history_qs = Transaction.objects.filter(user=instance.user).exclude(pk=instance.pk)
    history_df = pd.DataFrame(list(history_qs.values(
        "amount",
        "device_type",
        "created_at",
        "status"
    )))
    if not history_df.empty:
        history_df = history_df.rename(columns={
            "amount": "Transaction_Amount",
            "device_type": "Device_Type",
            "created_at": "Timestamp"
        })

    try:
        risk, decision = evaluate_transaction(instance, history_df)
    except Exception as e:
        logger.exception("Fraud check failed for txn %s: %s", instance.txn_id, e)
        risk = None
        decision = "CHALLENGE"
        status = "OTP_REQUIRED"
        otp_required = True
    else:
        if decision == "ALLOW":
            status = "SUCCESS"
            otp_required = False
        elif decision == "CHALLENGE":
            status = "OTP_REQUIRED"
            otp_required = True
        elif decision == "DENY":
            status = "BLOCKED"
            otp_required = False
        else:
            status = instance.status
            otp_required = instance.otp_required

    Transaction.objects.filter(pk=instance.pk).update(
        risk_score=risk,
        fraud_decision=decision,
        status=status,
        otp_required=otp_required,
    )
