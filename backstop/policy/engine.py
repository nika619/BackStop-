from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Any
from backstop.models import RootCause, Action, Case, PaymentEvent
from backstop.diagnose.taxonomy import CAUSE_TO_CANDIDATE_ACTIONS, NEVER_RETRY, HARD_STOP
from backstop.policy.calendar import to_ist, is_within_trai_window, IST

POLICY_VERSION = "2026.09.01"

MAX_ATTEMPTS = 3
COOL_OFF_HOURS = {0: 0, 1: 4, 2: 48}  # attempt_no -> required hours before next attempt
MAX_CONTACTS_PER_DAY = 2
QUIET_START, QUIET_END = 9, 21  # 09:00 to 21:00 IST
AFA_DEFAULT_PAISE = 15_00_000  # ₹15,000 RBI standard ceiling
AFA_ELEVATED_PAISE = 1_00_00_000  # ₹1,00,000 RBI elevated ceiling (Framework 2026)
AFA_ELEVATED_CATS = {"insurance", "mutual_fund", "credit_card_bill"}
PREDEBIT_NOTICE_HOURS = 24


@dataclass(frozen=True)
class Verdict:
    permitted: frozenset[Action]
    denied: dict[Action, str] = field(default_factory=dict)
    rule_triggers: list[str] = field(default_factory=list)
    policy_version: str = POLICY_VERSION


@dataclass
class PolicyContext:
    agent_enabled: bool = True
    dry_run: bool = True
    incentive_budget_paise: int = 500_000_00  # ₹50,000 budget in paise
    incentive_spent_paise: int = 0
    _contacts_today_fn: Callable[[str], int] | None = None
    _is_dnd_fn: Callable[[str], bool] | None = None
    _predebit_notice_fn: Callable[[str], datetime | None] | None = None
    _has_approval_fn: Callable[[str], bool] | None = None
    _executed_keys: set[str] = field(default_factory=set)

    def contacts_today(self, customer_ref: str) -> int:
        if self._contacts_today_fn:
            return self._contacts_today_fn(customer_ref)
        return 0

    def is_dnd(self, customer_ref: str) -> bool:
        if self._is_dnd_fn:
            return self._is_dnd_fn(customer_ref)
        return False

    def predebit_notice_sent_at(self, case_id: str) -> datetime | None:
        if self._predebit_notice_fn:
            return self._predebit_notice_fn(case_id)
        return None

    def has_approval(self, case_id: str) -> bool:
        if self._has_approval_fn:
            return self._has_approval_fn(case_id)
        return False

    def already_executed(self, idempotency_key: str) -> bool:
        return idempotency_key in self._executed_keys

    def mark_executed(self, idempotency_key: str):
        self._executed_keys.add(idempotency_key)


