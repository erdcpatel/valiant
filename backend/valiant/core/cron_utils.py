"""
Cron expression parsing, validation, and next execution calculation utilities.
Supports standard 5-field cron syntax and friendly interval shortcuts.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
import re

try:
    from croniter import croniter
    HAS_CRONITER = True
except ImportError:
    HAS_CRONITER = False


SHORTCUT_INTERVALS = {
    "@hourly": timedelta(hours=1),
    "@daily": timedelta(days=1),
    "@midnight": timedelta(days=1),
    "@weekly": timedelta(days=7),
}

PRESET_DESCRIPTIONS = {
    "*/1 * * * *": "Every 1 minute",
    "*/5 * * * *": "Every 5 minutes",
    "*/10 * * * *": "Every 10 minutes",
    "*/15 * * * *": "Every 15 minutes",
    "*/30 * * * *": "Every 30 minutes",
    "0 * * * *": "Every hour (at minute 0)",
    "0 0 * * *": "Daily at midnight",
    "0 9 * * *": "Daily at 9:00 AM",
    "0 12 * * *": "Daily at 12:00 PM",
    "0 0 * * 1": "Weekly on Monday",
    "@hourly": "Every hour",
    "@daily": "Daily at midnight",
    "@midnight": "Daily at midnight",
    "@weekly": "Weekly on Monday",
}


def validate_cron_expression(expr: str) -> Tuple[bool, Optional[str]]:
    """Validate cron expression syntax."""
    expr = expr.strip()
    if not expr:
        return False, "Cron expression cannot be empty"

    if expr in SHORTCUT_INTERVALS:
        return True, None

    # Check for @every <number><unit> (e.g., @every 5m, @every 2h)
    m = re.match(r"^@every\s+(\d+)\s*(s|m|h|d)$", expr, re.IGNORECASE)
    if m:
        return True, None

    if HAS_CRONITER:
        if croniter.is_valid(expr):
            return True, None
        return False, f"Invalid cron expression: '{expr}'"
    else:
        # Fallback basic 5-field check
        parts = expr.split()
        if len(parts) == 5:
            return True, None
        return False, "Expression must have 5 space-separated fields or standard interval shortcut"


def compute_next_run_iso(expr: str, base_time: Optional[datetime] = None) -> str:
    """Compute the next execution timestamp as an ISO 8601 string."""
    expr = expr.strip()
    base_time = base_time or datetime.utcnow()

    # Handle shortcuts
    if expr in SHORTCUT_INTERVALS:
        delta = SHORTCUT_INTERVALS[expr]
        return (base_time + delta).isoformat()

    # Handle @every Xm/h/d
    m = re.match(r"^@every\s+(\d+)\s*(s|m|h|d)$", expr, re.IGNORECASE)
    if m:
        val = int(m.group(1))
        unit = m.group(2).lower()
        if unit == "s":
            delta = timedelta(seconds=val)
        elif unit == "m":
            delta = timedelta(minutes=val)
        elif unit == "h":
            delta = timedelta(hours=val)
        else:
            delta = timedelta(days=val)
        return (base_time + delta).isoformat()

    if HAS_CRONITER:
        itr = croniter(expr, base_time)
        next_dt: datetime = itr.get_next(datetime)
        return next_dt.isoformat()
    else:
        # Default 1 hour fallback
        return (base_time + timedelta(hours=1)).isoformat()


def get_human_description(expr: str) -> str:
    """Return a human-friendly label for common cron patterns."""
    expr = expr.strip()
    if expr in PRESET_DESCRIPTIONS:
        return PRESET_DESCRIPTIONS[expr]

    m = re.match(r"^@every\s+(\d+)\s*(s|m|h|d)$", expr, re.IGNORECASE)
    if m:
        val = m.group(1)
        unit = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}.get(m.group(2).lower(), "minutes")
        return f"Every {val} {unit}"

    return expr
