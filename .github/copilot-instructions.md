# Project Guidelines

## Mission
Keep this face-recognition attendance system working end to end on Windows first. Prefer safe, minimal changes that preserve current behavior unless a bug fix explicitly requires behavior changes.

## Build And Test
Run these commands before finalizing meaningful changes.

Backend (PowerShell):
- `cd backend`
- `python -m venv .venv` (if missing)
- `.\.venv\Scripts\Activate.ps1`
- `pip install -r requirements.txt`
- `pytest -q`

Backend run server:
- `cd backend`
- `.\.venv\Scripts\Activate.ps1`
- `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`

Frontend:
- `cd frontend`
- `npm install`
- `npm run dev`
- `npm run build`

Docker (optional full stack):
- `docker-compose up --build`

## Architecture
Backend boundaries:
- API routes live in `backend/app/api/`.
- Business logic belongs in `backend/app/services/`.
- Database models belong in `backend/app/models/`.
- Shared helpers belong in `backend/app/utils/`.
- App startup and service wiring happen in `backend/app/main.py`.

Frontend boundaries:
- Route pages live in `frontend/src/pages/`.
- Reusable UI components live in `frontend/src/components/`.
- API and WebSocket client code belongs in `frontend/src/services/`.

## Conventions
- Python: follow Black and Ruff conventions from CONTRIBUTING.
- Keep imports grouped as stdlib, third-party, then local app imports.
- Preserve async patterns in FastAPI and SQLAlchemy code.
- Keep auth behavior consistent with existing JWT and dependency flow in `backend/app/api/auth.py` and `backend/app/api/deps.py`.
- Keep CORS and security defaults strict in `backend/app/main.py`.

## Windows-First Requirements
- Prefer PowerShell-compatible commands.
- Use `pathlib.Path` and avoid OS-specific separators in Python code.
- Assume local development runs on Windows unless task explicitly targets Linux or Docker.
- Do not introduce scripts that only work in bash when a PowerShell equivalent is feasible.

## Stability Rules
- Fix root causes, not symptoms.
- Do not remove or bypass validation/security logic unless explicitly requested.
- Keep API contract compatibility for frontend consumers unless coordinated updates are made in the same change.
- If changing backend payloads, update corresponding frontend service/page usage in the same task.

## Common Pitfalls
- Python 3.11+ is required.
- The app auto-creates DB tables and a default admin user on startup.
- Face index/training state lives under backend data paths; avoid committing generated model/data artifacts.
- GPU is optional; code must continue to work in CPU mode.

## Documentation Links
- Project overview and setup: `README.md`
- Contribution workflow and style: `CONTRIBUTING.md`
- Security expectations: `SECURITY.md`
- Login/CORS setup notes: `LOGIN_SETUP.md`
- Git hygiene and secret handling: `GIT_SECURITY.md`

## Cleanup Guidance
Remove temporary AI/tool artifacts (logs, caches, one-off check outputs) when they are not part of runtime or tests. Keep reusable scripts only if they serve an ongoing development purpose.
