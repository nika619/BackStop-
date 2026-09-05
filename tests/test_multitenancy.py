from datetime import datetime, timezone

from sqlmodel import Session

from backstop.database import engine, init_db
from backstop.models import Action, Case, MerchantPolicy, PaymentEvent, RootCause
from backstop.policy.engine import PolicyContext, evaluate


def test_merchant_isolation():
    init_db()
    now_dt = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)

    # Merchant A (max_attempts = 3)
    policy_a = MerchantPolicy(
        merchant_id="merch_A",
        name="Merchant A",
        max_attempts=3,
        incentive_budget_paise=1000,
        incentive_spent_paise=1000,  # Budget exhausted
    )

    # Merchant B (max_attempts = 1, budget remaining)
    policy_b = MerchantPolicy(
        merchant_id="merch_B",
        name="Merchant B",
        max_attempts=1,
        incentive_budget_paise=50000,
        incentive_spent_paise=0,
    )

    event_a = PaymentEvent(
        event_id="evt_ma_01",
        merchant_id="merch_A",
        payment_id="pay_ma_01",
        customer_ref="cust_a",
        amount_paise=50000,
        failed_at=now_dt,
    )
    case_a = Case(
        merchant_id="merch_A",
        payment_event_id=event_a.id,
        payment_id="pay_ma_01",
        customer_ref="cust_a",
        root_cause=RootCause.RAIL_INELIGIBLE,
        attempt_no=1,
    )

    ctx_a = PolicyContext(merchant_id="merch_A", incentive_spent_paise=1000, incentive_budget_paise=1000)
    verdict_a = evaluate(case_a, event_a, ctx_a, now_dt, merchant_policy=policy_a)

    # Merchant A budget is exhausted, so SWITCH_RAIL_LINK denied
    assert Action.SWITCH_RAIL_LINK not in verdict_a.permitted
    assert "R13" in verdict_a.denied[Action.SWITCH_RAIL_LINK]

    # Merchant B has budget and attempt cap = 1
    event_b = PaymentEvent(
        event_id="evt_mb_01",
        merchant_id="merch_B",
        payment_id="pay_mb_01",
        customer_ref="cust_b",
        amount_paise=50000,
        failed_at=now_dt,
    )
    case_b = Case(
        merchant_id="merch_B",
        payment_event_id=event_b.id,
        payment_id="pay_mb_01",
        customer_ref="cust_b",
        root_cause=RootCause.RAIL_INELIGIBLE,
        attempt_no=1,  # Attempt cap reached for Merchant B (max = 1)
    )

    ctx_b = PolicyContext(merchant_id="merch_B", incentive_spent_paise=0, incentive_budget_paise=50000)
    verdict_b = evaluate(case_b, event_b, ctx_b, now_dt, merchant_policy=policy_b)

    # Merchant B attempt cap reached
    assert Action.RETRY_SAME_RAIL not in verdict_b.permitted
