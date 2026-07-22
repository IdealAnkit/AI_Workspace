"""
Datetime utilities.

Provides timezone-aware datetime helpers.
Always use UTC internally; convert to local time only at the presentation layer.
"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(UTC)


def format_iso(dt: datetime) -> str:
    """Format a datetime as an ISO 8601 string with UTC timezone."""
    return dt.astimezone(UTC).isoformat()


def format_iso_now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return format_iso(utcnow())
