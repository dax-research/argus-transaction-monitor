import random
from django.utils import timezone
from datetime import timedelta
from otp_service.models import TransactionOTP

def generate_otp():
    return str(random.randint(100000, 999999))

def create_otp(transaction):

    otp_code = generate_otp()

    otp_obj = TransactionOTP.objects.create(
        transaction=transaction,
        otp_code=otp_code,
        expires_at=timezone.now() + timedelta(minutes=5)
    )

    transaction.otp_required = True
    transaction.status = "OTP_REQUIRED"
    transaction.save()

    print(f"OTP for {transaction.txn_id} is {otp_code}")  # simulate SMS

    return otp_obj

def verify_otp(transaction, entered_otp):

    try:
        otp_obj = transaction.otp
    except TransactionOTP.DoesNotExist:
        return "No OTP found."

    if otp_obj.is_verified:
        return "OTP already verified."

    if otp_obj.is_expired():
        transaction.status = "FAILED"
        transaction.save()
        return "OTP expired."

    if otp_obj.attempts >= 3:
        transaction.status = "BLOCKED"
        transaction.save()
        return "Too many attempts. Transaction blocked."

    otp_obj.attempts += 1
    otp_obj.save()

    if otp_obj.otp_code == entered_otp:
        otp_obj.is_verified = True
        otp_obj.save()

        transaction.otp_verified = True
        transaction.status = "SUCCESS"
        transaction.save()

        return "OTP verified. Transaction successful."

    else:
        if otp_obj.attempts >= 3:
            transaction.status = "BLOCKED"
            transaction.save()
            return "Invalid OTP. Transaction blocked."

        return "Invalid OTP."
