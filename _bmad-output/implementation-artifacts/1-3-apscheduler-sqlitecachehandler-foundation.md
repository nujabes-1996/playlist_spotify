# Story 1.3: APScheduler & SQLiteCacheHandler Foundation

Status: review

## Change Log

- 2026-05-19: Implemented Story 1.3 — APScheduler with SQLAlchemyJobStore, SQLiteCacheHandler, spotify_token_json column added to Config, main.py lifespan updated. All 10 tests pass, all ACs verified.

## Story

As a developer,
I want APScheduler configured with SQLAlchemyJobStore and a custom SQLiteCacheHandler implemented,
so that scheduler persistence and Spotify token storage are production-ready from the start.

## Acceptance Criteria

1. **Given** the backend starts, **When** the FastAPI lifespan executes, **Then** APScheduler is initialized with `SQLAlchemyJobStore` pointing to `sqlite:////data/app.db` (not the default MemoryJobStore).
2. **Given** APScheduler is initialized, **When** I inspect `app.db`, **Then** the APScheduler job store table (`apscheduler_jobs`) exists (even if empty — no jobs registered yet).
3. **Given** `services/token_manager.py`, **When** I review the code, **Then** it contains `SQLiteCacheHandler` subclassing spotipy's `CacheHandler` with `get_cached_token()` reading from the `config` table and `save_token_to_cache()` writing to the `config` table.
4. **Given** no Spotify credentials are configured yet, **When** the backend starts, **Then** no errors are raised — APScheduler starts with no jobs, `SQLiteCacheHandler` handles `None` token gracefully.

## Tasks / Subtasks

