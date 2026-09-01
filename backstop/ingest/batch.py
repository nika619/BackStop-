import csv
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError
from backstop.models import PaymentEvent, Case
from backstop.diagnose.classifier import classify
from backstop.eval.generator import assign_arm


def import_batch_records(session: Session, records: list[dict]) -> tuple[int, int]:
    """
    Import batch of failed payment records.
    Returns: (imported_count, duplicate_skipped_count)
    """
    imported = 0
    duplicates = 0

    for item in records:
        event_id = item.get("event_id") or f"evt_{hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()[:16]}"
        pid = item.get("payment_id") or f"pay_{event_id}"
        customer_id = item.get("customer_ref") or item.get("customer_id") or pid
        customer_ref = hashlib.sha256(str(customer_id).encode("utf-8")).hexdigest()[:16]

        failed_at_val = item.get("failed_at")
        if isinstance(failed_at_val, str):
            try:
                failed_dt = datetime.fromisoformat(failed_at_val)
            except Exception:
                failed_dt = datetime.now(timezone.utc)
        else:
            failed_dt = failed_at_val or datetime.now(timezone.utc)

        event = PaymentEvent(
            event_id=event_id,
            merchant_id=item.get("merchant_id", "merch_default"),
            payment_id=pid,
            order_id=item.get("order_id", ""),
            customer_ref=customer_ref,
            amount_paise=int(item.get("amount_paise", item.get("amount", 0))),
            currency=item.get("currency", "INR"),
            method=item.get("method", "card"),
            error_code=item.get("error_code"),
            error_source=item.get("error_source"),
            error_step=item.get("error_step"),
            error_reason=item.get("error_reason"),
            error_description=item.get("error_description"),
            failed_at=failed_dt,
            is_recurring=bool(item.get("is_recurring", False)),
            mandate_category=item.get("mandate_category"),
            raw=item,
        )

        try:
            session.add(event)
            session.commit()
            session.refresh(event)

            root_cause, confidence, _ = classify(event)
            case = Case(
                payment_event_id=event.id,
                payment_id=event.payment_id,
                customer_ref=event.customer_ref,
                root_cause=root_cause,
                cause_confidence=confidence,
                cohort_arm=item.get("cohort_arm") or assign_arm(event.payment_id),
            )
            session.add(case)
            session.commit()
            imported += 1
        except IntegrityError:
            session.rollback()
            duplicates += 1

    return imported, duplicates
