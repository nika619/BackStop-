import hashlib
import random
from datetime import datetime, timedelta, timezone
from backstop.policy.calendar import IST

CAUSE_MIX = [
    ("insufficient_funds", 0.22),
    ("authentication_failed", 0.14),
    ("payment_timed_out", 0.11),
    ("gateway_technical_error", 0.09),
    ("payment_cancelled", 0.09),
    ("bank_not_available", 0.07),
    ("card_expired", 0.05),
    ("invalid_vpa", 0.05),
    ("card_declined", 0.05),
    ("payment_risk_check_failed", 0.04),
    ("international_transaction_not_allowed", 0.03),
    ("input_validation_failed", 0.03),
    ("mandate_creation_failed", 0.03),
]

BASE_RECOVERY = {
    "transient_infra": 0.31,
    "issuer_soft_decline": 0.24,
    "auth_abandoned": 0.19,
    "user_aborted": 0.08,
    "instrument_terminal": 0.04,
    "rail_ineligible": 0.03,
    "risk_decline": 0.01,
    "merchant_config": 0.02,
    "mandate_failure": 0.12,
    "unknown": 0.05,
}

UPLIFT = {
    "transient_infra": 2.4,
    "issuer_soft_decline": 2.1,
    "auth_abandoned": 2.0,
    "user_aborted": 1.2,
    "instrument_terminal": 1.9,
    "rail_ineligible": 2.2,
    "risk_decline": 1.0,
    "merchant_config": 1.0,
    "mandate_failure": 1.7,
    "unknown": 1.0,
}


def assign_arm(payment_id: str, control_frac: float = 0.20) -> str:
    """
    Deterministic 80/20 split based on SHA-256 hash of payment_id.
    Guarantees stability across multiple runs and environments.
    """
    h = int(hashlib.sha256(payment_id.encode("utf-8")).hexdigest()[:8], 16)
    return "control" if (h % 100) < control_frac * 100 else "treatment"


def generate(n: int = 1000, seed: int = 20260901) -> list[dict]:
    """Generate n seeded, synthetic failed payment cases."""
    rng = random.Random(seed)
    reasons = [r for r, _ in CAUSE_MIX]
    weights = [w for _, w in CAUSE_MIX]
    base_date = datetime(2026, 8, 1, tzinfo=IST)

    dataset = []
    for i in range(n):
        pid = f"pay_SYN{i:06d}"
        reason = rng.choices(reasons, weights=weights, k=1)[0]
        customer_id_num = i % 340
        customer_hash = hashlib.sha256(f"cust_{customer_id_num}".encode("utf-8")).hexdigest()[:16]

        amount = rng.choice([49900, 99900, 149900, 249900, 599900, 1499900, 2500000])
        method = rng.choices(["upi", "card", "netbanking", "wallet"], weights=[0.52, 0.31, 0.12, 0.05])[0]
        is_recurring = rng.random() < 0.18
        mandate_cat = rng.choice(["insurance", "mutual_fund", "credit_card_bill", "other"]) if is_recurring else None

        dataset.append({
            "event_id": f"evt_SYN{i:06d}",
            "payment_id": pid,
            "order_id": f"order_SYN{i:06d}",
            "merchant_id": "merch_demo_01",
            "customer_ref": customer_hash,
            "amount_paise": amount,
            "currency": "INR",
            "method": method,
            "error_reason": reason,
            "error_source": rng.choice(["customer", "gateway", "bank", "razorpay", "business"]),
            "error_step": rng.choice(["payment_initiation", "payment_authentication", "payment_authorization"]),
            "error_description": f"Simulation failure: {reason.replace('_', ' ')}",
            "failed_at": (base_date + timedelta(minutes=rng.randint(0, 44640))).isoformat(),
            "is_recurring": is_recurring,
            "mandate_category": mandate_cat,
            "cohort_arm": assign_arm(pid),
        })

    return dataset


if __name__ == "__main__":
    data = generate(1000)
    control_count = sum(1 for d in data if d["cohort_arm"] == "control")
    print(f"Generated {len(data)} cases. Control: {control_count} ({control_count / len(data) * 100:.1f}%), Treatment: {len(data) - control_count}")
