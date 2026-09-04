from collections.abc import Callable
from dataclasses import dataclass

from backstop.models import Action, Case, PaymentEvent


@dataclass
class Tool:
    name: str
    action: Action
    description: str
    max_amount_paise: int  # Spend cap
    requires_approver: bool  # Four-eyes requirement
    rate_limit_per_hour: int
    fn: Callable[[Case, PaymentEvent, dict], dict]


def dummy_tool_exec(case: Case, event: PaymentEvent, params: dict) -> dict:
    return {"status": "success", "executed_at": "simulated"}


TOOL_REGISTRY: dict[Action, Tool] = {
    Action.RETRY_SAME_RAIL: Tool(
        name="retry_same_rail",
        action=Action.RETRY_SAME_RAIL,
        description="Trigger programmatic retry on the same payment rail with exponential backoff",
        max_amount_paise=5_000_000,  # ₹50,000 cap
        requires_approver=False,
        rate_limit_per_hour=100,
        fn=dummy_tool_exec,
    ),
    Action.SWITCH_RAIL_LINK: Tool(
        name="switch_rail_link",
        action=Action.SWITCH_RAIL_LINK,
        description="Generate alternative payment link on a different rail (UPI/Cards)",
        max_amount_paise=10_000_000,  # ₹1,00,000 cap
        requires_approver=False,
        rate_limit_per_hour=50,
        fn=dummy_tool_exec,
    ),
    Action.NUDGE_CHECKOUT: Tool(
        name="nudge_checkout",
        action=Action.NUDGE_CHECKOUT,
        description="Send single compliant checkout nudge message (SMS/WhatsApp) while intent is warm",
        max_amount_paise=10_000_000,
        requires_approver=False,
        rate_limit_per_hour=50,
        fn=dummy_tool_exec,
    ),
    Action.UPDATE_INSTRUMENT: Tool(
        name="update_instrument",
        action=Action.UPDATE_INSTRUMENT,
        description="Send instrument update link for expired cards or invalid VPAs",
        max_amount_paise=10_000_000,
        requires_approver=False,
        rate_limit_per_hour=30,
        fn=dummy_tool_exec,
    ),
    Action.SCHEDULE_FOLLOWUP: Tool(
        name="schedule_followup",
        action=Action.SCHEDULE_FOLLOWUP,
        description="Schedule time-shifted follow-up near salary/payday window",
        max_amount_paise=10_000_000,
        requires_approver=False,
        rate_limit_per_hour=100,
        fn=dummy_tool_exec,
    ),
    Action.ESCALATE_HUMAN: Tool(
        name="escalate_human",
        action=Action.ESCALATE_HUMAN,
        description="Route suspicious or high-risk case to human compliance team",
        max_amount_paise=10_000_000,
        requires_approver=True,
        rate_limit_per_hour=20,
        fn=dummy_tool_exec,
    ),
    Action.ALERT_MERCHANT: Tool(
        name="alert_merchant",
        action=Action.ALERT_MERCHANT,
        description="Alert merchant engineering team of configuration/integration defect",
        max_amount_paise=10_000_000,
        requires_approver=False,
        rate_limit_per_hour=50,
        fn=dummy_tool_exec,
    ),
    Action.NO_ACTION: Tool(
        name="no_action",
        action=Action.NO_ACTION,
        description="Deliberately take no automated action (control arm or policy restriction)",
        max_amount_paise=10_000_000,
        requires_approver=False,
        rate_limit_per_hour=1000,
        fn=dummy_tool_exec,
    ),
}
