from datetime import datetime, timezone

import pytest
from sqlmodel import Session, SQLModel, create_engine

from backstop.execute.executor import execute
from backstop.models import Action, Case, PaymentEvent, RootCause
from backstop.policy.engine import PolicyContext


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_idempotency_prevents_duplicate_charge(session):
    ctx = PolicyContext(agent_enabled=True, dry_run=True)
    now = datetime(2026, 9, 2, 14, 0, tzinfo=timezone.utc)

    case = Case(
        payment_event_id="evt_idem_01",
        payment_id="pay_idem_01",
        customer_ref="cust_idem",
        root_cause=RootCause.TRANSIENT_INFRA,
        attempt_no=0,
    )
    event = PaymentEvent(
        event_id="evt_idem_01",
        payment_id="pay_idem_01",
        customer_ref="cust_idem",
        amount_paise=149900,
        failed_at=now,
    )

    # First execution succeeds
    outcome1 = execute(Action.RETRY_SAME_RAIL, case, event, ctx, session, now)
    assert outcome1.status in ("executed", "simulated")

    # Immediate replay of the exact same action and attempt hits Wall 5
    outcome2 = execute(Action.RETRY_SAME_RAIL, case, event, ctx, session, now)
    assert outcome2.status == "duplicate_noop"
    assert "Wall 5" in outcome2.reason
