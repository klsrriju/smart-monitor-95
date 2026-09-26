"""
attendance_rules.py
--------------------
All the "business rules" about what counts as PRESENT, LATE, or ABSENT
live here, in ONE place, so they're easy to find and change later
without touching the core logic in attendance_service.py.
"""

from datetime import time

# ---- CONFIGURABLE SETTINGS ----
# Change this whenever working hours change. Nothing else needs editing.
EXPECTED_ENTRY_TIME = time(9, 0, 0)   # 09:00:00

# Arriving up to this many minutes after EXPECTED_ENTRY_TIME still
# counts as PRESENT, not LATE. Set to 0 if you want zero tolerance.
GRACE_PERIOD_MINUTES = 10


def set_expected_entry_time(hour: int, minute: int = 0):
    """
    Lets someone change the expected entry time while the app is running.
    Example: set_expected_entry_time(9, 30)  -> expected entry becomes 09:30
    """
    global EXPECTED_ENTRY_TIME
    EXPECTED_ENTRY_TIME = time(hour, minute, 0)


def determine_status(entry_time_str: str) -> str:
    """
    Given an entry time like "09:04:21", decide PRESENT or LATE.
    (ABSENT is handled separately in attendance_service.get_absentees,
    since an absent employee has NO entry time at all.)
    """
    if entry_time_str is None:
        return "ABSENT"

    entry_time = time.fromisoformat(entry_time_str)

    cutoff_minutes = (
        EXPECTED_ENTRY_TIME.hour * 60
        + EXPECTED_ENTRY_TIME.minute
        + GRACE_PERIOD_MINUTES
    )
    entry_minutes = entry_time.hour * 60 + entry_time.minute

    if entry_minutes <= cutoff_minutes:
        return "PRESENT"
    return "LATE"
