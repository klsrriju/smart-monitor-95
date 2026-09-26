import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "monitoring.db"

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def add_evidence(meta, object_path, file_url, storage_backend):
    evidence_id = "EVD-" + uuid4().hex[:10].upper()
    with db() as c:
        c.execute("""INSERT INTO evidence
        (id, project_id, inspection_id, inspector_id, file_path, file_url,
         file_type, upload_time, latitude, longitude, description,
         verification_status, storage_backend)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            evidence_id, meta["project_id"], meta["inspection_id"], meta["inspector_id"],
            object_path, file_url, meta["file_type"], datetime.utcnow().isoformat(),
            meta.get("latitude"), meta.get("longitude"), meta.get("description"),
            "PENDING", storage_backend
        ))
    return get_evidence(evidence_id)

def list_evidence(inspection_id=None, project_id=None):
    sql = "SELECT * FROM evidence WHERE 1=1"
    args = []
    if inspection_id:
        sql += " AND inspection_id=?"; args.append(inspection_id)
    if project_id:
        sql += " AND project_id=?"; args.append(project_id)
    sql += " ORDER BY upload_time DESC"
    with db() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]

def get_evidence(evidence_id):
    with db() as c:
        r = c.execute("SELECT * FROM evidence WHERE id=?", (evidence_id,)).fetchone()
    return dict(r) if r else None


def verify_evidence(evidence_id, status, remarks=None):
    if status not in {"PENDING", "VERIFIED", "REJECTED"}:
        raise ValueError("Invalid verification status")
    with db() as c:
        c.execute("""UPDATE evidence SET verification_status=?, description=COALESCE(?, description)
                     WHERE id=?""", (status, remarks, evidence_id))
    return get_evidence(evidence_id)
