# SmartMonitor Integration Plan

## Phase 1 — Working UI/demo
- V14 remains the single portal.
- One connected demo dataset feeds all major modules.
- Frontend falls back to demo data if the backend is unavailable.
- AI Assistant widget has service + demo fallback.

## Phase 2 — PostgreSQL
- Set `DATABASE_URL`.
- Use the combined gateway as the stable API boundary.
- Move the demo collections from JSON compatibility storage into normalized PostgreSQL tables when production persistence is required.

## Phase 3 — Service integration
- Attendance: port 8002.
- Chatbot: port 8003.
- Monitoring/Risk: port 8004.
- CCTV/YOLO: port 8001.
- Face recognition remains a worker and posts recognition events to attendance.

## Phase 4 — Production hardening
- Authentication and authorization.
- PostgreSQL migrations.
- Evidence/object storage.
- Audit logging.
- Service health checks.
- End-to-end tests.
