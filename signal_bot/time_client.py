"""Time and date utilities for Signal bots."""

from datetime import datetime
import time
from zoneinfo import ZoneInfo


def get_datetime(tz_name: str = "UTC") -> dict:
    """
    Get the current date and time for a specified timezone.

    Args:
        tz_name: IANA timezone name (e.g., 'America/New_York', 'UTC')

    Returns:
        Dict with timezone, datetime, date, time, day_of_week, and iso_format
    """
    try:
        tz = ZoneInfo(tz_name)
        current = datetime.now(tz)
        return {
            "timezone": tz_name,
            "datetime": current.strftime("%Y-%m-%d %H:%M:%S"),
            "date": current.strftime("%Y-%m-%d"),
            "time": current.strftime("%H:%M:%S"),
            "day_of_week": current.strftime("%A"),
            "iso_format": current.isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


def get_current_unix_timestamp() -> dict:
    """
    Get the current Unix timestamp.

    Returns:
        Dict with unix_timestamp (float) and unix_timestamp_int (int)
    """
    ts = time.time()
    return {
        "unix_timestamp": ts,
        "unix_timestamp_int": int(ts)
    }


# Sync wrappers (for consistency with other clients like weather_client.py)
def get_datetime_sync(tz_name: str = "UTC") -> dict:
    """Sync wrapper for get_datetime."""
    return get_datetime(tz_name)


def get_unix_timestamp_sync() -> dict:
    """Sync wrapper for get_current_unix_timestamp."""
    return get_current_unix_timestamp()
