import os
import math
from pathlib import Path
from datetime import datetime, timezone
from scipy import stats
from sqlmodel import Session, create_engine, SQLModel
from backstop.models import RootCause, Action, PaymentEvent, Case
from backstop.diagnose.taxonomy import REASON_MAP
from backstop.diagnose.classifier import classify
from backstop.policy.engine import evaluate, PolicyContext, POLICY_VERSION
from backstop.planner.planner import plan
from backstop.execute.executor import execute
from backstop.eval.generator import generate
from backstop.eval.simulator import SimulationMetrics, simulate_case_outcome
from backstop.eval.baselines import run_do_nothing, run_retry_all_3x


def compute_incremental_lift(treatment_recovered: int, treatment_total: int, control_recovered: int, control_total: int) -> dict:
    """
    Compute two-proportion z-test and 95% confidence interval for incremental recovery lift.
    """
    if treatment_total == 0 or control_total == 0:
        return {"lift_pp": 0.0, "ci_95_lower": 0.0, "ci_95_upper": 0.0, "p_value": 1.0, "z_score": 0.0}

    p1 = treatment_recovered / treatment_total
    p2 = control_recovered / control_total

    lift_pp = (p1 - p2) * 100.0

    # Pooled standard error for hypothesis testing
    pooled_p = (treatment_recovered + control_recovered) / (treatment_total + control_total)
    se_pooled = math.sqrt(pooled_p * (1 - pooled_p) * ((1 / treatment_total) + (1 / control_total)))
    z_score = (p1 - p2) / se_pooled if se_pooled > 0 else 0.0
    p_value = 2 * (1 - stats.norm.cdf(abs(z_score))) if se_pooled > 0 else 1.0

    # Unpooled standard error for confidence interval
    se_diff = math.sqrt((p1 * (1 - p1) / treatment_total) + (p2 * (1 - p2) / control_total))
    ci_lower = ((p1 - p2) - 1.96 * se_diff) * 100.0
    ci_upper = ((p1 - p2) + 1.96 * se_diff) * 100.0

    return {
        "lift_pp": round(lift_pp, 2),
        "ci_95_lower": round(ci_lower, 2),
        "ci_95_upper": round(ci_upper, 2),
        "p_value": p_value,
        "z_score": round(z_score, 3),
    }


def run_backstop_evaluation(cases: list[dict]) -> SimulationMetrics:
    """Run full Backstop revenue recovery pipeline across batch cases."""
    # Use in-memory SQLite for high performance evaluation
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)

    metrics = SimulationMetrics(strategy_name="Backstop")
    ctx = PolicyContext(agent_enabled=True, dry_run=True)

    with Session(engine) as session:
        for raw in cases:
            metrics.total_cases += 1
            is_control = raw.get("cohort_arm") == "control"
            if is_control:
                metrics.control_cases += 1
            else:
                metrics.treatment_cases += 1

            # Build in-memory event and case records
            event = PaymentEvent(
                event_id=raw["event_id"],
                payment_id=raw["payment_id"],
                order_id=raw["order_id"],
                customer_ref=raw["customer_ref"],
                amount_paise=raw["amount_paise"],
                currency=raw.get("currency", "INR"),
                method=raw.get("method", "card"),
                error_reason=raw.get("error_reason"),
                error_source=raw.get("error_source"),
                error_step=raw.get("error_step"),
                error_description=raw.get("error_description"),
                failed_at=datetime.fromisoformat(raw["failed_at"]),
                is_recurring=raw.get("is_recurring", False),
                mandate_category=raw.get("mandate_category"),
                raw=raw,
            )

            root_cause, confidence, _ = classify(event)
            case = Case(
                payment_event_id=event.id,
                payment_id=event.payment_id,
                customer_ref=event.customer_ref,
                root_cause=root_cause,
                cause_confidence=confidence,
                cohort_arm=raw.get("cohort_arm", "treatment"),
            )

            # Evaluate Policy Pre-Gate
            now_dt = event.failed_at
            verdict = evaluate(case, event, ctx, now_dt)

            # Planner (LLM or deterministic fallback inside permitted set)
            chosen_action, plan_details = plan(case, event, verdict.permitted)

            # Execute via 5-wall Gated Executor
            outcome = execute(chosen_action, case, event, ctx, session, now_dt, params=plan_details)

            # Check for policy compliance
            is_compliant = (outcome.status != "blocked" and chosen_action in verdict.permitted)
            if not is_compliant:
                metrics.policy_violations += 1

            if root_cause in {RootCause.RISK_DECLINE} and chosen_action not in (Action.ESCALATE_HUMAN, Action.NO_ACTION):
                metrics.hard_stops_auto_actioned += 1

            # Simulate outcome
            recovered, paise, rec_time, contacts = simulate_case_outcome(
                raw, chosen_action, root_cause, is_policy_compliant=is_compliant, policy_violations_count=0
            )

            metrics.total_contacts_sent += contacts
            if recovered:
                metrics.recovered_count += 1
                metrics.gross_recovered_paise += paise
                metrics.recovery_times_hours.append(rec_time)
                if is_control:
                    metrics.control_recovered_count += 1
                    metrics.control_recovered_paise += paise
                else:
                    metrics.treatment_recovered_count += 1
                    metrics.treatment_recovered_paise += paise

    return metrics


