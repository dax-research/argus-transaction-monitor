import pyotp
from django.utils import timezone
from datetime import timedelta
from otp_service.models import TransactionOTP

# ------------------------------------------------------------------
# OTP expiry configuration
# ------------------------------------------------------------------
OTP_VALID_MINUTES = 5          # How long the OTP is valid
TOTP_INTERVAL = OTP_VALID_MINUTES * 60  # pyotp interval in seconds


def _make_totp(secret: str) -> pyotp.TOTP:
    """Return a TOTP object bound to *secret* with the project's interval."""
    return pyotp.TOTP(secret, interval=TOTP_INTERVAL, digits=6)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def create_otp(transaction) -> TransactionOTP:
    """
    Generate a TOTP-backed OTP for *transaction* and persist it.

    A fresh base32 secret is created for every call so that each
    transaction gets its own unique OTP regardless of timing.
    """
    secret = pyotp.random_base32()          # cryptographically random secret
    totp = _make_totp(secret)
    otp_code = totp.now()                   # 6-digit code valid for OTP_VALID_MINUTES

    otp_obj = TransactionOTP.objects.create(
        transaction=transaction,
        otp=otp_code,
        secret=secret,
        expires_at=timezone.now() + timedelta(minutes=OTP_VALID_MINUTES),
    )

    transaction.otp_required = True
    transaction.status = "OTP_REQUIRED"
    transaction.save()

    # Simulate SMS / notification delivery
    print(f"[OTP] Transaction {transaction.txn_id} → code: {otp_code}")

    return otp_obj


def verify_otp(transaction, entered_otp: str) -> str:
    """
    Validate *entered_otp* against the stored TOTP for *transaction*.

    Returns a human-readable result string.  Transaction status is
    updated in-place depending on the outcome.
    """
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

    if otp_obj.attempts >= TransactionOTP.MAX_ATTEMPTS:
        transaction.status = "BLOCKED"
        transaction.save()
        return "Too many attempts. Transaction blocked."

    # Increment attempt counter before checking (prevents timing exploits)
    otp_obj.attempts += 1
    otp_obj.save()

    # -----------------------------------------------------------------
    # pyotp verification
    #   valid_window=1  →  also accept the previous interval window
    #   (guards against edge-case where the user receives the OTP just
    #    before an interval boundary, then submits just after).
    # -----------------------------------------------------------------
    totp = _make_totp(otp_obj.secret)
    is_valid = totp.verify(entered_otp, valid_window=1)

    if is_valid:
        otp_obj.is_verified = True
        otp_obj.save()

        transaction.otp_verified = True
        transaction.status = "SUCCESS"
        transaction.save()

        return "OTP verified. Transaction successful."

    # Wrong OTP — check if this was the final allowed attempt
    if otp_obj.attempts >= TransactionOTP.MAX_ATTEMPTS:
        transaction.status = "BLOCKED"
        transaction.save()
        return "Invalid OTP. Transaction blocked after too many attempts."

    remaining = TransactionOTP.MAX_ATTEMPTS - otp_obj.attempts
    return f"Invalid OTP. {remaining} attempt(s) remaining."
