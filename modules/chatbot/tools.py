from typing import Dict, Any, List, Optional
from database import db

def get_employee_attendance(employee_name: Optional[str] = None, employee_id: Optional[str] = None) -> Dict[str, Any]:
    records = db.attendance
    if employee_id:
        records = [r for r in records if r.get("employee_id").lower() == employee_id.lower()]
    elif employee_name:
        records = [r for r in records if employee_name.lower() in r.get("name", "").lower()]
    
    if not records:
        return {"status": "error", "message": f"No attendance record found for {employee_name or employee_id}."}
    return {"status": "success", "data": records}

def get_camera_status(camera_id: Optional[str] = None, location: Optional[str] = None) -> Dict[str, Any]:
    cameras = db.cameras
    if camera_id:
        filtered = [c for c in cameras if c.get("camera_id").lower() == camera_id.lower()]
    elif location:
        filtered = [c for c in cameras if location.lower() in c.get("location", "").lower()]
    else:
        filtered = cameras

    if not filtered:
        return {"status": "error", "message": "No matching camera found."}
    return {"status": "success", "data": filtered}

def get_project_status(project_id: Optional[str] = None) -> Dict[str, Any]:
    projects = db.projects
    if project_id:
        filtered = [p for p in projects if p.get("project_id").lower() == project_id.lower()]
        if not filtered:
            return {"status": "error", "message": f"Project {project_id} not found."}
        return {"status": "success", "data": filtered[0]}
    return {"status": "success", "data": projects}

def get_anomalies(project_id: Optional[str] = None, severity: Optional[str] = None) -> Dict[str, Any]:
    anomalies = db.anomalies
    if project_id:
        anomalies = [a for a in anomalies if a.get("project_id").lower() == project_id.lower()]
    if severity:
        anomalies = [a for a in anomalies if a.get("severity").lower() == severity.lower()]
    
    return {"status": "success", "data": anomalies}

def get_inspections(project_id: Optional[str] = None) -> Dict[str, Any]:
    inspections = db.inspections
    if project_id:
        inspections = [i for i in inspections if i.get("project_id").lower() == project_id.lower()]
    
    return {"status": "success", "data": inspections}