def evaluate(case: Case, event: PaymentEvent, ctx: PolicyContext, now: datetime) -> Verdict:
    """
    Deterministic policy engine.
    Every time-dependent check consumes explicit `now: datetime`.
    Guarantees deterministic, reproducible, testable verdicts.
    """
    now_ist = to_ist(now)
    candidates = set(CAUSE_TO_CANDIDATE_ACTIONS.get(case.root_cause, [Action.NO_ACTION]))
    denied: dict[Action, str] = {}
    triggers: list[str] = []

    def deny(action: Action, rule_id: str, reason: str):
        if action in candidates:
            candidates.discard(action)
            denied[action] = f"{rule_id}: {reason}"
            triggers.append(f"{rule_id}:{action.value}")

    # R01 — Global Kill Switch. Absolute first line.
    if not ctx.agent_enabled:
        triggers.append("R01:kill_switch")
        return Verdict(
            permitted=frozenset({Action.NO_ACTION}),
            denied={a: "R01: Global kill switch engaged" for a in candidates if a != Action.NO_ACTION},
            rule_triggers=triggers,
        )

    # R14 — Control Arm Isolation: Observe only, zero intervention.
    if case.cohort_arm == "control":
        triggers.append("R14:control_arm")
        return Verdict(
            permitted=frozenset({Action.NO_ACTION}),
            denied={a: "R14: Control arm — observation only" for a in candidates if a != Action.NO_ACTION},
            rule_triggers=triggers,
        )

    # R02 — Risk Hard Stop: Human review only. No automated recovery action.
    if case.root_cause in HARD_STOP:
        triggers.append("R02:risk_hard_stop")
        return Verdict(
            permitted=frozenset({Action.ESCALATE_HUMAN}),
            denied={a: "R02: Risk decline requires mandatory human investigation" for a in candidates if a != Action.ESCALATE_HUMAN},
            rule_triggers=triggers,
        )

    # R03 — Terminal Cause: Retry is mathematically futile and banned.
    if case.root_cause in NEVER_RETRY:
        deny(Action.RETRY_SAME_RAIL, "R03", f"Root cause '{case.root_cause.value}' cannot be fixed by retrying")

    # R04 — Attempt Cap: Maximum retry limit reached.
    if case.attempt_no >= MAX_ATTEMPTS:
        deny(Action.RETRY_SAME_RAIL, "R04", f"Maximum attempt cap ({MAX_ATTEMPTS}) reached")

    # R05 — Cool-off Window between retries.
    wait_hours = COOL_OFF_HOURS.get(case.attempt_no, 48)
    if case.last_action_at:
        last_at = case.last_action_at
        if last_at.tzinfo is None:
            last_at = last_at.replace(tzinfo=timezone.utc)
        curr_now = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        if curr_now - last_at < timedelta(hours=wait_hours):
            deny(Action.RETRY_SAME_RAIL, "R05", f"Cool-off window of {wait_hours}h has not elapsed since last attempt")

    # R06 — TRAI Quiet Hours (Commercial Comms restricted outside 09:00–21:00 IST).
    if not (QUIET_START <= now_ist.hour < QUIET_END):
        for a in (Action.NUDGE_CHECKOUT, Action.SWITCH_RAIL_LINK, Action.UPDATE_INSTRUMENT):
            deny(a, "R06", f"TRAI quiet hours: customer contact forbidden outside {QUIET_START}:00–{QUIET_END}:00 IST (current: {now_ist.strftime('%H:%M')} IST)")

    # R07 — Daily Contact Cap: Anti-harassment limitation.
    if ctx.contacts_today(case.customer_ref) >= MAX_CONTACTS_PER_DAY:
        for a in (Action.NUDGE_CHECKOUT, Action.SWITCH_RAIL_LINK, Action.UPDATE_INSTRUMENT):
            deny(a, "R07", f"Daily customer contact cap ({MAX_CONTACTS_PER_DAY}) reached for customer {case.customer_ref}")

    # R08 — DND / Consent Opt-out: Hard block.
    if ctx.is_dnd(case.customer_ref):
        for a in (Action.NUDGE_CHECKOUT, Action.SWITCH_RAIL_LINK, Action.UPDATE_INSTRUMENT):
            deny(a, "R08", "Customer has active DND / revoked comms consent")

    # R09 — RBI Digital Payments E-mandate Framework 2026: Pre-debit notice ≥ 24h.
    if event.is_recurring:
        notice_time = ctx.predebit_notice_sent_at(case.id)
        curr_now = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        if notice_time is None:
            deny(Action.RETRY_SAME_RAIL, "R09", "RBI E-mandate 2026: 24h pre-debit notification was not recorded")
        else:
            if notice_time.tzinfo is None:
                notice_time = notice_time.replace(tzinfo=timezone.utc)
            if curr_now - notice_time < timedelta(hours=PREDEBIT_NOTICE_HOURS):
                deny(Action.RETRY_SAME_RAIL, "R09", f"RBI E-mandate 2026: Mandatory {PREDEBIT_NOTICE_HOURS}h pre-debit notice period not elapsed")

    # R10 — RBI Digital Payments E-mandate Framework 2026: AFA Ceiling Thresholds.
    if event.is_recurring:
        ceiling = AFA_ELEVATED_PAISE if (event.mandate_category or "").lower() in AFA_ELEVATED_CATS else AFA_DEFAULT_PAISE
        if event.amount_paise > ceiling:
            deny(Action.RETRY_SAME_RAIL, "R10", f"RBI E-mandate 2026: Amount ₹{event.amount_paise / 100:,.2f} exceeds AFA-exempt ceiling ₹{ceiling / 100:,.2f}")

    # R11 — Active Promise-to-Pay Freeze: Do not harass customer who committed a date.
    if case.promise_to_pay_at:
        p_at = case.promise_to_pay_at
        if p_at.tzinfo is None:
            p_at = p_at.replace(tzinfo=timezone.utc)
        curr_now = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        if curr_now < p_at:
            for a in (Action.NUDGE_CHECKOUT, Action.RETRY_SAME_RAIL, Action.SWITCH_RAIL_LINK):
                deny(a, "R11", f"Active promise-to-pay commitment valid until {p_at.isoformat()}")

    # R12 — Merchant Configuration Bug: Customer must never be blamed or contacted.
    if case.root_cause == RootCause.MERCHANT_CONFIG:
        for a in (Action.NUDGE_CHECKOUT, Action.RETRY_SAME_RAIL, Action.SWITCH_RAIL_LINK, Action.UPDATE_INSTRUMENT):
            deny(a, "R12", "Defect is merchant-side configuration/integration; customer contact strictly prohibited")

    # R13 — Incentive Budget Cap: Rail switch discounts cap.
    if ctx.incentive_spent_paise >= ctx.incentive_budget_paise:
        deny(Action.SWITCH_RAIL_LINK, "R13", "Batch promotional incentive budget exhausted")

    # NO_ACTION is always safe and permitted
    candidates.add(Action.NO_ACTION)

    return Verdict(
        permitted=frozenset(candidates),
        denied=denied,
        rule_triggers=triggers,
    )
