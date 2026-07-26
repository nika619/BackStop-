"""
BackStop — DB-Backed Persistent Queue Worker

Replaces FastAPI's volatile in-memory BackgroundTasks with a durable SQLite-backed queue.

Why this matters:
  - FastAPI BackgroundTasks live in Python heap. Pod restart = all pending jobs lost.
  - QueueJob rows in SQLite survive restarts, OOM kills, and redeploys.
  - On startup, lifespan() calls recover_interrupted_jobs() to resume incomplete work.
  - process_job_by_event_id() is the single entry point for both fast-path (background task)
    and slow-path (periodic drain loop) execution.

Job lifecycle:
  pending → processing → completed
                      → failed (retried up to max_attempts)
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from backstop.database import engine
from backstop.models import Action, Case, PaymentEvent, QueueJob
from backstop.planner.planner import plan
from backstop.policy.engine import POLICY_VERSION, PolicyContext, evaluate

logger = logging.getLogger(__name__)

# Drain interval: check DB queue every N seconds
DRAIN_INTERVAL_SECONDS = 5
# Max jobs to process per drain cycle (prevents runaway long drains)
DRAIN_BATCH_SIZE = 20


def process_job_by_event_id(event_id: str) -> bool:
    """
    Process a single QueueJob identified by event_id.
    - Marks job as `processing`, runs the full plan+execute pipeline, marks `completed`.
    - On error: increments attempts; marks `failed` if max_attempts exhausted.
    - Returns True if job was successfully processed, False otherwise.

    This function is called:
      1. Immediately as a FastAPI BackgroundTask (fast path, best-effort)
      2. By drain_pending_jobs() on a periodic schedule (reliable path)
    """
    with Session(engine) as session:
        # Find the queue job
        job = session.exec(select(QueueJob).where(QueueJob.event_id == event_id)).first()
        if not job:
            logger.warning("QueueJob not found for event_id=%s", event_id)
            return False

        if job.status in ("completed",):
            logger.debug("QueueJob event_id=%s already %s — skipping", event_id, job.status)
            return True

        if job.status == "processing":
            # Another worker picked it up — skip (idempotency)
            logger.debug("QueueJob event_id=%s already processing — skipping", event_id)
            return False

        # Mark as processing (atomic claim)
        job.status = "processing"
        job.attempts += 1
        job.updated_at = datetime.now(timezone.utc)
        session.add(job)
        session.commit()

    # Do the work in a fresh session to avoid long transactions
    try:
        _run_recovery_pipeline(event_id)
        # Mark completed
        with Session(engine) as session:
            job = session.exec(select(QueueJob).where(QueueJob.event_id == event_id)).first()
            if job:
                job.status = "completed"
                job.updated_at = datetime.now(timezone.utc)
                session.add(job)
                session.commit()
        logger.info("QueueJob completed: event_id=%s", event_id)
        return True
    except Exception as exc:
        logger.error("QueueJob failed: event_id=%s error=%s", event_id, exc, exc_info=True)
        with Session(engine) as session:
            job = session.exec(select(QueueJob).where(QueueJob.event_id == event_id)).first()
            if job:
                if job.attempts >= job.max_attempts:
                    job.status = "failed"
                    logger.error("QueueJob permanently failed after %s attempts: event_id=%s", job.attempts, event_id)
                else:
                    job.status = "pending"  # Reset for retry by drain loop
                job.error_message = str(exc)[:500]
                job.updated_at = datetime.now(timezone.utc)
                session.add(job)
                session.commit()
        return False


def _run_recovery_pipeline(event_id: str):
    """
    Core recovery pipeline: fetch event → find/create case → policy evaluate → plan → execute.
    Isolated in its own function for clean error boundary.

    Note: QueueJobs with event_id prefixed 'followup_' are scheduled intent records, not
    real payment events. They are skipped here and handled by a scheduled follow-up mechanism.
    """
    from backstop.execute.executor import execute
    from backstop.ledger.chain import append as append_ledger

    # Skip followup placeholder jobs — they represent deferred intent, not re-ingestable events
    if event_id.startswith("followup_"):
        logger.info("Skipping followup placeholder job: %s (not a real payment event)", event_id)
        return

    with Session(engine) as session:
        # Fetch the payment event
        event = session.exec(select(PaymentEvent).where(PaymentEvent.event_id == event_id)).first()
        if not event:
            logger.warning("PaymentEvent not found for event_id=%s — skipping", event_id)
            return

        # Find the associated case
        case = session.exec(select(Case).where(Case.payment_event_id == event.id)).first()
        if not case:
            logger.warning("Case not found for event.id=%s — skipping", event.id)
            return

        # Skip cases already past open
        if case.status not in ("open",):
            logger.info(
                "Case %s is status=%s — no re-processing needed", case.id, case.status
            )
            return

        now_dt = datetime.now(timezone.utc)

        # 1. Policy evaluation
        ctx = PolicyContext(
            agent_enabled=True,
            dry_run=False,  # Real execution — not dry run
            merchant_id=event.merchant_id,
        )
        verdict = evaluate(case, event, ctx, now_dt)
        append_ledger(
            session=session,
            case_id=case.id,
            payment_id=event.payment_id,
            merchant_id=event.merchant_id,
            actor="queue_worker",
            stage="pregate",
            payload={
                "permitted": [a.value for a in verdict.permitted],
                "denied": {a.value: r for a, r in verdict.denied.items()},
            },
            policy_version=POLICY_VERSION,
        )

        # 2. Plan (Gemini or heuristic)
        chosen_action, plan_details = plan(case, event, verdict.permitted)
        append_ledger(
            session=session,
            case_id=case.id,
            payment_id=event.payment_id,
            merchant_id=event.merchant_id,
            actor="planner_gemini",
            stage="plan",
            payload=plan_details,
            policy_version=POLICY_VERSION,
        )

        # 3. Gated execution
        outcome = execute(chosen_action, case, event, ctx, session, now_dt, params=plan_details)

        # 4. Update case lifecycle — CORRECT status mapping
        #    dispatch ≠ recovery; recovery only confirmed on payment.captured webhook
        case.last_action = chosen_action
        case.last_action_at = now_dt
        case.attempt_no += 1

        if chosen_action in (Action.NUDGE_CHECKOUT, Action.SWITCH_RAIL_LINK, Action.UPDATE_INSTRUMENT):
            case.contacts_sent += 1

        if outcome.status in ("executed", "simulated"):
            if chosen_action == Action.NO_ACTION:
                case.status = "closed"
                case.recovered_paise = 0
            elif chosen_action == Action.ESCALATE_HUMAN:
                case.status = "escalated"
                case.recovered_paise = 0
            else:
                # Action was dispatched — awaiting customer action + capture webhook
                case.status = "action_dispatched"
                case.recovered_paise = 0  # NOT recovered yet — confirmed only on capture
                # Store recovery_ref from dispatch details for attribution
                recovery_ref = (
                    outcome.details.get("payment_link_id")
                    or outcome.details.get("api_response", {}).get("id")
                )
                if recovery_ref:
                    case.recovery_ref = recovery_ref
        elif outcome.status == "blocked":
            case.status = "blocked"
        elif outcome.status == "pending_approval":
            case.status = "escalated"

        session.add(case)
        session.commit()

        logger.info(
            "Pipeline completed: event_id=%s case_id=%s action=%s case_status=%s",
            event_id, case.id, chosen_action.value, case.status,
        )


def drain_pending_jobs(batch_size: int = DRAIN_BATCH_SIZE) -> int:
    """
    Pick up all `pending` QueueJobs and process them.
    Called periodically by the async background loop in api.py lifespan.
    Returns the number of jobs processed in this cycle.
    """
    with Session(engine) as session:
        pending_jobs = session.exec(
            select(QueueJob)
            .where(QueueJob.status == "pending")
            .limit(batch_size)
        ).all()
        event_ids = [j.event_id for j in pending_jobs]

    if not event_ids:
        return 0

    logger.info("drain_pending_jobs: found %d pending jobs", len(event_ids))
    processed = 0
    for event_id in event_ids:
        try:
            success = process_job_by_event_id(event_id)
            if success:
                processed += 1
        except Exception as e:
            logger.error("drain_pending_jobs: unhandled error for event_id=%s: %s", event_id, e)

    return processed


def recover_interrupted_jobs():
    """
    On startup: reset any jobs stuck in `processing` state back to `pending`.
    These were interrupted mid-execution by a pod restart or OOM kill.
    Called once during lifespan startup.
    """
    with Session(engine) as session:
        stuck = session.exec(
            select(QueueJob).where(QueueJob.status == "processing")
        ).all()
        for job in stuck:
            job.status = "pending"
            job.error_message = "Reset from interrupted processing on startup"
            job.updated_at = datetime.now(timezone.utc)
            session.add(job)
        if stuck:
            session.commit()
            logger.warning(
                "Startup recovery: reset %d interrupted QueueJobs back to pending", len(stuck)
            )
        else:
            logger.info("Startup recovery: no interrupted jobs found")


async def queue_drain_loop():
    """
    Asyncio background coroutine that drains the persistent DB queue every N seconds.
    Runs for the lifetime of the FastAPI process.
    This is the durable replacement for volatile BackgroundTasks.
    """
    logger.info("Queue drain loop started (interval=%ds)", DRAIN_INTERVAL_SECONDS)
    while True:
        try:
            processed = drain_pending_jobs()
            if processed > 0:
                logger.info("Queue drain: processed %d jobs", processed)
        except Exception as e:
            logger.error("Queue drain loop error: %s", e, exc_info=True)
        await asyncio.sleep(DRAIN_INTERVAL_SECONDS)
