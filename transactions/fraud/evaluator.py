from .rules import (
    high_amount_rule,
    rapid_transactions_rule,
    failed_attempts_rule,
    location_anomaly,
    device_change_rule,
   # merchant_risk_rule,
    payment_type_risk_rule,
    daily_velocity_rule,
)
RULES = [
    high_amount_rule,
    rapid_transactions_rule,
    failed_attempts_rule,
    location_anomaly,
    device_change_rule,
    #merchant_risk_rule,
    payment_type_risk_rule,
    daily_velocity_rule,
]

def evaluate_rules(txn):
    for rule in RULES:
        result = rule(txn)
        print(rule.__name__, "->", result)
        if result == "BLOCK":
            return "BLOCK"

    return 1