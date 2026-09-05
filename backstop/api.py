import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, select

from backstop.database import get_session, init_db
from backstop.diagnose.bank_health import get_bank_health, set_bank_health
from backstop.diagnose.taxonomy import (
    CAUSE_TO_CANDIDATE_ACTIONS,
    HARD_STOP,
    NEVER_RETRY,
)
from backstop.eval.generator import generate
from backstop.eval.report import run_full_benchmark
from backstop.execute.executor import execute
from backstop.ingest.batch import import_batch_records
from backstop.ingest.webhook import router as webhook_router
from backstop.ledger.chain import append as append_ledger
from backstop.ledger.chain import tamper_entry, verify_chain
from backstop.models import (
    Action,
    BankHealthTelemetry,
    Case,
    LedgerEntry,
    MerchantPolicy,
    PaymentEvent,
    RootCause,
)
from backstop.planner.planner import PROMPT_VERSION, plan
from backstop.planner.redact import redact
from backstop.policy.calendar import to_ist
from backstop.policy.engine import (
    POLICY_VERSION,
    PolicyContext,
    evaluate,
)

# Global Kill Switch State (In-memory + Ledger logged)
GLOBAL_KILL_SWITCH = {"enabled": True}
CACHED_BENCHMARK = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Recover any QueueJobs that were interrupted by a previous pod restart/OOM
    from backstop.ingest.queue_worker import recover_interrupted_jobs, queue_drain_loop
    recover_interrupted_jobs()
    # Start the persistent DB-backed queue drain loop (replaces volatile BackgroundTasks)
    drain_task = asyncio.create_task(queue_drain_loop())
    yield
    drain_task.cancel()
    try:
        await drain_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Backstop API — Razorpay AI Buildathon 2026",
    description="Deterministic Policy-Gated AI Revenue Recovery Engine for Failed Razorpay Payments",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)


