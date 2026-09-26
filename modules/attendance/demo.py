"""
demo.py
--------
Run this file to see the WHOLE core flow working, with pure Python -
no FastAPI, no server, no CCTV needed.

What it proves:
  1. EMP001 entering creates an attendance record.
  2. EMP001 being detected 500 more times does NOT create duplicates.
  3. EMP001's last detection becomes their exit time.
  4. Employees never detected show up as ABSENT.
  5. Status correctly becomes PRESENT or LATE based on entry time.
"""

from datetime import datetime, timedelta

import database
import attendance_service as service
from models import RecognitionEvent

# Start completely fresh each time this demo runs
database.reset_db()
service.setup()

TODAY = datetime.now().date()


def make_event(person_id, name, hour, minute, second, track_id=1, confidence=0.9):
    ts = datetime.combine(TODAY, datetime.min.time()) + timedelta(
        hours=hour, minutes=minute, seconds=second
    )
    return RecognitionEvent(
        person_id=person_id,
        name=name,
        track_id=track_id,
        confidence=confidence,
        timestamp=ts,
    )


print("=== STEP 1: EMP001 enters at 09:04:21 ===")
result = service.process_recognition_event(make_event("EMP001", "R. Meena", 9, 4, 21))
print(result)

print("\n=== STEP 2: EMP001 gets detected 500 MORE times during the day ===")
for i in range(500):
    minute_offset = (i * 3) % (7 * 60 + 28)   # spread detections across the working day
    hour = 9 + minute_offset // 60
    minute = minute_offset % 60
    service.process_recognition_event(make_event("EMP001", "R. Meena", hour, minute, 0))
print("Sent 500 duplicate detections.")

print("\n=== STEP 3: EMP001's final exit detection at 16:32:10 ===")
result = service.process_recognition_event(make_event("EMP001", "R. Meena", 16, 32, 10))
print(result)

print("\n=== STEP 4: EMP003 enters LATE at 09:20:00 ===")
result = service.process_recognition_event(make_event("EMP003", "P. Priya", 9, 20, 0))
print(result)

print("\n=== STEP 5: Today's attendance table (must be exactly ONE row for EMP001) ===")
today_rows = service.get_today_attendance()
for r in today_rows:
    print(r)
emp001_rows = [r for r in today_rows if r.employee_id == "EMP001"]
assert len(emp001_rows) == 1, "DUPLICATE PREVENTION FAILED!"
print(f"\n✅ Confirmed: exactly {len(emp001_rows)} attendance row exists for EMP001 today.")

print("\n=== STEP 6: Absentees (EMP002 and EMP004 never showed up) ===")
for r in service.get_absentees():
    print(r)

print("\n=== STEP 7: Daily summary ===")
print(service.get_summary())

print("\n=== STEP 8: Raw event log size for EMP001 (should be 502: 1 + 500 + 1) ===")
events = service.get_all_events("EMP001")
print(f"Total raw events logged: {len(events)}")
