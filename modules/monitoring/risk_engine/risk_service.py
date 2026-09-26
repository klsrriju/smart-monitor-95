import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "monitoring.db"

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def clamp(v, lo=0, hi=100): return max(lo, min(hi, v))

def calculate_risk(project_id):
    with db() as c:
        project = c.execute("SELECT * FROM project_metrics WHERE project_id=?", (project_id,)).fetchone()
        anomalies = c.execute("SELECT * FROM anomalies WHERE project_id=? AND status='OPEN'", (project_id,)).fetchall()
        inspections = c.execute("SELECT * FROM inspections WHERE project_id=?", (project_id,)).fetchall()
        evidence = c.execute("SELECT * FROM evidence WHERE project_id=?", (project_id,)).fetchall()
    if not project:
        return None

    # Maximum = 100 points.
    # Attendance 0-25: below 90% increases risk linearly.
    attendance_risk = clamp((90 - project["attendance_pct"]) / 90 * 25, 0, 25)
    # Occupancy 0-20: 0 when within capacity; 20 at 25%+ over capacity.
    occupancy_over = max(0, project["people_detected"] - project["capacity"]) / max(project["capacity"], 1)
    occupancy_risk = clamp(occupancy_over / 0.25 * 20, 0, 20)
    # Financial 0-20: utilization above physical progress creates risk.
    financial_gap = max(0, project["fund_utilization_pct"] - project["physical_progress_pct"])
    financial_risk = clamp(financial_gap / 40 * 20, 0, 20)
    # Inspection 0-15: overdue/cancelled/incomplete.
    completed = sum(1 for x in inspections if x["status"] == "COMPLETED")
    inspection_risk = 0 if completed else 15
    # Evidence 0-10: missing/unverified evidence.
    total_ev = len(evidence)
    verified_ev = sum(1 for x in evidence if x["verification_status"] == "VERIFIED")
    evidence_risk = 10 if total_ev == 0 else clamp((total_ev-verified_ev)/max(total_ev,1)*10,0,10)
    # Anomalies 0-10: severity weighted, capped.
    weights = {"LOW": 1, "MEDIUM": 3, "HIGH": 5}
    anomaly_risk = clamp(sum(weights.get(x["severity"],0) for x in anomalies), 0, 10)

    score = round(attendance_risk + occupancy_risk + financial_risk + inspection_risk + evidence_risk + anomaly_risk, 2)
    band = "LOW" if score < 30 else "MEDIUM" if score < 60 else "HIGH"
    surprise = any(x["severity"] == "HIGH" for x in anomalies)

    result = {
        "project_id": project_id,
        "overall_score": score,
        "risk_level": band,
        "components": {
            "attendance": round(attendance_risk,2),
            "occupancy": round(occupancy_risk,2),
            "financial": round(financial_risk,2),
            "inspection": round(inspection_risk,2),
            "evidence": round(evidence_risk,2),
            "anomalies": round(anomaly_risk,2)
        },
        "formula": "Score = Attendance(25) + Occupancy(20) + Financial(20) + Inspection(15) + Evidence(10) + Anomalies(10)",
        "surprise_inspection_recommended": surprise
    }
    return result
