from datetime import datetime, timezone

from backstop.models import Action, Case, PaymentEvent, RootCause
from backstop.policy.calendar import IST
from backstop.policy.engine import PolicyContext, evaluate


def create_event(
    amount_paise: int = 149900,
    is_recurring: bool = False,
    mandate_category: str | None = None,
    failed_at: datetime | None = None,
) -> PaymentEvent:
    return PaymentEvent(
        event_id="evt_test_01",
        payment_id="pay_test_01",
        customer_ref="cust_hash_01",
        amount_paise=amount_paise,
        is_recurring=is_recurring,
        mandate_category=mandate_category,
        failed_at=failed_at or datetime(2026, 9, 2, 14, 0, 0, tzinfo=IST),
    )


def create_case(
    root_cause: RootCause = RootCause.TRANSIENT_INFRA,
    cohort_arm: str = "treatment",
    attempt_no: int = 0,
    last_action_at: datetime | None = None,
    promise_to_pay_at: datetime | None = None,
) -> Case:
    return Case(
        payment_event_id="evt_test_01",
        payment_id="pay_test_01",
        customer_ref="cust_hash_01",
        root_cause=root_cause,
        cause_confidence=1.0,
        cohort_arm=cohort_arm,
        attempt_no=attempt_no,
        last_action_at=last_action_at,
        promise_to_pay_at=promise_to_pay_at,
    )


# --- R01: Kill Switch Tests ---
def test_r01_kill_switch_blocks_all_actions():
    ctx = PolicyContext(agent_enabled=False)
    v = evaluate(create_case(RootCause.TRANSIENT_INFRA), create_event(), ctx, datetime(2026, 9, 2, 14, 0, tzinfo=IST))
    assert v.permitted == frozenset({Action.NO_ACTION})
    assert "R01:kill_switch" in v.rule_triggers


# --- R02: Risk Hard Stop Tests ---
def test_r02_risk_decline_permits_only_human_escalation():
    ctx = PolicyContext(agent_enabled=True)
    v = evaluate(create_case(RootCause.RISK_DECLINE), create_event(), ctx, datetime(2026, 9, 2, 14, 0, tzinfo=IST))
    assert v.permitted == frozenset({Action.ESCALATE_HUMAN})
    assert Action.RETRY_SAME_RAIL not in v.permitted
    assert Action.NUDGE_CHECKOUT not in v.permitted


# --- R03: Terminal Cause Tests ---
def test_r03_terminal_instrument_denies_retry():
    ctx = PolicyContext(agent_enabled=True)
    v = evaluate(create_case(RootCause.INSTRUMENT_TERMINAL), create_event(), ctx, datetime(2026, 9, 2, 14, 0, tzinfo=IST))
    assert Action.RETRY_SAME_RAIL not in v.permitted
    assert Action.UPDATE_INSTRUMENT in v.permitted


def test_r03_rail_ineligible_denies_retry():
    ctx = PolicyContext(agent_enabled=True)
    v = evaluate(create_case(RootCause.RAIL_INELIGIBLE), create_event(), ctx, datetime(2026, 9, 2, 14, 0, tzinfo=IST))
    assert Action.RETRY_SAME_RAIL not in v.permitted
    assert Action.SWITCH_RAIL_LINK in v.permitted


# --- R04: Attempt Cap Tests ---
def test_r04_attempt_cap_blocks_after_3_attempts():
    ctx = PolicyContext(agent_enabled=True)
    v = evaluate(create_case(RootCause.TRANSIENT_INFRA, attempt_no=3), create_event(), ctx, datetime(2026, 9, 2, 14, 0, tzinfo=IST))
    assert Action.RETRY_SAME_RAIL not in v.permitted
    assert "R04" in v.denied.get(Action.RETRY_SAME_RAIL, "")


def test_r04_attempt_below_cap_allows_retry():
    ctx = PolicyContext(agent_enabled=True)
    v = evaluate(create_case(RootCause.TRANSIENT_INFRA, attempt_no=0), create_event(), ctx, datetime(2026, 9, 2, 14, 0, tzinfo=IST))
    assert Action.RETRY_SAME_RAIL in v.permitted


