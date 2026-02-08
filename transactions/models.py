from django.db import models
from users.models import User
# Create your models here.

class Transaction(models.Model):

    #--Relationships--#
    user = models.ForeignKey(
            User,
            on_delete=models.CASCADE,
            related_name='transactions'
        )

    # ---- Transaction Identity ----
    txn_id = models.CharField(max_length=100, unique=True)

    # ---- Amount & Currency ----
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')

    # ---- Transaction Status ----
    STATUS_CHOICES = [
        ('INITIATED', 'Initiated'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('OTP_REQUIRED', 'OTP Required'),
        ('BLOCKED', 'Blocked'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='INITIATED'
    )
    
     # ---- Fraud Decision ----
    FRAUD_DECISION_CHOICES = [
        ('ALLOW', 'Allow'),
        ('CHALLENGE', 'Challenge'),
        ('DENY', 'Deny'),
    ]
    fraud_decision = models.CharField(
        max_length=20,
        choices=FRAUD_DECISION_CHOICES,
        null=True,
        blank=True
    )

     # ---- Risk Scoring ----
    risk_score = models.FloatField(null=True, blank=True)

    # ---- Context / Signals ----
    device_id = models.CharField(max_length=100, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    channel = models.CharField(
        max_length=50,
        default='APP'
    )  # APP / WEB / API

     # ---- OTP ----
    otp_required = models.BooleanField(default=False)
    otp_verified = models.BooleanField(default=False)

    # ---- Failure Reason ----
    failure_reason = models.CharField(max_length=255, null=True, blank=True)

    # ---- Timestamps ----
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.txn_id} - {self.status}"