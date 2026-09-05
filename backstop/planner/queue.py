import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from sqlmodel import Session, select

from backstop.database import engine
from backstop.diagnose.taxonomy import REASON_MAP
from backstop.execute.executor import execute
from backstop.ledger.chain import append as append_ledger
from backstop.models import Action, Case, PaymentEvent, RootCause
from backstop.planner.planner import plan
from backstop.policy.engine import POLICY_VERSION, PolicyContext, evaluate

logger = logging.getLogger(__name__)


def process_payment_event_async(event_id: str):
    """
    Background worker task for processing payment events asynchronously.
    Offloads Gemini LLM calls and execution off the main HTTP webhook thread.
    """
    try:
        with Session(engine) as session:
            event = session.exec(select(PaymentEvent).where(PaymentEvent.event_id == event_id)).first()
            if not event:
                return

            # Check existing case or create
            case = session.exec(select(Case).where(Case.payment_event_id == event.id)).first()
            if not case:
                # 1. Deterministic Taxonomy diagnosis
                reason = (event.error_reason or "").lower().strip()
                root_cause = REASON_MAP.get(reason, RootCause.UNKNOWN)
                confidence = 1.0 if root_cause != RootCause.UNKNOWN else 0.0

                case = Case(
                    merchant_id=event.merchant_id,
                    payment_event_id=event.id,
                    payment_id=event.payment_id,
                    customer_ref=event.customer_ref,
                    root_cause=root_cause,
                    cause_confidence=confidence,
                    status="open",
                    created_at=datetime.now(timezone.utc),
                )
                session.add(case)
                session.commit()
                session.refresh(case)

            # 2. Plan (falls back to Gemini if UNKNOWN)
            ctx = PolicyContext(merchant_id=event.merchant_id)
            plan_res = plan(case, event, ctx, session)

            # 3. Execute planned action
            if plan_res.action != Action.NO_ACTION:
                execute(
                    action=plan_res.action,
                    case=case,
                    event=event,
                    ctx=ctx,
                    session=session,
                    now=datetime.now(timezone.utc),
                )
    except Exception as e:
        logger.error(f"Error in background event processing for {event_id}: {e}")
