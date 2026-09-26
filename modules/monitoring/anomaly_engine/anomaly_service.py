import sqlite3
from datetime import datetime
from pathlib import Path

from .attendance_rules import detect_attendance
from .occupancy_rules import detect_occupancy
from .financial_rules import detect_financial
from .inspection_rules import detect_inspection, detect_repeated_issues
from .evidence_rules import detect_evidence

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "monitoring.db"

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def save_anomaly(a):
    with db() as c:
        c.execute("""INSERT INTO anomalies
        (project_id, anomaly_type, severity, title, description, detected_at, status)
        VALUES (?,?,?,?,?,?,?)""", (
            a["project_id"], a["anomaly_type"], a["severity"], a["title"],
            a["description"], datetime.utcnow().isoformat(), "OPEN"
        ))
    return a

def get_anomalies(project_id=None, severity=None):
    sql = "SELECT * FROM anomalies WHERE 1=1"
    args = []
    if project_id: sql += " AND project_id=?"; args.append(project_id)
    if severity: sql += " AND severity=?"; args.append(severity.upper())
    sql += " ORDER BY detected_at DESC"
    with db() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]

def run_rules(payload):
    out = []
    a = detect_attendance(payload["project_id"], payload["expected_attendance"], payload["actual_attendance"], payload.get("attendance_threshold",15))
    if a: out.append(a)
    a = detect_occupancy(payload["project_id"], payload["capacity"], payload["people_detected"])
    if a: out.append(a)
    a = detect_financial(payload["project_id"], payload["fund_utilization"], payload["physical_progress"], payload.get("financial_threshold",20))
    if a: out.append(a)
    out.extend(detect_inspection(payload["project_id"], payload["inspection_status"], payload["inspection_date"], payload.get("inspection_issue_count",0)))
    a = detect_repeated_issues(payload["project_id"], payload.get("repeated_issue_count",0))
    if a: out.append(a)
    out.extend(detect_evidence(payload["project_id"], payload.get("inspection_completed",False),
                               payload.get("required_evidence_count",1), payload.get("verified_evidence_count",0),
                               payload.get("total_evidence_count",0)))
    for item in out: save_anomaly(item)
    return get_anomalies(payload["project_id"])
