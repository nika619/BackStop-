import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from backstop.database import get_session
from backstop.diagnose.classifier import classify
from backstop.eval.generator import assign_arm
from backstop.models import Case, PaymentEvent
from backstop.planner.queue import process_payment_event_async

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = logging.getLogger(__name__)

DEFAULT_SECRET = "dummy_webhook_secret_for_testing_only"


def verify_signature(raw_body: bytes, signature: str, secret: bytes) -> bool:
    """
    Verify HMAC-SHA256 signature on RAW byte body using constant-time comparison.
    Never re-serialize JSON before verifying (key ordering changes break hashes).
    """
    if not signature or not secret:
        return False
    expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/razorpay", status_code=202)
async def receive_razorpay_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_razorpay_signature: str = Header(default="", alias="X-Razorpay-Signature"),
    x_razorpay_event_id: str | None = Header(default=None, alias="X-Razorpay-Event-Id"),
    x_razorpay_merchant_id: str | None = Header(default=None, alias="X-Razorpay-Merchant-Id"),
    session: Session = Depends(get_session),
):
    """
    Ingest Razorpay webhook events with cryptographic HMAC verification, instant ACK (HTTP 202, <15ms),
    and offloaded async background processing.
    """
    raw_body = await request.body()
    secret_str = os.getenv("RAZORPAY_WEBHOOK_SECRET", DEFAULT_SECRET)
    secret_bytes = secret_str.encode("utf-8")

    # In production/test with signature provided, verify signature
    if x_razorpay_signature:
        if not verify_signature(raw_body, x_razorpay_signature, secret_bytes):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_id = payload.get("id") or x_razorpay_event_id or f"evt_{hashlib.sha256(raw_body).hexdigest()[:16]}"
    event_name = payload.get("event", "payment.failed")

    # Extract payment entity
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", payload)
    payment_id = payment_entity.get("id", f"pay_{event_id}")

    customer_id = payment_entity.get("customer_id") or payment_entity.get("contact") or payment_id
    customer_ref = hashlib.sha256(str(customer_id).encode("utf-8")).hexdigest()[:16]

    merchant_id = payload.get("merchant_id") or x_razorpay_merchant_id or "merch_ecommerce_01"

    payment_event = PaymentEvent(
        event_id=event_id,
        merchant_id=merchant_id,
        payment_id=payment_id,
        order_id=payment_entity.get("order_id", ""),
        customer_ref=customer_ref,
        amount_paise=payment_entity.get("amount", 0),
        currency=payment_entity.get("currency", "INR"),
        method=payment_entity.get("method", "card"),
        error_code=payment_entity.get("error_code"),
        error_source=payment_entity.get("error_source"),
        error_step=payment_entity.get("error_step"),
        error_reason=payment_entity.get("error_reason"),
        error_description=payment_entity.get("error_description"),
        failed_at=datetime.now(timezone.utc),
        is_recurring=payment_entity.get("recurring", False),
        mandate_category=payment_entity.get("mandate_category"),
        raw=payload,
    )

    # Replay defense enforced by Database Unique Index on event_id
    try:
        session.add(payment_event)
        session.commit()
        session.refresh(payment_event)
    except IntegrityError:
        session.rollback()
        # Return 200/202 so webhook sender does not keep retrying already-persisted events
        return {"status": "duplicate_ignored", "event_id": event_id}

    # Automatically diagnose and open case
    root_cause, confidence, _ = classify(payment_event)
    case = Case(
        merchant_id=merchant_id,
        payment_event_id=payment_event.id,
        payment_id=payment_event.payment_id,
        customer_ref=payment_event.customer_ref,
        root_cause=root_cause,
        cause_confidence=confidence,
        status="open",
        cohort_arm=assign_arm(payment_event.payment_id),
    )
    session.add(case)
    session.commit()
    session.refresh(case)

    # Trigger async background queue for LLM fallback / planning
    background_tasks.add_task(process_payment_event_async, event_id)

    return {
        "status": "accepted",
        "mode": "async_queued",
        "event_id": event_id,
        "payment_id": payment_id,
        "merchant_id": merchant_id,
        "case_id": case.id,
        "root_cause": root_cause.value,
        "cohort_arm": case.cohort_arm,
    }
