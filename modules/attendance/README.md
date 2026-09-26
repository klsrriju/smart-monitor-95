# Employee Attendance Module (Member 2)

Core Employee Attendance + Entry/Exit module. Converts mock recognition
events into daily attendance records — no CCTV, YOLO, face recognition,
frontend, or `main.py` involved. This is a standalone module other team
members can plug into later.

## Core flow

```
Recognition event (mock JSON)
        ↓
Employee ID lookup
        ↓
Entry / Exit classification
        ↓
Attendance event logged (audit trail)
        ↓
ONE daily attendance record created/updated (no duplicates)
```

## How Entry/Exit + duplicate prevention works

- The **first** detection of an employee on a given day → **ENTRY** (creates the
  one attendance row for that day).
- **Every** detection after that on the same day → **EXIT** (updates `exit_time`
  on that same row, but only moves it *forward* — an out-of-order or duplicate
  detection can never move the exit time backward).
- The database itself has a `UNIQUE(employee_id, date)` constraint, so it is
  physically impossible to end up with two attendance rows for the same person
  on the same day, no matter how many times the same person is detected
  (tested with 500 duplicate detections in `demo.py`).
- Every raw detection (including duplicates) is still logged in the `events`
  table, so nothing is lost — it's just not turned into duplicate attendance.

## Project structure

```
attendance-module/
├── database.py           # SQLite tables + connection helper
├── models.py              # Pydantic request/response models
├── attendance_rules.py    # Configurable PRESENT/LATE rules
├── entry_exit.py           # ENTRY vs EXIT classification logic
├── attendance_service.py  # Core business logic (the "brain")
├── api.py                  # FastAPI endpoints (thin HTTP layer)
├── demo.py                 # Standalone script proving the core flow works
├── requirements.txt
└── README.md
```

## Sample employees

| ID     | Name       |
|--------|------------|
| EMP001 | R. Meena   |
| EMP002 | S. Kumar   |
| EMP003 | P. Priya   |
| EMP004 | A. Rahman  |

## Database structure (SQLite, file: `attendance.db`)

**employees**
| column       | type | notes       |
|--------------|------|-------------|
| employee_id  | TEXT | primary key |
| name         | TEXT |             |

**attendance** — one row per employee per day
| column       | type | notes                              |
|--------------|------|-------------------------------------|
| id           | INTEGER | primary key, autoincrement       |
| employee_id  | TEXT |                                     |
| date         | TEXT | e.g. "2026-09-21"                  |
| entry_time   | TEXT | e.g. "09:04:21"                    |
| exit_time    | TEXT | e.g. "16:32:10"                    |
| status       | TEXT | PRESENT / LATE                     |
|              |      | `UNIQUE(employee_id, date)` — prevents duplicates |

**events** — every raw detection ever received (audit trail)
| column         | type    | notes            |
|----------------|---------|------------------|
| id             | INTEGER | primary key      |
| employee_id    | TEXT    |                  |
| event_type     | TEXT    | ENTRY or EXIT    |
| event_time     | TEXT    | "09:04:21"       |
| full_timestamp | TEXT    | full ISO string  |
| confidence     | REAL    |                  |
| track_id       | INTEGER |                  |

## Attendance status rules (`attendance_rules.py`)

```python
EXPECTED_ENTRY_TIME = time(9, 0, 0)   # configurable
GRACE_PERIOD_MINUTES = 10             # configurable
```

- Entry at or before `EXPECTED_ENTRY_TIME + GRACE_PERIOD_MINUTES` → **PRESENT**
- Entry after that → **LATE**
- No entry at all for the day → **ABSENT**

Change the expected time later either by editing the constant, or at runtime:

```python
import attendance_rules
attendance_rules.set_expected_entry_time(9, 30)  # new expected entry: 09:30
```

## How to run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the standalone demo (no server needed)

This proves the core flow (entry, exit, 500 duplicate detections, absentees,
status rules) works with pure Python:

```bash
python demo.py
```

Expected output includes:
```
✅ Confirmed: exactly 1 attendance row exists for EMP001 today.
```

### 3. Run the API server

```bash
uvicorn api:app --reload
```

Then open **http://127.0.0.1:8000/docs** for interactive API docs (Swagger UI),
or use curl/Postman as shown below.

## API list

| Method | Endpoint                          | Description                                   |
|--------|-------------------------------------|------------------------------------------------|
| POST   | `/recognition-event`               | Receive a mock recognition event               |
| GET    | `/attendance/today`                | All attendance records for today               |
| GET    | `/attendance/summary`              | Counts: present / late / absent                |
| GET    | `/attendance/absentees`            | Employees not detected today                   |
| GET    | `/attendance/events`               | Raw event log (optional `?employee_id=EMP001`) |
| GET    | `/attendance/{employee_id}/history`| Full day-by-day history for one employee       |
| GET    | `/attendance/{employee_id}`        | Today's record for one employee                |

## Example requests / responses

**Send a mock recognition event (this is what CCTV/YOLO would eventually call):**
```bash
curl -X POST http://127.0.0.1:8000/recognition-event \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "EMP001",
    "name": "R. Meena",
    "track_id": 17,
    "confidence": 0.87,
    "timestamp": "2026-09-21T09:04:21"
  }'
```
Response:
```json
{"employee_id":"EMP001","name":"R. Meena","date":"2026-09-21","entry_time":"09:04:21","exit_time":"09:04:21","status":"PRESENT"}
```

**Get today's attendance:**
```bash
curl http://127.0.0.1:8000/attendance/today
```
Response:
```json
[
  {"employee_id":"EMP001","name":"R. Meena","date":"2026-09-21","entry_time":"09:04:21","exit_time":"16:32:10","status":"PRESENT"},
  {"employee_id":"EMP003","name":"P. Priya","date":"2026-09-21","entry_time":"09:25:00","exit_time":"09:25:00","status":"LATE"}
]
```

**Get summary:**
```bash
curl http://127.0.0.1:8000/attendance/summary
```
```json
{"date":"2026-09-21","total_employees":4,"present":1,"late":1,"absent":2}
```

**Get absentees:**
```bash
curl http://127.0.0.1:8000/attendance/absentees
```
```json
[
  {"employee_id":"EMP002","name":"S. Kumar","date":"2026-09-21","entry_time":null,"exit_time":null,"status":"ABSENT"},
  {"employee_id":"EMP004","name":"A. Rahman","date":"2026-09-21","entry_time":null,"exit_time":null,"status":"ABSENT"}
]
```

## Limitations (intentional, for this first version)

- Entry/Exit is inferred purely from **order of detection in the day**, not
  from separate entry/exit camera zones — first sighting = entry, every
  later sighting = a candidate exit. This is a reasonable placeholder until
  the CCTV/zone team provides zone information.
- SQLite is a single local file — fine for development, not for multiple
  servers writing at once. Swapping to PostgreSQL/Supabase later only
  requires changing `database.py`; every other file is unaffected.
- No authentication on the API yet — anyone who can reach the server can
  post events or read attendance.
- Status logic only covers PRESENT/LATE/ABSENT with a single grace period;
  no half-day, overtime, or shift-based rules yet.
- Timezones aren't handled explicitly — timestamps are treated as naive
  local time, matching the mock data format given.
- This module does not interpret `track_id` or `confidence` beyond storing
  them — filtering low-confidence detections is left to the recognition
  system (or can be added here later as a simple threshold check).
