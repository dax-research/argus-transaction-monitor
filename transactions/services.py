from .models import Transaction
from django.core.exceptions import ValidationError
from .fraud.evaluator import evaluate_rules
ALLOWED_STATUS_TRANSITIONS ={
    "INITIATED" : ["OTP_REQUIRED","SUCCESS","FAILED","BLOCKED"],
    "OTP_REQUIRED" : ["SUCCESS","FAILED","BLOCKED"],
    "SUCCESS" : [],
    "FAILED" : [],
    "BLOCKED" : [],
}
def create_transaction(user,amount,device_id,ip_address,channel,generated_txn_id):
    txn = Transaction.objects.create(
        user = user,
        amount = amount,
        device_id =device_id,
        ip_address = ip_address,
        channel = channel,
        txn_id = generated_txn_id
    )
    return txn

def update_transaction_status(txn: Transaction, new_status: str):
    current_status = txn.status

    if new_status not in ALLOWED_STATUS_TRANSITIONS[current_status]:
        raise ValidationError(
            f"Invalid status transition : {current_status}->{new_status}"
        )
    
    txn.status = new_status
    txn.save(update_fields=["status"])

    return txn

def evaluate_fraud_rules(txn: Transaction):
    user = txn.user

    #if the user is blocked dont allow the transaction
    if user.is_blocked:
        txn.fraud_decision="DENY"
        txn.failure_reason="User is blocked"
        txn.save(update_fields=["fraud_decision","failure_reason"])
        return "DENY"
    
    Threshold_amount = 10000

    if txn.amount >= Threshold_amount:
        txn.fraud_decision="CHALLENGE"
        txn.otp_required="True"
        txn.save(update_fields=["fraud_decision","otp_required"])
        return "CHALLENGE"

    txn.fraud_decision="ALLOW"
    txn.save(update_fields=["fraud_decision"])
    return "ALLOW"        

def process_transaction(txn:Transaction):
    decision = evaluate_fraud_rules(txn)

    if decision == 'DENY':
        update_transaction_status(txn,"BLOCKED")
    elif decision == 'ALLOW':
        update_transaction_status(txn,"SUCCESS")
    else:
        update_transaction_status(txn,"OTP_REQUIRED")

    return txn

def transaction_result(txn : Transaction):
    rule_result = evaluate_rules(txn)
    if rule_result =="BLOCK":
        txn.status = "BLOCKED"
        txn.save()
        return txn
