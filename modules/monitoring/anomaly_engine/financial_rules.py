def detect_financial(project_id, fund_utilization_pct, physical_progress_pct, threshold_pct=20):
    gap = fund_utilization_pct - physical_progress_pct
    if gap >= threshold_pct:
        severity = "HIGH" if gap >= 35 else "MEDIUM"
        return {
            "project_id": project_id, "anomaly_type": "FINANCIAL",
            "severity": severity, "title": "Fund/progress mismatch",
            "description": f"Fund utilization {fund_utilization_pct:.1f}% is {gap:.1f} percentage points above physical progress {physical_progress_pct:.1f}%."
        }
    return None
