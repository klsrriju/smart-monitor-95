"""
SmartMonitor combined gateway.

Default: DEMO mode, using demo_data.json. If DATABASE_URL is configured,
the same collections are stored in PostgreSQL in smartmonitor_records
(collection, record_id, payload). This keeps the V14 UI contract stable
while allowing PostgreSQL to become the persistent source of truth.

Run:
    uvicorn main:app --host 127.0.0.1 --port 8001
"""
from __future__ import annotations
import copy, hashlib, json, os, secrets, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
BASE = Path(__file__).resolve().parent
DATA_FILE = BASE / "demo_data.json"
FRONTEND = BASE.parent / "frontend" / "index.html"

with DATA_FILE.open("r", encoding="utf-8") as f:
    DEMO = json.load(f)

def normalize_demo_data():
    DEMO["users"] = [u for u in DEMO.get("users", []) if u.get("id") != "USR-STA-001"]
    user_statuses = {"USR-ADM-001": "Active", "USR-INS-001": "Active", "USR-INS-002": "On Leave", "USR-INS-003": "Active", "USR-NGO-001": "Active", "USR-NGO-002": "Pending Review", "USR-NGO-003": "Inactive"}
    for user in DEMO["users"]:
        user["status"] = user_statuses.get(user.get("id"), "Active")
    DEMO["feedback"] = [f for f in DEMO.get("feedback", []) if f.get("project_id") != "PRJ-001"]
    feedback_users = {"PRJ-002": "USR-NGO-001", "PRJ-003": "USR-NGO-002"}
    for feedback in DEMO.get("feedback", []):
        feedback.setdefault("user_id", feedback_users.get(feedback.get("project_id"), "USR-NGO-001"))
        feedback.setdefault("user_name", next((u.get("name") for u in DEMO["users"] if u.get("id") == feedback["user_id"]), "User"))
        feedback.setdefault("review_text", feedback.pop("remarks", "Project feedback"))
    statuses = {
        "PRJ-001": ("Completed", 100), "PRJ-002": ("On Track", 72),
        "PRJ-003": ("Needs Review", 55), "PRJ-004": ("Pending Inspection", 40),
        "PRJ-005": ("Delayed", 30), "PRJ-006": ("In Progress", 50),
    }
    for project in DEMO.get("projects", []):
        status, progress = statuses.get(project.get("id"), (project.get("status", "In Progress"), 0))
        project["status"], project["progress_percent"] = status, progress
        project["location"] = project.get("address", project.get("district", ""))
        project["incharge"] = project.get("organization", "")
    assignment_map = {"PRJ-001":"INSP-001", "PRJ-002":"INSP-002", "PRJ-003":"INSP-003",
                      "PRJ-004":"INSP-001", "PRJ-005":"INSP-002", "PRJ-006":"INSP-003"}
    for assignment in DEMO.get("assignments", []):
        assignment["inspector_id"] = assignment_map.get(assignment.get("project_id"), assignment.get("inspector_id"))
        assignment["status"] = "completed" if assignment.get("project_id") == "PRJ-001" else "pending"
    for inspection in DEMO.get("inspections", []):
        if inspection.get("id") == "INS-006":
            inspection.update(project_id="PRJ-001", project="Chennai Community Support Centre", inspector_id="INSP-001", inspector_name="Arvind R.", status="completed", overall_score=88)
        elif inspection.get("id") == "INS-001":
            inspection["status"] = "completed"
        else:
            inspection["status"] = "pending"
    allowed_cameras = {"CAM-001", "CAM-002", "CAM-003", "CAM-004"}
    DEMO["cameras"] = [c for c in DEMO.get("cameras", []) if c.get("camera_id") in allowed_cameras]
    for camera in DEMO["cameras"]:
        camera.setdefault("offline_reason", "")
        camera.setdefault("offline_since", None)
        if camera.get("camera_id") == "CAM-004":
            camera.update(status="OFFLINE", offline_reason="Network connection lost.", offline_since="2026-09-23T08:50:00+00:00")
    DEMO["occupancy"] = [o for o in DEMO.get("occupancy", []) if o.get("camera_id") in allowed_cameras]
    alert_rows = []
    assignments = {a.get("project_id"): a for a in DEMO.get("assignments", [])}
    cameras = {c.get("camera_id"): c for c in DEMO.get("cameras", [])}
    for camera_id, camera in cameras.items():
        project_id = camera.get("project_id")
        assignment = assignments.get(project_id, {})
        if str(camera.get("status", "")).upper() == "OFFLINE":
            alert_rows.append({"id": "ALT-CAMERA-" + camera_id, "type": "CAMERA_OFFLINE", "category": "CAMERA", "severity": "HIGH", "project_id": project_id, "camera_id": camera_id, "inspector_id": assignment.get("inspector_id"), "status": "OPEN", "created_at": camera.get("offline_since")})
        occupancy = next((o for o in DEMO.get("occupancy", []) if o.get("camera_id") == camera_id), {})
        if float(occupancy.get("occupancy_percentage", 0)) >= 80:
            alert_rows.append({"id": "ALT-OCCUPANCY-" + camera_id, "type": "OCCUPANCY", "category": "CAMERA", "severity": "MEDIUM", "project_id": project_id, "camera_id": camera_id, "inspector_id": assignment.get("inspector_id"), "status": "OPEN", "created_at": occupancy.get("recorded_at")})
    for inspection in DEMO.get("inspections", []):
        if str(inspection.get("status", "")).lower() == "pending":
            project_id = inspection.get("project_id")
            alert_rows.append({"id": "ALT-INSPECTION-" + str(inspection.get("id")), "type": "INSPECTION_PENDING", "category": "INSPECTION", "severity": "MEDIUM", "project_id": project_id, "camera_id": None, "inspector_id": inspection.get("inspector_id"), "status": "OPEN", "created_at": inspection.get("started_at") or "2026-09-24T00:00:00+00:00"})
    for project in DEMO.get("projects", []):
        if project.get("status") == "Delayed":
            assignment = assignments.get(project.get("id"), {})
            alert_rows.append({"id": "ALT-DELAY-" + str(project.get("id")), "type": "PROJECT_DELAY", "category": "PROJECT_DELAY", "severity": "HIGH", "project_id": project.get("id"), "camera_id": None, "inspector_id": assignment.get("inspector_id"), "status": "OPEN", "created_at": "2026-09-24T00:00:00+00:00"})
    DEMO["alerts"] = alert_rows

