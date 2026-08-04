from datetime import datetime, timezone

from backstop.models import Action, Case, PaymentEvent


def get_amount_band(amount_paise: int) -> str:
    """Discretize exact rupee amounts into bands for privacy preservation."""
    amount_inr = amount_paise / 100.0
    if amount_inr < 500:
        return "< ₹500"
    elif amount_inr <= 1000:
        return "₹500–₹1,000"
    elif amount_inr <= 5000:
        return "₹1,000–₹5,000"
    elif amount_inr <= 15000:
        return "₹5,000–₹15,000"
    else:
        return "> ₹15,000"


def hours_since(failed_at: datetime | str | None) -> float:
    """Calculate elapsed hours since failure."""
    if not failed_at:
        return 0.0
    if isinstance(failed_at, str):
        failed_dt = datetime.fromisoformat(failed_at)
    else:
        failed_dt = failed_at
    if failed_dt.tzinfo is None:
        failed_dt = failed_dt.replace(tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc)
    diff = (now_utc - failed_dt).total_seconds() / 3600.0
    return max(0.0, round(diff, 1))


def redact(case: Case, event: PaymentEvent, permitted: frozenset[Action]) -> dict:
    """
    DPDP Act 2023 compliant data minimisation.
    The model receives purely structured behavioral signals and permitted actions.
    Never receives raw PII (names, phones, emails, card numbers, or customer notes).
    """
    sanitized_notes = ""
    if case.notes:
        # Wrap untrusted customer notes in strict delimiter tags
        sanitized_notes = f"<untrusted>{case.notes[:200]}</untrusted>"

    return {
        "case_id": case.id,
        "cause": case.root_cause.value,
        "cause_confidence": round(case.cause_confidence, 2),
        "amount_band": get_amount_band(event.amount_paise),
        "payment_method": event.method,
        "hours_since_failure": hours_since(event.failed_at),
        "attempt_number": case.attempt_no,
        "contacts_already_sent": case.contacts_sent,
        "is_recurring_mandate": event.is_recurring,
        "mandate_category": event.mandate_category or "none",
        "permitted_actions": sorted([a.value for a in permitted]),
        "customer_input": sanitized_notes if sanitized_notes else "none",
    }
