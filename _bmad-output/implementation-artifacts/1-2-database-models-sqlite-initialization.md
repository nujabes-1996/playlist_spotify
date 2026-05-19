# Story 1.2: Database Models & SQLite Initialization

Status: review

## Story

As a developer,
I want SQLModel table models defined and the database auto-created on startup,
so that the application has persistent storage ready for all features.

## Acceptance Criteria

1. **Given** the backend starts, **When** the FastAPI lifespan executes, **Then** `SQLModel.metadata.create_all()` runs and creates all tables in `./data/app.db`.
2. **Given** the database is initialized, **When** I inspect `app.db`, **Then** the following tables exist: `config`, `playlist`, `sync_log`.
3. **Given** the `config` table, **When** I review the schema, **Then** it has columns: `id`, `client_id` (str nullable), `client_secret` (str nullable), `playlist_size` (int, default 50), `cron_expr` (str nullable).
4. **Given** the `playlist` table, **When** I review the schema, **Then** it has columns: `id`, `spotify_id` (str unique), `name` (str), `is_included` (bool, default false).
5. **Given** the `sync_log` table, **When** I review the schema, **Then** it has columns: `id`, `status` (str: "success"/"failure"), `track_count` (int nullable), `error_message` (str nullable), `timestamp` (str ISO 8601).
6. **Given** `./data/app.db` is a host bind mount, **When** the Docker container is stopped and restarted, **Then** the database and all its contents persist.

## Tasks / Subtasks

