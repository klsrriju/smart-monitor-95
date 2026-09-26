from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend" / "index.html"
CHATBOT = ROOT / "modules" / "chatbot" / "sample_data"
sys.path.insert(0, str(BACKEND))
import main


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main_sync() -> None:
    data = main.DEMO
    write_json(main.DATA_FILE, data)
    html = FRONTEND.read_text(encoding="utf-8")
    embedded = "<script id=\"smartmonitor-demo-data\">\nwindow.SM_DEMO_DB = " + json.dumps(data, separators=(",", ":"), ensure_ascii=False) + ";\nwindow.SM_DEMO_ACTIVE = false;\n</script>"
    html, count = re.subn(r"<script id=\"smartmonitor-demo-data\">.*?</script>", embedded, html, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("smartmonitor-demo-data marker was not found exactly once")
    FRONTEND.write_text(html, encoding="utf-8")

    write_json(CHATBOT / "projects.json", [
        {"project_id": p["id"], "title": p["name"], "status": p["status"], "progress_percentage": p.get("progress_percent", 0), "risk_score": p.get("risk_score", 0)}
        for p in data.get("projects", [])
    ])
    write_json(CHATBOT / "cameras.json", [
        {"camera_id": c["camera_id"], "project_id": c.get("project_id"), "location": c.get("location"), "status": c.get("status"), "max_capacity": c.get("capacity", 0), "offline_reason": c.get("offline_reason", "")}
        for c in data.get("cameras", [])
    ])
    write_json(CHATBOT / "inspections.json", [
        {"inspection_id": i["id"], "project_id": i["project_id"], "inspector_name": i.get("inspector_name"), "status": i.get("status", "pending").upper(), "scheduled_date": i.get("started_at"), "notes": i.get("remarks", "")}
        for i in data.get("inspections", [])
    ])
    write_json(CHATBOT / "anomalies.json", [
        {"anomaly_id": a["id"], "project_id": a.get("project_id"), "camera_id": a.get("camera_id"), "anomaly_type": a.get("type", a.get("category")), "severity": a.get("severity"), "title": a.get("type", "Alert"), "description": a.get("description", "")}
        for a in data.get("alerts", [])
    ])
    write_json(CHATBOT / "attendance.json", data.get("attendance", []))
    write_json(CHATBOT / "employees.json", [
        {"employee_id": u["id"], "name": u["name"], "department": u.get("department", "")}
        for u in data.get("users", []) if u.get("role") != "admin"
    ])
    print(f"Synchronized {len(data.get('projects', []))} projects, {len(data.get('cameras', []))} cameras, and {len(data.get('alerts', []))} derived alerts.")


if __name__ == "__main__":
    main_sync()
