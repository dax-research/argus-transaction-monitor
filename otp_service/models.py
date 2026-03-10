from django.db import models
from django.utils import timezone
from transactions.models import Transaction

class TransactionOTP(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name="otp")
    otp = models.CharField(max_length=6)
    secret = models.CharField(max_length=64, blank=True, default="")   # pyotp TOTP base32 secret
    attempts = models.PositiveSmallIntegerField(default=0)              # failed verification count
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)

    MAX_ATTEMPTS = 3

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"OTP for {self.transaction.txn_id}"