- [x] Task 1: Create `backend/database.py` — engine + session factory (AC: #1, #6)
  - [x] Create SQLite engine pointing to `sqlite:////data/app.db`
  - [x] Create `get_session()` generator function for FastAPI dependency injection

- [x] Task 2: Create SQLModel table models (AC: #2, #3, #4, #5)
  - [x] Create `backend/models/config.py` — Config model
  - [x] Create `backend/models/playlist.py` — Playlist model
  - [x] Create `backend/models/sync_log.py` — SyncLog model
  - [x] Update `backend/models/__init__.py` — import all three models (required for metadata)

- [x] Task 3: Create `backend/dependencies.py` — shared FastAPI DB dependency (AC: #1)
  - [x] Import `get_session` from `database.py`
  - [x] Export `SessionDep` as `Annotated[Session, Depends(get_session)]`

- [x] Task 4: Update `backend/main.py` to add FastAPI lifespan with `create_all` (AC: #1, #2)
  - [x] Replace the bare FastAPI app with a lifespan context manager
  - [x] Import all models via `backend/models` before calling `create_all()`
  - [x] Call `SQLModel.metadata.create_all(engine)` on startup

- [x] Task 5: Verify acceptance criteria (AC: #1–#6)
  - [x] Start backend locally with `uv run uvicorn main:app --reload`
  - [x] Confirm `data/app.db` is created and all three tables exist (use `sqlite3` CLI or Python)
  - [x] Confirm `/health` still returns `{"status": "ok"}` (no regression)

## Dev Notes

### Critical File Locations

| File | Purpose |
|---|---|
| `backend/database.py` | **CREATE** — engine + session factory (only file that creates the engine) |
| `backend/models/config.py` | **CREATE** — Config SQLModel table |
| `backend/models/playlist.py` | **CREATE** — Playlist SQLModel table |
| `backend/models/sync_log.py` | **CREATE** — SyncLog SQLModel table |
| `backend/models/__init__.py` | **UPDATE** — import all three models |
| `backend/dependencies.py` | **CREATE** — `SessionDep` for router injection |
| `backend/main.py` | **UPDATE** — add lifespan with create_all |

### `backend/database.py`

```python
from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = "sqlite:////data/app.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def get_session():
    with Session(engine) as session:
        yield session
```

**Critical:** `sqlite:////data/app.db` = 4 slashes. Three slashes = relative path. Four slashes = absolute path `/data/app.db` inside the container, which matches the Docker bind mount `./data:/data`.

`check_same_thread=False` is required for SQLite when used with FastAPI's async request handling.

### SQLModel Table Definitions

**`backend/models/config.py`:**
```python
from typing import Optional
from sqlmodel import Field, SQLModel


class Config(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    playlist_size: int = Field(default=50)
    cron_expr: Optional[str] = None
```

**`backend/models/playlist.py`:**
```python
from typing import Optional
from sqlmodel import Field, SQLModel


class Playlist(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    spotify_id: str = Field(unique=True)
    name: str
    is_included: bool = Field(default=False)
```

**`backend/models/sync_log.py`:**
```python
from typing import Optional
from sqlmodel import Field, SQLModel


class SyncLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str  # "success" or "failure"
    track_count: Optional[int] = None
    error_message: Optional[str] = None
    timestamp: str  # ISO 8601 string, e.g. "2026-05-19T14:30:00Z"
```

**`backend/models/__init__.py`:**
```python
from .config import Config
from .playlist import Playlist
from .sync_log import SyncLog

__all__ = ["Config", "Playlist", "SyncLog"]
```

**Critical — models must be imported before `create_all()`:** SQLModel registers table metadata at class-definition time. If models are not imported before `SQLModel.metadata.create_all(engine)` runs, the tables are not created. The `__init__.py` import ensures all models are registered when `from models import *` or `import models` is executed in `main.py`.

### `backend/dependencies.py`

```python
from typing import Annotated
from fastapi import Depends
from sqlmodel import Session
from database import get_session

SessionDep = Annotated[Session, Depends(get_session)]
```

Routers import `SessionDep` from here — not from `database.py` directly. This centralises the dependency pattern for all future routers (Stories 2.x through 5.x).

### Updated `backend/main.py`

Add a lifespan context manager — do NOT use deprecated `@app.on_event("startup")`:

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

import models  # noqa: F401 — side-effect import registers all table metadata
from database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(title="playlist_spotify", lifespan=lifespan)

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

**The `import models` line is intentional.** The `# noqa: F401` comment suppresses the "unused import" linting warning. Without this import, models are not loaded into the SQLModel metadata registry and `create_all()` creates zero tables.

### Scope Boundary — What STOPS Here

This story delivers ONLY the database layer. Do NOT implement:
- ❌ APScheduler setup or `SQLAlchemyJobStore` → Story 1.3
- ❌ `SQLiteCacheHandler` or any spotipy usage → Story 1.3
- ❌ NavBar, React Router, shadcn/ui → Story 1.4
- ❌ Any FastAPI router files with actual endpoints → later stories
- ❌ Any Alembic migration tooling — `SQLModel.metadata.create_all()` is the intentional strategy (AR8)

### Architecture Constraints

- **Table naming:** SQLModel defaults to the class name lowercased as table name: `Config → config`, `Playlist → playlist`, `SyncLog → sync_log`. This matches the required table names in AC #2.
- **No migration tooling:** `create_all()` is idempotent — it creates tables that don't exist and skips existing ones. This is acceptable for greenfield development (AR8).
- **engine is a module-level singleton** in `database.py` — never re-create it in other files. All sessions come from this single engine.
- **All DB access via sessions from `dependencies.py`** — routers never call `Session(engine)` directly, always via `SessionDep`.
- **`data/app.db` path:** Inside the container it resolves to `/data/app.db`. The Docker Compose bind mount `./data:/data` ensures this file is on the host filesystem and persists across container restarts.

### Previous Story Context (1.1)

From Story 1.1 (status: review):
- `backend/models/__init__.py` already exists as an empty file — update it (don't create new).
- `pyproject.toml` already declares `sqlmodel>=0.0.21` — no new dependencies needed.
- `backend/main.py` exists with the minimal FastAPI app shown above — update it in-place, preserving the CORS middleware and `/health` endpoint.
- Docker v29.3.1 est disponible dans l'environnement WSL2 — vérification possible via `docker compose up` ou localement avec `uv run uvicorn main:app --reload`.

### Testing Guidance

No pytest tests are required for this story. Verification is manual:

```bash
# From project root
cd backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
# Wait for startup message, then:
sqlite3 ../data/app.db ".tables"
# Expected output: config  playlist  sync_log
sqlite3 ../data/app.db ".schema config"
# Verify columns match AC #3
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

### Project Structure Notes

After this story, the backend structure should be:

```
backend/
├── Dockerfile
├── pyproject.toml
├── uv.lock
├── main.py              ← UPDATED (lifespan + create_all)
├── database.py          ← NEW
├── dependencies.py      ← NEW
├── models/
│   ├── __init__.py      ← UPDATED (import all 3 models)
│   ├── config.py        ← NEW
│   ├── playlist.py      ← NEW
│   └── sync_log.py      ← NEW
├── routers/
│   └── __init__.py      (unchanged — still empty)
├── services/
│   └── __init__.py      (unchanged — still empty)
└── tests/
    └── conftest.py      (unchanged — still empty)
```

### References

- Architecture: SQLModel auto-create decision [Source: architecture.md#Data-Architecture]
- Architecture: `database.py` purpose and singleton pattern [Source: architecture.md#Data-Boundary]
- Architecture: `dependencies.py` for DB session sharing [Source: architecture.md#Complete-Project-Directory-Structure]
- Architecture: SQLite path `/data/app.db` inside container [Source: architecture.md#Containerization]
- Architecture: Table naming conventions (snake_case singular) [Source: architecture.md#Naming-Patterns]
- Epics: Story 1.2 acceptance criteria [Source: epics.md#Story-1.2]
- PRD: AR8 — `SQLModel.metadata.create_all()` on startup, no Alembic [Source: prd.md#Additional-Requirements]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- SyncLog table was named `synclog` by SQLModel default (camelCase lowercased). Fixed by adding `__tablename__ = "sync_log"` explicitly to match AC #2.

### Completion Notes List

- Implemented all 5 tasks: `database.py` (engine singleton + session factory), 3 SQLModel table models (`Config`, `Playlist`, `SyncLog`), `dependencies.py` (SessionDep), updated `main.py` with lifespan + `create_all`.
- Verified via Docker: tables `config`, `playlist`, `sync_log` created on startup; `/health` returns `{"status":"ok"}`; DB persists across container stop/start.
- No new dependencies required — `sqlmodel>=0.0.21` already declared in `pyproject.toml`.

### File List

- `backend/database.py` — NEW: SQLite engine singleton + `get_session()` factory
- `backend/models/config.py` — NEW: Config SQLModel table model
- `backend/models/playlist.py` — NEW: Playlist SQLModel table model
- `backend/models/sync_log.py` — NEW: SyncLog SQLModel table model (explicit `__tablename__ = "sync_log"`)
- `backend/models/__init__.py` — UPDATED: imports all 3 models for metadata registration
- `backend/dependencies.py` — NEW: `SessionDep` type alias for router injection
- `backend/main.py` — UPDATED: lifespan context manager with `SQLModel.metadata.create_all(engine)`

## Change Log

- 2026-05-19: Implemented Story 1.2 — database models and SQLite initialization. Created engine, 3 table models, dependencies module, and updated main.py with lifespan startup. All AC verified via Docker Compose.
