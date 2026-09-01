from datetime import datetime, timezone
from backstop.models import RootCause, Action, Case, PaymentEvent
from backstop.diagnose.taxonomy import REASON_MAP, HARD_STOP, NEVER_RETRY
from backstop.policy.engine import evaluate, PolicyContext
from backstop.eval.simulator import SimulationMetrics, simulate_case_outcome


def run_do_nothing(cases: list[dict]) -> SimulationMetrics:
    """Baseline 1: Do-Nothing (Pure organic recovery control)."""
    metrics = SimulationMetrics(strategy_name="Do nothing")
    for raw in cases:
        metrics.total_cases += 1
        is_control = raw.get("cohort_arm") == "control"
        if is_control:
            metrics.control_cases += 1
        else:
            metrics.treatment_cases += 1

        reason = raw.get("error_reason", "")
        root_cause = REASON_MAP.get(reason, RootCause.UNKNOWN)
        recovered, paise, rec_time, contacts = simulate_case_outcome(
            raw, Action.NO_ACTION, root_cause, is_policy_compliant=True, policy_violations_count=0
        )
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


def run_retry_all_3x(cases: list[dict]) -> SimulationMetrics:
    """Baseline 2: Blindly retry all failed payments 3x immediately with customer SMS."""
    metrics = SimulationMetrics(strategy_name="Retry-all ×3")
    for raw in cases:
        metrics.total_cases += 1
        is_control = raw.get("cohort_arm") == "control"
        if is_control:
            metrics.control_cases += 1
        else:
            metrics.treatment_cases += 1

        reason = raw.get("error_reason", "")
        root_cause = REASON_MAP.get(reason, RootCause.UNKNOWN)
        
        # Blindly retries even terminal instruments, risk declines, outside quiet hours, without pre-debit notice
        violations = 0
        if root_cause in HARD_STOP:
            metrics.hard_stops_auto_actioned += 1
            violations += 1
        if root_cause in NEVER_RETRY:
            violations += 1
        if raw.get("is_recurring"):
            violations += 1  # No 24h pre-debit notice, ignores AFA
        if raw.get("error_source") == "business":
            violations += 1  # Blames customer for merchant defect

        # 3 retry attempts + 2 SMS notifications
        metrics.total_contacts_sent += 2
        metrics.policy_violations += violations

        recovered, paise, rec_time, _ = simulate_case_outcome(
            raw,
            Action.RETRY_SAME_RAIL,
            root_cause,
            is_policy_compliant=(violations == 0),
            policy_violations_count=violations,
        )
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