normalize_demo_data()

SESSIONS = {}
PASSWORDS = {
    "admin": ("3lXrwmVzhMiusVnbdTmHdg==", "QfLhk58oC2p8KkUIrqvjSyzBjShcLm9jkGnKESgkPXo="),
    "ramesh": ("mOK323gLWBh9GT1m7f+m7w==", "YjDncuhS04aOpYi6Znu0tpf++LD6NgCyfkO+gwKSjJQ="),
    "kalaivani": ("foPgpfGsbQwUstRB/SkQzg==", "26op6GJIyjTi1Umnf+10DfiNXe+UvdZDANmCOeNe2lA="),
    "priya": ("gcCTvHCD6H69pfiPdFYAcA==", "aK8MthdlkMjub0xKVhW+eT2po/Kr90hmCWJlDeb2DUk="),
    "aravind": ("q1ZZHQ+wn/c/9DiQn+qVlg==", "J7rnAmFu4a5k5OYtiMhVrpawDllR5JtpbyU71VyUhOI="),
    "meena": ("UiOe91o5vr/kb4tWniS2rw==", "ui/ro0X4C5ftQW1Pk9tNPgXREFHqL6I86JBTEyXcTOk="),
    "karthik": ("lRyb+HYFMjd0WQyQnH7ACA==", "tfqS3XEObaLkDE/QX9CtM+03GdTarzTOGr7lRLNWodg="),
}
LOGIN_IDS = {"admin":"USR-ADM-001", "ramesh":"USR-NGO-001", "kalaivani":"USR-NGO-002", "priya":"USR-NGO-003", "aravind":"USR-INS-001", "meena":"USR-INS-002", "karthik":"USR-INS-003"}