- [x] Task 1: Add `spotify_token_json` column to Config model and reset database (AC: #3, #4)
  - [x] Add `spotify_token_json: Optional[str] = None` field to `backend/models/config.py`
  - [x] Delete `data/app.db` so `create_all()` recreates it with the new column (see Dev Notes)

- [x] Task 2: Create `backend/scheduler.py` — APScheduler with SQLAlchemyJobStore (AC: #1, #2)
  - [x] Import `BackgroundScheduler` from `apscheduler.schedulers.background`
  - [x] Import `SQLAlchemyJobStore` from `apscheduler.jobstores.sqlalchemy`
  - [x] Define module-level `scheduler` singleton with `SQLAlchemyJobStore(url="sqlite:////data/app.db")`

- [x] Task 3: Create `backend/services/token_manager.py` — `SQLiteCacheHandler` (AC: #3, #4)
  - [x] Subclass `spotipy.cache_handler.CacheHandler`
  - [x] Implement `get_cached_token()` — reads JSON from `config.spotify_token_json`, returns `None` gracefully if not set
  - [x] Implement `save_token_to_cache(token_info)` — upserts JSON string to `config.spotify_token_json`

- [x] Task 4: Update `backend/main.py` lifespan to start/stop scheduler (AC: #1, #2, #4)
  - [x] Import `scheduler` from `scheduler.py`
  - [x] Call `scheduler.start()` after `create_all()` in lifespan startup
  - [x] Call `scheduler.shutdown(wait=False)` in lifespan teardown (after `yield`)

- [x] Task 5: Verify acceptance criteria (AC: #1–#4)
  - [x] Start backend; confirm `apscheduler_jobs` table exists in `app.db`
  - [x] Confirm no startup errors when no Spotify credentials are present
  - [x] Confirm `/health` still returns `{"status": "ok"}` (regression check)

## Dev Notes

### Files to Create / Modify

| File | Action | Purpose |
|---|---|---|
| `backend/models/config.py` | **UPDATE** — add `spotify_token_json` field | Store spotipy token as JSON string |
| `backend/scheduler.py` | **CREATE** | APScheduler singleton with SQLAlchemyJobStore |
| `backend/services/token_manager.py` | **CREATE** | SQLiteCacheHandler for spotipy |
| `backend/main.py` | **UPDATE** — add scheduler start/stop to lifespan | Wire scheduler into app lifecycle |
| `data/app.db` | **DELETE** — let create_all() recreate it | Apply new Config column (no Alembic) |

### Critical: Database Reset Required

`SQLModel.metadata.create_all()` is **idempotent — it does NOT add new columns to existing tables**. Adding `spotify_token_json` to the `Config` model has no effect on an already-created `config` table.

**Action required before running the backend:**
```bash
rm data/app.db
```
On next startup, `create_all()` recreates all tables including the new column. This is intentional — no Alembic per AR8. Development data can be discarded at this stage.

### Updated `backend/models/config.py`

```python
from typing import Optional
from sqlmodel import Field, SQLModel


class Config(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    playlist_size: int = Field(default=50)
    cron_expr: Optional[str] = None
    spotify_token_json: Optional[str] = None  # spotipy token dict serialized as JSON
```

### `backend/scheduler.py`

APScheduler **3.11.2** (3.x API) — use `BackgroundScheduler`, NOT `AsyncScheduler`:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

DATABASE_URL = "sqlite:////data/app.db"

scheduler = BackgroundScheduler(
    jobstores={
        "default": SQLAlchemyJobStore(url=DATABASE_URL)
    }
)
```

**Key points:**
- Module-level singleton — never instantiate `scheduler` elsewhere.
- `SQLAlchemyJobStore` creates/manages the `apscheduler_jobs` table automatically when the scheduler starts.
- No jobs are registered in this story. Job registration happens in Story 4.1.
- `BackgroundScheduler` runs in a daemon thread — it is compatible with uvicorn's threading model.

### `backend/services/token_manager.py`

spotipy **2.26.0** — `CacheHandler` is in `spotipy.cache_handler`:

```python
import json
from spotipy.cache_handler import CacheHandler
from sqlmodel import Session, select

from database import engine
from models.config import Config


class SQLiteCacheHandler(CacheHandler):
    """Stores spotipy OAuth token in the SQLite config table.

    Replaces default CacheFileHandler (filesystem-based, not Docker-safe).
    """

    def get_cached_token(self):
        with Session(engine) as session:
            config = session.exec(select(Config)).first()
            if config and config.spotify_token_json:
                return json.loads(config.spotify_token_json)
            return None

    def save_token_to_cache(self, token_info):
        with Session(engine) as session:
            config = session.exec(select(Config)).first()
            if config is None:
                config = Config()
                session.add(config)
            config.spotify_token_json = json.dumps(token_info)
            session.commit()
```

**Invariants the dev must preserve:**
- `get_cached_token()` must return `None` (not raise) when no token is stored — spotipy calls this at initialization.
- `save_token_to_cache()` must upsert — create the `Config` row if it doesn't exist yet.
- Use the engine from `database.py` directly (no `SessionDep` — this is a service, not a router).

### Updated `backend/main.py` Lifespan

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

import models  # noqa: F401 — side-effect import registers all table metadata
from database import engine
from scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


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

**Critical:** `scheduler.shutdown(wait=False)` prevents uvicorn from hanging on shutdown. `wait=True` (default) would block until running jobs complete, which is unnecessary here since no jobs run in this story.

### No New Dependencies

All required packages are already in `pyproject.toml` and `uv.lock`:
- `apscheduler>=3.10` → resolves to **3.11.2**
- `spotipy>=2.24` → resolves to **2.26.0**
- `sqlalchemy` is a transitive dependency of both `sqlmodel` and `apscheduler` — already present

**Do NOT run `uv add` for anything.** The lockfile is already correct.

### Architecture Constraints — MUST FOLLOW

- **AR3:** APScheduler MUST use `SQLAlchemyJobStore` — never the default `MemoryJobStore`. The `MemoryJobStore` loses all jobs on container restart (FR16 violation).
- **AR4:** `SQLiteCacheHandler` MUST be in `services/token_manager.py` and subclass spotipy's `CacheHandler`.
- Both the scheduler and the token manager read/write to `sqlite:////data/app.db` — the same file as the SQLModel tables. This is intentional: a single SQLite file for everything (simplicity, single bind mount).
- The `scheduler` singleton in `scheduler.py` is imported by `main.py` AND will be imported by `routers/sync.py` (Story 4.1) to trigger manual syncs. Do NOT create a second instance.

### Anti-Patterns to Avoid

- ❌ `MemoryJobStore` — loses jobs on restart
- ❌ `AsyncScheduler` (APScheduler 4.x API) — this project uses APScheduler 3.x
- ❌ `SQLiteCacheHandler` raising on `None` — `get_cached_token()` must return `None` gracefully
- ❌ Creating a new scheduler instance in routers — import the singleton from `scheduler.py`
- ❌ Running `uv add` — all packages are already locked
- ❌ Using relative path in `SQLAlchemyJobStore` URL — must use `sqlite:////data/app.db` (4 slashes = absolute path inside container)

### Previous Story Context (Learnings from 1.1 and 1.2)

From Story 1.1:
- Docker service name is `backend` — Python path inside container is `/app` (not `/backend`)
- `uv.lock` is already generated with all 4 dependencies including `apscheduler` and `spotipy`

From Story 1.2:
- `database.py` exports `engine` — import it directly in `token_manager.py`
- `SQLModel` table naming: SQLModel lowercases the class name. `Config` → table `config`. No `__tablename__` needed (unlike `SyncLog` → had to explicitly set `__tablename__ = "sync_log"`)
- `create_all()` only creates tables — it does NOT add columns. **Delete `data/app.db` before testing.**
- Debug note from 1.2: SyncLog needed explicit `__tablename__ = "sync_log"` — `Config` does not have this issue (class name lowercased = `config` which matches the required table name).

### Scope Boundary — What STOPS Here

- ❌ Registering any APScheduler jobs → Story 4.1
- ❌ Initializing a spotipy `Spotify` client with `SQLiteCacheHandler` → Story 2.2
- ❌ Any auth routes or OAuth flow → Story 2.1/2.2
- ❌ NavBar, React Router, shadcn/ui → Story 1.4
- ❌ Any `services/spotify.py` wrapper → Story 2.2

### Verification

```bash
# Start backend locally (from backend/)
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# In another terminal:
sqlite3 ../data/app.db ".tables"
# Expected: apscheduler_jobs  config  playlist  sync_log

sqlite3 ../data/app.db ".schema config"
# Expected: spotify_token_json column present

curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

### Project Structure After This Story

```
backend/
├── main.py              ← UPDATED (scheduler start/stop in lifespan)
├── scheduler.py         ← NEW (APScheduler singleton + SQLAlchemyJobStore)
├── database.py          (unchanged)
├── dependencies.py      (unchanged)
├── models/
│   ├── config.py        ← UPDATED (spotify_token_json field added)
│   ├── playlist.py      (unchanged)
│   ├── sync_log.py      (unchanged)
│   └── __init__.py      (unchanged)
├── services/
│   ├── token_manager.py ← NEW (SQLiteCacheHandler)
│   └── __init__.py      (unchanged)
└── tests/
    └── conftest.py      (unchanged)
```

### References

- Architecture: APScheduler SQLAlchemyJobStore requirement (Gap 1 Critical) [Source: architecture.md#Gap-Analysis]
- Architecture: SQLiteCacheHandler requirement (Gap 2 Critical) [Source: architecture.md#Gap-Analysis]
- Architecture: `scheduler.py` boundary — imports services, not routers [Source: architecture.md#Scheduler-Boundary]
- Architecture: `database.py` singleton pattern [Source: architecture.md#Data-Boundary]
- Epics: Story 1.3 acceptance criteria [Source: epics.md#Story-1.3]
- PRD: AR3 — APScheduler must use SQLAlchemyJobStore [Source: prd.md#Additional-Requirements]
- PRD: AR4 — SQLiteCacheHandler in services/token_manager.py [Source: prd.md#Additional-Requirements]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Fixed failing test `test_get_cached_token_returns_none_when_no_row`: `SQLModel.metadata.create_all()` only creates tables for imported models. Added `import models` at top of test file to ensure all metadata is registered before the fixture calls `create_all()`.

### Completion Notes List

- Implemented `SQLiteCacheHandler` in `backend/services/token_manager.py` subclassing `spotipy.cache_handler.CacheHandler`. `get_cached_token()` returns `None` gracefully; `save_token_to_cache()` upserts the Config row.
- Created `backend/scheduler.py` with `BackgroundScheduler` + `SQLAlchemyJobStore(url="sqlite:////data/app.db")` singleton. No jobs registered (deferred to Story 4.1).
- Updated `backend/main.py` lifespan to call `scheduler.start()` at startup and `scheduler.shutdown(wait=False)` at teardown.
- Added `spotify_token_json: Optional[str] = None` field to `Config` model; deleted `data/app.db` to trigger `create_all()` recreation.
- All 4 tables confirmed present in DB: `config`, `playlist`, `sync_log`, `apscheduler_jobs`.
- 10/10 tests pass. `/health` returns `{"status": "ok"}`.

### File List

- `backend/models/config.py` — updated: added `spotify_token_json` field
- `backend/scheduler.py` — created: APScheduler singleton with SQLAlchemyJobStore
- `backend/services/token_manager.py` — created: SQLiteCacheHandler
- `backend/main.py` — updated: scheduler start/stop in lifespan
- `backend/tests/test_story_1_3.py` — created: 10 tests covering all ACs
- `data/app.db` — deleted and recreated by backend on startup
