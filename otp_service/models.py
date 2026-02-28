from django.db import models
from django.utils import timezone
from transactions.models import Transaction

class TransactionOTP(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name="otp")
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"OTP for {self.transaction.txn_id}"