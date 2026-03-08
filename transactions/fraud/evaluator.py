from .rules import HARD_BLOCK_RULES, SOFT_BOOST_RULES


def evaluate_rules(txn):
    """
    Run the two-tier rule engine against a Transaction object.

    Returns a dict:
      {
        "hard_block": bool,          # True if any hard-block rule fired
        "risk_boost": float,         # Sum of all soft-rule boosts (0.0–1.0)
        "triggered_rules": list[str] # Names of rules that fired
      }
    """
    triggered = []
    hard_block = False

    # ── Tier 1: Hard block rules ─────────────────────────────────────────────
    for rule in HARD_BLOCK_RULES:
        result = rule(txn)
        print(f"[RULE] {rule.__name__} -> {result}")
        if result == "BLOCK":
            hard_block = True
            triggered.append(rule.__name__)

    # ── Tier 2: Soft boost rules ─────────────────────────────────────────────
    total_boost = 0.0
    for rule in SOFT_BOOST_RULES:
        boost = rule(txn)
        print(f"[BOOST] {rule.__name__} -> +{boost:.2f}")
        if boost > 0:
            total_boost += boost
            triggered.append(f"{rule.__name__}(+{boost:.2f})")

    return {
        "hard_block": hard_block,
        "risk_boost": min(total_boost, 1.0),  # cap at 1.0
        "triggered_rules": triggered,
    }