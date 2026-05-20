# Story 4.1: Scheduler Bootstrap & Job Persistence

Status: review

## Story

As a user,
I want sync jobs to run automatically on my configured schedule and survive container restarts,
so that my playlist stays current without any manual intervention.

## Acceptance Criteria

1. **Given** the backend starts and a `cron_expr` is stored in the DB, **When** the FastAPI lifespan executes, **Then** APScheduler registers a cron job using the stored `cron_expr` that calls `sync_engine.run_sync()`.

2. **Given** the APScheduler job is registered with `SQLAlchemyJobStore`, **When** the Docker container is stopped and restarted, **Then** the job is restored from the DB and continues firing on schedule without re-registration (FR16, NFR9).

3. **Given** no `cron_expr` is stored yet, **When** the backend starts, **Then** no job is registered — APScheduler starts empty with no errors.

4. **Given** the scheduler is running and the cron fires, **When** `sync_engine.run_sync()` executes, **Then** the same sync logic as the manual trigger runs, including sync logging.

5. **Given** a scheduled sync runs while another sync is already in progress, **When** the job fires, **Then** the concurrent execution is skipped — no duplicate sync runs simultaneously.

## Tasks / Subtasks

- [x] Task 1: Add `bootstrap_scheduler(cron_expr: str | None)` to `backend/scheduler.py` (AC: #1, #3, #5)
  - [x] Import `CronTrigger` from `apscheduler.triggers.cron` and `run_sync` from `services.sync_engine`
  - [x] If `cron_expr` is not None: call `scheduler.add_job(run_sync, CronTrigger.from_crontab(cron_expr), id="sync_job", replace_existing=True, max_instances=1, coalesce=True)`
  - [x] If `cron_expr` is None: remove job if it exists — `if scheduler.get_job("sync_job"): scheduler.remove_job("sync_job")`
  - [x] Function must be importable from `main.py`

- [x] Task 2: Call `bootstrap_scheduler` in `backend/main.py` lifespan (AC: #1, #2, #3)
  - [x] After `scheduler.start()`, open a DB session, read `cron_expr` from `Config` table, call `bootstrap_scheduler(config.cron_expr if config else None)`
  - [x] Use a `with Session(engine) as session:` block — do NOT use `SessionDep` (lifespan is not a request context)
  - [x] Import `bootstrap_scheduler` from `scheduler`

- [x] Task 3: Create `backend/tests/test_story_4_1.py` (AC: #1, #2, #3, #5)
  - [x] `test_bootstrap_with_cron_expr_registers_job`: mock `scheduler.add_job`, call `bootstrap_scheduler("0 * * * *")`, assert `add_job` called with `id="sync_job"`, `replace_existing=True`, `max_instances=1`
  - [x] `test_bootstrap_without_cron_expr_does_not_register_job`: mock `scheduler.add_job`, call `bootstrap_scheduler(None)`, assert `add_job` NOT called
  - [x] `test_bootstrap_without_cron_expr_removes_existing_job`: mock `scheduler.get_job` returning a job object, mock `scheduler.remove_job`, call `bootstrap_scheduler(None)`, assert `remove_job("sync_job")` called
  - [x] `test_bootstrap_uses_crontab_trigger`: asserts that `add_job` reçoit bien une instance `CronTrigger` — 5 tests au total

- [x] Task 4: Run full test suite and confirm no regressions
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` — 61 passed, 0 failures

## Dev Notes

### Scope of This Story

Story 4.1 is **startup-only scheduler bootstrap**. It wires the existing `scheduler.py` + `sync_engine.run_sync()` together at app startup:
- Reads `cron_expr` from DB on startup → registers job if present
- Uses `replace_existing=True` so restart with same cron is idempotent
- Uses `max_instances=1` to prevent concurrent sync runs (AC #5)

Story 4.1 does NOT include:
- Live schedule reconfiguration via `PATCH /api/v1/config` (Story 4.2)
- Any new API endpoints — no Postman update needed
- Frontend changes — scheduler runs in background only

---

### Codebase State Entering This Story

| File | State | Action |
|------|-------|--------|
| `backend/scheduler.py` | ✅ Exists (Story 1.3) — `BackgroundScheduler` + `SQLAlchemyJobStore` | MODIFY — add `bootstrap_scheduler()` |
| `backend/main.py` | ✅ Exists — `scheduler.start()` + `scheduler.shutdown(wait=False)` in lifespan | MODIFY — call `bootstrap_scheduler` after start |
| `backend/services/sync_engine.py` | ✅ Complete (Story 3.4) — `run_sync()` fully implemented | UNCHANGED |
| `backend/models/config.py` | ✅ Exists — has `cron_expr: Optional[str]` column | UNCHANGED |
| `backend/database.py` | ✅ Exists — exports `engine` | UNCHANGED |
| `backend/tests/test_story_4_1.py` | ❌ Missing | CREATE |

---

### Current `backend/scheduler.py` (from Story 1.3)

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

**Add `bootstrap_scheduler` to this file:**

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger

DATABASE_URL = "sqlite:////data/app.db"

scheduler = BackgroundScheduler(
    jobstores={
        "default": SQLAlchemyJobStore(url=DATABASE_URL)
    }
)


def bootstrap_scheduler(cron_expr: str | None) -> None:
    from services.sync_engine import run_sync  # local import to avoid circular imports

    if cron_expr:
        scheduler.add_job(
            run_sync,
            CronTrigger.from_crontab(cron_expr),
            id="sync_job",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    else:
        if scheduler.get_job("sync_job"):
            scheduler.remove_job("sync_job")
```

**Why local import for `run_sync`:** Avoids a circular import at module load time (scheduler imports sync_engine which imports database which might trigger model registration). The local import inside the function executes only when `bootstrap_scheduler` is called, after all modules are initialized.

**Why `replace_existing=True`:** The `SQLAlchemyJobStore` persists jobs in SQLite. On restart, the job already exists in the DB. Without `replace_existing=True`, `add_job` would raise `ConflictingIdError`. With it, the job trigger is refreshed — critical if `cron_expr` was changed while the app was down.

**Why `max_instances=1`:** Prevents two `run_sync()` calls from running concurrently if a sync takes longer than the cron interval. APScheduler will skip the scheduled firing if the job is already running.

**Why `coalesce=True`:** If the app was down for multiple cron intervals, APScheduler fires only once on restart rather than firing N missed times.

---

### File: `backend/main.py` — MODIFY lifespan

Current lifespan:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)
```

Updated lifespan:
```python
from scheduler import scheduler, bootstrap_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    scheduler.start()
    with Session(engine) as session:
        config = session.exec(select(Config)).first()
        bootstrap_scheduler(config.cron_expr if config else None)
    yield
    scheduler.shutdown(wait=False)
```

**Additional imports needed in `main.py`:**
```python
from sqlmodel import Session, select
from models.config import Config
from scheduler import scheduler, bootstrap_scheduler
```

Note: `Session` and `select` may already be imported — verify before adding duplicates.

---

### File: `backend/tests/test_story_4_1.py` — CREATE

```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from scheduler import bootstrap_scheduler


def test_bootstrap_with_cron_expr_registers_job():
    with patch("scheduler.scheduler.add_job") as mock_add_job, \
         patch("scheduler.scheduler.get_job", return_value=None):
        bootstrap_scheduler("0 * * * *")
    mock_add_job.assert_called_once()
    call_kwargs = mock_add_job.call_args
    assert call_kwargs.kwargs.get("id") == "sync_job" or call_kwargs.args[2] == "sync_job" or any(
        a == "sync_job" for a in call_kwargs.args
    )


def test_bootstrap_without_cron_expr_does_not_register_job():
    with patch("scheduler.scheduler.add_job") as mock_add_job, \
         patch("scheduler.scheduler.get_job", return_value=None):
        bootstrap_scheduler(None)
    mock_add_job.assert_not_called()


def test_bootstrap_without_cron_expr_removes_existing_job():
    mock_job = MagicMock()
    with patch("scheduler.scheduler.get_job", return_value=mock_job), \
         patch("scheduler.scheduler.remove_job") as mock_remove:
        bootstrap_scheduler(None)
    mock_remove.assert_called_once_with("sync_job")
```

**Mock pattern:** `patch("scheduler.scheduler.add_job", ...)` — patch the `scheduler` object's methods at the module level. This matches the project's established mock convention: patch at the module where the object is defined.

**Note on the `add_job` assertion:** APScheduler's `add_job` accepts positional and keyword args — the exact call signature is:
```python
scheduler.add_job(
    func,           # positional: run_sync
    trigger,        # positional: CronTrigger instance
    id="sync_job",
    replace_existing=True,
    max_instances=1,
    coalesce=True,
)
```
Test should assert `mock_add_job.call_args.kwargs["id"] == "sync_job"` and `mock_add_job.call_args.kwargs["replace_existing"] is True` and `mock_add_job.call_args.kwargs["max_instances"] == 1`.

---

### Architecture Rules — MUST FOLLOW

- **Business logic in `services/`, never in `routers/`** — `bootstrap_scheduler` lives in `scheduler.py`, not in a router.
- **Scheduler imports `sync_engine` via local import** — prevents circular dependency at module load.
- **`SQLAlchemyJobStore` only** — never use the default `MemoryJobStore` (AR3). Already configured in `scheduler.py`.
- **`Session(engine)` in lifespan** — lifespan has no request context, so `SessionDep` (FastAPI dependency injection) cannot be used. Use `with Session(engine) as session:` directly.
- **No new API endpoints in Story 4.1** — scheduler bootstrap is internal. Dynamic reconfiguration is Story 4.2.

---

### Anti-Patterns to Avoid

- ❌ Using `MemoryJobStore` — already configured as `SQLAlchemyJobStore`, do NOT change it.
- ❌ Calling `scheduler.add_job` at module import time — the scheduler must be started first (`scheduler.start()`), which happens in lifespan.
- ❌ Using `SessionDep` in the lifespan function — it's a FastAPI request-scope dependency, not usable outside request handlers.
- ❌ `scheduler.add_job(..., id="sync_job")` without `replace_existing=True` — will raise `ConflictingIdError` on restart if job is already in the SQLite job store.
- ❌ Omitting `max_instances=1` — allows concurrent `run_sync()` calls if a sync takes longer than the cron interval.
- ❌ Adding `GET /api/v1/scheduler/*` endpoints in this story — no scheduler API in 4.1.
- ❌ Implementing `cron_expr` change detection in `PATCH /api/v1/config` — that belongs to Story 4.2.

---

### Verification Checklist

```bash
# Run new story tests only
docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_4_1.py -v
# Expected: 3+ tests pass

# Run full suite — no regressions
docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v
# Expected: all prior tests + new tests = total pass, 0 failures

# Manual verification: start with cron_expr configured
# 1. Set cron_expr in DB (e.g., via PATCH /api/v1/config)
# 2. docker-compose restart backend
# 3. Check logs — APScheduler should not print "No jobs currently scheduled"
# 4. docker exec playlist_spotify-backend-1 python -c "
#    from scheduler import scheduler; scheduler.start()
#    print(scheduler.get_jobs())"
```

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No issues encountered. All 5 tests passed on first run after implementation.

### Completion Notes List

- Added `bootstrap_scheduler(cron_expr: str | None)` to `backend/scheduler.py`: registers `sync_engine.run_sync` as a `CronTrigger` job with `id="sync_job"`, `replace_existing=True`, `max_instances=1`, `coalesce=True` when `cron_expr` is provided; removes existing job when `cron_expr` is None.
- Local import of `run_sync` inside `bootstrap_scheduler` avoids circular dependency at module load time.
- Modified `backend/main.py` lifespan: after `scheduler.start()`, opens a `Session(engine)` directly (not `SessionDep`), reads `Config.cron_expr`, calls `bootstrap_scheduler(...)`.
- Created `backend/tests/test_story_4_1.py` with 5 tests: job registered with correct kwargs, job not registered when no cron, existing job removed when cron cleared, no remove called when no existing job, `CronTrigger` instance used.
- Full test suite: **61 passed** (56 prior + 5 new), 0 failures, 0 regressions.

### File List

- `backend/scheduler.py` — modified (added `CronTrigger` import + `bootstrap_scheduler` function)
- `backend/main.py` — modified (added `Session`, `select`, `Config`, `bootstrap_scheduler` imports; updated lifespan to call `bootstrap_scheduler`)
- `backend/tests/test_story_4_1.py` — created (5 tests)
