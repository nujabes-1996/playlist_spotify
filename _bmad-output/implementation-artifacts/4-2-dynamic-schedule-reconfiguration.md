# Story 4.2: Dynamic Schedule Reconfiguration

Status: review

## Story

As a user,
I want changes to the sync schedule to take effect immediately without restarting the app,
so that I can adjust the frequency at any time from the dashboard.

## Acceptance Criteria

1. **Given** a cron job is currently registered in APScheduler, **When** I update `cron_expr` via `PUT /api/v1/config` or `PATCH /api/v1/config` with a new value, **Then** the existing APScheduler job is removed and a new job is registered with the updated schedule immediately.

2. **Given** I set `cron_expr` to `"0 */6 * * *"` (every 6 hours), **When** the schedule is updated, **Then** the next sync fires at the next 6-hour boundary — not at the old schedule.

3. **Given** I clear `cron_expr` (set to null or empty string), **When** the config is saved, **Then** the APScheduler job is removed and no more scheduled syncs run until a new schedule is configured.

4. **Given** I enter an invalid cron expression in the `ConfigForm`, **When** I click Save, **Then** the backend returns a 400 error, the job is not modified, and the previous schedule remains active.

## Tasks / Subtasks

- [x] Task 1: Add `_validate_cron` helper + call `bootstrap_scheduler` in `routers/config.py` (AC: #1, #2, #3, #4)
  - [x] Import `bootstrap_scheduler` from `scheduler` at the top of `routers/config.py`
  - [x] Import `CronTrigger` from `apscheduler.triggers.cron` in `routers/config.py`
  - [x] Add private helper `_validate_cron(cron_expr: str | None) -> None` — calls `CronTrigger.from_crontab(cron_expr)` and raises `HTTPException(status_code=400, detail="Invalid cron expression")` on `ValueError`; does nothing if `cron_expr` is falsy (None or empty string)
  - [x] In `update_config` (PUT): call `_validate_cron(payload.cron_expr)` BEFORE saving; call `bootstrap_scheduler(config.cron_expr)` AFTER commit — treat empty string as None (normalize: `config.cron_expr = payload.cron_expr or None`)
  - [x] In `patch_config` (PATCH): if `"cron_expr"` is in `payload.model_fields_set`, call `_validate_cron(payload.cron_expr)` BEFORE saving; call `bootstrap_scheduler(config.cron_expr)` AFTER commit — normalize empty string to None here too; if `cron_expr` not in payload, do NOT call bootstrap (unchanged schedule)

- [x] Task 2: Create `backend/tests/test_story_4_2.py` (AC: #1, #3, #4)
  - [x] Use same session + client fixture pattern as `test_story_2_4.py` (StaticPool in-memory SQLite + dependency_overrides)
  - [x] Mock `bootstrap_scheduler` at `routers.config.bootstrap_scheduler` in ALL tests that exercise PUT/PATCH with cron changes — otherwise the real APScheduler (not started in test context) will error
  - [x] `test_put_config_with_cron_calls_bootstrap`: PUT with `cron_expr="0 */6 * * *"`, assert `bootstrap_scheduler` called with `"0 */6 * * *"`
  - [x] `test_put_config_without_cron_calls_bootstrap_none`: PUT with `cron_expr=None`, assert `bootstrap_scheduler` called with `None`
  - [x] `test_patch_with_valid_cron_calls_bootstrap`: PATCH `{"cron_expr": "0 0 * * *"}`, assert `bootstrap_scheduler` called with `"0 0 * * *"`
  - [x] `test_patch_clear_cron_calls_bootstrap_none`: PATCH `{"cron_expr": null}`, assert `bootstrap_scheduler` called with `None`
  - [x] `test_patch_without_cron_key_skips_bootstrap`: PATCH `{"playlist_size": 75}` only, assert `bootstrap_scheduler` NOT called
  - [x] `test_invalid_cron_put_returns_400`: PUT with `cron_expr="not-a-cron"`, assert 400, assert `bootstrap_scheduler` NOT called
  - [x] `test_invalid_cron_patch_returns_400`: PATCH with `{"cron_expr": "not-a-cron"}`, assert 400, assert `bootstrap_scheduler` NOT called
  - [x] `test_invalid_cron_does_not_corrupt_db`: seed cron `"0 * * * *"`, PATCH with invalid cron → 400, GET config → `cron_expr` still `"0 * * * *"`

- [x] Task 3: Run full test suite (no regressions)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_4_2.py -v` — all 8 tests pass
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` — 69 passed (61 prior + 8 new), 0 failures

- [x] Task 4: Update Postman collection
  - [x] Fetch current collection (`GET https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`)
  - [x] Update `PUT /api/v1/config` request description: note that saving a `cron_expr` immediately reschedules APScheduler without restart; saving `null` removes the job
  - [x] Update `PATCH /api/v1/config` request description: same note; add example showing invalid cron → 400
  - [x] Push updated collection (`PUT https://api.getpostman.com/collections/{uid}`)

## Dev Notes

### What This Story Adds

Story 4.1 wired the scheduler at **startup** (one-time bootstrap). Story 4.2 makes the scheduler **responsive to live config changes**. The two endpoints that write `cron_expr` must both trigger rescheduling:
- `PUT /api/v1/config` — full config overwrite (used by initial setup wizard and when re-entering credentials)
- `PATCH /api/v1/config` — partial update (used by `ConfigForm` for day-to-day schedule changes)

No new endpoints. No frontend changes — the `ConfigForm` from Story 2.4 already calls `PATCH /api/v1/config` and displays inline error messages on 4xx responses.

---

### Files to Touch

| File | Action | Notes |
|------|--------|-------|
| `backend/routers/config.py` | MODIFY | Add `_validate_cron`, import `bootstrap_scheduler` + `CronTrigger`, update both handlers |
| `backend/tests/test_story_4_2.py` | CREATE | 8 tests |
| Postman collection | UPDATE | Description updates on PUT + PATCH config |

No other files need modification. `backend/scheduler.py` (`bootstrap_scheduler`) is already complete from Story 4.1 — do NOT modify it.

---

### Implementation: `routers/config.py` Changes

**New imports to add:**
```python
from apscheduler.triggers.cron import CronTrigger
from scheduler import bootstrap_scheduler
```

**New helper (add before the router handlers):**
```python
def _validate_cron(cron_expr: str | None) -> None:
    if not cron_expr:
        return
    try:
        CronTrigger.from_crontab(cron_expr)
    except (ValueError, KeyError):
        raise HTTPException(status_code=400, detail="Invalid cron expression")
```

**Updated `patch_config`:**
```python
@router.patch("/config", response_model=ConfigRead)
def patch_config(payload: ConfigPatch, session: SessionDep) -> ConfigRead:
    config = session.exec(select(Config)).first()
    if config is None:
        raise HTTPException(status_code=400, detail="Setup required before updating config")
    cron_changed = "cron_expr" in payload.model_fields_set
    if payload.playlist_size is not None:
        config.playlist_size = payload.playlist_size
    if cron_changed:
        _validate_cron(payload.cron_expr)
        config.cron_expr = payload.cron_expr or None  # normalize empty string → None
    session.commit()
    session.refresh(config)
    if cron_changed:
        bootstrap_scheduler(config.cron_expr)
    return ConfigRead(
        setup_required=not bool(config.client_id),
        playlist_size=config.playlist_size,
        cron_expr=config.cron_expr,
    )
```

**Updated `update_config`:**
```python
@router.put("/config", response_model=ConfigRead)
def update_config(payload: ConfigWrite, session: SessionDep) -> ConfigRead:
    config = session.exec(select(Config)).first()
    if config is None:
        config = Config()
        session.add(config)
    _validate_cron(payload.cron_expr)
    config.client_id = payload.client_id
    config.client_secret = payload.client_secret
    config.playlist_size = payload.playlist_size if payload.playlist_size is not None else 50
    config.cron_expr = payload.cron_expr or None  # normalize empty string → None
    session.commit()
    session.refresh(config)
    bootstrap_scheduler(config.cron_expr)
    return ConfigRead(
        setup_required=not bool(config.client_id),
        playlist_size=config.playlist_size,
        cron_expr=config.cron_expr,
    )
```

**Critical: Validate BEFORE commit.** If `_validate_cron` raises, the DB is not touched and the existing job is not affected. This satisfies AC #4.

---

### Implementation: `test_story_4_2.py`

```python
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from models.config import Config


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def _seed_config(session, cron_expr=None):
    config = Config(client_id="id", client_secret="secret", playlist_size=50, cron_expr=cron_expr)
    session.add(config)
    session.commit()
    session.refresh(config)
    return config


def test_put_config_with_cron_calls_bootstrap(client, session):
    with patch("routers.config.bootstrap_scheduler") as mock_bs:
        r = client.put("/api/v1/config", json={"client_id": "a", "client_secret": "b", "cron_expr": "0 */6 * * *"})
    assert r.status_code == 200
    mock_bs.assert_called_once_with("0 */6 * * *")


def test_put_config_without_cron_calls_bootstrap_none(client, session):
    with patch("routers.config.bootstrap_scheduler") as mock_bs:
        r = client.put("/api/v1/config", json={"client_id": "a", "client_secret": "b"})
    assert r.status_code == 200
    mock_bs.assert_called_once_with(None)


def test_patch_with_valid_cron_calls_bootstrap(client, session):
    _seed_config(session)
    with patch("routers.config.bootstrap_scheduler") as mock_bs:
        r = client.patch("/api/v1/config", json={"cron_expr": "0 0 * * *"})
    assert r.status_code == 200
    mock_bs.assert_called_once_with("0 0 * * *")


def test_patch_clear_cron_calls_bootstrap_none(client, session):
    _seed_config(session, cron_expr="0 * * * *")
    with patch("routers.config.bootstrap_scheduler") as mock_bs:
        r = client.patch("/api/v1/config", json={"cron_expr": None})
    assert r.status_code == 200
    mock_bs.assert_called_once_with(None)


def test_patch_without_cron_key_skips_bootstrap(client, session):
    _seed_config(session, cron_expr="0 * * * *")
    with patch("routers.config.bootstrap_scheduler") as mock_bs:
        r = client.patch("/api/v1/config", json={"playlist_size": 75})
    assert r.status_code == 200
    mock_bs.assert_not_called()


def test_invalid_cron_put_returns_400(client, session):
    with patch("routers.config.bootstrap_scheduler") as mock_bs:
        r = client.put("/api/v1/config", json={"client_id": "a", "client_secret": "b", "cron_expr": "not-a-cron"})
    assert r.status_code == 400
    mock_bs.assert_not_called()


def test_invalid_cron_patch_returns_400(client, session):
    _seed_config(session)
    with patch("routers.config.bootstrap_scheduler") as mock_bs:
        r = client.patch("/api/v1/config", json={"cron_expr": "not-a-cron"})
    assert r.status_code == 400
    mock_bs.assert_not_called()


def test_invalid_cron_does_not_corrupt_db(client, session):
    _seed_config(session, cron_expr="0 * * * *")
    with patch("routers.config.bootstrap_scheduler"):
        client.patch("/api/v1/config", json={"cron_expr": "not-a-cron"})
    r = client.get("/api/v1/config")
    assert r.json()["cron_expr"] == "0 * * * *"
```

**Mock path:** `routers.config.bootstrap_scheduler` — mock at the import site in `routers/config.py`, not at the definition site in `scheduler.py`. This is the established project convention (e.g., `patch("routers.<module>.spotify_service.<fn>", ...)`).

---

### Why `cron_changed` Flag in `patch_config`

The PATCH endpoint must distinguish "user explicitly cleared the cron" from "user didn't mention the cron at all". The existing `payload.model_fields_set` check already does this for DB writes; the same flag gates the `bootstrap_scheduler` call. Calling bootstrap when cron was not in the payload would incorrectly reschedule based on the DB's current cron_expr even though the user didn't intend to change the schedule.

---

### Architecture Rules — MUST FOLLOW

- Business logic belongs in `services/` — but `bootstrap_scheduler` is a **scheduler operation** (not business logic), so calling it from the router is correct here. The router is coordinating a side-effect on the infrastructure layer, not performing sync business logic.
- All JSON fields: snake_case — no changes to response shape.
- No direct `spotipy` calls in routers.
- No new API endpoints in this story.

---

### Anti-Patterns to Avoid

- ❌ Modifying `scheduler.py` — `bootstrap_scheduler` is already correct and complete from Story 4.1. Do NOT touch it.
- ❌ Calling `bootstrap_scheduler` BEFORE `session.commit()` — if commit fails, the scheduler would be out of sync with the DB.
- ❌ Calling `bootstrap_scheduler` when `cron_expr` not in PATCH payload — only reschedule if the cron was explicitly set by the caller.
- ❌ Letting invalid cron expressions reach `session.commit()` — validate first, short-circuit before any DB mutation.
- ❌ Raising `HTTPException(500)` for invalid cron — it's a client error, use 400.
- ❌ Not normalizing empty string `""` to `None` — APScheduler would receive `""` and could fail or behave unexpectedly.

---

### Previous Story Learnings (from Story 4.1)

- `bootstrap_scheduler(cron_expr)` is idempotent: it uses `replace_existing=True` so calling it twice with the same cron just refreshes the job — no `ConflictingIdError`.
- `bootstrap_scheduler(None)` safely removes the job if it exists, or does nothing if there's no job — safe to call unconditionally.
- Local import of `run_sync` inside `bootstrap_scheduler` was the fix for circular imports at module load. No need to re-introduce this pattern in the router.
- Test pattern from 4.1: patch at the module where the object lives — `patch("scheduler.scheduler.add_job")`. For 4.2, the equivalent is `patch("routers.config.bootstrap_scheduler")`.
- Full test suite had 61 tests at end of Story 4.1. New story should bring total to ~69 (61 + 8).

---

### Project Structure Notes

- `backend/routers/config.py` — modify only (no new file in routers/)
- `backend/tests/test_story_4_2.py` — create (mirrors `test_story_2_4.py` structure)
- No frontend files to touch — `ConfigForm` (Story 2.4) already handles the PUT/PATCH calls and shows inline errors on 4xx

### References

- Story 4.1 implementation: `_bmad-output/implementation-artifacts/4-1-scheduler-bootstrap-job-persistence.md`
- `bootstrap_scheduler` definition: `backend/scheduler.py`
- Config router (current): `backend/routers/config.py`
- Test fixture pattern: `backend/tests/test_story_2_4.py`
- Architecture: `_bmad-output/planning-artifacts/architecture.md` — "Business logic in services/, never in routers/"
- Postman collection UID: `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` (API key in `.mcp.json`)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No issues encountered. All 8 tests passed on first run after implementation.

### Completion Notes List

- Added imports `CronTrigger` (from apscheduler) and `bootstrap_scheduler` (from scheduler) to `backend/routers/config.py`.
- Added `_validate_cron(cron_expr: str | None)` helper: validates via `CronTrigger.from_crontab()`, raises `HTTPException(400)` on `ValueError`/`KeyError`. Does nothing for falsy values.
- Updated `patch_config` (PATCH): uses `cron_changed` flag (via `model_fields_set`) to detect explicit cron payload; validates before commit; calls `bootstrap_scheduler(config.cron_expr)` only when cron was explicitly set. Empty string normalized to `None`.
- Updated `update_config` (PUT): validates cron before commit; calls `bootstrap_scheduler(config.cron_expr)` after commit always. Empty string normalized to `None`.
- Created `backend/tests/test_story_4_2.py` with 8 tests covering: PUT/PATCH calls bootstrap with correct arg, PATCH without cron key skips bootstrap, invalid cron → 400 for both PUT and PATCH, invalid cron does not corrupt DB.
- Mock path: `routers.config.bootstrap_scheduler` (import-site mock, project convention).
- Full test suite: **69 passed** (61 prior + 8 new), 0 failures, 0 regressions.
- Postman collection updated: `PUT /api/v1/config` and `PATCH /api/v1/config` descriptions updated to document live rescheduling behavior and 400 on invalid cron.

### File List

- `backend/routers/config.py` — modified (added `_validate_cron`, `CronTrigger` import, `bootstrap_scheduler` import + calls in PUT and PATCH handlers)
- `backend/tests/test_story_4_2.py` — created (8 tests)
