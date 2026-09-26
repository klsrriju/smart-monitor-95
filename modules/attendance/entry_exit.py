"""
entry_exit.py
-------------
Decides whether a recognition event should be treated as an ENTRY or an EXIT.

SIMPLE RULE (since we don't have separate entry/exit cameras yet):
  - The FIRST time we see an employee on a given day   -> ENTRY
  - EVERY time after that, on the same day             -> counts as EXIT

Why this works well even with 500 duplicate detections:
  Entry stays fixed at the very first sighting. Exit keeps getting pushed
  forward with every later sighting. So by the end of the day, "exit_time"
  naturally holds the LAST time the person was seen - which is exactly
  what a real exit time should be.
"""

from database import get_connection


def classify_event(employee_id: str, date: str) -> str:
    """
    Looks at whether an attendance row already exists for this
    employee today, and decides ENTRY or EXIT accordingly.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM attendance WHERE employee_id = ? AND date = ?",
        (employee_id, date),
    )
    existing = cur.fetchone()
    conn.close()

    if existing is None:
        return "ENTRY"
    return "EXIT"
