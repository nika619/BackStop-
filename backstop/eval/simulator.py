import random
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from backstop.models import RootCause, Action, PaymentEvent, Case
from backstop.diagnose.taxonomy import REASON_MAP, NEVER_RETRY, HARD_STOP, CAUSE_TO_CANDIDATE_ACTIONS
from backstop.eval.generator import BASE_RECOVERY, UPLIFT


@dataclass
class SimulationMetrics:
    strategy_name: str
    total_cases: int = 0
    control_cases: int = 0
    treatment_cases: int = 0
    recovered_count: int = 0
    treatment_recovered_count: int = 0
    control_recovered_count: int = 0
    gross_recovered_paise: int = 0
    treatment_recovered_paise: int = 0
    control_recovered_paise: int = 0
    total_contacts_sent: int = 0
    policy_violations: int = 0
    hard_stops_auto_actioned: int = 0
    recovery_times_hours: list[float] = field(default_factory=list)

    @property
    def recovery_rate(self) -> float:
        return self.recovered_count / self.total_cases if self.total_cases > 0 else 0.0

    @property
    def treatment_recovery_rate(self) -> float:
        return self.treatment_recovered_count / self.treatment_cases if self.treatment_cases > 0 else 0.0

    @property
    def control_recovery_rate(self) -> float:
        return self.control_recovered_count / self.control_cases if self.control_cases > 0 else 0.0

    @property
    def gross_recovered_inr(self) -> float:
        return self.gross_recovered_paise / 100.0

    @property
    def contacts_per_thousand_inr(self) -> float:
        inr = self.gross_recovered_inr
        return (self.total_contacts_sent / (inr / 1000.0)) if inr > 0 else 0.0

    @property
    def median_recovery_time_hours(self) -> float:
        if not self.recovery_times_hours:
            return 0.0
        sorted_times = sorted(self.recovery_times_hours)
        n = len(sorted_times)
        mid = n // 2
        return (sorted_times[mid] if n % 2 != 0 else (sorted_times[mid - 1] + sorted_times[mid]) / 2.0)


def simulate_case_outcome(
    raw_case: dict,
    chosen_action: Action,
    root_cause: RootCause,
    is_policy_compliant: bool,
    policy_violations_count: int = 0,
) -> tuple[bool, int, float, int]:
    """
    Simulate the physical payment outcome.
    Returns: (recovered: bool, recovered_paise: int, recovery_time_hours: float, contacts_sent: int)
    """
    pid = raw_case["payment_id"]
    # Deterministic pseudo-random seed per payment ID
    case_seed = int(hashlib.md5(f"{pid}_outcome".encode()).hexdigest()[:8], 16)
    rng = random.Random(case_seed)

    base_prob = BASE_RECOVERY.get(root_cause.value, 0.05)
    amount_paise = raw_case["amount_paise"]
    contacts = 0

    if chosen_action in (Action.NUDGE_CHECKOUT, Action.SWITCH_RAIL_LINK, Action.UPDATE_INSTRUMENT):
        contacts = 1

    # Control arm or NO_ACTION: natural organic recovery
    if chosen_action == Action.NO_ACTION or raw_case.get("cohort_arm") == "control":
        recovered = rng.random() < base_prob
        rec_time = rng.uniform(12.0, 96.0) if recovered else 0.0
        return recovered, (amount_paise if recovered else 0), rec_time, 0

    # If action violated hard policies, recovery degrades or fails
    if not is_policy_compliant:
        effective_prob = base_prob * 0.4
        recovered = rng.random() < effective_prob
        return recovered, (amount_paise if recovered else 0), (rng.uniform(24.0, 120.0) if recovered else 0.0), contacts

    # Effective action matched to root cause
    correct_actions = CAUSE_TO_CANDIDATE_ACTIONS.get(root_cause, [])
    if chosen_action in correct_actions and chosen_action != Action.NO_ACTION:
        uplift_mult = UPLIFT.get(root_cause.value, 1.5)
        effective_prob = min(0.92, base_prob * uplift_mult)
        recovered = rng.random() < effective_prob
        rec_time = rng.uniform(1.5, 36.0) if recovered else 0.0
        return recovered, (amount_paise if recovered else 0), rec_time, contacts
    else:
        # Action is non-optimal
        effective_prob = base_prob * 0.8
        recovered = rng.random() < effective_prob
        rec_time = rng.uniform(24.0, 72.0) if recovered else 0.0
        return recovered, (amount_paise if recovered else 0), rec_time, contacts
