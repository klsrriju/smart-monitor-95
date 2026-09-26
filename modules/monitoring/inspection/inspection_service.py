import json
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "monitoring.db"
VALID_STATUSES = {"SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"}

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def row_to_dict(row):
    d = dict(row)
    d["checklist"] = json.loads(d["checklist"] or "[]")
    return d

def create_inspection(payload):
    if payload.status not in VALID_STATUSES:
        raise ValueError("Invalid inspection status")
    inspection_id = "INS-" + uuid4().hex[:10].upper()
    now = datetime.utcnow().isoformat()
    with db() as c:
        c.execute("""INSERT INTO inspections
        (id, project_id, inspector_id, date, start_time, end_time, status,
         checklist, remarks, latitude, longitude, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            inspection_id, payload.project_id, payload.inspector_id,
            payload.date.isoformat(),
            payload.start_time.isoformat() if payload.start_time else None,
            payload.end_time.isoformat() if payload.end_time else None,
            payload.status, json.dumps([x.model_dump() for x in payload.checklist]),
            payload.remarks, payload.latitude, payload.longitude, now, now
        ))
    return get_inspection(inspection_id)

def list_inspections(project_id=None, inspector_id=None, status=None):
    sql = "SELECT * FROM inspections WHERE 1=1"
    args = []
    if project_id:
        sql += " AND project_id=?"; args.append(project_id)
    if inspector_id:
        sql += " AND inspector_id=?"; args.append(inspector_id)
    if status:
        sql += " AND status=?"; args.append(status)
    sql += " ORDER BY date DESC, created_at DESC"
    with db() as c:
        return [row_to_dict(r) for r in c.execute(sql, args).fetchall()]

def get_inspection(inspection_id):
    with db() as c:
        r = c.execute("SELECT * FROM inspections WHERE id=?", (inspection_id,)).fetchone()
    if not r:
        return None
    return row_to_dict(r)

def update_inspection(inspection_id, payload):
    current = get_inspection(inspection_id)
    if not current:
        return None
    data = current.copy()
    for k, v in payload.model_dump(exclude_unset=True).items():
        if k == "checklist" and v is not None:
            data[k] = [x if isinstance(x, dict) else x.model_dump() for x in v]
        elif v is not None:
            data[k] = v.isoformat() if hasattr(v, "isoformat") else v
    if data["status"] not in VALID_STATUSES:
        raise ValueError("Invalid inspection status")
    with db() as c:
        c.execute("""UPDATE inspections SET inspector_id=?, date=?, start_time=?,
        end_time=?, status=?, checklist=?, remarks=?, latitude=?, longitude=?,
        updated_at=? WHERE id=?""", (
            data["inspector_id"], data["date"], data["start_time"], data["end_time"],
            data["status"], json.dumps(data["checklist"]), data["remarks"],
            data["latitude"], data["longitude"], datetime.utcnow().isoformat(), inspection_id
        ))
    return get_inspection(inspection_id)
