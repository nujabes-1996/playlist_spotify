# Story 3.4: Dynamic Playlist Push & Sync Logging

Status: review

## Story

As a user,
I want the sync engine to update my Spotify dynamic playlist and log every outcome,
so that I always have an up-to-date playlist and full traceability of what happened.

## Acceptance Criteria

1. **Given** the harvest and dedup are complete, **When** the target "Recent Adds" playlist does not exist on Spotify, **Then** it is created and its Spotify ID is stored in the DB (FR8).

2. **Given** the target playlist exists, **When** the push runs, **Then** its contents are fully replaced with the harvested top-N tracks (FR9).

3. **Given** a successful sync, **When** `run_sync()` completes, **Then** a `SyncLog` entry is written with `status="success"`, `track_count=N`, `timestamp=ISO8601`, `error_message=None` (NFR11).

4. **Given** any error occurs during the sync (e.g., Spotify API error, token failure, no playlists selected), **When** the exception is caught, **Then** the existing dynamic playlist contents are left unchanged (NFR10) and a `SyncLog` entry is written with `status="failure"` and the `error_message` populated (NFR11).

5. **Given** Spotify API returns HTTP 429, **When** spotipy handles the response, **Then** the request is retried with exponential backoff automatically — no manual retry loop in `sync_engine.py` (NFR12).

## Tasks / Subtasks