# --- R05: Cool-off Window Tests ---
def test_r05_cool_off_window_enforced_between_retries():
    ctx = PolicyContext(agent_enabled=True)
    last_at = datetime(2026, 9, 2, 12, 0, tzinfo=IST)
    now_too_early = datetime(2026, 9, 2, 14, 0, tzinfo=IST)  # Only 2 hours later (needs 4h for attempt 1)
    v = evaluate(create_case(RootCause.TRANSIENT_INFRA, attempt_no=1, last_action_at=last_at), create_event(), ctx, now_too_early)
    assert Action.RETRY_SAME_RAIL not in v.permitted

    now_ok = datetime(2026, 9, 2, 17, 0, tzinfo=IST)  # 5 hours later (satisfies 4h)
    v_ok = evaluate(create_case(RootCause.TRANSIENT_INFRA, attempt_no=1, last_action_at=last_at), create_event(), ctx, now_ok)
    assert Action.RETRY_SAME_RAIL in v_ok.permitted


# --- R06: TRAI Quiet Hours Tests (09:00–21:00 IST) ---
def test_r06_quiet_hours_blocks_nudge_at_3am_ist():
    ctx = PolicyContext(agent_enabled=True)
    now_3am = datetime(2026, 9, 2, 3, 0, 0, tzinfo=IST)
    v = evaluate(create_case(RootCause.AUTH_ABANDONED), create_event(), ctx, now_3am)
    assert Action.NUDGE_CHECKOUT not in v.permitted
    assert "R06" in v.denied.get(Action.NUDGE_CHECKOUT, "")


def test_r06_quiet_hours_converts_utc_to_ist_accurately():
    ctx = PolicyContext(agent_enabled=True)
    # 22:30 UTC == 04:00 IST next day (Night in India)
    now_utc_night = datetime(2026, 9, 2, 22, 30, 0, tzinfo=timezone.utc)
    v = evaluate(create_case(RootCause.AUTH_ABANDONED), create_event(), ctx, now_utc_night)
    assert Action.NUDGE_CHECKOUT not in v.permitted


def test_r06_quiet_hours_allows_nudge_during_daylight_ist():
    ctx = PolicyContext(agent_enabled=True)
    now_daylight = datetime(2026, 9, 2, 14, 30, 0, tzinfo=IST)
    v = evaluate(create_case(RootCause.AUTH_ABANDONED), create_event(), ctx, now_daylight)
    assert Action.NUDGE_CHECKOUT in v.permitted


# --- R07: Daily Contact Cap Tests ---
def test_r07_daily_contact_cap_blocks_after_2_messages():
    ctx = PolicyContext(agent_enabled=True, _contacts_today_fn=lambda c: 2)
    v = evaluate(create_case(RootCause.AUTH_ABANDONED), create_event(), ctx, datetime(2026, 9, 2, 14, 0, tzinfo=IST))
    assert Action.NUDGE_CHECKOUT not in v.permitted
    assert "R07" in v.denied.get(Action.NUDGE_CHECKOUT, "")


# --- R08: Consent / DND Tests ---
def test_r08_dnd_active_hard_blocks_customer_nudge():
    ctx = PolicyContext(agent_enabled=True, _is_dnd_fn=lambda c: True)
    v = evaluate(create_case(RootCause.AUTH_ABANDONED), create_event(), ctx, datetime(2026, 9, 2, 14, 0, tzinfo=IST))
    assert Action.NUDGE_CHECKOUT not in v.permitted
    assert "R08" in v.denied.get(Action.NUDGE_CHECKOUT, "")


# --- R09: RBI E-mandate Framework 2026 — Pre-debit Notice Tests ---
def test_r09_recurring_without_predebit_notice_denies_retry():
    ctx = PolicyContext(agent_enabled=True, _predebit_notice_fn=lambda cid: None)
    event = create_event(is_recurring=True, amount_paise=99900)
    v = evaluate(create_case(RootCause.TRANSIENT_INFRA), event, ctx, datetime(2026, 9, 2, 14, 0, tzinfo=IST))
    assert Action.RETRY_SAME_RAIL not in v.permitted
    assert "R09" in v.denied.get(Action.RETRY_SAME_RAIL, "")


def test_r09_recurring_with_satisfied_24h_notice_allows_retry():
    notice_time = datetime(2026, 9, 1, 10, 0, tzinfo=IST)  # Sent 28 hours ago
    ctx = PolicyContext(agent_enabled=True, _predebit_notice_fn=lambda cid: notice_time)
    event = create_event(is_recurring=True, amount_paise=99900)
    now = datetime(2026, 9, 2, 14, 0, tzinfo=IST)
    v = evaluate(create_case(RootCause.TRANSIENT_INFRA), event, ctx, now)
    assert Action.RETRY_SAME_RAIL in v.permitted


