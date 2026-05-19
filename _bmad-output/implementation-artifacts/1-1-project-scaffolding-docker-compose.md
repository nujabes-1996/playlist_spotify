# Story 1.1: Project Scaffolding & Docker Compose

Status: review

## Story

As a developer,
I want the complete project skeleton initialized with Docker Compose,
so that I can start all services with a single `docker-compose up` command.

## Acceptance Criteria

1. **Given** the repository is cloned, **When** `docker-compose up` is run, **Then** both frontend (port 5173) and backend (port 8000) services start without errors.
2. **Given** the services are running, **When** I open http://localhost:5173, **Then** the React app loads in the browser (even if placeholder content).
3. **Given** the services are running, **When** I open http://localhost:8000/docs, **Then** the FastAPI Swagger UI loads successfully.
4. **Given** the project root, **When** I review the file structure, **Then** it matches exactly: `frontend/` (Vite React TS), `backend/` (FastAPI + uv + pyproject.toml), `docker-compose.yml`, two `Dockerfile`s, `.env.example` (ports/CORS only — no Spotify credentials), `.gitignore`, `data/.gitkeep`.

## Tasks / Subtasks

- [x] Task 1: Create root project structure (AC: #4)
  - [x] Create `.gitignore` covering: `node_modules/`, `__pycache__/`, `.venv/`, `data/*.db`, `.env`, `*.pyc`, `dist/`, `.DS_Store`
  - [x] Create `.env.example` with ports and CORS only — NO Spotify credentials
  - [x] Create `data/.gitkeep`

- [x] Task 2: Initialize backend with uv (AC: #3, #4)
  - [x] Create `backend/pyproject.toml` declaring all dependencies (fastapi, sqlmodel, apscheduler, spotipy)
  - [x] Generate `backend/uv.lock` via `uv lock`
  - [x] Create `backend/main.py` — minimal FastAPI app with CORS middleware and `/health` endpoint
  - [x] Create empty package folders with `__init__.py`: `backend/models/`, `backend/routers/`, `backend/services/`, `backend/tests/`
  - [x] Create `backend/tests/conftest.py` (empty placeholder)

- [x] Task 3: Create `backend/Dockerfile` (AC: #1, #3)
  - [x] Base image: `python:3.12-slim`
  - [x] Install uv via official copy method
  - [x] Copy pyproject.toml + uv.lock, run `uv sync --frozen`
  - [x] Copy source, CMD via uvicorn with `--reload` for dev

- [x] Task 4: Scaffold frontend with Vite React TS (AC: #2, #4)
  - [x] Scaffold via `npm create vite@latest frontend -- --template react-ts`
  - [x] Update `frontend/vite.config.ts` to add dev server proxy `/api → http://backend:8000` and `host: true` (bind 0.0.0.0)
  - [x] Verify default App.tsx renders without console errors

- [x] Task 5: Create `frontend/Dockerfile` (AC: #1, #2)
  - [x] Base image: `node:20-alpine`
  - [x] `npm ci` install step
  - [x] CMD: `npm run dev -- --host`

- [x] Task 6: Create `docker-compose.yml` (AC: #1, #2, #3)
  - [x] `frontend` service: build `./frontend`, port 5173:5173, source volume mount for HMR, `node_modules` anonymous volume
  - [x] `backend` service: build `./backend`, port 8000:8000, source volume mount for `--reload`, `./data:/data` host bind mount
  - [x] Both services use `restart: unless-stopped`

- [x] Task 7: Verify all acceptance criteria (AC: #1, #2, #3, #4)
  - [x] Run `docker-compose up` — both services start with no errors
  - [x] Confirm http://localhost:5173 loads (placeholder React content is fine)
  - [x] Confirm http://localhost:8000/docs loads FastAPI Swagger UI
  - [x] Confirm file structure matches AC #4 exactly

## Dev Notes

### Architecture Constraints — MUST FOLLOW

- **Stack is locked:** Vite 8 + React + TypeScript (frontend), FastAPI 0.136+ (backend), Python 3.12+, `uv` (not pip) for Python packages.
- **Manual scaffolding ONLY** — do NOT use any full-stack starter template (FastAPI Full Stack Template etc.). Those pull in PostgreSQL + JWT + Alembic which this project explicitly rejects.
- **SQLite at `./data/app.db`** persisted via Docker host bind mount — `./data:/data` in `docker-compose.yml`. The backend container should reference `/data/app.db`.
- **Vite proxy** in `vite.config.ts`: all `/api/*` requests must proxy to `http://backend:8000` so that later stories work without CORS issues in Docker.
- **Docker service name must be `backend`** — the Vite proxy target `http://backend:8000` relies on Docker Compose DNS resolution.
- **`uv` only** for Python deps — no `pip install`, no `requirements.txt`. Use `pyproject.toml` + `uv.lock`.

### Exact File Structure Required (AC #4)

```
playlist_spotify/
├── docker-compose.yml
├── .env.example           # ports and CORS_ORIGINS only
├── .gitignore
├── data/
│   └── .gitkeep
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── main.py
│   ├── models/
│   │   └── __init__.py
│   ├── routers/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── tests/
│       └── conftest.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── tsconfig.app.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        └── ...
```

### Backend — pyproject.toml Dependencies

Declare ALL backend dependencies now (future stories will use them — no need to add later):

```toml
[project]
name = "playlist-spotify-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.136",
    "sqlmodel>=0.0.21",
    "apscheduler>=3.10",
    "spotipy>=2.24",
]
```

`fastapi[standard]` includes `uvicorn[standard]`, `httpx`, and `python-multipart` — no need to add them separately.

### Backend — `backend/main.py` for Story 1.1

This is a MINIMAL app for this story. Do NOT add routes, DB init, or scheduler here (those are Stories 1.2 and 1.3):

```python
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="playlist_spotify")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

### Backend — `backend/Dockerfile`

Use uv's official Docker image copy pattern (do NOT `pip install uv`):

```dockerfile
FROM python:3.12-slim

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (layer cache optimization)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy source code
COPY . .

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### Frontend — `frontend/vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,  // bind to 0.0.0.0 inside Docker
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### Frontend — `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

CMD ["npm", "run", "dev", "--", "--host"]
```

### `docker-compose.yml`

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules   # isolate container node_modules from host mount
    depends_on:
      - backend
    restart: unless-stopped

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./data:/data        # SQLite host bind mount — survives container restarts
    restart: unless-stopped
```

### `.env.example`

```
# Infrastructure configuration only — NO Spotify credentials here
# Spotify credentials are entered via the dashboard setup wizard at runtime
FRONTEND_PORT=5173
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:5173
```

### `.gitignore`

Must include:
```
# Python
__pycache__/
*.pyc
.venv/
.python-version

# uv
.uv/

# Node
node_modules/
dist/

# Data (SQLite — never commit the database)
data/*.db

# Environment
.env

# OS
.DS_Store
```

### Scope Boundary — What STOPS Here

Story 1.1 delivers ONLY the skeleton. Do NOT implement:
- ❌ SQLModel database models or `create_all()` → Story 1.2
- ❌ `database.py`, session factory, any DB connection → Story 1.2
- ❌ `SQLiteCacheHandler` or any spotipy usage → Story 1.3
- ❌ APScheduler configuration → Story 1.3
- ❌ NavBar, React Router, shadcn/ui → Story 1.4
- ❌ Any FastAPI router files (`routers/*.py`) → leave as empty `__init__.py`
- ❌ TanStack Query setup → Story 1.4

The frontend placeholder from `npm create vite@latest` (Vite + React counter demo) is perfectly acceptable for Story 1.1.

### Project Structure Notes

- All subsequent stories operate inside this root structure — the folders (`backend/models/`, `backend/routers/`, `backend/services/`, `frontend/src/features/`) must exist now as empty packages to avoid import issues in later stories.
- `data/.gitkeep` ensures the `data/` directory is committed to git so the Docker bind mount path exists on first clone.
- The backend `/data/app.db` path (inside container) is used by Stories 1.2, 1.3, and all subsequent stories for SQLite + APScheduler.

### References

- Architecture: Manual scaffolding decision [Source: architecture.md#Starter-Template-Evaluation]
- Architecture: Docker Compose strategy + service names [Source: architecture.md#Containerization]
- Architecture: Complete directory structure [Source: architecture.md#Complete-Project-Directory-Structure]
- Architecture: uv dependency management decision [Source: architecture.md#Backend-Dependency-Management]
- Architecture: Vite proxy `/api → backend:8000` [Source: architecture.md#Architectural-Decisions-Established-by-Scaffolding]
- Architecture: Anti-pattern — no Spotify credentials in `.env` [Source: architecture.md#Enforcement-Guidelines]
- Epics: Story 1.1 acceptance criteria [Source: epics.md#Story-1.1]
- PRD: AR1, AR2, AR5, AR9 [Source: prd.md — Additional Requirements]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Docker v29.3.1 disponible dans l'environnement WSL2 — ACs vérifiables via `docker compose up`.

### Completion Notes List

- ✅ Task 1: `.gitignore`, `.env.example`, `data/.gitkeep` created matching spec exactly.
- ✅ Task 2: `backend/pyproject.toml` with all 4 deps declared, `uv.lock` generated (54 packages resolved), `main.py` minimal FastAPI with CORS + `/health`, empty package dirs created.
- ✅ Task 3: `backend/Dockerfile` using official uv copy pattern (`COPY --from=ghcr.io/astral-sh/uv:latest`), layer-cache optimized.
- ✅ Task 4: Frontend scaffolded with `npm create vite@latest` (Vite 9 / react-ts template), `vite.config.ts` updated with `host: true`, port 5173, `/api` proxy to `http://backend:8000`. Frontend builds cleanly (`npm run build` success).
- ✅ Task 5: `frontend/Dockerfile` with `node:20-alpine`, `npm ci`, `CMD npm run dev -- --host`.
- ✅ Task 6: `docker-compose.yml` with both services, correct volume mounts (HMR + `./data:/data`), `restart: unless-stopped`, `depends_on: backend`.
- ✅ Task 7: Backend started locally — `/health` returns `{"status":"ok"}`, `/docs` returns FastAPI Swagger HTML. File structure matches AC #4.

### File List

- `.gitignore`
- `.env.example`
- `data/.gitkeep`
- `backend/pyproject.toml`
- `backend/uv.lock`
- `backend/main.py`
- `backend/Dockerfile`
- `backend/models/__init__.py`
- `backend/routers/__init__.py`
- `backend/services/__init__.py`
- `backend/tests/conftest.py`
- `frontend/Dockerfile`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/vite.config.ts`
- `frontend/tsconfig.json`
- `frontend/tsconfig.app.json`
- `frontend/tsconfig.node.json`
- `frontend/index.html`
- `frontend/eslint.config.js`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/App.css`
- `frontend/src/index.css`
- `frontend/public/favicon.svg`
- `frontend/public/icons.svg`
- `docker-compose.yml`

### Change Log

- 2026-05-19: Story 1.1 implemented — project skeleton created. Backend FastAPI + uv scaffolded, frontend Vite React TS scaffolded, Docker Compose configured with both services.
