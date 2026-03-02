"""Calendar utility for availability checks.

References:
- data/user_calendar.json (calendar source)
"""

import json
import os
from datetime import date, timedelta


def _load_calendar(path: str | None = None) -> dict:
    calendar_path = path or os.getenv("USER_CALENDAR_PATH", "data/user_calendar.json")
    try:
        with open(calendar_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def check_calendar(days: int = 3, start_date: date | None = None) -> dict:
    """
    Mengambil status kalender untuk rentang hari sesuai durasi request user.
    """
    horizon_days = max(int(days), 1)
    anchor_date = start_date or date.today()
    raw_calendar = _load_calendar()

    availability = {}
    for offset in range(horizon_days):
        current_date = (anchor_date + timedelta(days=offset)).isoformat()
        availability[current_date] = raw_calendar.get(current_date, "unavailable")
    return availability
