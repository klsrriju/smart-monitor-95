import json
from pathlib import Path
from typing import List, Dict, Any, Optional

DATA_DIR = Path(__file__).parent / "sample_data"

class MockDatabase:
    def __init__(self):
        self.employees = self._load("employees.json")
        self.attendance = self._load("attendance.json")
        self.cameras = self._load("cameras.json")
        self.projects = self._load("projects.json")
        self.anomalies = self._load("anomalies.json")
        self.inspections = self._load("inspections.json")

    def _load(self, filename: str) -> List[Dict[str, Any]]:
        path = DATA_DIR / filename
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

db = MockDatabase()