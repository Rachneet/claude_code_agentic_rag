from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, available_timezones

from langsmith import traceable

logger = logging.getLogger(__name__)


@traceable(name="get_datetime", run_type="tool")
async def get_datetime(timezone_name: str = "UTC") -> str:
    """Get the current date and time in a specified timezone.

    Returns formatted date/time string. On error (e.g. invalid timezone),
    returns an error message string.
    """
    try:
        if timezone_name.upper() == "UTC":
            tz = timezone.utc
        else:
            tz = ZoneInfo(timezone_name)

        now = datetime.now(tz)

        return (
            f"Current date and time in {timezone_name}:\n"
            f"  Date: {now.strftime('%A, %B %d, %Y')}\n"
            f"  Time: {now.strftime('%I:%M:%S %p')}\n"
            f"  ISO: {now.isoformat()}\n"
            f"  Unix timestamp: {int(now.timestamp())}"
        )
    except KeyError:
        query = timezone_name.lower()
        suggestions = [
            tz for tz in sorted(available_timezones()) if query in tz.lower()
        ][:5]
        msg = f"Unknown timezone: '{timezone_name}'."
        if suggestions:
            msg += f" Did you mean: {', '.join(suggestions)}?"
        return msg
    except Exception as e:
        logger.warning("DateTime tool error: %s", e)
        return f"Date/time error: {e}"
