def detect_evidence(project_id, inspection_completed, required_count, verified_count, total_count):
    results = []
    if required_count > total_count:
        results.append({"project_id": project_id, "anomaly_type": "EVIDENCE",
                        "severity": "HIGH", "title": "Required evidence missing",
                        "description": f"Required evidence count is {required_count}, but only {total_count} file(s) were uploaded."})
    if inspection_completed and total_count == 0:
        results.append({"project_id": project_id, "anomaly_type": "EVIDENCE",
                        "severity": "HIGH", "title": "Completed inspection without evidence",
                        "description": "Inspection is completed but no evidence file is attached."})
    if total_count and verified_count < total_count:
        results.append({"project_id": project_id, "anomaly_type": "EVIDENCE",
                        "severity": "LOW", "title": "Evidence not fully verified",
                        "description": f"{total_count - verified_count} uploaded evidence file(s) are not verified."})
    return results
