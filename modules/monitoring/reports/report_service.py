import csv, io, sqlite3
from pathlib import Path
from datetime import datetime
from anomaly_engine.anomaly_service import get_anomalies
from risk_engine.risk_service import calculate_risk

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "monitoring.db"

def db():
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; return conn

def build_report(project_id):
    with db() as c:
        project=c.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        metrics=c.execute("SELECT * FROM project_metrics WHERE project_id=?", (project_id,)).fetchone()
        inspections=[dict(x) for x in c.execute("SELECT * FROM inspections WHERE project_id=? ORDER BY date DESC",(project_id,))]
        evidence=[dict(x) for x in c.execute("SELECT * FROM evidence WHERE project_id=? ORDER BY upload_time DESC",(project_id,))]
    if not project: return None
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "project": dict(project),
        "attendance": metrics["attendance_pct"] if metrics else None,
        "cctv_occupancy": {"capacity": metrics["capacity"], "people_detected": metrics["people_detected"]} if metrics else None,
        "financial": {"fund_utilization_pct": metrics["fund_utilization_pct"], "physical_progress_pct": metrics["physical_progress_pct"]} if metrics else None,
        "inspection_history": inspections,
        "evidence": evidence,
        "anomalies": get_anomalies(project_id),
        "risk_assessment": calculate_risk(project_id),
        "recommendations": [
            "Review every HIGH severity anomaly within the next field-monitoring cycle.",
            "Verify missing or pending evidence before closing an inspection.",
            "Compare financial utilization with physical progress whenever the configured gap threshold is exceeded."
        ]
    }

def report_csv(project_id):
    report=build_report(project_id)
    if not report: return None
    out=io.StringIO(); w=csv.writer(out)
    w.writerow(["section","key","value"])
    w.writerow(["project","project_id",project_id])
    w.writerow(["attendance","attendance_pct",report["attendance"]])
    occ=report["cctv_occupancy"] or {}
    w.writerow(["occupancy","capacity",occ.get("capacity")])
    w.writerow(["occupancy","people_detected",occ.get("people_detected")])
    fin=report["financial"] or {}
    w.writerow(["financial","fund_utilization_pct",fin.get("fund_utilization_pct")])
    w.writerow(["financial","physical_progress_pct",fin.get("physical_progress_pct")])
    risk=report["risk_assessment"] or {}
    w.writerow(["risk","overall_score",risk.get("overall_score")])
    w.writerow(["risk","risk_level",risk.get("risk_level")])
    for a in report["anomalies"]:
        w.writerow(["anomaly",a["anomaly_type"],f'{a["severity"]}: {a["title"]}'])
    return out.getvalue()
