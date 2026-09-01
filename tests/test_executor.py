import pytest
from datetime import datetime, timezone
from sqlmodel import Session, create_engine, SQLModel
from backstop.models import Action, Case, PaymentEvent, RootCause
from backstop.policy.engine import PolicyContext
from backstop.execute.executor import execute


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_executor_wall_1_kill_switch(session):
    ctx = PolicyContext(agent_enabled=False)
    case = Case(payment_event_id="e1", payment_id="p1", root_cause=RootCause.TRANSIENT_INFRA)
    event = PaymentEvent(event_id="e1", payment_id="p1", customer_ref="c1", amount_paise=1000)
    outcome = execute(Action.RETRY_SAME_RAIL, case, event, ctx, session, datetime.now(timezone.utc))
    assert outcome.status == "blocked"
    assert "Wall 1" in outcome.reason


def test_executor_wall_2_postgate_blocks_illegal_action(session):
    ctx = PolicyContext(agent_enabled=True)
    # Terminal cause cannot be retried
    case = Case(payment_event_id="e1", payment_id="p1", root_cause=RootCause.INSTRUMENT_TERMINAL)
    event = PaymentEvent(event_id="e1", payment_id="p1", customer_ref="c1", amount_paise=1000)
    outcome = execute(Action.RETRY_SAME_RAIL, case, event, ctx, session, datetime.now(timezone.utc))
    assert outcome.status == "blocked"
    assert "Wall 2" in outcome.reason


def test_executor_wall_3_spend_cap(session):
    ctx = PolicyContext(agent_enabled=True)
    case = Case(payment_event_id="e1", payment_id="p1", root_cause=RootCause.TRANSIENT_INFRA)
    # Retry cap is 50,000 INR (5000000 paise). Send 60,000 INR.
    event = PaymentEvent(event_id="e1", payment_id="p1", customer_ref="c1", amount_paise=6000000)
    outcome = execute(Action.RETRY_SAME_RAIL, case, event, ctx, session, datetime.now(timezone.utc))
    assert outcome.status == "blocked"
    assert "Wall 3" in outcome.reason


def test_executor_wall_4_four_eyes_approval(session):
    ctx = PolicyContext(agent_enabled=True, _has_approval_fn=lambda cid: False)
    case = Case(payment_event_id="e1", payment_id="p1", root_cause=RootCause.RISK_DECLINE)
    event = PaymentEvent(event_id="e1", payment_id="p1", customer_ref="c1", amount_paise=1000)
    outcome = execute(Action.ESCALATE_HUMAN, case, event, ctx, session, datetime.now(timezone.utc))
    assert outcome.status == "pending_approval"
    assert "Wall 4" in outcome.reason