def password_ok(password: str, salt: str, expected: str):
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), __import__("base64").b64decode(salt), 120000)
    return secrets.compare_digest(__import__("base64").b64encode(digest).decode(), expected)

def user_for_token(token: str | None):
    return SESSIONS.get(token or "")

def scope_rows(name: str, rows: list[dict], user_id: str | None, role: str | None):
    if not user_id or str(role).lower() == "admin": return rows
    projects = {str(p.get("id")) for p in DEMO.get("projects", []) if str(p.get("owner_user_id")) == str(user_id)}
    inspector_ids = {str(i.get("id")) for i in DEMO.get("inspectors", []) if str(i.get("user_id")) == str(user_id)}
    projects.update(str(a.get("project_id")) for a in DEMO.get("assignments", []) if str(a.get("inspector_id")) in inspector_ids)
    if name == "users": return [x for x in rows if str(x.get("id")) == str(user_id)]
    if name == "inspectors": return [x for x in rows if str(x.get("user_id")) == str(user_id)]
    if name == "projects": return [x for x in rows if str(x.get("id")) in projects]
    if name == "assignments": return [x for x in rows if str(x.get("project_id")) in projects]
    if name == "inspections": return [x for x in rows if str(x.get("project_id")) in projects]
    if name == "alerts": return [x for x in rows if str(x.get("project_id")) in projects]
    if name == "notifications": return [x for x in rows if str(x.get("target_user_id", user_id)) == str(user_id) or str(x.get("project_id")) in projects]
    return [x for x in rows if str(x.get("project_id")) in projects or not x.get("project_id")]

