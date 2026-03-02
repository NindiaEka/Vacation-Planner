# user_calendar.py
import json
import os

def get_calendar(path=None):
    """
    Membaca file kalender user (JSON) dari path yang diberikan atau default.
    """
    if path is None:
        path = os.getenv("USER_CALENDAR_PATH", "data/user_calendar.json")
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return {}
