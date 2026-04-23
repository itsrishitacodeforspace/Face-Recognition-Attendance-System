# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- RTSP stream support for IP cameras
- Multi-camera simultaneous recognition
- Face liveness detection (anti-spoofing)
- Role-based access control (admin / operator / viewer)
- PostgreSQL support as an alternative to SQLite
- Prometheus metrics endpoint for monitoring

---

## [1.0.0] — 2026-03-29

### Added

#### Backend (FastAPI)
- Async FastAPI application with SQLAlchemy 2.0 async ORM and SQLite via `aiosqlite`
- JWT authentication with access tokens and refresh tokens
- Bcrypt password hashing via `passlib`
- Login rate limiting to mitigate brute-force attacks
- Person management CRUD endpoints (`POST`, `GET`, `PUT`, `DELETE` `/api/persons`)
- Reference image upload and deletion per person
- InsightFace `buffalo_l` model integration for face detection and embedding extraction
  - Auto-downloads model weights on first run
  - Runs on CPU by default; auto-promotes to CUDA GPU when available
- FAISS `IndexFlatIP` vector index for cosine-similarity identity lookup
  - Embedding averaging across multiple reference images per person
  - Persistent index and embedding cache saved to disk
- Training pipeline: upload images → detect → align → embed → average → index
  - Async background training with status polling and streaming log output
- Attendance auto-marking on recognition events above configurable threshold
- Attendance cooldown logic to prevent duplicate marks within a configurable window
- Cropped face archival for each attendance event
- Attendance analytics: today's records, paginated history, CSV export, heatmap data, trend time series
- WebSocket endpoint (`/ws/process`) for real-time frame ingestion and recognition event streaming
- Video ingestion service supporting webcam, local file, and RTSP (placeholder)
- Pydantic Settings with full `.env` override support
- Bootstrap admin account created on startup if the database is empty
- `pytest` test suite covering embedding averaging, threshold boundary behaviour, and attendance cooldown logic
- `httpx` async HTTP client for integration tests

#### Frontend (React + Vite + Tailwind)
- JWT-based login page with persistent session via `localStorage`
- Protected route layout with auto-redirect to login on token expiry
- Dashboard overview page with attendance and person count summary cards
- Persons page: create/edit/delete persons, upload/delete reference images with gallery view
- Training page: one-click train trigger, real-time log streaming, status badge
- Live Recognition page:
  - WebSocket connection to backend stream
  - Live video canvas with bounding box and name overlay
  - Recognised person event list with IST timestamps
  - Attendance event "clear" action
- Attendance page: paginated table with date/person filters, CSV export button
- Heatmap page: calendar heatmap of daily attendance frequency
- Trends page: Chart.js line chart of attendance over time
- Responsive Tailwind layout with sidebar navigation

#### Infrastructure
- `docker-compose.yml` to run backend and frontend in separate containers
- Backend `Dockerfile` with multi-stage build
- `.env.example` files for both backend and frontend with all variables documented
- Comprehensive `.gitignore` covering Python, Node, ML weights, datasets, secrets, and OS artefacts
- `SECURITY.md` with responsible disclosure policy
- `GIT_SECURITY.md` with repository hygiene guidelines

### Configuration defaults
- `RECOGNITION_THRESHOLD`: `0.35`
- `FACE_DETECTION_THRESHOLD`: `0.5`
- `ATTENDANCE_COOLDOWN_SECONDS`: `60`
- `INSIGHTFACE_MODEL`: `buffalo_l`
- `GPU_STRICT_MODE`: `false`

---

[Unreleased]: https://github.com/<your-username>/face-recognition-attendance/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/<your-username>/face-recognition-attendance/releases/tag/v1.0.0
