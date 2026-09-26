# Member 4 API Documentation

Base URL: `http://127.0.0.1:8000`

FastAPI interactive docs: `/docs`

## 1. Inspections

### POST /inspections
Create and assign an inspection.

Example:
```json
{
  "project_id": "PS-26095",
  "inspector_id": "INSP-004",
  "date": "2026-09-21",
  "status": "SCHEDULED",
  "checklist": [
    {"item": "Site accessible", "checked": false},
    {"item": "Attendance register checked", "checked": false}
  ],
  "remarks": "Initial field visit",
  "latitude": 13.0827,
  "longitude": 80.2707
}
```

### GET /inspections
Optional query parameters: `project_id`, `inspector_id`, `status`.

### GET /inspections/{id}
Returns one inspection.

### PUT /inspections/{id}
Update inspector, date/time, status, checklist, remarks or GPS.

Start:
```json
{"status":"IN_PROGRESS","start_time":"10:00:00"}
```

Complete:
```json
{"status":"COMPLETED","end_time":"11:30:00"}
```

## 2. Evidence

### POST /inspections/{id}/evidence
Multipart form:
- project_id
- inspector_id
- file_type
- description
- latitude
- longitude
- file

The actual file goes to Supabase Storage when configured. Metadata is stored in the database.

### GET /inspections/{id}/evidence
Returns all evidence for an inspection.

### PUT /evidence/{evidence_id}/verify
```json
{
  "verification_status":"VERIFIED",
  "remarks":"Document checked against field record."
}
```

## 3. Anomaly Detection

### POST /anomalies/detect

Input:
```json
{
  "project_id":"PS-26095",
  "expected_attendance":90,
  "actual_attendance":62,
  "capacity":25,
  "people_detected":31,
  "fund_utilization":80,
  "physical_progress":55,
  "attendance_threshold":15,
  "financial_threshold":20,
  "inspection_status":"COMPLETED",
  "inspection_date":"2026-09-21",
  "inspection_completed":true,
  "required_evidence_count":1,
  "total_evidence_count":0,
  "verified_evidence_count":0,
  "repeated_issue_count":3
}
```

### GET /anomalies
Optional `project_id` and `severity`.

### GET /anomalies/{project_id}
Returns project anomalies.

Anomaly object:
```json
{
  "project_id":"PS-26095",
  "anomaly_type":"OCCUPANCY",
  "severity":"HIGH",
  "title":"Capacity exceeded",
  "description":"Detected occupancy 31 exceeded configured capacity 25.",
  "detected_at":"2026-09-21T06:00:00",
  "status":"OPEN"
}
```

## 4. Risk

### GET /risk/{project_id}

Example:
```json
{
  "project_id":"PS-26095",
  "overall_score":64.48,
  "risk_level":"HIGH",
  "components":{
    "attendance":7.78,
    "occupancy":19.2,
    "financial":12.5,
    "inspection":15,
    "evidence":10,
    "anomalies":10
  },
  "formula":"Score = Attendance(25) + Occupancy(20) + Financial(20) + Inspection(15) + Evidence(10) + Anomalies(10)",
  "surprise_inspection_recommended":true
}
```

## 5. Surprise inspection

### GET /surprise-inspections/{project_id}

Returns the HIGH anomaly trigger and recommendation.

## 6. Reports

### GET /reports/{project_id}?format=json
Returns project details, attendance, occupancy, financial information, inspection history, evidence, anomalies, risk and recommendations.

### GET /reports/{project_id}?format=csv
Downloads a CSV report.

## 7. Health

### GET /health
Returns service health.
