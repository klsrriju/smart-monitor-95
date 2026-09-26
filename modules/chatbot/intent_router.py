import re
from typing import Dict, Any, Tuple
import tools

def extract_entities(query: str) -> Dict[str, Any]:
    entities = {}
    
    # Extract Project IDs (e.g., PS-26095)
    project_match = re.search(r"PS-\d+", query, re.IGNORECASE)
    if project_match:
        entities["project_id"] = project_match.group(0).upper()
        
    # Extract Camera IDs (e.g., CAM-001)
    camera_match = re.search(r"CAM-\d+", query, re.IGNORECASE)
    if camera_match:
        entities["camera_id"] = camera_match.group(0).upper()
        
    # Extract Employee IDs (e.g., EMP001)
    emp_id_match = re.search(r"EMP\d+", query, re.IGNORECASE)
    if emp_id_match:
        entities["employee_id"] = emp_id_match.group(0).upper()

    # Known Employee Names matching
    known_names = ["R. Meena", "Meena", "K. Rajesh", "Rajesh", "P. Priya", "Priya", "S. Suresh", "Suresh"]
    for name in known_names:
        if re.search(rf"\b{re.escape(name)}\b", query, re.IGNORECASE):
            entities["employee_name"] = name
            break
            
    return entities

def route_query(query: str) -> Tuple[str, Dict[str, Any]]:
    q_lower = query.lower()
    entities = extract_entities(query)
    
    # 1. Attendance Queries
    if "attendance" in q_lower or "present" in q_lower or "absent" in q_lower or "late" in q_lower or "working" in q_lower:
        result = tools.get_employee_attendance(
            employee_name=entities.get("employee_name"),
            employee_id=entities.get("employee_id")
        )
        return "ATTENDANCE_QUERY", result

    # 2. Camera / Occupancy Queries
    elif "camera" in q_lower or "occupancy" in q_lower or "capacity" in q_lower or "gate" in q_lower or "zone" in q_lower:
        result = tools.get_camera_status(
            camera_id=entities.get("camera_id")
        )
        return "CAMERA_QUERY", result

    # 3. Anomaly / Safety Violation Queries
    elif "anomaly" in q_lower or "anomalies" in q_lower or "violation" in q_lower or "alert" in q_lower:
        result = tools.get_anomalies(
            project_id=entities.get("project_id")
        )
        return "ANOMALY_QUERY", result

    # 4. Inspection Queries
    elif "inspection" in q_lower or "audit" in q_lower or "inspector" in q_lower:
        result = tools.get_inspections(
            project_id=entities.get("project_id")
        )
        return "INSPECTION_QUERY", result

    # 5. Project Status / Risk Queries
    elif "project" in q_lower or "progress" in q_lower or "risk" in q_lower or "status" in q_lower:
        result = tools.get_project_status(
            project_id=entities.get("project_id")
        )
        return "PROJECT_QUERY", result

    # Fallback to general LLM conversation
    else:
        return "GENERAL_QUERY", {"status": "info", "message": "No direct tool match required."}