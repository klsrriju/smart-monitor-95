# Member 4 — Monitoring & Risk Engine

Independent backend for **Inspection, Evidence, Anomaly Detection, Risk Assessment, Surprise Inspection recommendations and Reports**.

It does not modify the existing SmartMonitor `main.py`, YOLO, CCTV or dashboard. The supplied HTML is treated as the frontend and a Member-4 API panel is added in `member4_frontend.html`.

## Architecture

HTML Frontend
→ FastAPI REST API
→ Inspection / Evidence / Anomaly / Risk / Report services
→ SQLite for zero-setup demo
→ Supabase Storage when `SUPABASE_URL` + `SUPABASE_KEY` are configured.

### Risk calculation

Maximum = 100 points:

- Attendance: 25 points
- CCTV occupancy: 20 points
- Financial/progress mismatch: 20 points
- Inspection status: 15 points
- Evidence compliance: 10 points
- Open anomaly severity: 10 points

Formula:

`overall_score = attendance_risk + occupancy_risk + financial_risk + inspection_risk + evidence_risk + anomaly_risk`

Bands:
- LOW: score < 30
- MEDIUM: 30–59.99
- HIGH: >= 60

Rules are calculated from live project metrics and database records; the final score is not a hardcoded number.

### Surprise inspection

If at least one open HIGH severity anomaly exists for a project:

`HIGH anomaly → surprise_inspection_recommended = true`

## Folder

```text
monitoring-engine/
├── inspection/
│   ├── inspection_service.py
│   ├── inspection_api.py
│   └── models.py
├── evidence/
│   ├── evidence_service.py
│   └── storage.py
├── anomaly_engine/
│   ├── attendance_rules.py
│   ├── occupancy_rules.py
│   ├── financial_rules.py
│   ├── inspection_rules.py
│   ├── evidence_rules.py
│   └── anomaly_service.py
├── risk_engine/
│   └── risk_service.py
├── reports/
│   └── report_service.py
├── data/
├── demo.py
├── main.py
├── init_db.py
├── schema.sql
├── schema_sqlite.sql
├── seed.sql
├── requirements.txt
└── README.md
```

## Run

### Windows

```bat
cd monitoring-engine
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python init_db.py
uvicorn main:app --reload --port 8000
```

### Linux/macOS

```bash
cd monitoring-engine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python init_db.py
uvicorn main:app --reload --port 8000
```

API documentation:

`http://127.0.0.1:8000/docs`

Open the supplied frontend through a local web server, not `file://`:

```bash
python -m http.server 5500
```

Then open:

`http://127.0.0.1:5500/member4_frontend.html`

## Supabase Storage

Create a bucket named `inspection-evidence` and set:

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_KEY=YOUR_KEY
SUPABASE_STORAGE_BUCKET=inspection-evidence
```

For server-side uploads, use a protected service-role key only in the backend environment. Do not expose it in HTML/JavaScript.

The demo automatically falls back to local storage if Supabase credentials are absent.

## API summary

- `POST /inspections`
- `GET /inspections`
- `GET /inspections/{id}`
- `PUT /inspections/{id}`
- `POST /inspections/{id}/evidence`
- `GET /inspections/{id}/evidence`
- `PUT /evidence/{evidence_id}/verify`
- `GET /surprise-inspections/{project_id}`
- `GET /anomalies`
- `GET /anomalies/{project_id}`
- `POST /anomalies/detect`
- `GET /risk/{project_id}`
- `GET /reports/{project_id}?format=json`
- `GET /reports/{project_id}?format=csv`
- `GET /health`

## Sample anomaly request

```json
{
  "project_id": "PS-26095",
  "expected_attendance": 90,
  "actual_attendance": 62,
  "capacity": 25,
  "people_detected": 31,
  "fund_utilization": 80,
  "physical_progress": 55,
  "inspection_status": "COMPLETED",
  "inspection_date": "2026-09-21",
  "attendance_threshold": 15,
  "financial_threshold": 20,
  "inspection_completed": true,
  "required_evidence_count": 1,
  "verified_evidence_count": 0,
  "total_evidence_count": 0,
  "repeated_issue_count": 3
}
```

This produces attendance, occupancy, financial and evidence/inspection anomalies as applicable.

## Sample risk

For `PS-26095`, the seed metrics are intentionally abnormal:
- attendance = 62%
- capacity = 25
- detected people = 31
- fund utilization = 80%
- physical progress = 55%

The risk endpoint converts those measurements into component scores and an overall LOW/MEDIUM/HIGH band.

## Notes for integration

The final SmartMonitor integration can send:
- YOLO occupancy → `POST /anomalies/detect` fields `capacity` and `people_detected`
- Face/attendance service → `expected_attendance` and `actual_attendance`
- Project financial service → `fund_utilization` and `physical_progress`
- Inspector UI → inspection and evidence endpoints.

No changes are required in the CCTV/YOLO module.
