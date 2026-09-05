import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlmodel import Session

from backstop.execute.lock import acquire_idempotency_lock
from backstop.execute.razorpay_client import RazorpayEnterpriseClient
from backstop.execute.registry import TOOL_REGISTRY
from backstop.ledger.chain import append as append_ledger
from backstop.models import Action, Case, PaymentEvent
from backstop.policy.engine import POLICY_VERSION, PolicyContext, evaluate

logger = logging.getLogger(__name__)
razorpay_client = RazorpayEnterpriseClient()


@dataclass
class ExecutionOutcome:
    status: str  # "executed" | "blocked" | "pending_approval" | "duplicate_noop" | "simulated"
    action: Action
    idempotency_key: str
    reason: str
    details: dict[str, Any]


def execute(
    action: Action,
    case: Case,
    event: PaymentEvent,
    ctx: PolicyContext,
    session: Session,
    now: datetime,
    params: dict | None = None,
) -> ExecutionOutcome:
    """
    5-Wall Gated Executor:
    Wall 1: Global Kill Switch Check
    Wall 2: Deterministic Post-Gate Re-Validation against physical record
    Wall 3: Tool Spend Cap Verification
    Wall 4: Four-Eyes Human Approval for material actions
    Wall 5: SHA-256 Distributed Idempotency Key (Redis SETNX lock, prevents duplicate charges)
    """
    params = params or {}
    m_id = getattr(event, "merchant_id", None) or getattr(case, "merchant_id", "merch_ecommerce_01")
    idempotency_key = hashlib.sha256(
        f"{m_id}|{event.payment_id}|{action.value}|{case.attempt_no}".encode()
    ).hexdigest()

    # --- WALL 1: Global Kill Switch ---
    if not ctx.agent_enabled:
        append_ledger(
            session=session,
            merchant_id=m_id,
            case_id=case.id,
            payment_id=event.payment_id,
            actor="system",
            stage="execute",
            payload={"action": action.value, "error": "kill_switch_engaged"},
            policy_version=POLICY_VERSION,
            outcome="blocked_kill_switch",
        )
        return ExecutionOutcome(
            status="blocked",
            action=action,
            idempotency_key=idempotency_key,
            reason="Wall 1: Global kill switch engaged",
            details={},
        )

    # --- WALL 2: Post-Gate Policy Check ---
    verdict = evaluate(case, event, ctx, now)
    if action not in verdict.permitted:
        deny_reason = verdict.denied.get(action, "Not permitted by current policy")
        append_ledger(
            session=session,
            merchant_id=m_id,
            case_id=case.id,
            payment_id=event.payment_id,
            actor="policy_engine",
            stage="postgate",
            payload={"action": action.value, "permitted": [a.value for a in verdict.permitted], "denied_reason": deny_reason},
            policy_version=POLICY_VERSION,
            outcome="rejected_postgate",
        )
        return ExecutionOutcome(
            status="blocked",
            action=action,
            idempotency_key=idempotency_key,
            reason=f"Wall 2: Post-gate rejected action '{action.value}': {deny_reason}",
            details={"verdict": verdict.denied},
        )

    tool = TOOL_REGISTRY.get(action)
    if not tool:
        return ExecutionOutcome(
            status="blocked",
            action=action,
            idempotency_key=idempotency_key,
            reason=f"Action {action.value} not registered in tool allow-list",
            details={},
        )

    # --- WALL 3: Spend Cap ---
    if event.amount_paise > tool.max_amount_paise:
        append_ledger(
            session=session,
            merchant_id=m_id,
            case_id=case.id,
            payment_id=event.payment_id,
            actor="executor",
            stage="execute",
            payload={"action": action.value, "amount_paise": event.amount_paise, "max_cap": tool.max_amount_paise},
            policy_version=POLICY_VERSION,
            outcome="blocked_spend_cap",
        )
        return ExecutionOutcome(
            status="blocked",
            action=action,
            idempotency_key=idempotency_key,
            reason=f"Wall 3: Transaction amount ₹{event.amount_paise/100:,.2f} exceeds tool cap ₹{tool.max_amount_paise/100:,.2f}",
            details={},
        )

    # --- WALL 4: Four-Eyes Approval ---
    if tool.requires_approver and not ctx.has_approval(case.id):
        append_ledger(
            session=session,
            merchant_id=m_id,
            case_id=case.id,
            payment_id=event.payment_id,
            actor="executor",
            stage="execute",
            payload={"action": action.value, "approval_required": True},
            policy_version=POLICY_VERSION,
            outcome="pending_approval",
        )
        return ExecutionOutcome(
            status="pending_approval",
            action=action,
            idempotency_key=idempotency_key,
            reason="Wall 4: Four-eyes authorization required for this action",
            details={},
        )

    # --- WALL 5: Redis Distributed SETNX Idempotency Lock ---
    lock_acquired = acquire_idempotency_lock(
        merchant_id=m_id,
        payment_id=event.payment_id,
        attempt_no=case.attempt_no,
        ttl_seconds=60,
    )
    if not lock_acquired or ctx.already_executed(idempotency_key):
        return ExecutionOutcome(
            status="duplicate_noop",
            action=action,
            idempotency_key=idempotency_key,
            reason=f"Wall 5: Idempotency lock active ({idempotency_key[:12]}...), duplicate execution prevented across pods",
            details={},
        )

    # Mark idempotency key as consumed locally as well
    ctx.mark_executed(idempotency_key)

    # Additional execution safeguards: Order cancellation for rail switch
    extra_details = {}
    if not ctx.dry_run and action == Action.SWITCH_RAIL_LINK and event.order_id:
        cancel_res = razorpay_client.cancel_order(event.order_id, idempotency_key=idempotency_key)
        extra_details["cancelled_original_order"] = cancel_res

    # Record execution in ledger
    if ctx.dry_run:
        exec_result = {"status": "dry_run", "action": action.value, "simulated": True}
    else:
        exec_result = tool.fn(case, event, params)
        exec_result.update(extra_details)
    status_str = "simulated" if ctx.dry_run else "executed"

    # If schedule_followup signals it, persist the QueueJob in the executor's existing session
    # (avoids nested session / SQLite lock that would occur in the tool fn itself)
    if exec_result.get("persist_queue_job"):
        try:
            from backstop.models import QueueJob
            from sqlmodel import select as sql_select
            followup_id = exec_result.get("followup_event_id", f"followup_{event.event_id}_{case.attempt_no}")
            existing_job = session.exec(sql_select(QueueJob).where(QueueJob.event_id == followup_id)).first()
            if not existing_job:
                followup_job = QueueJob(
                    event_id=followup_id,
                    merchant_id=m_id,
                    status="pending",
                    attempts=0,
                    max_attempts=3,
                )
                session.add(followup_job)
                session.flush()
                exec_result["job_id"] = followup_job.id
                exec_result["persisted"] = True
            else:
                exec_result["job_id"] = existing_job.id
                exec_result["persisted"] = True
        except Exception as e:
            logger.warning("Failed to persist QueueJob for schedule_followup: %s", e)
            exec_result["persisted"] = False
            exec_result["persist_error"] = str(e)

    append_ledger(
        session=session,
        merchant_id=m_id,
        case_id=case.id,
        payment_id=event.payment_id,
        actor="executor",
        stage="execute",
        payload={"action": action.value, "dry_run": ctx.dry_run, "idempotency_key": idempotency_key, "params": params},
        policy_version=POLICY_VERSION,
        outcome=status_str,
    )

    return ExecutionOutcome(
        status=status_str,
        action=action,
        idempotency_key=idempotency_key,
        reason=f"Action '{action.value}' successfully executed ({status_str})",
        details=exec_result,
    )
