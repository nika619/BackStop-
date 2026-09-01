import pytest
from datetime import datetime, timezone
from sqlmodel import Session, create_engine, SQLModel
from backstop.models import Action, Case, PaymentEvent, RootCause
from backstop.policy.engine import PolicyContext
from backstop.planner.planner import plan, safest
from backstop.ingest.batch import import_batch_records
from backstop.ledger.chain import verify_chain, append as append_ledger


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_duplicate_webhook_produces_one_record(session):
    record = {
        "event_id": "evt_dup_01",
        "payment_id": "pay_dup_01",
        "amount_paise": 49900,
        "error_reason": "gateway_technical_error",
    }
    imported1, dup1 = import_batch_records(session, [record])
    assert imported1 == 1
    assert dup1 == 0

    # Second arrival of identical event ID
    imported2, dup2 = import_batch_records(session, [record])
    assert imported2 == 0
    assert dup2 == 1


def test_planner_handles_empty_permitted_set_safely():
    case = Case(payment_event_id="e1", payment_id="p1", root_cause=RootCause.UNKNOWN)
    event = PaymentEvent(event_id="e1", payment_id="p1", customer_ref="c1", amount_paise=1000)
    action, plan_data = plan(case, event, frozenset())
    assert action == Action.NO_ACTION


def test_safest_fallback_ladder_prefers_inaction():
    # When NO_ACTION is available, it is always chosen first
    assert safest(frozenset({Action.RETRY_SAME_RAIL, Action.NO_ACTION})) == Action.NO_ACTION
    # When SCHEDULE_FOLLOWUP is available without NO_ACTION, it is chosen before RETRY
    assert safest(frozenset({Action.RETRY_SAME_RAIL, Action.SCHEDULE_FOLLOWUP})) == Action.SCHEDULE_FOLLOWUP