- [x] Task 1: Add `dynamic_playlist_id` column to Config model (AC: #1)
  - [x] Add `dynamic_playlist_id: Optional[str] = None` field in `backend/models/config.py`
  - [x] Delete `./data/app.db` locally to force schema recreation (no migrations)

- [x] Task 2: Add Spotify push functions to `backend/services/spotify.py` (AC: #1, #2, #5)
  - [x] `get_or_create_dynamic_playlist(sp) -> str`: looks up `Config.dynamic_playlist_id`, verifies it exists on Spotify, creates "Recent Adds" (private) if missing, persists new ID to DB
  - [x] `replace_playlist_tracks(playlist_id, track_uris, sp) -> None`: calls `sp.playlist_replace_items()` + `sp.playlist_add_items()` in 100-item batches for >100 tracks

- [x] Task 3: Extend `run_sync()` in `backend/services/sync_engine.py` (AC: #1–#5)
  - [x] Add imports: `from datetime import datetime`, `from models.sync_log import SyncLog`
  - [x] Extract `_write_sync_log(status, track_count, error_message, timestamp)` helper
  - [x] Wrap full pipeline in `try/except Exception`: capture `timestamp` before try, push after slice, write success log, re-raise on failure after writing failure log
  - [x] Change return type to `dict` → `{"status": "success", "track_count": N}` (Story 3.5 router will consume this)

- [x] Task 4: Create `backend/tests/test_story_3_4.py` (AC: #1–#5)
  - [x] `test_get_or_create_uses_stored_id`: Config has `dynamic_playlist_id`, sp.playlist succeeds → stored ID returned, no create called
  - [x] `test_get_or_create_creates_when_no_stored_id`: No stored ID → `sp.user_playlist_create` called, new ID persisted to DB
  - [x] `test_get_or_create_recreates_on_404`: Stored ID but `sp.playlist` raises → new playlist created, new ID persisted
  - [x] `test_replace_tracks_single_batch`: ≤100 URIs → only `playlist_replace_items` called once, no `add_items`
  - [x] `test_replace_tracks_chunked`: 150 URIs → `playlist_replace_items([:100])` + `add_items([100:150])`
  - [x] `test_run_sync_success_writes_log`: happy path, SyncLog row with `status="success"`, `track_count` matches, `error_message=None`
  - [x] `test_run_sync_success_returns_dict`: return value is `{"status": "success", "track_count": N}`
  - [x] `test_run_sync_no_playlists_writes_failure_log`: no `is_included=true` → SyncLog `status="failure"`, `error_message="No playlists selected"`, no Spotify push
  - [x] `test_run_sync_spotify_error_writes_failure_log`: `replace_playlist_tracks` raises → SyncLog `status="failure"`, exception re-raised
  - [x] `test_run_sync_preserves_playlist_on_error`: verify `replace_playlist_tracks` NOT called when exception occurs before push

- [x] Task 5: Run full test suite and confirm no regressions (AC: all)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`
  - [x] Expected: 43 existing tests pass + new tests (min 10) pass, 0 failures — Actual: 53 passed, 0 failures

## Dev Notes

### Scope of This Story

Story 3.4 is **backend-only** and extends `services/sync_engine.py` + `services/spotify.py`. It does NOT include:
- `POST /api/v1/sync/run` HTTP endpoint (Story 3.5)
- `SyncButton` frontend component (Story 3.5)
- `GET /api/v1/sync/logs` endpoint (Story 5.1)
- Any SSE streaming (Story 5.3)

`run_sync()` at end of 3.4: complete push + log pipeline, returns `{"status": "success", "track_count": N}`.

---

### File: `backend/models/config.py` — ADD `dynamic_playlist_id`

```python
from typing import Optional
from sqlmodel import Field, SQLModel


class Config(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    playlist_size: int = Field(default=50)
    cron_expr: Optional[str] = None
    spotify_token_json: Optional[str] = None
    dynamic_playlist_id: Optional[str] = None  # ADD THIS FIELD
```

**CRITICAL — schema migration note:** `SQLModel.metadata.create_all()` uses `checkfirst=True` and does NOT add columns to existing tables. Delete `./data/app.db` locally before testing to force schema recreation. Test fixtures use in-memory SQLite — no action needed for tests.

---

### File: `backend/services/spotify.py` — ADD TWO FUNCTIONS

Add at the bottom of the file:

```python
def get_or_create_dynamic_playlist(sp: Spotify) -> str:
    """Return the Spotify ID of the 'Recent Adds' playlist, creating it if needed."""
    with Session(engine) as session:
        config = session.exec(select(Config)).first()
        stored_id = config.dynamic_playlist_id if config else None

    if stored_id:
        try:
            sp.playlist(stored_id, fields="id")
            return stored_id
        except Exception:
            pass  # Playlist deleted on Spotify — fall through to create

    user_id = sp.me()["id"]
    new_playlist = sp.user_playlist_create(
        user_id, "Recent Adds", public=False, description="Managed by playlist_spotify"
    )
    new_id = new_playlist["id"]

    with Session(engine) as session:
        config = session.exec(select(Config)).first()
        if config:
            config.dynamic_playlist_id = new_id
            session.add(config)
            session.commit()

    return new_id


def replace_playlist_tracks(playlist_id: str, track_uris: list[str], sp: Spotify) -> None:
    """Replace playlist contents with track_uris. Handles >100 tracks via chunking."""
    sp.playlist_replace_items(playlist_id, track_uris[:100])
    for i in range(100, len(track_uris), 100):
        sp.playlist_add_items(playlist_id, track_uris[i : i + 100])
```

**Key decisions:**
- `get_or_create_dynamic_playlist` does NOT search existing playlists by name — stored ID lookup + recreate-if-missing is simpler and avoids name collision issues.
- `replace_playlist_tracks`: `playlist_replace_items` clears the playlist and adds first 100 atomically; subsequent `add_items` calls append the rest. This is the correct Spotify API pattern for bulk replace.
- No manual retry — spotipy handles HTTP 429 (NFR12).

---

### File: `backend/services/sync_engine.py` — REWRITE `run_sync()` + ADD HELPER

Full updated file:

```python
from datetime import datetime

import services.spotify as spotify_service
from sqlmodel import Session, select

from database import engine
from models.config import Config
from models.playlist import Playlist
from models.sync_log import SyncLog


def harvest_tracks(included_playlists: list, sp) -> list[dict]:
    """Fetch all tracks from all included playlists. Returns flat list of {spotify_id, uri, added_at}."""
    all_tracks = []
    for playlist in included_playlists:
        tracks = spotify_service.get_playlist_tracks(playlist.spotify_id, sp)
        all_tracks.extend(tracks)
    return all_tracks


def deduplicate(tracks: list[dict]) -> list[dict]:
    """Keep one entry per spotify_id — the one with the most recent added_at."""
    best: dict[str, dict] = {}
    for track in tracks:
        tid = track["spotify_id"]
        if tid not in best or track["added_at"] > best[tid]["added_at"]:
            best[tid] = track
    return list(best.values())


def sort_and_slice(tracks: list[dict], playlist_size: int) -> list[dict]:
    """Sort by added_at descending, return top playlist_size tracks."""
    sorted_tracks = sorted(tracks, key=lambda t: t["added_at"], reverse=True)
    return sorted_tracks[:playlist_size]


def _write_sync_log(
    status: str,
    track_count: int | None,
    error_message: str | None,
    timestamp: str,
) -> None:
    with Session(engine) as session:
        session.add(
            SyncLog(
                status=status,
                track_count=track_count,
                error_message=error_message,
                timestamp=timestamp,
            )
        )
        session.commit()


def run_sync() -> dict:
    """
    Full sync pipeline: harvest → dedup → sort → slice → push → log.
    Returns {"status": "success", "track_count": N} on success.
    On failure: writes SyncLog with status="failure" and re-raises the exception.
    Existing dynamic playlist is preserved on any error (NFR10).
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        with Session(engine) as session:
            playlists = session.exec(
                select(Playlist).where(Playlist.is_included == True)  # noqa: E712
            ).all()
            if not playlists:
                raise ValueError("No playlists selected")
            config = session.exec(select(Config)).first()
            playlist_size = config.playlist_size if config else 50

        sp = spotify_service.get_authenticated_client()
        raw_tracks = harvest_tracks(playlists, sp)
        deduped = deduplicate(raw_tracks)
        sliced = sort_and_slice(deduped, playlist_size)

        # Push to Spotify — only reached if harvest/dedup/sort succeeded (NFR10)
        target_id = spotify_service.get_or_create_dynamic_playlist(sp)
        track_uris = [t["uri"] for t in sliced]
        spotify_service.replace_playlist_tracks(target_id, track_uris, sp)

        _write_sync_log(
            status="success",
            track_count=len(sliced),
            error_message=None,
            timestamp=timestamp,
        )
        return {"status": "success", "track_count": len(sliced)}

    except Exception as exc:
        _write_sync_log(
            status="failure",
            track_count=None,
            error_message=str(exc),
            timestamp=timestamp,
        )
        raise
```

**Key decisions:**
- `timestamp` captured BEFORE the try block — the log timestamp reflects when the sync was initiated, not when it ended.
- Push happens AFTER full harvest/dedup/sort — if any earlier step fails, `replace_playlist_tracks` is never called, preserving the existing playlist (NFR10).
- Single `except Exception` catches everything: `ValueError("No playlists selected")`, token errors, Spotify API errors. All write a failure log (NFR11).
- Return type changed to `dict` for Story 3.5 router consumption.
- `_write_sync_log` uses its own `Session(engine)` — not the session used for playlist/config queries, which is already closed by this point.

---

### New File: `backend/tests/test_story_3_4.py`

```python
import pytest
from unittest.mock import patch, MagicMock, call
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from models.config import Config
from models.playlist import Playlist
from models.sync_log import SyncLog
import services.sync_engine as sync_engine
import services.spotify as spotify_service_module


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


# ────────────────────────────────────────────────────────────
# Tests for get_or_create_dynamic_playlist
# ────────────────────────────────────────────────────────────

def test_get_or_create_uses_stored_id(session):
    session.add(Config(playlist_size=50, dynamic_playlist_id="existing_id"))
    session.commit()

    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {"id": "existing_id"}

    with patch("services.spotify.engine", session.get_bind()):
        result = spotify_service_module.get_or_create_dynamic_playlist(mock_sp)

    assert result == "existing_id"
    mock_sp.user_playlist_create.assert_not_called()


def test_get_or_create_creates_when_no_stored_id(session):
    session.add(Config(playlist_size=50, dynamic_playlist_id=None))
    session.commit()

    mock_sp = MagicMock()
    mock_sp.me.return_value = {"id": "user123"}
    mock_sp.user_playlist_create.return_value = {"id": "new_playlist_id"}

    with patch("services.spotify.engine", session.get_bind()):
        result = spotify_service_module.get_or_create_dynamic_playlist(mock_sp)

    assert result == "new_playlist_id"
    mock_sp.user_playlist_create.assert_called_once()
    # Verify persisted in DB
    config = session.exec(
        __import__("sqlmodel", fromlist=["select"]).select(Config)
    ).first()
    assert config.dynamic_playlist_id == "new_playlist_id"


def test_get_or_create_recreates_on_invalid_stored_id(session):
    session.add(Config(playlist_size=50, dynamic_playlist_id="stale_id"))
    session.commit()

    mock_sp = MagicMock()
    mock_sp.playlist.side_effect = Exception("404 Not Found")
    mock_sp.me.return_value = {"id": "user123"}
    mock_sp.user_playlist_create.return_value = {"id": "new_id"}

    with patch("services.spotify.engine", session.get_bind()):
        result = spotify_service_module.get_or_create_dynamic_playlist(mock_sp)

    assert result == "new_id"
    mock_sp.user_playlist_create.assert_called_once()


# ────────────────────────────────────────────────────────────
# Tests for replace_playlist_tracks
# ────────────────────────────────────────────────────────────

def test_replace_tracks_single_batch():
    mock_sp = MagicMock()
    uris = [f"spotify:track:{i}" for i in range(50)]
    spotify_service_module.replace_playlist_tracks("pl1", uris, mock_sp)
    mock_sp.playlist_replace_items.assert_called_once_with("pl1", uris)
    mock_sp.playlist_add_items.assert_not_called()


def test_replace_tracks_chunked():
    mock_sp = MagicMock()
    uris = [f"spotify:track:{i}" for i in range(150)]
    spotify_service_module.replace_playlist_tracks("pl1", uris, mock_sp)
    mock_sp.playlist_replace_items.assert_called_once_with("pl1", uris[:100])
    mock_sp.playlist_add_items.assert_called_once_with("pl1", uris[100:150])


# ────────────────────────────────────────────────────────────
# Integration tests for run_sync()
# ────────────────────────────────────────────────────────────

PLAYLIST_A = [
    {"spotify_id": "t1", "uri": "spotify:track:t1", "added_at": "2026-05-10T00:00:00Z"},
    {"spotify_id": "t2", "uri": "spotify:track:t2", "added_at": "2026-05-08T00:00:00Z"},
]


def test_run_sync_success_writes_log(session):
    session.add(Playlist(spotify_id="pl1", name="Mix", is_included=True))
    session.add(Config(playlist_size=2, dynamic_playlist_id="dyn_id"))
    session.commit()

    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", return_value=PLAYLIST_A),
        patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", return_value="dyn_id"),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks"),
    ):
        sync_engine.run_sync()

    from sqlmodel import select as sel
    logs = session.exec(sel(SyncLog)).all()
    assert len(logs) == 1
    assert logs[0].status == "success"
    assert logs[0].track_count == 2
    assert logs[0].error_message is None
    assert logs[0].timestamp.endswith("Z")


def test_run_sync_success_returns_dict(session):
    session.add(Playlist(spotify_id="pl1", name="Mix", is_included=True))
    session.add(Config(playlist_size=50, dynamic_playlist_id="dyn_id"))
    session.commit()

    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", return_value=PLAYLIST_A),
        patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", return_value="dyn_id"),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks"),
    ):
        result = sync_engine.run_sync()

    assert result == {"status": "success", "track_count": 2}


def test_run_sync_no_playlists_writes_failure_log(session):
    # No is_included=True playlists
    session.add(Config(playlist_size=50))
    session.commit()

    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks") as mock_replace,
    ):
        with pytest.raises(ValueError, match="No playlists selected"):
            sync_engine.run_sync()
        mock_replace.assert_not_called()

    from sqlmodel import select as sel
    logs = session.exec(sel(SyncLog)).all()
    assert len(logs) == 1
    assert logs[0].status == "failure"
    assert "No playlists selected" in logs[0].error_message


def test_run_sync_spotify_error_writes_failure_log(session):
    session.add(Playlist(spotify_id="pl1", name="Mix", is_included=True))
    session.add(Config(playlist_size=50, dynamic_playlist_id="dyn_id"))
    session.commit()

    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", return_value=PLAYLIST_A),
        patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", return_value="dyn_id"),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks", side_effect=Exception("Spotify 500")),
    ):
        with pytest.raises(Exception, match="Spotify 500"):
            sync_engine.run_sync()

    from sqlmodel import select as sel
    logs = session.exec(sel(SyncLog)).all()
    assert len(logs) == 1
    assert logs[0].status == "failure"
    assert "Spotify 500" in logs[0].error_message


def test_run_sync_preserves_playlist_on_harvest_error(session):
    session.add(Playlist(spotify_id="pl1", name="Mix", is_included=True))
    session.add(Config(playlist_size=50, dynamic_playlist_id="dyn_id"))
    session.commit()

    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", side_effect=Exception("Token error")),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks") as mock_replace,
    ):
        with pytest.raises(Exception):
            sync_engine.run_sync()

    mock_replace.assert_not_called()  # Playlist untouched (NFR10)
```

---

### Codebase State Entering This Story

| File | State | Action |
|------|-------|--------|
| `backend/models/config.py` | ✅ Exists | MODIFY — add `dynamic_playlist_id` field |
| `backend/services/spotify.py` | ✅ Complete (3.3) | MODIFY — add `get_or_create_dynamic_playlist()`, `replace_playlist_tracks()` |
| `backend/services/sync_engine.py` | ✅ Complete (3.3) | MODIFY — rewrite `run_sync()`, add `_write_sync_log()`, add imports |
| `backend/tests/test_story_3_4.py` | ❌ Missing | CREATE |
| `backend/routers/sync.py` | ❌ Missing | NOT YET — Story 3.5 |
| `backend/main.py` | ✅ No sync router yet | UNCHANGED |
| All other files | ✅ Complete | UNCHANGED |

---

### Mock Pattern — MUST FOLLOW

From stories 3.1–3.3, the established pattern:

```python
# For sync_engine tests touching the DB engine:
patch("services.sync_engine.engine", session.get_bind())

# For spotify.py tests touching the DB engine:
patch("services.spotify.engine", session.get_bind())

# For mocking spotify service functions called from sync_engine:
patch("services.sync_engine.spotify_service.get_authenticated_client", ...)
patch("services.sync_engine.spotify_service.get_playlist_tracks", ...)
patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", ...)
patch("services.sync_engine.spotify_service.replace_playlist_tracks", ...)
```

`_write_sync_log()` is an internal function in `sync_engine.py` — it opens its own `Session(engine)`. Since we patch `services.sync_engine.engine`, the log writes hit the same in-memory DB as the test session. Verify logs by querying `SyncLog` via the test session after `run_sync()` returns or raises.

---

### Architecture Rules — MUST FOLLOW

- **No manual retry loops** — spotipy handles HTTP 429 (NFR12). `replace_playlist_tracks` calls `sp.playlist_replace_items()` and `sp.playlist_add_items()` directly.
- **Business logic in `services/`, never in `routers/`** — all Spotify push logic goes in `spotify.py`, orchestration in `sync_engine.py`.
- **All spotipy calls via `services/spotify.py`** — `sync_engine.py` never imports spotipy directly.
- **Snake_case JSON** — not relevant here (no endpoints), but `SyncLog` fields are snake_case.
- **NFR10**: the push (`replace_playlist_tracks`) is called only after the full harvest/dedup/sort pipeline succeeds. Any exception before the push leaves the playlist intact.
- **NFR11**: every call to `run_sync()` produces a `SyncLog` entry — the `except Exception` branch ensures even "No playlists selected" is logged.

---

### Anti-Patterns to Avoid

- ❌ Writing `SyncLog` before the push and then again after — one write per sync run in success path, one write in failure path.
- ❌ Calling `sp.playlist_clear()` separately before `playlist_replace_items` — `playlist_replace_items` already clears the playlist atomically.
- ❌ Using `sp.playlist_tracks()` — the correct method is `sp.playlist_items()` (already established in 3.3).
- ❌ Searching user playlists by name to find "Recent Adds" — use the stored `Config.dynamic_playlist_id` with fallback to create.
- ❌ Adding a `POST /api/v1/sync/run` endpoint in this story — that is Story 3.5.
- ❌ Writing `timestamp` inside the except block — capture it before the try so both success and failure logs share the same initiation timestamp.
- ❌ Using `datetime.now()` without UTC — use `datetime.utcnow()` for ISO 8601 consistency with existing `added_at` values.

---

### Postman — No Update Required

No new HTTP endpoints in Story 3.4. `POST /api/v1/sync/run` is Story 3.5.

---

### Verification Checklist

```bash
# Run new story tests only
docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_3_4.py -v
# Expected: 10 tests pass

# Run full suite — no regressions
docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v
# Expected: all 43 prior tests + 10 new = 53 total, 0 failures

# TypeScript build check (no frontend changes)
docker exec playlist_spotify-frontend-1 npm run build
# Expected: 0 errors
```

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Fixed regression in `test_story_3_3.py::test_run_sync_returns_sliced_tracks` — test was asserting on a list return value; updated to match new `dict` return contract + added required Spotify push mocks.

### Completion Notes List

- Added `dynamic_playlist_id: Optional[str] = None` to `Config` model; deleted `data/app.db` for schema recreation.
- Added `get_or_create_dynamic_playlist()` and `replace_playlist_tracks()` to `services/spotify.py`.
- Rewrote `run_sync()` in `services/sync_engine.py`: timestamp captured before try, full push pipeline, `_write_sync_log()` helper on both success and failure, returns `{"status": "success", "track_count": N}`.
- Created `backend/tests/test_story_3_4.py` with 10 tests covering all ACs.
- Full suite: 53 passed, 0 failures (43 prior + 10 new).

### File List

- `backend/models/config.py` — added `dynamic_playlist_id` field
- `backend/services/spotify.py` — added `get_or_create_dynamic_playlist()`, `replace_playlist_tracks()`
- `backend/services/sync_engine.py` — rewrote `run_sync()`, added `_write_sync_log()`, added imports
- `backend/tests/test_story_3_4.py` — created (10 tests)
- `backend/tests/test_story_3_3.py` — updated `test_run_sync_returns_sliced_tracks` for new return contract
- `data/app.db` — deleted (schema recreation required)
