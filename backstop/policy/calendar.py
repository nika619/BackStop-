from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
QUIET_START_HOUR_IST = 9
QUIET_END_HOUR_IST = 21


def to_ist(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware and converted to Indian Standard Time (IST)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


def is_within_trai_window(dt: datetime) -> bool:
    """TRAI comms window: 09:00 to 21:00 IST."""
    dt_ist = to_ist(dt)
    return QUIET_START_HOUR_IST <= dt_ist.hour < QUIET_END_HOUR_IST


def is_payday_window(dt: datetime) -> bool:
    """Salary/liquidity window: 28th to 5th of each month."""
    dt_ist = to_ist(dt)
    return dt_ist.day >= 28 or dt_ist.day <= 5
