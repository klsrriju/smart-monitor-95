import json
from datetime import date
from inspection.models import InspectionCreate, ChecklistItem
from inspection.inspection_service import create_inspection
from anomaly_engine.anomaly_service import run_rules
from risk_engine.risk_service import calculate_risk
from reports.report_service import build_report

def main():
    # Create a real inspection record.
    inspection = create_inspection(InspectionCreate(
        project_id="PS-26095",
        inspector_id="INSP-004",
        date=date.today(),
        status="COMPLETED",
        checklist=[
            ChecklistItem(item="Site accessible", checked=True),
            ChecklistItem(item="Attendance register checked", checked=True),
            ChecklistItem(item="Safety measures available", checked=False, note="Fire extinguisher needs review")
        ],
        remarks="Sample independent Member 4 inspection."
    ))
    print("\nINSPECTION\n", json.dumps(inspection, indent=2))

    anomalies = run_rules({
        "project_id":"PS-26095",
        "expected_attendance":90,
        "actual_attendance":62,
        "capacity":25,
        "people_detected":31,
        "fund_utilization":80,
        "physical_progress":55,
        "inspection_status":"COMPLETED",
        "inspection_date":date.today().isoformat(),
        "inspection_issue_count":1,
        "repeated_issue_count":3,
        "inspection_completed":True,
        "required_evidence_count":1,
        "verified_evidence_count":0,
        "total_evidence_count":0
    })
    print("\nANOMALIES\n", json.dumps(anomalies, indent=2))

    risk = calculate_risk("PS-26095")
    print("\nRISK\n", json.dumps(risk, indent=2))

    report = build_report("PS-26095")
    print("\nREPORT KEYS\n", list(report.keys()))

if __name__ == "__main__":
    main()