# --- R10: RBI E-mandate Framework 2026 — AFA Ceilings Tests ---
def test_r10_standard_recurring_above_15k_afa_ceiling_denied():
    notice_time = datetime(2026, 9, 1, 10, 0, tzinfo=IST)
    ctx = PolicyContext(agent_enabled=True, _predebit_notice_fn=lambda cid: notice_time)
    event = create_event(amount_paise=20_000_00, is_recurring=True, mandate_category="other")  # ₹20,000 > ₹15,000
    v = evaluate(create_case(RootCause.ISSUER_SOFT_DECLINE), event, ctx, datetime(2026, 9, 2, 14, 0, tzinfo=IST))
    assert Action.RETRY_SAME_RAIL not in v.permitted
    assert "R10" in v.denied.get(Action.RETRY_SAME_RAIL, "")


def test_r10_insurance_category_allowed_under_1_lakh_ceiling():
    notice_time = datetime(2026, 9, 1, 10, 0, tzinfo=IST)
    ctx = PolicyContext(agent_enabled=True, _predebit_notice_fn=lambda cid: notice_time)
    event = create_event(amount_paise=50_000_00, is_recurring=True, mandate_category="insurance")  # ₹50,000 < ₹1,00,000
    v = evaluate(create_case(RootCause.ISSUER_SOFT_DECLINE), event, ctx, datetime(2026, 9, 2, 14, 0, tzinfo=IST))
    assert Action.RETRY_SAME_RAIL in v.permitted


def test_r10_mutual_fund_category_allowed_under_1_lakh_ceiling():
    notice_time = datetime(2026, 9, 1, 10, 0, tzinfo=IST)
    ctx = PolicyContext(agent_enabled=True, _predebit_notice_fn=lambda cid: notice_time)
    event = create_event(amount_paise=80_000_00, is_recurring=True, mandate_category="mutual_fund")
    v = evaluate(create_case(RootCause.ISSUER_SOFT_DECLINE), event, ctx, datetime(2026, 9, 2, 14, 0, tzinfo=IST))
    assert Action.RETRY_SAME_RAIL in v.permitted


# --- R11: Promise to Pay Tests ---
def test_r11_active_promise_to_pay_freezes_recovery():
    future_promise = datetime(2026, 9, 5, 12, 0, tzinfo=IST)
    case = create_case(RootCause.ISSUER_SOFT_DECLINE, promise_to_pay_at=future_promise)
    ctx = PolicyContext(agent_enabled=True)
    now = datetime(2026, 9, 2, 14, 0, tzinfo=IST)
    v = evaluate(case, create_event(), ctx, now)
    assert Action.NUDGE_CHECKOUT not in v.permitted
    assert Action.RETRY_SAME_RAIL not in v.permitted


# --- R12: Merchant Configuration Defect Tests ---
def test_r12_merchant_config_never_contacts_customer():
    case = create_case(RootCause.MERCHANT_CONFIG)
    ctx = PolicyContext(agent_enabled=True)
    v = evaluate(case, create_event(), ctx, datetime(2026, 9, 2, 14, 0, tzinfo=IST))
    assert Action.NUDGE_CHECKOUT not in v.permitted
    assert Action.UPDATE_INSTRUMENT not in v.permitted
    assert Action.ALERT_MERCHANT in v.permitted


# --- R13: Incentive Budget Cap Tests ---
def test_r13_exhausted_incentive_budget_blocks_rail_switch():
    ctx = PolicyContext(agent_enabled=True, incentive_budget_paise=100000, incentive_spent_paise=100000)
    case = create_case(RootCause.RAIL_INELIGIBLE)
    v = evaluate(case, create_event(), ctx, datetime(2026, 9, 2, 14, 0, tzinfo=IST))
    assert Action.SWITCH_RAIL_LINK not in v.permitted


# --- R14: Control Arm Isolation Tests ---
def test_r14_control_arm_permits_only_no_action():
    case = create_case(RootCause.TRANSIENT_INFRA, cohort_arm="control")
    ctx = PolicyContext(agent_enabled=True)
    v = evaluate(case, create_event(), ctx, datetime(2026, 9, 2, 14, 0, tzinfo=IST))
    assert v.permitted == frozenset({Action.NO_ACTION})
    assert "R14:control_arm" in v.rule_triggers
