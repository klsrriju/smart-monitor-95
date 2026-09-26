def detect_attendance(project_id, expected_pct, actual_pct, threshold_pct=15):
    gap = expected_pct - actual_pct
    if gap >= threshold_pct:
        severity = "HIGH" if gap >= 25 else "MEDIUM"
        return {
            "project_id": project_id, "anomaly_type": "ATTENDANCE",
            "severity": severity, "title": "Attendance below expectation",
            "description": f"Expected attendance {expected_pct:.1f}% but actual attendance was {actual_pct:.1f}% (gap {gap:.1f}%)."
        }
    return None
