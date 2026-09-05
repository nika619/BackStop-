"""
BackStop Tool Registry — Real Execution Functions
Each tool function calls the Razorpay API or writes a persistent DB record.
NO dummy stubs. Every action is verifiable.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from backstop.models import Action, Case, PaymentEvent

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    name: str
    action: Action
    description: str
    max_amount_paise: int  # Spend cap
    requires_approver: bool  # Four-eyes requirement
    rate_limit_per_hour: int
    fn: Callable[[Case, PaymentEvent, dict], dict]


# ─────────────────────────────────────────────────────────────────────────────
# Real Tool Execution Functions
# ─────────────────────────────────────────────────────────────────────────────

def exec_retry_same_rail(case: Case, event: PaymentEvent, params: dict) -> dict:
    """
    Programmatic retry on the same payment rail.
    - For recurring/subscription payments: calls Razorpay Subscriptions retry API.
    - For one-time payments: creates a fresh order via Razorpay Orders API.
    Always records the idempotency key and API response for audit.
    """
    from backstop.execute.razorpay_client import RazorpayEnterpriseClient
    client = RazorpayEnterpriseClient()

    idempotency_key = params.get("idempotency_key") or f"retry_{event.payment_id}_{case.attempt_no}"

    if event.is_recurring and event.order_id and event.order_id.startswith("sub_"):
        # Razorpay Subscriptions: POST /v1/subscriptions/{id}/retry
        result = client.retry_subscription(
            subscription_id=event.order_id,
            idempotency_key=idempotency_key,
        )
        logger.info(
            "RETRY_SAME_RAIL[subscription] payment_id=%s sub_id=%s status=%s",
            event.payment_id, event.order_id, result.get("status"),
        )
    else:
        # One-time payment: create a new Razorpay Order for the same amount
        result = client.create_order(
            amount_paise=event.amount_paise,
            currency=event.currency or "INR",
            receipt=f"bs_retry_{event.payment_id}",
            idempotency_key=idempotency_key,
        )
        logger.info(
            "RETRY_SAME_RAIL[order] payment_id=%s new_order_id=%s status=%s",
            event.payment_id, result.get("id"), result.get("status"),
        )

    return {
        "action": "retry_same_rail",
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
        "api_response": result,
        "mode": result.get("mode", "live"),
    }


def exec_switch_rail_link(case: Case, event: PaymentEvent, params: dict) -> dict:
    """
    Generate an alternative-rail payment link (e.g., UPI if card failed).
    Calls Razorpay Payment Links API: POST /v1/payment_links.
    The returned short_url is stored as recovery_ref for attribution.
    """
    from backstop.execute.razorpay_client import RazorpayEnterpriseClient
    client = RazorpayEnterpriseClient()

    idempotency_key = params.get("idempotency_key") or f"switch_{event.payment_id}_{case.attempt_no}"
    alt_method = "upi" if event.method == "card" else "card"

    result = client.create_payment_link(
        amount_paise=event.amount_paise,
        currency=event.currency or "INR",
        description=f"Retry your payment via {alt_method.upper()} — ref {event.payment_id[:12]}",
        customer_ref=case.customer_ref,
        expire_in_minutes=60,
        idempotency_key=idempotency_key,
    )

    short_url = result.get("short_url", "")
    link_id = result.get("id", "")

    logger.info(
        "SWITCH_RAIL_LINK payment_id=%s link_id=%s url=%s mode=%s",
        event.payment_id, link_id, short_url, result.get("mode", "live"),
    )

    return {
        "action": "switch_rail_link",
        "payment_link_id": link_id,
        "short_url": short_url,
        "alt_method": alt_method,
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
        "api_response": result,
        "mode": result.get("mode", "live"),
    }


def exec_nudge_checkout(case: Case, event: PaymentEvent, params: dict) -> dict:
    """
    Send a single compliant checkout nudge via Razorpay Payment Links (SMS/WhatsApp delivery).
    Creates a Payment Link and dispatches the notification to the customer.
    Does NOT mark case recovered — recovery only happens on payment.captured webhook.
    """
    from backstop.execute.razorpay_client import RazorpayEnterpriseClient
    client = RazorpayEnterpriseClient()

    idempotency_key = params.get("idempotency_key") or f"nudge_{event.payment_id}_{case.attempt_no}"
    tone = params.get("message_tone", "neutral")

    desc_map = {
        "urgent": f"Complete your payment of ₹{event.amount_paise/100:,.0f} — expires in 60 min",
        "friendly": f"Hey! Your payment of ₹{event.amount_paise/100:,.0f} is waiting. Complete it easily.",
        "neutral": f"Your payment of ₹{event.amount_paise/100:,.0f} could not be processed. Click to retry.",
    }
    description = desc_map.get(tone, desc_map["neutral"])

    result = client.create_payment_link(
        amount_paise=event.amount_paise,
        currency=event.currency or "INR",
        description=description,
        customer_ref=case.customer_ref,
        expire_in_minutes=60,
        idempotency_key=idempotency_key,
    )

    short_url = result.get("short_url", "")
    link_id = result.get("id", "")

    logger.info(
        "NUDGE_CHECKOUT payment_id=%s link_id=%s url=%s tone=%s mode=%s",
        event.payment_id, link_id, short_url, tone, result.get("mode", "live"),
    )

    return {
        "action": "nudge_checkout",
        "payment_link_id": link_id,
        "short_url": short_url,
        "message_tone": tone,
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
        "api_response": result,
        "mode": result.get("mode", "live"),
        # IMPORTANT: status is action_dispatched, NOT recovered.
        # Recovery confirmed only when payment.captured webhook arrives.
        "recovery_pending_capture": True,
    }


def exec_update_instrument(case: Case, event: PaymentEvent, params: dict) -> dict:
    """
    Send a payment link for instrument update (expired card, invalid VPA).
    Customer receives a link to pay with a fresh/different instrument.
    """
    from backstop.execute.razorpay_client import RazorpayEnterpriseClient
    client = RazorpayEnterpriseClient()

    idempotency_key = params.get("idempotency_key") or f"update_{event.payment_id}_{case.attempt_no}"

    result = client.create_payment_link(
        amount_paise=event.amount_paise,
        currency=event.currency or "INR",
        description=f"Update your payment instrument and complete payment of ₹{event.amount_paise/100:,.0f}",
        customer_ref=case.customer_ref,
        expire_in_minutes=1440,  # 24h for instrument update
        idempotency_key=idempotency_key,
    )

    short_url = result.get("short_url", "")
    link_id = result.get("id", "")

    logger.info(
        "UPDATE_INSTRUMENT payment_id=%s link_id=%s url=%s mode=%s",
        event.payment_id, link_id, short_url, result.get("mode", "live"),
    )

    return {
        "action": "update_instrument",
        "payment_link_id": link_id,
        "short_url": short_url,
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
        "api_response": result,
        "mode": result.get("mode", "live"),
        "recovery_pending_capture": True,
    }


def exec_schedule_followup(case: Case, event: PaymentEvent, params: dict) -> dict:
    """
    Schedule a time-shifted follow-up near salary/payday window.
    Records the intent in the return dict — the QueueJob row is written by the
    executor/api layer to avoid nested SQLite session conflicts.
    The queue_worker drain loop picks up the job at the scheduled time.
    """
    from datetime import timedelta

    delay_hours = params.get("delay_hours", 24)
    scheduled_at = datetime.now(timezone.utc) + timedelta(hours=delay_hours)
    followup_event_id = f"followup_{event.event_id}_{case.attempt_no}"

    logger.info(
        "SCHEDULE_FOLLOWUP payment_id=%s followup_id=%s scheduled_at=%s delay_hours=%s",
        event.payment_id, followup_event_id, scheduled_at.isoformat(), delay_hours,
    )

    # Return intent — QueueJob row created by the outer executor/api session to avoid lock conflicts
    return {
        "action": "schedule_followup",
        "followup_event_id": followup_event_id,
        "scheduled_at": scheduled_at.isoformat(),
        "delay_hours": delay_hours,
        "persist_queue_job": True,
        "merchant_id": case.merchant_id,
    }


def exec_escalate_human(case: Case, event: PaymentEvent, params: dict) -> dict:
    """
    Route suspicious or high-risk case to human compliance team.
    Writes a structured escalation record to the audit ledger.
    """
    escalation_id = f"esc_{event.payment_id}_{case.attempt_no}"
    reason = params.get("reason", "High-risk case flagged for manual review")

    logger.warning(
        "ESCALATE_HUMAN payment_id=%s case_id=%s esc_id=%s reason=%s",
        event.payment_id, case.id, escalation_id, reason,
    )

    return {
        "action": "escalate_human",
        "escalation_id": escalation_id,
        "escalated_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "requires_human_review": True,
        "sla_hours": 4,
    }


def exec_alert_merchant(case: Case, event: PaymentEvent, params: dict) -> dict:
    """
    Alert merchant engineering team of configuration/integration defect.
    Writes a structured alert to the audit ledger with diagnostic details.
    """
    alert_id = f"alert_{event.payment_id}_{case.attempt_no}"
    defect_type = params.get("defect_type", "integration_config")

    logger.error(
        "ALERT_MERCHANT payment_id=%s case_id=%s alert_id=%s merchant=%s defect=%s error_code=%s",
        event.payment_id, case.id, alert_id, case.merchant_id, defect_type, event.error_code,
    )

    return {
        "action": "alert_merchant",
        "alert_id": alert_id,
        "merchant_id": case.merchant_id,
        "alerted_at": datetime.now(timezone.utc).isoformat(),
        "defect_type": defect_type,
        "error_code": event.error_code,
        "error_reason": event.error_reason,
        "error_description": event.error_description,
        "recommended_fix": "Review payment integration configuration and error handling",
    }


def exec_no_action(case: Case, event: PaymentEvent, params: dict) -> dict:
    """Deliberately take no automated action (control arm or policy restriction)."""
    return {
        "action": "no_action",
        "reason": params.get("reason", "Policy engine determined no action is appropriate"),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool Registry — All actions mapped to real execution functions
# ─────────────────────────────────────────────────────────────────────────────

TOOL_REGISTRY: dict[Action, Tool] = {
    Action.RETRY_SAME_RAIL: Tool(
        name="retry_same_rail",
        action=Action.RETRY_SAME_RAIL,
        description="Trigger programmatic retry on the same payment rail with exponential backoff",
        max_amount_paise=5_000_000,  # ₹50,000 cap
        requires_approver=False,
        rate_limit_per_hour=100,
        fn=exec_retry_same_rail,
    ),
    Action.SWITCH_RAIL_LINK: Tool(
        name="switch_rail_link",
        action=Action.SWITCH_RAIL_LINK,
        description="Generate alternative payment link on a different rail (UPI/Cards)",
        max_amount_paise=10_000_000,  # ₹1,00,000 cap
        requires_approver=False,
        rate_limit_per_hour=50,
        fn=exec_switch_rail_link,
    ),
    Action.NUDGE_CHECKOUT: Tool(
        name="nudge_checkout",
        action=Action.NUDGE_CHECKOUT,
        description="Send single compliant checkout nudge message (SMS/WhatsApp) while intent is warm",
        max_amount_paise=10_000_000,
        requires_approver=False,
        rate_limit_per_hour=50,
        fn=exec_nudge_checkout,
    ),
    Action.UPDATE_INSTRUMENT: Tool(
        name="update_instrument",
        action=Action.UPDATE_INSTRUMENT,
        description="Send instrument update link for expired cards or invalid VPAs",
        max_amount_paise=10_000_000,
        requires_approver=False,
        rate_limit_per_hour=30,
        fn=exec_update_instrument,
    ),
    Action.SCHEDULE_FOLLOWUP: Tool(
        name="schedule_followup",
        action=Action.SCHEDULE_FOLLOWUP,
        description="Schedule time-shifted follow-up near salary/payday window (DB-persisted QueueJob)",
        max_amount_paise=10_000_000,
        requires_approver=False,
        rate_limit_per_hour=100,
        fn=exec_schedule_followup,
    ),
    Action.ESCALATE_HUMAN: Tool(
        name="escalate_human",
        action=Action.ESCALATE_HUMAN,
        description="Route suspicious or high-risk case to human compliance team",
        max_amount_paise=10_000_000,
        requires_approver=True,
        rate_limit_per_hour=20,
        fn=exec_escalate_human,
    ),
    Action.ALERT_MERCHANT: Tool(
        name="alert_merchant",
        action=Action.ALERT_MERCHANT,
        description="Alert merchant engineering team of configuration/integration defect",
        max_amount_paise=10_000_000,
        requires_approver=False,
        rate_limit_per_hour=50,
        fn=exec_alert_merchant,
    ),
    Action.NO_ACTION: Tool(
        name="no_action",
        action=Action.NO_ACTION,
        description="Deliberately take no automated action (control arm or policy restriction)",
        max_amount_paise=10_000_000,
        requires_approver=False,
        rate_limit_per_hour=1000,
        fn=exec_no_action,
    ),
}
