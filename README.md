# SmartMonitor SIH 2026 — Combined Build

This package combines the Hexabots main portal with the supplied Attendance,
Monitoring/Risk, AI Chatbot, Face Recognition, and YOLO/CCTV modules.

## What is ready

- `frontend/index.html` — the V14 dashboard with all existing Admin,
  Inspector and NGO/User modules.
- One connected fictional demo dataset
- Integrated SmartMonitor AI Assistant widget (service-backed with local demo fallback) in `backend/demo_data.json`.
- The frontend tries the FastAPI backend first and automatically falls back
  to the same demo dataset if the backend/database is unavailable.
- `backend/main.py` — combined FastAPI gateway on port 8001.
- PostgreSQL support through `DATABASE_URL`.
- YOLO CCTV service on the four supplied video feeds when dependencies are installed.
- Attendance service on 8002.
- Chatbot service on 8003.
- Monitoring/Risk service on 8004.
- Face-recognition module retained as a separate worker/CLI.

## Quickest demo

You can simply open `frontend/index.html` in Chrome.
The complete UI loads from the embedded connected demo dataset.

Demo login accounts are documented in [DEMO_CREDENTIALS.md](DEMO_CREDENTIALS.md):

| Login ID | Password | Role |
|---|---|---|
| `admin` | `Admin@2026` | Administrator |
| `ramesh` | `Ramesh@2026` | User / NGO |
| `kalaivani` | `Kalai@2026` | User / NGO |
| `priya` | `Priya@2026` | User / NGO |
| `aravind` | `Aravind@2026` | Inspector |
| `meena` | `Meena@2026` | Inspector |
| `karthik` | `Karthik@2026` | Inspector |

The corresponding account email also works. For example, `kalaivani@ngo.org`
and `kalaivani.s@ngo.org` both authenticate as Kalaivani.

No database is required for this UI-only demo.

## Backend demo

From this project root:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend\requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

Then open:

```text
http://127.0.0.1:8001/
```

The backend uses the demo dataset when `DATABASE_URL` is absent.

## PostgreSQL

Create a PostgreSQL database and set:

```text
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/smartmonitor
```

Then start the gateway. The gateway creates `smartmonitor_records` automatically.
The frontend contract does not change.

For a production version, the JSONB compatibility table can later be normalized
into separate relational tables without changing the V14 render layer.

## Start all supplied services

Use:

```powershell
python run_all.py
```

Ports:
- 8001 — combined portal + CCTV
- 8002 — attendance
- 8003 — chatbot
- 8004 — monitoring/risk

Face recognition remains a worker/CLI because the supplied module does not expose
an HTTP server.

The launcher must be run from this nested project root. The demo gateway accepts
the login IDs and passwords in `DEMO_CREDENTIALS.md`; its alert collection is
derived from current project, inspection, occupancy and camera records, so its
size is intentionally data-driven rather than fixed. `DATABASE_URL` is optional
and may point to local PostgreSQL or a Supabase PostgreSQL connection string such
as `postgresql+psycopg://...?...sslmode=require`.

## Important

The module source was combined without copying IDE caches, Python bytecode, or
the chatbot secret `.env`. Use `modules/chatbot/.env.example` to configure the
chatbot.

The V14 UI is kept as HTML/CSS/JavaScript; it was not converted to React/Vue.

## Chatbot sample questions

Open the AI Assistant in the portal or use `POST http://127.0.0.1:8003/api/v1/chat`
with a JSON body such as `{"query":"Which projects are delayed?"}`. Useful demo
questions include:

- Which projects are delayed?
- How many projects are completed?
- Which cameras are offline?
- Show the latest occupancy status.
- Which inspections are pending?
- Are there any attendance anomalies?
- What is the risk status of PRJ-005?
- Which projects belong to Kalaivani?


## Final UI + module integration check (23 Sep 2026)

- The V14 HTML remains the single user-facing dashboard.
- CCTV live streams use the working `/stream?camera=CAM-xxx` MJPEG endpoint.
- CCTV Recorded History creates a browser-side occupancy snapshot every 10 minutes and keeps the recent history in localStorage until the PostgreSQL persistence layer is enabled.
- District Compliance now uses formatted progress bars, status labels, and summary cards.
- Flagged Cases / Anomaly Analytics now use formatted severity cards, metadata, descriptions, status badges, and action buttons.
- The backend root route now correctly resolves the sibling `frontend/index.html` instead of looking under `backend/frontend/`.
- Included module packages: `modules/attendance`, `modules/face-recognition`, `modules/monitoring`, and `modules/chatbot`.
- The uploaded monitoring SQLite demo database is included at `modules/monitoring/data/monitoring.db`.
- Chatbot secrets are not bundled; only `.env.example` is retained.
