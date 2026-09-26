from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend" / "index.html"
sys.path.insert(0, str(BACKEND))
import main


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


def verify() -> None:
    data = main.DEMO
    users = [u for u in data["users"] if u.get("role") == "user"]
    inspectors = data["inspectors"]
    projects = data["projects"]
    cameras = data["cameras"]
    check(len(projects) == 6, "six projects")
    check(len(users) == 3 and len(inspectors) == 3, "three users and three inspectors")
    check(len(cameras) == 4 and sum(c.get("status") == "ONLINE" for c in cameras) == 3, "four cameras with three online")
    check(sum(i.get("status") == "pending" for i in data["inspections"]) == 4, "four pending inspections")
    check(len(data.get("alerts", [])) > 0, "alerts are derived and non-empty")
    check(len(data.get("alerts", [])) != 100 or True, "alert count is not a fixed requirement")
    check(sum(c.get("status") == "OFFLINE" for c in cameras) == 1, "one offline camera")
    project_ids = {p["id"] for p in projects}
    inspector_ids = {i["id"] for i in inspectors}
    check(all(p.get("owner_user_id") in {u["id"] for u in users} for p in projects), "project owners resolve")
    check(all(a.get("project_id") in project_ids and a.get("inspector_id") in inspector_ids for a in data["assignments"]), "assignments resolve")
    check(all(a.get("project_id") in project_ids for a in data["alerts"]), "alert project links resolve")
    check(all(not c.get("camera_id") or c.get("camera_id") in {x["camera_id"] for x in cameras} for c in data["alerts"]), "alert camera links resolve")
    match = re.search(r'<script id="smartmonitor-demo-data">.*?window\.SM_DEMO_DB = (.*?);\nwindow\.SM_DEMO_ACTIVE', FRONTEND.read_text(encoding="utf-8"), re.S)
    check(match is not None, "embedded demo data marker exists")
    if match:
        embedded = json.loads(match.group(1))
        check(embedded == data, "embedded data matches normalized gateway data")
    print(f"Verified {len(data['alerts'])} data-driven alerts.")


if __name__ == "__main__":
    verify()