def run_full_benchmark(n: int = 1000, seed: int = 20260901) -> dict:
    """Execute complete 3-way benchmark: Do Nothing vs Retry-All 3x vs Backstop."""
    cases = generate(n=n, seed=seed)

    do_nothing = run_do_nothing(cases)
    retry_all = run_retry_all_3x(cases)
    backstop = run_backstop_evaluation(cases)

    # Control comparison for Backstop
    control_rate = backstop.control_recovery_rate
    treatment_rate = backstop.treatment_recovery_rate

    # Incremental revenue calculation: Treatment gross - expected baseline organic gross
    expected_organic_in_treatment = backstop.treatment_cases * (backstop.control_recovered_paise / max(1, backstop.control_cases))
    incremental_paise = max(0, backstop.treatment_recovered_paise - expected_organic_in_treatment)
    incremental_inr = incremental_paise / 100.0

    lift_stats = compute_incremental_lift(
        treatment_recovered=backstop.treatment_recovered_count,
        treatment_total=backstop.treatment_cases,
        control_recovered=backstop.control_recovered_count,
        control_total=backstop.control_cases,
    )

    return {
        "n": n,
        "seed": seed,
        "do_nothing": do_nothing,
        "retry_all": retry_all,
        "backstop": backstop,
        "lift_stats": lift_stats,
        "incremental_inr": incremental_inr,
    }


def generate_report_text(benchmark: dict) -> str:
    """Format benchmark results into Markdown and ASCII evidence table."""
    dn = benchmark["do_nothing"]
    ra = benchmark["retry_all"]
    bs = benchmark["backstop"]
    ls = benchmark["lift_stats"]
    inc_inr = benchmark["incremental_inr"]

    report = []
    report.append("=========================================================================================")
    report.append("                          BACKSTOP EVALUATION REPORT — TRACK 03                          ")
    report.append("                      Seeded Synthetic Benchmark (N=1,000, Seed=20260901)                 ")
    report.append("=========================================================================================\n")

    report.append("| Metric                             | Do nothing (Control) | Retry-all ×3 (Naive) | Backstop (Agent)     |")
    report.append("|------------------------------------|----------------------|----------------------|----------------------|")
    report.append(f"| Total Cases (80/20 Arm Split)      | {dn.total_cases:<20} | {ra.total_cases:<20} | {bs.total_cases:<20} |")
    report.append(f"| Gross Recovered (₹)                | ₹{dn.gross_recovered_inr:>16,.2f} | ₹{ra.gross_recovered_inr:>16,.2f} | ₹{bs.gross_recovered_inr:>16,.2f} |")
    report.append(f"| Incremental vs Control (₹)         | ₹{0:>16,.2f} | ₹{max(0, ra.gross_recovered_inr - dn.gross_recovered_inr):>16,.2f} | ₹{inc_inr:>16,.2f} |")
    report.append(f"| Lift over Control (95% CI)         | {'—':<20} | {((ra.recovery_rate - dn.recovery_rate)*100):>+6.1f} pp             | {ls['lift_pp']:>+5.1f}% [{ls['ci_95_lower']:>+.1f}%, {ls['ci_95_upper']:>+.1f}%] |")
    report.append(f"| Recovery Rate (Overall)            | {dn.recovery_rate*100:>18.1f}% | {ra.recovery_rate*100:>18.1f}% | {bs.recovery_rate*100:>18.1f}% |")
    report.append(f"| Customer Contacts Sent             | {dn.total_contacts_sent:<20} | {ra.total_contacts_sent:<20} | {bs.total_contacts_sent:<20} |")
    report.append(f"| Contacts per ₹1,000 Recovered      | {dn.contacts_per_thousand_inr:>19.2f}  | {ra.contacts_per_thousand_inr:>19.2f}  | {bs.contacts_per_thousand_inr:>19.2f}  |")
    report.append(f"| Policy Violations                  | {dn.policy_violations:<20} | {ra.policy_violations:<20} | {bs.policy_violations:<20} |")
    report.append(f"| Hard-stop Cases Auto-actioned      | {dn.hard_stops_auto_actioned:<20} | {ra.hard_stops_auto_actioned:<20} | {bs.hard_stops_auto_actioned:<20} |")
    report.append(f"| Median Time to Recovery (Hours)    | {dn.median_recovery_time_hours:>18.1f}h | {ra.median_recovery_time_hours:>18.1f}h | {bs.median_recovery_time_hours:>18.1f}h |")
    report.append("-----------------------------------------------------------------------------------------\n")

    report.append("KEY STATISTICAL FINDINGS:")
    report.append(f"1. Incremental Recovery: Backstop recovered ₹{inc_inr:,.2f} in incremental revenue over the organic control.")
    report.append(f"2. Statistical Significance: Lift of {ls['lift_pp']}% (95% CI: [{ls['ci_95_lower']}%, {ls['ci_95_upper']}%], p-value = {ls['p_value']:.2e}).")
    report.append(f"3. Contact Efficiency: Backstop sent {bs.total_contacts_sent} contacts vs {ra.total_contacts_sent} from Retry-All (a {(1 - bs.total_contacts_sent/max(1, ra.total_contacts_sent))*100:.1f}% reduction in customer spam).")
    report.append(f"4. Compliance Cage Integrity: Exactly {bs.policy_violations} policy violations and {bs.hard_stops_auto_actioned} hard-stop auto-actions across the entire batch.")

    return "\n".join(report)


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    benchmark = run_full_benchmark(1000, 20260901)
    report_text = generate_report_text(benchmark)
    try:
        print(report_text)
    except UnicodeEncodeError:
        print(report_text.replace("₹", "Rs. "))

    evidence_dir = Path("docs/evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    with open(evidence_dir / "eval_run.txt", "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\nWrote evidence artifact to docs/evidence/eval_run.txt")
