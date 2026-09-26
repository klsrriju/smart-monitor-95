"""
models.py
---------
Pydantic models describing the SHAPE of data flowing in and out of the system.
FastAPI uses these to automatically validate incoming JSON and to document
the API (you'll see them in the auto-generated /docs page).
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class RecognitionEvent(BaseModel):
    """
    This is the mock data coming from the (not-yet-built) recognition system.
    We only care about this exact shape - nothing about CCTV/YOLO/faces.
    """
    person_id: str
    name: str
    track_id: int
    confidence: float
    timestamp: datetime  # Pydantic auto-parses "2026-09-21T09:04:21"


class EventOut(BaseModel):
    """One row from the raw events log (includes duplicates)."""
    id: int
    employee_id: str
    event_type: str      # ENTRY or EXIT
    event_time: str
    full_timestamp: str
    confidence: Optional[float] = None
    track_id: Optional[int] = None


class AttendanceRecord(BaseModel):
    """One row from the attendance table - ONE per employee per day."""
    employee_id: str
    name: str
    date: str
    entry_time: Optional[str] = None
    exit_time: Optional[str] = None
    status: str  # PRESENT / LATE / ABSENT


class AttendanceSummary(BaseModel):
    date: str
    total_employees: int
    present: int
    late: int
    absent: int
