def detect_occupancy(project_id, capacity, people_detected):
    if people_detected > capacity:
        ratio = people_detected / max(capacity, 1)
        severity = "HIGH" if ratio >= 1.20 else "MEDIUM"
        return {
            "project_id": project_id, "anomaly_type": "OCCUPANCY",
            "severity": severity, "title": "Capacity exceeded",
            "description": f"Detected occupancy {people_detected} exceeded configured capacity {capacity}."
        }
    return None
