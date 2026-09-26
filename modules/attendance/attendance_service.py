"""
attendance_service.py
----------------------
This is the "brain" of the module. It takes a raw RecognitionEvent and
turns it into:
  1. A logged event (in the events table - our audit trail)
  2. A created/updated attendance record (in the attendance table)

Every other file (api.py, demo.py) should talk to the attendance
system ONLY through the functions in this file. This keeps the
database details and business rules hidden behind a clean interface.
"""

from datetime import datetime
from typing import List, Optional

from database import get_connection, init_db, seed_employees
from models import RecognitionEvent, AttendanceRecord, AttendanceSummary, EventOut
from entry_exit import classify_event
from attendance_rules import determine_status

# Sample employees required by the project spec.
# In a real system this would come from an HR database instead.
SAMPLE_EMPLOYEES = {
    "EMP001": "R. Meena",
    "EMP002": "S. Kumar",
    "EMP003": "P. Priya",
    "EMP004": "A. Rahman",
}


def setup():
    """Call this once when the app starts: creates tables + sample employees."""
    init_db()
    seed_employees(SAMPLE_EMPLOYEES)


def process_recognition_event(event: RecognitionEvent) -> AttendanceRecord:
    """
    THE CORE FUNCTION of the whole module.
    Takes one recognition event (could be 1 of 500 duplicates for the
    same person) and safely updates attendance - never creating a
    second row for the same person on the same day.
    """
    employee_id = event.person_id
    date_str = event.timestamp.date().isoformat()   # "2026-09-21"
    time_str = event.timestamp.time().isoformat()    # "09:04:21"
    full_ts = event.timestamp.isoformat()

    event_type = classify_event(employee_id, date_str)

    conn = get_connection()
    cur = conn.cursor()

    # 1. ALWAYS log the raw event - this is our full audit trail,
    #    so even the 499 duplicate detections are never lost, they're
    #    just not turned into duplicate attendance rows.
    cur.execute(
        """INSERT INTO events (employee_id, event_type, event_time, full_timestamp, confidence, track_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (employee_id, event_type, time_str, full_ts, event.confidence, event.track_id),
    )

    if event_type == "ENTRY":
        # First sighting today -> create the ONE attendance row for today.
        status = determine_status(time_str)
        cur.execute(
            """INSERT INTO attendance (employee_id, date, entry_time, exit_time, status)
               VALUES (?, ?, ?, ?, ?)""",
            (employee_id, date_str, time_str, time_str, status),
        )
    else:
        # A row already exists today -> push exit_time forward, but ONLY
        # if this detection is LATER than the current exit_time.
        # Detections can arrive slightly out of order (network delays,
        # multiple camera feeds, etc.), so we guard against exit_time
        # ever moving backward. Comparing as strings works here because
        # time_str is always zero-padded "HH:MM:SS".
        # This is what turns 499 duplicate detections into ZERO extra
        # attendance rows: they all UPDATE the same single row.
        cur.execute(
            """UPDATE attendance SET exit_time = ?
               WHERE employee_id = ? AND date = ?
                 AND (exit_time IS NULL OR ? > exit_time)""",
            (time_str, employee_id, date_str, time_str),
        )

    conn.commit()

    # Read back the final state of today's row, to return to the caller.
    cur.execute(
        "SELECT * FROM attendance WHERE employee_id = ? AND date = ?",
        (employee_id, date_str),
    )
    row = cur.fetchone()
    conn.close()

    name = SAMPLE_EMPLOYEES.get(employee_id, event.name)
    return AttendanceRecord(
        employee_id=row["employee_id"],
        name=name,
        date=row["date"],
        entry_time=row["entry_time"],
        exit_time=row["exit_time"],
        status=row["status"],
    )


def get_today_attendance(date_str: Optional[str] = None) -> List[AttendanceRecord]:
    """All attendance rows for a given date (defaults to today)."""
    date_str = date_str or datetime.now().date().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM attendance WHERE date = ?", (date_str,))
    rows = cur.fetchall()
    conn.close()

    return [
        AttendanceRecord(
            employee_id=r["employee_id"],
            name=SAMPLE_EMPLOYEES.get(r["employee_id"], "Unknown"),
            date=r["date"],
            entry_time=r["entry_time"],
            exit_time=r["exit_time"],
            status=r["status"],
        )
        for r in rows
    ]


def get_absentees(date_str: Optional[str] = None) -> List[AttendanceRecord]:
    """
    Anyone in SAMPLE_EMPLOYEES who does NOT have an attendance row today
    was never detected at all, so they're absent.
    """
    date_str = date_str or datetime.now().date().isoformat()
    present_ids = {r.employee_id for r in get_today_attendance(date_str)}

    absentees = []
    for emp_id, name in SAMPLE_EMPLOYEES.items():
        if emp_id not in present_ids:
            absentees.append(
                AttendanceRecord(
                    employee_id=emp_id,
                    name=name,
                    date=date_str,
                    entry_time=None,
                    exit_time=None,
                    status="ABSENT",
                )
            )
    return absentees


def get_summary(date_str: Optional[str] = None) -> AttendanceSummary:
    """Quick counts: how many present / late / absent today."""
    date_str = date_str or datetime.now().date().isoformat()
    today = get_today_attendance(date_str)
    absentees = get_absentees(date_str)

    present = sum(1 for r in today if r.status == "PRESENT")
    late = sum(1 for r in today if r.status == "LATE")

    return AttendanceSummary(
        date=date_str,
        total_employees=len(SAMPLE_EMPLOYEES),
        present=present,
        late=late,
        absent=len(absentees),
    )


def get_employee_today(employee_id: str, date_str: Optional[str] = None) -> Optional[AttendanceRecord]:
    """Today's single attendance row for one employee (or None)."""
    date_str = date_str or datetime.now().date().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM attendance WHERE employee_id = ? AND date = ?",
        (employee_id, date_str),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return AttendanceRecord(
        employee_id=row["employee_id"],
        name=SAMPLE_EMPLOYEES.get(employee_id, "Unknown"),
        date=row["date"],
        entry_time=row["entry_time"],
        exit_time=row["exit_time"],
        status=row["status"],
    )


def get_employee_history(employee_id: str) -> List[AttendanceRecord]:
    """All past attendance rows for one employee, most recent first."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM attendance WHERE employee_id = ? ORDER BY date DESC",
        (employee_id,),
    )
    rows = cur.fetchall()
    conn.close()

    return [
        AttendanceRecord(
            employee_id=r["employee_id"],
            name=SAMPLE_EMPLOYEES.get(employee_id, "Unknown"),
            date=r["date"],
            entry_time=r["entry_time"],
            exit_time=r["exit_time"],
            status=r["status"],
        )
        for r in rows
    ]


def get_all_events(employee_id: Optional[str] = None) -> List[EventOut]:
    """The raw audit trail - every single detection ever received."""
    conn = get_connection()
    cur = conn.cursor()
    if employee_id:
        cur.execute("SELECT * FROM events WHERE employee_id = ? ORDER BY id", (employee_id,))
    else:
        cur.execute("SELECT * FROM events ORDER BY id")
    rows = cur.fetchall()
    conn.close()

    return [
        EventOut(
            id=r["id"],
            employee_id=r["employee_id"],
            event_type=r["event_type"],
            event_time=r["event_time"],
            full_timestamp=r["full_timestamp"],
            confidence=r["confidence"],
            track_id=r["track_id"],
        )
        for r in rows
    ]
