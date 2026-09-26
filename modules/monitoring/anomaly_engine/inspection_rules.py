from datetime import date

def detect_inspection(project_id, status, scheduled_date, issue_count=0):
    results = []
    if status == "CANCELLED":
        results.append({"project_id": project_id, "anomaly_type": "INSPECTION",
                        "severity": "MEDIUM", "title": "Inspection cancelled",
                        "description": "A scheduled inspection was cancelled."})
    if status == "SCHEDULED" and date.fromisoformat(scheduled_date) < date.today():
        results.append({"project_id": project_id, "anomaly_type": "INSPECTION",
                        "severity": "HIGH", "title": "Inspection overdue",
                        "description": "The scheduled inspection date has passed and the inspection is not completed."})
    if status == "IN_PROGRESS" and issue_count > 0:
        results.append({"project_id": project_id, "anomaly_type": "INSPECTION",
                        "severity": "MEDIUM", "title": "Inspection incomplete",
                        "description": "Inspection remains in progress while checklist issues are present."})
    return results

def detect_repeated_issues(project_id, issue_count):
    if issue_count >= 3:
        return {"project_id": project_id, "anomaly_type": "INSPECTION",
                "severity": "HIGH", "title": "Repeated inspection issues",
                "description": f"{issue_count} repeated inspection issues were recorded."}
    return None
