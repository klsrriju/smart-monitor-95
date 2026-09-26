import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from dotenv import load_dotenv

load_dotenv()

from inspection.inspection_api import router as inspection_router
from evidence.evidence_service import add_evidence, list_evidence, verify_evidence
from evidence.storage import upload_file
from anomaly_engine.anomaly_service import get_anomalies, run_rules
from risk_engine.risk_service import calculate_risk
from reports.report_service import build_report, report_csv

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Member 4 Monitoring & Risk Engine", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(inspection_router)

@app.get("/")
def root():
    return {"service":"monitoring-engine","status":"ok","docs":"/docs"}

@app.post("/inspections/{inspection_id}/evidence", status_code=201)
async def upload_evidence(
    inspection_id: str,
    project_id: str = Form(...),
    inspector_id: str = Form(...),
    file_type: str = Form(...),
    description: str = Form(""),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    file: UploadFile = File(...)
):
    data = await file.read()
    object_path, file_url, backend = upload_file(data, file.filename, file.content_type or "application/octet-stream")
    item = add_evidence({
        "project_id": project_id, "inspection_id": inspection_id, "inspector_id": inspector_id,
        "file_type": file_type, "description": description,
        "latitude": latitude, "longitude": longitude
    }, object_path, file_url, backend)
    return item

@app.get("/inspections/{inspection_id}/evidence")
def inspection_evidence(inspection_id: str):
    return list_evidence(inspection_id=inspection_id)


@app.put("/evidence/{evidence_id}/verify")
def verify(evidence_id: str, payload: dict):
    try:
        item = verify_evidence(evidence_id, payload.get("verification_status", "PENDING"), payload.get("remarks"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not item:
        raise HTTPException(404, "Evidence not found")
    return item

@app.get("/surprise-inspections/{project_id}")
def surprise(project_id: str):
    anomalies = [a for a in get_anomalies(project_id) if a["status"] == "OPEN" and a["severity"] == "HIGH"]
    return {
        "project_id": project_id,
        "triggered": bool(anomalies),
        "trigger": anomalies[0]["anomaly_type"] + "_ANOMALY" if anomalies else None,
        "action": "SURPRISE_INSPECTION_RECOMMENDED" if anomalies else "NO_SURPRISE_INSPECTION",
        "high_anomalies": anomalies
    }

@app.get("/anomalies")
def anomalies(project_id: str | None = None, severity: str | None = None):
    return get_anomalies(project_id, severity)

@app.get("/anomalies/{project_id}")
def project_anomalies(project_id: str):
    return get_anomalies(project_id)

@app.post("/anomalies/detect")
def detect(payload: dict):
    required = ["project_id","expected_attendance","actual_attendance","capacity","people_detected",
                "fund_utilization","physical_progress","inspection_status","inspection_date"]
    missing = [x for x in required if x not in payload]
    if missing: raise HTTPException(400, f"Missing fields: {missing}")
    return run_rules(payload)

@app.get("/risk/{project_id}")
def risk(project_id: str):
    item = calculate_risk(project_id)
    if not item: raise HTTPException(404, "Project metrics not found")
    return item

@app.get("/reports/{project_id}")
def report(project_id: str, format: str = "json"):
    if format.lower() == "csv":
        csv = report_csv(project_id)
        if csv is None: raise HTTPException(404, "Project not found")
        return Response(content=csv, media_type="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={project_id}_monitoring_report.csv"})
    item = build_report(project_id)
    if item is None: raise HTTPException(404, "Project not found")
    return item

@app.get("/health")
def health():
    return {"status":"healthy"}
