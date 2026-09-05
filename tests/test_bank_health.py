from datetime import datetime, timezone

from backstop.database import init_db
from backstop.diagnose.bank_health import set_bank_health
from backstop.models import Action, Case, PaymentEvent, RootCause
from backstop.policy.engine import PolicyContext, evaluate


def test_bank_outage_cooloff_rule_r15():
    init_db()
    now_dt = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)

    # Set HDFC bank health below 70% (e.g. 50% outage)
    set_bank_health("HDFC", 0.50, is_outage=True)

    event = PaymentEvent(
        event_id="evt_hdfc_down",
        merchant_id="merch_ecommerce_01",
        payment_id="pay_hdfc_01",
        customer_ref="cust_hdfc",
        amount_paise=100000,
        error_reason="bank_not_available",
        error_source="HDFC",
        failed_at=now_dt,
        raw={"bank_code": "HDFC"},
    )
    case = Case(
        merchant_id="merch_ecommerce_01",
        payment_event_id=event.id,
        payment_id=event.payment_id,
        customer_ref=event.customer_ref,
        root_cause=RootCause.TRANSIENT_INFRA,
        attempt_no=0,
    )

    ctx = PolicyContext(merchant_id="merch_ecommerce_01")
    verdict = evaluate(case, event, ctx, now_dt)

    # Retry must be denied under R15 due to bank health < 70%
    assert Action.RETRY_SAME_RAIL not in verdict.permitted
    assert "R15" in verdict.denied[Action.RETRY_SAME_RAIL]

    # Reset HDFC health back to 95%
    set_bank_health("HDFC", 0.95, is_outage=False)
    verdict_healthy = evaluate(case, event, ctx, now_dt)
    assert Action.RETRY_SAME_RAIL in verdict_healthy.permitted
