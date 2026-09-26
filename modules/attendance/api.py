"""
api.py
-------
FastAPI app exposing the attendance system over HTTP.
This is the ONLY file that knows about HTTP/FastAPI - all real logic
lives in attendance_service.py. This file just wires HTTP requests to it.

Run with:  uvicorn api:app --reload
Docs at:   http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException
from typing import List, Optional

import attendance_service as service
from models import RecognitionEvent, AttendanceRecord, AttendanceSummary, EventOut

app = FastAPI(
    title="Employee Attendance Module",
    description="Core attendance engine. Receives mock recognition events "
                 "and turns them into daily attendance records.",
)


@app.on_event("startup")
def startup():
    """Runs once when the server starts: creates tables + sample employees."""
    service.setup()


# ---------------------------------------------------------------------
# Endpoint that RECEIVES the mock recognition data (from CCTV/YOLO/etc,
# or in our case, from demo.py / curl / Postman pretending to be it).
# ---------------------------------------------------------------------
@app.post("/recognition-event", response_model=AttendanceRecord)
def receive_event(event: RecognitionEvent):
    """
    Example body:
    {
      "person_id": "EMP001",
      "name": "R. Meena",
      "track_id": 17,
      "confidence": 0.87,
      "timestamp": "2026-09-21T09:04:21"
    }
    """
    return service.process_recognition_event(event)


# ---------------------------------------------------------------------
# Read endpoints (order matters! specific paths before {employee_id})
# ---------------------------------------------------------------------
@app.get("/attendance/today", response_model=List[AttendanceRecord])
def attendance_today():
    return service.get_today_attendance()


@app.get("/attendance/summary", response_model=AttendanceSummary)
def attendance_summary():
    return service.get_summary()


@app.get("/attendance/absentees", response_model=List[AttendanceRecord])
def attendance_absentees():
    return service.get_absentees()


@app.get("/attendance/events", response_model=List[EventOut])
def attendance_events(employee_id: Optional[str] = None):
    """Raw audit trail of every detection. Optionally filter by ?employee_id=EMP001"""
    return service.get_all_events(employee_id)


@app.get("/attendance/{employee_id}/history", response_model=List[AttendanceRecord])
def attendance_history(employee_id: str):
    return service.get_employee_history(employee_id)


@app.get("/attendance/{employee_id}", response_model=AttendanceRecord)
def attendance_by_id(employee_id: str):
    record = service.get_employee_today(employee_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No attendance record for {employee_id} today (likely absent).",
        )
    return record