@app.get("/")
def root_status():
    return {
        "service": "Backstop Revenue Recovery Engine",
        "track": "03 — AI Revenue Recovery (Razorpay Buildathon 2026)",
        "status": "online",
        "policy_version": POLICY_VERSION,
        "docs_url": "/docs",
        "console_url": "http://localhost:5173",
        "endpoints": {
            "health": "/api/health",
            "benchmark": "/api/benchmark",
            "cases": "/api/cases",
            "policies": "/api/policies",
            "kill_switch": "/api/kill-switch",
            "ledger_verify": "/api/ledger/verify",
            "webhooks": "/webhooks/razorpay"
        }
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "backstop",
        "version": "1.0.0",
        "policy_version": POLICY_VERSION,
        "kill_switch_active": not GLOBAL_KILL_SWITCH["enabled"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/benchmark")
def get_benchmark(recompute: bool = False):
    global CACHED_BENCHMARK
    if CACHED_BENCHMARK is None or recompute:
        benchmark_data = run_full_benchmark(n=1000, seed=20260901)
        CACHED_BENCHMARK = {
            "n": benchmark_data["n"],
            "seed": benchmark_data["seed"],
            "incremental_inr": benchmark_data["incremental_inr"],
            "lift_stats": benchmark_data["lift_stats"],
            "metrics": {
                "do_nothing": {
                    "strategy": "Do nothing (Control)",
                    "gross_recovered_inr": benchmark_data["do_nothing"].gross_recovered_inr,
                    "incremental_inr": 0.0,
                    "recovery_rate": benchmark_data["do_nothing"].recovery_rate,
                    "contacts_sent": benchmark_data["do_nothing"].total_contacts_sent,
                    "contacts_per_thousand_inr": benchmark_data["do_nothing"].contacts_per_thousand_inr,
                    "policy_violations": benchmark_data["do_nothing"].policy_violations,
                    "hard_stops_auto_actioned": benchmark_data["do_nothing"].hard_stops_auto_actioned,
                    "median_recovery_time_hours": benchmark_data["do_nothing"].median_recovery_time_hours,
                },
                "retry_all": {
                    "strategy": "Retry-all ×3 (Naive)",
                    "gross_recovered_inr": benchmark_data["retry_all"].gross_recovered_inr,
                    "incremental_inr": max(0, benchmark_data["retry_all"].gross_recovered_inr - benchmark_data["do_nothing"].gross_recovered_inr),
                    "recovery_rate": benchmark_data["retry_all"].recovery_rate,
                    "contacts_sent": benchmark_data["retry_all"].total_contacts_sent,
                    "contacts_per_thousand_inr": benchmark_data["retry_all"].contacts_per_thousand_inr,
                    "policy_violations": benchmark_data["retry_all"].policy_violations,
                    "hard_stops_auto_actioned": benchmark_data["retry_all"].hard_stops_auto_actioned,
                    "median_recovery_time_hours": benchmark_data["retry_all"].median_recovery_time_hours,
                },
                "backstop": {
                    "strategy": "Backstop (Agent)",
                    "gross_recovered_inr": benchmark_data["backstop"].gross_recovered_inr,
                    "incremental_inr": benchmark_data["incremental_inr"],
                    "recovery_rate": benchmark_data["backstop"].recovery_rate,
                    "contacts_sent": benchmark_data["backstop"].total_contacts_sent,
                    "contacts_per_thousand_inr": benchmark_data["backstop"].contacts_per_thousand_inr,
                    "policy_violations": benchmark_data["backstop"].policy_violations,
                    "hard_stops_auto_actioned": benchmark_data["backstop"].hard_stops_auto_actioned,
                    "median_recovery_time_hours": benchmark_data["backstop"].median_recovery_time_hours,
                },
            },
        }
    return CACHED_BENCHMARK


@app.get("/api/merchants")
def list_merchants(session: Session = Depends(get_session)):
    """Retrieve all isolated multi-tenant merchant configurations."""
    merchants = session.exec(select(MerchantPolicy)).all()
    return {"merchants": merchants}


@app.get("/api/bank-health")
def list_bank_health(session: Session = Depends(get_session)):
    """Retrieve real-time bank health success rate telemetry and outage indicators."""
    telemetry = session.exec(select(BankHealthTelemetry)).all()
    return {"banks": telemetry}


class BankHealthUpdateRequest(BaseModel):
    bank_code: str
    success_rate: float
    is_outage: bool = False


@app.post("/api/bank-health")
def update_bank_health(req: BankHealthUpdateRequest, session: Session = Depends(get_session)):
    """Simulate or update live bank health telemetry (e.g. HDFC outage simulation)."""
    set_bank_health(req.bank_code, req.success_rate, req.is_outage)
    return {"status": "updated", "bank_code": req.bank_code, "success_rate": req.success_rate, "is_outage": req.is_outage}


@app.get("/api/cases")
def list_cases(
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    merchant_id: str | None = None,
    root_cause: str | None = None,
    cohort_arm: str | None = None,
    status: str | None = None,
    session: Session = Depends(get_session),
):
    query = select(Case, PaymentEvent).where(Case.payment_event_id == PaymentEvent.id)
    if merchant_id:
        query = query.where(Case.merchant_id == merchant_id)
    if root_cause:
        query = query.where(Case.root_cause == root_cause)
    if cohort_arm:
        query = query.where(Case.cohort_arm == cohort_arm)
    if status:
        query = query.where(Case.status == status)

    query = query.order_by(Case.created_at.desc()).offset(offset).limit(limit)  # type: ignore
    results = session.exec(query).all()

    cases_out = []
    for c, ev in results:
        cases_out.append({
            "case_id": c.id,
            "merchant_id": c.merchant_id,
            "payment_id": ev.payment_id,
            "customer_ref": c.customer_ref,
            "amount_inr": ev.amount_paise / 100.0,
            "method": ev.method,
            "root_cause": c.root_cause.value,
            "cause_confidence": c.cause_confidence,
            "status": c.status,
            "cohort_arm": c.cohort_arm,
            "attempt_no": c.attempt_no,
            "contacts_sent": c.contacts_sent,
            "failed_at": ev.failed_at.isoformat(),
            "last_action": c.last_action.value if c.last_action else None,
        })
    return {"total": len(cases_out), "cases": cases_out}


@app.get("/api/cases/{case_id}/timeline")
def get_case_timeline(case_id: str, session: Session = Depends(get_session)):
    """
    Retrieve the detailed, high-resolution visual lifecycle of a payment case:
    Event Ingest -> Deterministic Diagnosis -> Policy Pre-gate (Permitted & Denied rules) ->
    Redacted Planner Prompt -> Gemini Output -> 5-Wall Post-Gate -> Executed Action -> Hash Chain Ledger Stamp
    """
    case = session.exec(select(Case).where(Case.id == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    event = session.exec(select(PaymentEvent).where(PaymentEvent.id == case.payment_event_id)).first()
    if not event:
        raise HTTPException(status_code=404, detail="PaymentEvent not found")

    # Evaluate current policy status
    ctx = PolicyContext(agent_enabled=GLOBAL_KILL_SWITCH["enabled"], dry_run=True)
    now_dt = event.failed_at or datetime.now(timezone.utc)
    verdict = evaluate(case, event, ctx, now_dt)

    # Redacted payload representation
    redacted_data = redact(case, event, verdict.permitted)

    # Fetch audit ledger entries for this case
    ledger_entries = session.exec(
        select(LedgerEntry).where(LedgerEntry.case_id == case_id).order_by(LedgerEntry.seq.asc())  # type: ignore
    ).all()

    timeline_steps = [
        {
            "step": 1,
            "title": "Ingest & Verification",
            "actor": "Razorpay Ingest Gateway",
            "timestamp": event.failed_at.isoformat(),
            "status": "verified",
            "details": {
                "event_id": event.event_id,
                "payment_id": event.payment_id,
                "amount": f"₹{event.amount_paise / 100:,.2f}",
                "method": event.method.upper(),
                "error_reason": event.error_reason,
                "error_source": event.error_source,
                "error_step": event.error_step,
                "is_recurring": event.is_recurring,
                "mandate_category": event.mandate_category,
                "cohort_arm": case.cohort_arm,
            },
        },
        {
            "step": 2,
            "title": "Root-Cause Diagnosis",
            "actor": "Deterministic Classifier",
            "timestamp": event.failed_at.isoformat(),
            "status": "diagnosed",
            "details": {
                "root_cause": case.root_cause.value,
                "confidence": case.cause_confidence,
                "is_terminal": case.root_cause in NEVER_RETRY,
                "is_hard_stop": case.root_cause in HARD_STOP,
                "candidate_actions": [a.value for a in CAUSE_TO_CANDIDATE_ACTIONS.get(case.root_cause, [])],
            },
        },
        {
            "step": 3,
            "title": "Policy Engine — Pre-Gate Cage",
            "actor": f"Compliance Engine v{POLICY_VERSION}",
            "timestamp": event.failed_at.isoformat(),
            "status": "evaluated",
            "details": {
                "permitted_actions": [a.value for a in verdict.permitted],
                "denied_actions": {a.value: reason for a, reason in verdict.denied.items()},
                "active_rule_triggers": verdict.rule_triggers,
                "ist_evaluation_time": to_ist(now_dt).strftime("%Y-%m-%d %H:%M:%S IST"),
            },
        },
        {
            "step": 4,
            "title": "Privacy Redaction & Gemini Planner",
            "actor": "Google Gemini 2.5 Flash",
            "timestamp": event.failed_at.isoformat(),
            "status": "planned",
            "details": {
                "redacted_payload": redacted_data,
                "last_action": case.last_action.value if case.last_action else "none",
                "notes": case.notes,
            },
        },
        {
            "step": 5,
            "title": "5-Wall Gated Execution & Ledgering",
            "actor": "Gated Executor",
            "timestamp": (case.last_action_at or event.failed_at).isoformat(),
            "status": case.status,
            "details": {
                "status": case.status,
                "recovered_paise": case.recovered_paise,
                "recovered_inr": f"₹{case.recovered_paise / 100:,.2f}",
                "contacts_sent": case.contacts_sent,
                "attempt_no": case.attempt_no,
            },
        },
    ]

    ledger_out = [
        {
            "seq": entry.seq,
            "stage": entry.stage,
            "actor": entry.actor,
            "input_hash": entry.input_hash[:16] + "...",
            "prev_hash": entry.prev_hash[:16] + "...",
            "hash": entry.hash[:16] + "...",
            "outcome": entry.outcome,
            "decision": entry.decision,
            "timestamp": entry.ts.isoformat(),
        }
        for entry in ledger_entries
    ]

    return {
        "case_id": case.id,
        "payment_id": event.payment_id,
        "timeline": timeline_steps,
        "ledger": ledger_out,
    }


@app.post("/api/cases/{case_id}/process")
def process_single_case(case_id: str, session: Session = Depends(get_session)):
    """Run a single case through the full agent pipeline."""
    case = session.exec(select(Case).where(Case.id == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    event = session.exec(select(PaymentEvent).where(PaymentEvent.id == case.payment_event_id)).first()
    if not event:
        raise HTTPException(status_code=404, detail="PaymentEvent not found")

    ctx = PolicyContext(agent_enabled=GLOBAL_KILL_SWITCH["enabled"], dry_run=True)
    now_dt = datetime.now(timezone.utc)

    # 1. Pre-Gate
    verdict = evaluate(case, event, ctx, now_dt)
    append_ledger(
        session=session,
        case_id=case.id,
        payment_id=event.payment_id,
        actor="policy_engine",
        stage="pregate",
        payload={"permitted": [a.value for a in verdict.permitted], "denied": {a.value: r for a, r in verdict.denied.items()}},
        policy_version=POLICY_VERSION,
    )

    # 2. Planner
    chosen_action, plan_details = plan(case, event, verdict.permitted)
    append_ledger(
        session=session,
        case_id=case.id,
        payment_id=event.payment_id,
        actor="planner_gemini",
        stage="plan",
        payload=plan_details,
        policy_version=POLICY_VERSION,
        prompt_version=PROMPT_VERSION,
    )

    # 3. Gated Execution
    outcome = execute(chosen_action, case, event, ctx, session, now_dt, params=plan_details)

    case.last_action = chosen_action
    case.last_action_at = now_dt
    case.attempt_no += 1
    if chosen_action in (Action.NUDGE_CHECKOUT, Action.SWITCH_RAIL_LINK, Action.UPDATE_INSTRUMENT):
        case.contacts_sent += 1

    if outcome.status in ("executed", "simulated"):
        if chosen_action == Action.NO_ACTION:
            # Deliberate inaction — close cleanly with no revenue credit
            case.status = "closed"
            case.recovered_paise = 0
        elif chosen_action == Action.ESCALATE_HUMAN:
            case.status = "escalated"
            case.recovered_paise = 0
        else:
            # Action dispatched — customer must actually pay before recovery is credited.
            # True recovery is confirmed only when payment.captured / order.paid webhook arrives.
            case.status = "action_dispatched"
            case.recovered_paise = 0  # NEVER credit revenue at dispatch time
            # Store payment_link_id for attribution on capture webhook
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
    session.refresh(case)

    return {
        "status": "success",
        "case_id": case.id,
        "chosen_action": chosen_action.value,
        "execution_outcome": outcome.status,
        "case_status": case.status,
        "recovery_ref": case.recovery_ref,
        "note": "Case marked action_dispatched. Revenue credited only on payment.captured webhook.",
        "reason": outcome.reason,
    }


@app.get("/api/policies")
def list_policies():
    """Return all 14 policy rules, their active parameters, citations, and rationales."""
    rules = [
        {"id": "R01", "name": "Global Kill Switch", "citation": "Fintech Trust Standards", "type": "Hard Stop", "desc": "Immediately halts all automated recovery actions when engaged."},
        {"id": "R02", "name": "Risk Hard Stop", "citation": "PMLA 2002 / Razorpay Risk Policy", "type": "Routing", "desc": "Suspicious, tampered, or flagged risk payments route exclusively to human compliance."},
        {"id": "R03", "name": "Terminal Cause Never Retry", "citation": "Card Network Operational Rules", "type": "Futile Retries", "desc": "Expired cards, invalid VPAs, or closed accounts are never retried on the same rail."},
        {"id": "R04", "name": "Attempt Cap (Max 3)", "citation": "Customer Fatigue Standards", "type": "Rate Limit", "desc": "Caps maximum automated retry attempts to 3 per payment."},
        {"id": "R05", "name": "Cool-off Windows", "citation": "Issuer Protocol Guidelines", "type": "Time Backoff", "desc": "Enforces 0h, 4h, and 48h cool-off windows between subsequent retry attempts."},
        {"id": "R06", "name": "TRAI Quiet Hours (09:00–21:00 IST)", "citation": "TRAI Telecom Commercial Communications Rules", "type": "Quiet Hours", "desc": "Customer nudges are strictly forbidden outside 09:00–21:00 Indian Standard Time."},
        {"id": "R07", "name": "Daily Contact Cap (Max 2)", "citation": "Anti-Harassment Comms Policy", "type": "Rate Limit", "desc": "Limits outbound customer communications to max 2 messages per customer per day."},
        {"id": "R08", "name": "DND / Consent Opt-out", "citation": "TRAI National DND Registry & DPDP Act", "type": "Consent", "desc": "Hard blocks any customer-facing messages for opted-out or DND-registered users."},
        {"id": "R09", "name": "RBI E-mandate Pre-debit Notice ≥ 24h", "citation": "RBI E-mandate Framework (21 April 2026)", "type": "Regulatory Compliance", "desc": "Mandatory 24h prior notification before executing recurring subscription debits."},
        {"id": "R10", "name": "RBI E-mandate AFA Thresholds", "citation": "RBI E-mandate Framework (21 April 2026)", "type": "Regulatory Compliance", "desc": "₹15,000 standard ceiling; ₹1,00,000 elevated ceiling for Insurance, Mutual Funds, and Credit Card bills."},
        {"id": "R11", "name": "Active Promise-to-Pay Freeze", "citation": "Debt Collection Ethics", "type": "Customer Grace", "desc": "Freezes all follow-up chasing when a customer commits to a specific payment date."},
        {"id": "R12", "name": "Merchant Config Defect Isolation", "citation": "Integration Integrity Rule", "type": "Merchant Defect", "desc": "Never blames or contacts the customer for merchant integration/payload validation bugs."},
        {"id": "R13", "name": "Promotional Incentive Budget Cap", "citation": "Treasury Risk Limits", "type": "Budget Cap", "desc": "Stops discounted rail-switching offers once batch incentive budget is exhausted."},
        {"id": "R14", "name": "Control Arm Isolation (20%)", "citation": "Causal Experimentation Hygiene", "type": "Scientific Control", "desc": "Observes natural recovery without taking any automated actions."},
    ]
    return {"policy_version": POLICY_VERSION, "total_rules": len(rules), "rules": rules}


class KillSwitchRequest(BaseModel):
    enabled: bool
    actor: str = "operator_admin"
    reason: str = "Operator manual toggle"


@app.get("/api/kill-switch")
def get_kill_switch():
    return {
        "agent_enabled": GLOBAL_KILL_SWITCH["enabled"],
        "kill_switch_engaged": not GLOBAL_KILL_SWITCH["enabled"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/kill-switch")
def toggle_kill_switch(payload: KillSwitchRequest, session: Session = Depends(get_session)):
    GLOBAL_KILL_SWITCH["enabled"] = payload.enabled
    action_str = "ENABLED_AGENT" if payload.enabled else "ENGAGED_KILL_SWITCH"

    append_ledger(
        session=session,
        case_id="system_wide",
        payment_id="global",
        actor=payload.actor,
        stage="kill_switch",
        payload={"action": action_str, "reason": payload.reason},
        policy_version=POLICY_VERSION,
        outcome="success",
    )

    return {
        "status": "success",
        "agent_enabled": GLOBAL_KILL_SWITCH["enabled"],
        "message": f"Global agent execution {action_str}",
    }


@app.get("/api/ledger/verify")
def verify_audit_ledger(session: Session = Depends(get_session)):
    """Walk and cryptographically verify SHA-256 hash-chained audit ledger."""
    is_valid, bad_seq, details = verify_chain(session)
    count = session.exec(select(LedgerEntry)).all()
    return {
        "is_valid": is_valid,
        "total_blocks": len(count),
        "first_bad_sequence": bad_seq,
        "details": details,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


class TamperRequest(BaseModel):
    seq: int
    fake_amount_paise: int = 99999900


@app.post("/api/ledger/tamper")
def simulate_ledger_tamper(payload: TamperRequest, session: Session = Depends(get_session)):
    """Simulate database corruption / record tampering to test cryptographic verification."""
    try:
        tampered = tamper_entry(session, payload.seq, {"tampered": True, "fake_amount": payload.fake_amount_paise})
        is_valid, bad_seq, details = verify_chain(session)
        return {
            "status": "tampered_for_demo",
            "tampered_seq": payload.seq,
            "verification_result": {
                "is_valid": is_valid,
                "first_bad_sequence": bad_seq,
                "details": details,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class InjectionTestRequest(BaseModel):
    payload: str
    permitted_actions: list[str] = ["no_action", "schedule_followup"]


@app.post("/api/planner/test-injection")
def test_prompt_injection(req: InjectionTestRequest):
    """
    Adversarial sandbox to prove prompt injection payloads cannot breach the policy cage.
    """
    permitted = frozenset(Action(a) for a in req.permitted_actions if a in [act.value for act in Action])
    dummy_event = PaymentEvent(
        event_id="evt_test_sec",
        payment_id="pay_test_sec",
        customer_ref="cust_sec_hash",
        amount_paise=50000,
        failed_at=datetime.now(timezone.utc),
    )
    dummy_case = Case(
        payment_event_id=dummy_event.id,
        payment_id="pay_test_sec",
        customer_ref="cust_sec_hash",
        root_cause=RootCause.UNKNOWN,
        notes=req.payload,
    )

    action, plan_data = plan(dummy_case, dummy_event, permitted)
    is_safe = action in permitted

    return {
        "input_hostile_payload": req.payload,
        "permitted_actions": [a.value for a in permitted],
        "chosen_action": action.value,
        "is_safe_and_contained": is_safe,
        "model_response": plan_data,
        "defense_layers": [
            "Layer 1: Fenced <untrusted> tags isolate customer input as data",
            "Layer 2: Model output is constrained strictly to permitted_actions enum",
            "Layer 3: Post-gate revalidation checks against database record",
        ],
    }


@app.post("/api/demo/seed")
def seed_demo_data(count: int = 100, session: Session = Depends(get_session)):
    """Seed database with synthetic failed payments for immediate live console demo."""
    cases_raw = generate(n=count, seed=20260901)
    imported, _ = import_batch_records(session, cases_raw)

    # Process first 25 cases through the agent
    cases_to_process = session.exec(select(Case).limit(25)).all()
    ctx = PolicyContext(agent_enabled=GLOBAL_KILL_SWITCH["enabled"], dry_run=True)
    now_dt = datetime.now(timezone.utc)

    for case in cases_to_process:
        event = session.exec(select(PaymentEvent).where(PaymentEvent.id == case.payment_event_id)).first()
        if not event:
            continue
        verdict = evaluate(case, event, ctx, now_dt)
        chosen_action, plan_details = plan(case, event, verdict.permitted)
        outcome = execute(chosen_action, case, event, ctx, session, now_dt, params=plan_details)
        case.last_action = chosen_action
        case.attempt_no += 1
        case.last_action_at = now_dt
        # Correct lifecycle: dispatch ≠ recovery
        if chosen_action == Action.NO_ACTION:
            case.status = "closed"
            case.recovered_paise = 0
        elif chosen_action == Action.ESCALATE_HUMAN:
            case.status = "escalated"
            case.recovered_paise = 0
        else:
            case.status = "action_dispatched"
            case.recovered_paise = 0
            recovery_ref = (
                outcome.details.get("payment_link_id")
                or outcome.details.get("api_response", {}).get("id")
            )
            if recovery_ref:
                case.recovery_ref = recovery_ref
        session.add(case)

    session.commit()
    return {"status": "seeded", "imported_count": imported, "processed_sample_count": len(cases_to_process)}
