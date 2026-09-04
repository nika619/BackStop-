import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlmodel import Session

from backstop.execute.registry import TOOL_REGISTRY
from backstop.ledger.chain import append as append_ledger
from backstop.models import Action, Case, PaymentEvent
from backstop.policy.engine import POLICY_VERSION, PolicyContext, evaluate

logger = logging.getLogger(__name__)


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
    Wall 5: SHA-256 Idempotency Key (prevents duplicate charges)
    """
    params = params or {}
    idempotency_key = hashlib.sha256(
        f"{event.payment_id}|{action.value}|{case.attempt_no}".encode()
    ).hexdigest()

    # --- WALL 1: Global Kill Switch ---
    if not ctx.agent_enabled:
        append_ledger(
            session=session,
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

    # --- WALL 5: Idempotency Key ---
    if ctx.already_executed(idempotency_key):
        return ExecutionOutcome(
            status="duplicate_noop",
            action=action,
            idempotency_key=idempotency_key,
            reason=f"Wall 5: Idempotency key {idempotency_key[:12]}... already processed",
            details={},
        )

    # Mark idempotency key as consumed
    ctx.mark_executed(idempotency_key)

    # Record execution in ledger
    exec_result = tool.fn(case, event, params)
    status_str = "simulated" if ctx.dry_run else "executed"

    append_ledger(
        session=session,
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
