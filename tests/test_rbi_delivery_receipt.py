from datetime import datetime, timedelta, timezone

from backstop.models import Action, Case, PaymentEvent, RootCause
from backstop.policy.engine import PolicyContext, evaluate


def test_rbi_predebit_delivery_receipt_status():
    now_dt = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    notice_time = now_dt - timedelta(hours=30)  # >24h elapsed

    event = PaymentEvent(
        event_id="evt_rec_01",
        merchant_id="merch_saas_sub_02",
        payment_id="pay_rec_01",
        customer_ref="cust_rec",
        amount_paise=100000,
        is_recurring=True,
        mandate_category="other",
        failed_at=now_dt,
    )
    case = Case(
        merchant_id="merch_saas_sub_02",
        payment_event_id=event.id,
        payment_id=event.payment_id,
        customer_ref=event.customer_ref,
        root_cause=RootCause.TRANSIENT_INFRA,
        attempt_no=0,
    )

    # 1. Delivery notice status = FAILED
    ctx_failed = PolicyContext(
        merchant_id="merch_saas_sub_02",
        _predebit_notice_fn=lambda c_id: notice_time,
        _predebit_status_fn=lambda c_id: "FAILED",
    )
    verdict_failed = evaluate(case, event, ctx_failed, now_dt)
    assert Action.RETRY_SAME_RAIL not in verdict_failed.permitted
    assert "R09" in verdict_failed.denied[Action.RETRY_SAME_RAIL]
    assert "FAILED" in verdict_failed.denied[Action.RETRY_SAME_RAIL]

    # 2. Delivery notice status = DELIVERED
    ctx_delivered = PolicyContext(
        merchant_id="merch_saas_sub_02",
        _predebit_notice_fn=lambda c_id: notice_time,
        _predebit_status_fn=lambda c_id: "DELIVERED",
    )
    verdict_delivered = evaluate(case, event, ctx_delivered, now_dt)
    assert Action.RETRY_SAME_RAIL in verdict_delivered.permitted
