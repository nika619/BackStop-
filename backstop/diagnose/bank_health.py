from datetime import datetime, timezone
from sqlmodel import Session, select

from backstop.database import engine
from backstop.models import BankHealthTelemetry

# Static fallback map in case database is empty
DEFAULT_BANK_HEALTH: dict[str, float] = {
    "HDFC": 0.96,
    "ICICI": 0.94,
    "SBI": 0.91,
    "AXIS": 0.95,
}


def get_bank_health(bank_code: str | None) -> float:
    """
    Returns the real-time bank health success rate (0.0 to 1.0).
    If bank_code is None or unknown, defaults to 0.95 (healthy).
    """
    if not bank_code:
        return 0.95
    code = bank_code.upper().strip()
    try:
        with Session(engine) as session:
            telemetry = session.get(BankHealthTelemetry, code)
            if telemetry:
                if telemetry.is_outage:
                    return 0.50  # Hard outage forced below 70% threshold
                return telemetry.success_rate
    except Exception:
        pass
    return DEFAULT_BANK_HEALTH.get(code, 0.95)


def set_bank_health(bank_code: str, success_rate: float, is_outage: bool = False):
    """
    Update live bank health telemetry (used by admin or simulation).
    """
    code = bank_code.upper().strip()
    with Session(engine) as session:
        telemetry = session.get(BankHealthTelemetry, code)
        if not telemetry:
            telemetry = BankHealthTelemetry(
                bank_code=code,
                bank_name=f"{code} Bank",
                success_rate=success_rate,
                is_outage=is_outage,
            )
        else:
            telemetry.success_rate = success_rate
            telemetry.is_outage = is_outage
            telemetry.updated_at = datetime.now(timezone.utc)
        session.add(telemetry)
        session.commit()
