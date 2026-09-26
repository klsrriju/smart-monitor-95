from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, time, datetime

class ChecklistItem(BaseModel):
    item: str
    checked: bool = False
    note: Optional[str] = None

class InspectionCreate(BaseModel):
    project_id: str
    inspector_id: str
    date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: str = "SCHEDULED"
    checklist: List[ChecklistItem] = Field(default_factory=list)
    remarks: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class InspectionUpdate(BaseModel):
    inspector_id: Optional[str] = None
    date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[str] = None
    checklist: Optional[List[ChecklistItem]] = None
    remarks: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