COLLECTIONS = {
    "users":"users", "inspectors":"inspectors", "projects":"projects",
    "assignments":"assignments", "inspections":"inspections",
    "attendance":"attendance", "anomalies":"anomalies", "documents":"documents",
    "funds":"funds", "cameras":"cameras", "occupancy":"occupancy",
    "feedback":"feedback", "notifications":"notifications", "reschedules":"reschedules",
    "alerts":"alerts", "credentials":"credentials",
}
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
ENGINE = None
if DATABASE_URL:
    try:
        from sqlalchemy import create_engine, text
        ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)
        with ENGINE.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS smartmonitor_records (
                    collection TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (collection, record_id)
                )
            """))
    except Exception as exc:
        print(f"WARNING: PostgreSQL unavailable; using demo mode. {exc}")
        ENGINE = None

app = FastAPI(title="SmartMonitor Combined Gateway", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])

def _demo_collection(name: str):
    return DEMO.get(name, [])

def _db_collection(name: str):
    if ENGINE is None:
        return copy.deepcopy(_demo_collection(name))
    from sqlalchemy import text
    with ENGINE.connect() as conn:
        rows = conn.execute(
            text("SELECT payload FROM smartmonitor_records WHERE collection=:c ORDER BY updated_at DESC"),
            {"c": name}
        ).fetchall()
    return [dict(r[0]) for r in rows]

def collection(name: str):
    return _db_collection(name)

def write_record(name: str, record: dict):
    record = dict(record)
    rid = str(record.get("id") or record.get("user_id") or uuid.uuid4())
    record["id"] = rid
    if ENGINE is None:
        rows = DEMO.setdefault(name, [])
        for i, old in enumerate(rows):
            if str(old.get("id")) == rid:
                rows[i] = record
                break
        else:
            rows.append(record)
        return record
    from sqlalchemy import text
    with ENGINE.begin() as conn:
        conn.execute(text("""
            INSERT INTO smartmonitor_records(collection, record_id, payload)
            VALUES (:c,:id,:payload)
            ON CONFLICT(collection,record_id)
            DO UPDATE SET payload=EXCLUDED.payload, updated_at=NOW()
        """), {"c":name, "id":rid, "payload":json.dumps(record)})
    return record

def delete_record(name: str, rid: str):
    if ENGINE is None:
        rows = DEMO.setdefault(name, [])
        DEMO[name] = [x for x in rows if str(x.get("id")) != str(rid)]
        return
    from sqlalchemy import text
    with ENGINE.begin() as conn:
        conn.execute(text("DELETE FROM smartmonitor_records WHERE collection=:c AND record_id=:id"),
                     {"c":name,"id":rid})

def find_record(name: str, rid: str):
    return next((x for x in collection(name) if str(x.get("id")) == str(rid)), None)

@app.get("/")
def root():
    return FileResponse(FRONTEND)

@app.get("/health")
def health():
    return {"status":"ok","service":"SmartMonitor Combined Gateway",
            "database":"postgresql" if ENGINE else "demo"}

@app.get("/api/projects")
def projects(user_id:str|None=None, role:str|None=None):
    rows=scope_rows("projects", collection("projects"), user_id, role)
    return {"success":True,"count":len(rows),"projects":rows}

@app.get("/api/projects/{project_id}")
def project(project_id:str):
    p=find_record("projects",project_id)
    if not p: raise HTTPException(404,"Project not found")
    return {"success":True,"project":p}

@app.get("/api/projects/{project_id}/summary")
def project_summary(project_id:str):
    p=find_record("projects",project_id)
    if not p: raise HTTPException(404,"Project not found")
    return {"success":True,"project":p,
            "attendance": [x for x in collection("attendance") if str(x.get("project_id"))==project_id],
            "anomalies":[x for x in collection("anomalies") if str(x.get("project_id"))==project_id],
            "inspections":[x for x in collection("inspections") if str(x.get("project_id"))==project_id],
            "assignments":[x for x in collection("assignments") if str(x.get("project_id"))==project_id],
            "evidence":[x for x in collection("documents") if str(x.get("project_id"))==project_id],
            "documents":[x for x in collection("documents") if str(x.get("project_id"))==project_id],
            "funds":[x for x in collection("funds") if str(x.get("project_id"))==project_id],
            "feedback":[x for x in collection("feedback") if str(x.get("project_id"))==project_id]}

@app.get("/api/dashboard/summary")
def dashboard():
    ps=collection("projects"); an=collection("anomalies"); ins=collection("inspections")
    return {"success":True,"total_projects":len(ps),
            "active_projects":sum(str(x.get("status","")).lower()=="active" for x in ps),
            "open_anomalies":sum(str(x.get("resolution_status",x.get("status",""))).lower() in {"open","pending"} for x in an),
            "completed_inspections":sum(str(x.get("status","")).lower()=="completed" for x in ins)}

@app.get("/api/users")
def users(user_id:str|None=None, role:str|None=None): return {"success":True,"users":scope_rows("users", collection("users"), user_id, role)}

@app.get("/api/inspectors")
def inspectors(user_id:str|None=None, role:str|None=None): return {"success":True,"inspectors":scope_rows("inspectors", collection("inspectors"), user_id, role)}

@app.get("/api/inspection-assignments")
def assignments(user_id:str|None=None, role:str|None=None): return {"success":True,"assignments":scope_rows("assignments", collection("assignments"), user_id, role)}

@app.get("/api/inspections")
def inspections(user_id:str|None=None, role:str|None=None): return {"success":True,"inspections":scope_rows("inspections", collection("inspections"), user_id, role)}

@app.get("/api/attendance")
def attendance(): return {"success":True,"attendance":collection("attendance")}

@app.get("/api/anomalies")
def anomalies(user_id:str|None=None, role:str|None=None): return {"success":True,"anomalies":scope_rows("anomalies", collection("anomalies"), user_id, role)}

@app.get("/api/evidence")
def evidence(): return {"success":True,"evidence":collection("documents")}

@app.get("/api/feedback")
def feedback(user_id:str|None=None, role:str|None=None): return {"success":True,"feedback":scope_rows("feedback", collection("feedback"), user_id, role)}

@app.get("/api/funds")
def funds(): return {"success":True,"funds":collection("funds")}

@app.get("/api/cctv/cameras")
def cameras(user_id:str|None=None, role:str|None=None): return {"success":True,"cameras":scope_rows("cameras", collection("cameras"), user_id, role)}

@app.get("/api/cctv/occupancy")
def occupancy(user_id:str|None=None, role:str|None=None): return {"success":True,"occupancy":scope_rows("occupancy", collection("occupancy"), user_id, role)}

@app.get("/api/notifications")
def notifications(user_id:str|None=None, role:str|None=None): return {"success":True,"notifications":scope_rows("notifications", collection("notifications"), user_id, role)}

@app.get("/api/alerts")
def alerts(user_id:str|None=None, role:str|None=None):
    rows = scope_rows("alerts", collection("alerts"), user_id, role)
    return {"success":True,"count":len(rows),"alerts":rows}

@app.get("/api/projects/{project_id}/attendance")
def project_attendance(project_id:str):
    return {"success":True,"attendance":[x for x in collection("attendance") if str(x.get("project_id"))==project_id]}

@app.get("/api/projects/{project_id}/anomalies")
def project_anomalies(project_id:str):
    return {"success":True,"anomalies":[x for x in collection("anomalies") if str(x.get("project_id"))==project_id]}

@app.get("/api/projects/{project_id}/inspections")
def project_inspections(project_id:str):
    return {"success":True,"inspections":[x for x in collection("inspections") if str(x.get("project_id"))==project_id]}

@app.get("/api/projects/{project_id}/assignments")
def project_assignments(project_id:str):
    return {"success":True,"assignments":[x for x in collection("assignments") if str(x.get("project_id"))==project_id]}

@app.get("/api/projects/{project_id}/feedback")
def project_feedback(project_id:str):
    return {"success":True,"feedback":[x for x in collection("feedback") if str(x.get("project_id"))==project_id]}

@app.post("/api/feedback")
def create_feedback(payload:dict):
    project_id = str(payload.get("project_id", ""))
    user_id = str(payload.get("user_id", ""))
    project = find_record("projects", project_id)
    if not project or project.get("status") != "Completed":
        raise HTTPException(400, "Reviews are available only for completed projects")
    existing = next((x for x in collection("feedback") if str(x.get("project_id")) == project_id and str(x.get("user_id")) == user_id), None)
    item = dict(payload)
    item["id"] = existing.get("id") if existing else "FDB-" + uuid.uuid4().hex[:8].upper()
    item["created_at"] = existing.get("created_at") if existing else datetime.now(timezone.utc).isoformat()
    item["updated_at"] = datetime.now(timezone.utc).isoformat()
    item["user_name"] = next((u.get("name") for u in collection("users") if str(u.get("id")) == user_id), item.get("user_name", "User"))
    return {"success":True,"feedback":write_record("feedback", item)}

@app.patch("/api/feedback/{feedback_id}")
def update_feedback(feedback_id:str, payload:dict):
    item = find_record("feedback", feedback_id)
    if not item: raise HTTPException(404, "Review not found")
    item.update({"rating": payload.get("rating", item.get("rating")), "review_text": payload.get("review_text", item.get("review_text")), "updated_at": datetime.now(timezone.utc).isoformat()})
    item["id"] = feedback_id
    return {"success":True,"feedback":write_record("feedback", item)}

@app.get("/api/projects/{project_id}/cameras")
def project_cameras(project_id:str):
    return {"success":True,"cameras":[x for x in collection("cameras") if str(x.get("project_id"))==project_id]}

@app.get("/api/projects/{project_id}/evidence")
def project_evidence(project_id:str):
    return {"success":True,"evidence":[x for x in collection("documents") if str(x.get("project_id"))==project_id]}

@app.get("/api/project-details/v12/{project_id}")
@app.get("/api/project-details/{project_id}")
def project_details(project_id:str, user_id:str|None=None, role:str|None=None):
    return project_summary(project_id)

@app.get("/api/project-documents/v12")
@app.get("/api/project-documents")
def project_documents(user_id:str|None=None, role:str|None=None):
    rows=collection("documents")
    if role=="user" and user_id:
        rows=[x for x in rows if str(x.get("uploaded_by"))==user_id or str(x.get("project_id")) in
              {str(p.get("id")) for p in collection("projects") if str(p.get("owner_user_id"))==user_id}]
    return {"success":True,"documents":rows}

@app.get("/api/notifications/v12/{role}")
@app.get("/api/notifications/role/{role}")
def role_notifications(role:str,user_id:str|None=None):
    rows=collection("notifications")
    if role and role!="admin":
        rows=[x for x in rows if str(x.get("target_role","")).lower() in {role.lower(),"all"}]
    return {"success":True,"notifications":rows}

@app.get("/api/reschedule-requests/v12")
def reschedules(status:str|None=None):
    rows=collection("reschedules")
    if status: rows=[x for x in rows if str(x.get("status","")).lower()==status.lower()]
    return {"success":True,"requests":rows}

@app.post("/api/auth/login")
def login(payload:dict):
    login_id = str(payload.get("login_id") or payload.get("email") or "").strip().lower()
    account = next((u for u in DEMO.get("users", []) if str(u.get("email", "")).lower() == login_id or str(u.get("login_id", "")).lower() == login_id), None)
    if account is None:
        short_login = login_id.split("@", 1)[0]
        uid = LOGIN_IDS.get(login_id) or LOGIN_IDS.get(short_login)
        account = next((u for u in DEMO.get("users", []) if u.get("id") == uid), None)
    credential_key = next((key for key, uid in LOGIN_IDS.items() if account and uid == account.get("id")), login_id)
    if account is None or credential_key not in PASSWORDS or not password_ok(str(payload.get("password", "")), *PASSWORDS[credential_key]):
        raise HTTPException(401, "Invalid login ID or password")
    token = secrets.token_urlsafe(24)
    SESSIONS[token] = {"id": account["id"], "role": account["role"]}
    return {"success":True,"token":token,"user":account}

@app.post("/api/auth/change-password")
def change_password(payload:dict):
    user = next((u for u in DEMO.get("users", []) if u.get("id") == payload.get("user_id")), None)
    if not user: raise HTTPException(404, "User not found")
    return {"success":True,"message":"Password change recorded for the demo account."}

@app.post("/api/session/ensure")
@app.post("/api/session/ensure-v12")
def ensure_session(payload:dict):
    email=str(payload.get("email","")).lower()
    user=next((x for x in collection("users") if str(x.get("email","")).lower()==email),None)
    if not user:
        user={"id":"USR-"+uuid.uuid4().hex[:8].upper(),"name":payload.get("name","Demo User"),
              "email":email,"role":payload.get("role","user"),"department":payload.get("department","DoSJE")}
        write_record("users",user)
    return {"success":True,"user":user}

@app.post("/api/users/v13")
@app.post("/api/users")
def create_user(payload:dict):
    user=dict(payload); user["id"]=user.get("id") or "USR-"+uuid.uuid4().hex[:8].upper()
    return {"success":True,"user":write_record("users",user)}

@app.patch("/api/users/v13/{user_id}")
@app.patch("/api/users/{user_id}")
def update_user(user_id:str,payload:dict):
    user=find_record("users",user_id)
    if not user: raise HTTPException(404,"User not found")
    user.update(payload); user["id"]=user_id
    return {"success":True,"user":write_record("users",user)}

@app.delete("/api/users/v13/{user_id}")
@app.delete("/api/users/{user_id}")
def delete_user(user_id:str):
    delete_record("users",user_id)
    return {"success":True}

@app.delete("/api/projects/v13/{project_id}")
def delete_project(project_id:str):
    if not find_record("projects", project_id): raise HTTPException(404, "Project not found")
    for name in ("projects", "assignments", "inspections", "attendance", "anomalies", "documents", "funds", "cameras", "occupancy", "feedback", "alerts"):
        for row in collection(name):
            if str(row.get("id")) == project_id or str(row.get("project_id")) == project_id:
                delete_record(name, str(row.get("id")))
    return {"success":True}

@app.post("/api/projects/v12/create-and-assign")
@app.post("/api/projects/create-and-assign")
@app.post("/api/projects")
def create_project(payload:dict):
    project=dict(payload); project["id"]=project.get("id") or "PRJ-"+uuid.uuid4().hex[:8].upper()
    project.setdefault("status","active"); project.setdefault("risk_score",25)
    write_record("projects",project)
    return {"success":True,"project":project}

@app.post("/api/role/inspector/v12/inspections")
def submit_inspection(payload:dict):
    item=dict(payload); item["id"]=item.get("id") or "INS-"+uuid.uuid4().hex[:8].upper()
    item.setdefault("status","completed"); item.setdefault("completed_at",__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat())
    write_record("inspections",item)
    return {"success":True,"inspection":item}

@app.post("/api/role/inspector/v12/reschedule")
def submit_reschedule(payload:dict):
    item=dict(payload); item["id"]=item.get("id") or "RES-"+uuid.uuid4().hex[:8].upper(); item.setdefault("status","Pending")
    write_record("reschedules",item)
    return {"success":True,"request":item}

@app.patch("/api/reschedule-requests/v12/{request_id}")
def update_reschedule(request_id:str, payload:dict):
    item=find_record("reschedules", request_id)
    if not item: raise HTTPException(404, "Reschedule request not found")
    item.update(payload); item["id"] = request_id; write_record("reschedules", item)
    return {"success":True,"request":item}

@app.patch("/api/anomalies/v12/{anomaly_id}/resolve")
def resolve_anomaly(anomaly_id:str,payload:dict):
    a=find_record("anomalies",anomaly_id)
    if not a: raise HTTPException(404,"Anomaly not found")
    status=payload.get("resolution_status") or payload.get("status") or "acknowledged"
    a["resolution_status"]=status
    a["status"]=str(status).upper()
    a["resolution_remarks"]=payload.get("resolution_remarks","")
    write_record("anomalies",a)
    return {"success":True,"anomaly":a}

@app.post("/api/notifications/v12/broadcast")
@app.post("/api/notifications/broadcast")
def broadcast(payload:dict):
    n=dict(payload); n["id"]=n.get("id") or "NTF-"+uuid.uuid4().hex[:8].upper(); n.setdefault("is_read",False)
    write_record("notifications",n)
    return {"success":True,"notification":n}

@app.post("/api/notifications/v12/mark-read")
@app.post("/api/notifications/mark-read")
def mark_read(payload:dict):
    ids=payload.get("ids") or ([payload.get("id")] if payload.get("id") else [])
    for rid in ids:
        n=find_record("notifications",str(rid))
        if n: n["is_read"]=True; write_record("notifications",n)
    return {"success":True}

@app.patch("/api/project-documents/v12/{document_id}")
def update_document(document_id:str,payload:dict):
    d=find_record("documents",document_id)
    if not d: raise HTTPException(404,"Document not found")
    d.update(payload); d["id"]=document_id; write_record("documents",d)
    return {"success":True,"document":d}

@app.delete("/api/project-documents/v13/{document_id}")
def delete_document(document_id:str):
    delete_record("documents",document_id)
    return {"success":True}

@app.post("/api/project-documents/v12/upload")
def upload_document(payload:dict):
    d={"id":"DOC-"+uuid.uuid4().hex[:8].upper(),
       "project_id":payload.get("project_id"),"uploaded_by":payload.get("uploaded_by"),
       "document_name":payload.get("document_name","Uploaded document"),
       "document_type":payload.get("document_type","Document"),
       "status":"Pending","uploaded_at":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
       "file_url":"","project_name":next((p["name"] for p in collection("projects") if str(p["id"])==str(payload.get("project_id"))),"")}
    write_record("documents",d)
    return {"success":True,"document":d}

# Compatibility aliases used by older parts of V14.
@app.get("/api/role/inspector/v12/assignments")
@app.get("/api/role/inspector/assignments")
def inspector_assignments(user_id:str|None=None):
    rows=collection("assignments")
    if user_id:
        insp_ids={str(x["id"]) for x in collection("inspectors") if str(x.get("user_id"))==str(user_id)}
        rows=[x for x in rows if str(x.get("inspector_id")) in insp_ids or str(x.get("inspector_user_id"))==str(user_id)]
    return {"success":True,"assignments":rows}

@app.get("/api/role/inspector/v12/past-inspections")
@app.get("/api/role/inspector/past-inspections")
def inspector_past(user_id:str|None=None):
    return {"success":True,"inspections":[x for x in collection("inspections") if str(x.get("status","")).lower()=="completed"]}

@app.get("/api/role/inspector/v12/inspections")
@app.get("/api/role/inspector/inspections")
def inspector_inspections(user_id:str|None=None):
    return {"success":True,"inspections":collection("inspections")}

# Optional live CCTV service. If its dependencies are available, use the existing
# YOLO/MJPEG implementation; otherwise demo metadata remains available.
try:
    import sys
    sys.path.insert(0, str(BASE / "cctv"))
    import service as cctv_service
except Exception as exc:
    cctv_service=None
    print(f"INFO: live CCTV service unavailable in this environment: {exc}")

@app.get("/cameras/{camera_id}/status")
def camera_status(camera_id:str):
    row=next((x for x in collection("cameras") if x.get("camera_id")==camera_id.upper()),None)
    if not row: raise HTTPException(404,"Camera not found")
    occ=next((x for x in collection("occupancy") if x.get("camera_id")==camera_id.upper()),{})
    if str(row.get("status", "")).upper() == "OFFLINE":
        return {**row,**occ,"status":"OFFLINE","reason":row.get("offline_reason") or "Camera is offline."}
    if cctv_service and hasattr(cctv_service,"CAMERA_REGISTRY"):
        cam=cctv_service.CAMERA_REGISTRY.get(camera_id.upper())
        if cam: return cam.get_status_payload()
    return {**row,**occ}

@app.patch("/api/cctv/cameras/{camera_id}")
def update_camera(camera_id:str, payload:dict):
    row=next((x for x in collection("cameras") if x.get("camera_id")==camera_id.upper()),None)
    if not row: raise HTTPException(404,"Camera not found")
    row.update({k:v for k,v in payload.items() if k in {"status","offline_reason","offline_since","updated_by"}})
    if str(row.get("status", "")).upper() == "OFFLINE" and not row.get("offline_since"):
        row["offline_since"] = datetime.now(timezone.utc).isoformat()
    write_record("cameras", row)
    return {"success":True,"camera":row}

@app.get("/stream")
def stream(camera:str=Query(...)):
    row=next((x for x in collection("cameras") if x.get("camera_id")==camera.upper()),None)
    if row and str(row.get("status", "")).upper() == "OFFLINE":
        raise HTTPException(503, row.get("offline_reason") or "Camera is offline")
    if cctv_service and hasattr(cctv_service,"CAMERA_REGISTRY"):
        cam=cctv_service.CAMERA_REGISTRY.get(camera.upper())
        if cam:
            return StreamingResponse(cam.generate_stream(),media_type="multipart/x-mixed-replace; boundary=frame")
    raise HTTPException(503,"Live CCTV service is not running; use demo occupancy data or start the CCTV dependencies.")

if __name__=="__main__":
    import uvicorn
    uvicorn.run("main:app",host="127.0.0.1",port=8001,reload=False)
