import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import JSON, Column, Field, SQLModel


class RootCause(str, Enum):
    TRANSIENT_INFRA = "transient_infra"
    ISSUER_SOFT_DECLINE = "issuer_soft_decline"
    AUTH_ABANDONED = "auth_abandoned"
    USER_ABORTED = "user_aborted"
    INSTRUMENT_TERMINAL = "instrument_terminal"
    RAIL_INELIGIBLE = "rail_ineligible"
    RISK_DECLINE = "risk_decline"
    MERCHANT_CONFIG = "merchant_config"
    MANDATE_FAILURE = "mandate_failure"
    UNKNOWN = "unknown"


class Action(str, Enum):
    RETRY_SAME_RAIL = "retry_same_rail"
    SWITCH_RAIL_LINK = "switch_rail_link"
    NUDGE_CHECKOUT = "nudge_checkout"
    UPDATE_INSTRUMENT = "update_instrument"
    SCHEDULE_FOLLOWUP = "schedule_followup"
    ESCALATE_HUMAN = "escalate_human"
    ALERT_MERCHANT = "alert_merchant"
    NO_ACTION = "no_action"


class PaymentEvent(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    event_id: str = Field(index=True, unique=True)  # Deduplication key enforced at DB level
    merchant_id: str = Field(default="merch_ecommerce_01", index=True)
    payment_id: str = Field(index=True)
    order_id: str = Field(default="")
    customer_ref: str = Field(index=True)  # Pseudonymized hash handle — never raw PII
    amount_paise: int
    currency: str = "INR"
    method: str = "card"  # card | upi | netbanking | wallet
    error_code: str | None = None
    error_source: str | None = None  # customer | business | gateway | razorpay
    error_step: str | None = None
    error_reason: str | None = None
    error_description: str | None = None
    failed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_recurring: bool = False
    mandate_category: str | None = None  # insurance | mutual_fund | credit_card_bill | other
    raw: dict = Field(default_factory=dict, sa_column=Column(JSON))


class MerchantPolicy(SQLModel, table=True):
    merchant_id: str = Field(primary_key=True)
    name: str
    quiet_start_hour: int = 9
    quiet_end_hour: int = 21
    max_attempts: int = 3
    incentive_budget_paise: int = 5000000
    incentive_spent_paise: int = 0
    auto_recovery_enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BankHealthTelemetry(SQLModel, table=True):
    bank_code: str = Field(primary_key=True)  # HDFC | ICICI | SBI | AXIS
    bank_name: str
    success_rate: float = 0.95  # 0.0 to 1.0 (e.g. 0.65 = 65% health)
    is_outage: bool = False
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Case(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    merchant_id: str = Field(default="merch_ecommerce_01", index=True)
    payment_event_id: str = Field(index=True)
    payment_id: str = Field(default="", index=True)
    customer_ref: str = Field(default="", index=True)
    root_cause: RootCause = Field(default=RootCause.UNKNOWN)
    cause_confidence: float = 0.0
    attempt_no: int = 0
    contacts_sent: int = 0
    status: str = "open"  # open | recovered | abandoned | escalated | blocked
    cohort_arm: str = "treatment"  # treatment | control
    recovered_paise: int = 0
    promise_to_pay_at: datetime | None = None
    last_action_at: datetime | None = None
    last_action: Action | None = None
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LedgerEntry(SQLModel, table=True):
    seq: int | None = Field(default=None, primary_key=True)
    merchant_id: str = Field(default="merch_ecommerce_01", index=True)
    case_id: str = Field(index=True)
    payment_id: str = Field(default="", index=True)
    actor: str  # agent | human:<id> | system
    stage: str  # diagnose | pregate | plan | postgate | execute
    input_hash: str
    policy_version: str
    prompt_version: str | None = None
    decision: dict = Field(default_factory=dict, sa_column=Column(JSON))
    outcome: str | None = None
    prev_hash: str
    hash: str
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CustomerState(SQLModel, table=True):
    customer_ref: str = Field(primary_key=True)
    merchant_id: str = Field(default="merch_ecommerce_01", index=True)
    is_dnd: bool = False
    contacts_today: int = 0
    last_contact_date: str = ""  # YYYY-MM-DD for daily rate limiting
    predebit_notice_at: datetime | None = None
    predebit_notice_status: str = Field(default="DELIVERED")  # DELIVERED | FAILED | PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
