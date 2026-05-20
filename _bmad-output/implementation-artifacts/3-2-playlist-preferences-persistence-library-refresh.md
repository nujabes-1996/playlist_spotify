# Story 3.2: Playlist Preferences Persistence & Library Refresh

Status: review

## Story

As a user,
I want my playlist selections to be remembered and new playlists to appear automatically,
So that I never have to reconfigure after adding music or restarting the app.

## Acceptance Criteria

1. **Given** I have toggled several playlists and the Docker container is restarted, **When** I navigate to the dashboard, **Then** all `is_included` preferences are identical to what I set before the restart (FR12).

2. **Given** I create a new playlist on Spotify, **When** I reload the dashboard (triggering `GET /api/v1/playlists`), **Then** the new playlist appears in the list with `is_included: false` by default (FR13).

3. **Given** I delete a playlist from my Spotify library, **When** `GET /api/v1/playlists` is called, **Then** the deleted playlist no longer appears in the returned list.

4. **Given** a playlist was previously included (`is_included: true`) and is then deleted from Spotify, **When** `GET /api/v1/playlists` is called, **Then** it is removed from the DB and does not appear in the list.

## Tasks / Subtasks

- [x] Task 1: Create `backend/tests/test_story_3_2.py` with targeted persistence and library-refresh tests (AC: #1, #2, #3, #4)
  - [x] `test_is_included_preserved_on_repeated_get`: add playlist with `is_included=True`, call `GET /api/v1/playlists` with same Spotify data → `is_included` stays `True` (verifies upsert never resets it)
  - [x] `test_new_playlist_appears_with_false_default`: DB has one playlist; Spotify returns the original plus a brand-new one → the new one is in the response with `is_included=False`
  - [x] `test_removed_playlist_not_in_list`: Spotify no longer returns a playlist that existed in DB with `is_included=False` → absent from response
  - [x] `test_included_playlist_removed_when_deleted_from_spotify`: playlist with `is_included=True` disappears from Spotify → removed from DB, not in response (AC4 explicit)

- [x] Task 2: Run the full test suite and confirm no regressions (AC: all)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`
  - [x] All previous tests (story 2.4, 3.1, etc.) still pass

- [x] Task 3: TypeScript build check (AC: all — no frontend changes expected, but confirm)
  - [x] `docker exec playlist_spotify-frontend-1 npm run build`

## Dev Notes

### Critical Insight: No New Backend Code Required

**All four ACs are already satisfied by the implementation from Story 3.1.** The `GET /api/v1/playlists` endpoint in `backend/routers/playlists.py` already:

1. **Preserves `is_included` on upsert** — when a playlist already exists in the DB, only `name` is updated, never `is_included`:
   ```python
   if existing:
       existing.name = p["name"]   # is_included untouched ✅
   else:
       session.add(Playlist(spotify_id=p["spotify_id"], name=p["name"]))  # is_included=False (default) ✅
   ```

2. **Deletes removed playlists regardless of their `is_included` state**:
   ```python
   for db_p in db_playlists:
       if db_p.spotify_id not in spotify_ids:
           session.delete(db_p)   # Works whether is_included=True or False ✅
   ```

3. **Persistence across restarts** is provided by the SQLite host bind mount (`./data/app.db` in `docker-compose.yml`) — container restarts do not touch the file.

4. **Frontend refresh** works automatically: `usePlaylists()` uses `useQuery` with key `['playlists']`, which refetches on component mount — navigating to the dashboard always calls `GET /api/v1/playlists`.

**Story 3.2's only deliverable is targeted tests** that explicitly verify and document these behaviors. This guards against future regressions (e.g., someone accidentally adding `is_included: false` to the upsert branch).

---

### Codebase State Entering This Story

| File | State | Action |
|------|-------|--------|
| `backend/routers/playlists.py` | ✅ Complete (Story 3.1) | UNCHANGED |
| `backend/services/spotify.py` | ✅ Complete (Story 3.1) | UNCHANGED |
| `backend/tests/test_story_3_1.py` | ✅ 6 tests passing | UNCHANGED |
| `backend/tests/test_story_3_2.py` | ❌ Missing | CREATE |
| `frontend/src/features/playlists/PlaylistList.tsx` | ✅ Complete (Story 3.1) | UNCHANGED |
| `frontend/src/hooks/usePlaylists.ts` | ✅ Complete (Story 3.1) | UNCHANGED |

---

### Backend Tests: `test_story_3_2.py` — Full Implementation

Create `backend/tests/test_story_3_2.py`:

```python
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from models.playlist import Playlist


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


SPOTIFY_PLAYLISTS = [
    {"spotify_id": "abc", "name": "My Mix"},
    {"spotify_id": "def", "name": "Chill Vibes"},
]


def test_is_included_preserved_on_repeated_get(client, session):
    """AC1 — Upsert must never reset is_included for existing playlists."""
    # Pre-populate: user toggled "abc" to included
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=True))
    session.add(Playlist(spotify_id="def", name="Chill Vibes", is_included=False))
    session.commit()

    # Simulate page reload: Spotify returns same playlists
    with patch("routers.playlists.spotify_service.get_user_playlists", return_value=SPOTIFY_PLAYLISTS):
        r = client.get("/api/v1/playlists")

    assert r.status_code == 200
    data = {p["spotify_id"]: p for p in r.json()}
    assert data["abc"]["is_included"] is True   # must still be True
    assert data["def"]["is_included"] is False


def test_new_playlist_appears_with_false_default(client, session):
    """AC2 — New Spotify playlist (not yet in DB) appears with is_included=False."""
    # Only "abc" is known to the DB
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=True))
    session.commit()

    # Spotify now returns "abc" plus a brand-new playlist "xyz"
    spotify_with_new = SPOTIFY_PLAYLISTS + [{"spotify_id": "xyz", "name": "New Finds"}]
    with patch("routers.playlists.spotify_service.get_user_playlists", return_value=spotify_with_new):
        r = client.get("/api/v1/playlists")

    assert r.status_code == 200
    data = {p["spotify_id"]: p for p in r.json()}
    assert "xyz" in data
    assert data["xyz"]["is_included"] is False   # default for new playlists
    assert data["abc"]["is_included"] is True     # existing preference preserved


def test_removed_playlist_not_in_list(client, session):
    """AC3 — Playlist deleted from Spotify (is_included=False) is removed from the response."""
    session.add(Playlist(spotify_id="gone", name="Removed", is_included=False))
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=False))
    session.commit()

    # Spotify no longer returns "gone"
    with patch("routers.playlists.spotify_service.get_user_playlists", return_value=[SPOTIFY_PLAYLISTS[0]]):
        r = client.get("/api/v1/playlists")

    assert r.status_code == 200
    ids = [p["spotify_id"] for p in r.json()]
    assert "gone" not in ids
    assert "abc" in ids


def test_included_playlist_removed_when_deleted_from_spotify(client, session):
    """AC4 — Previously included playlist (is_included=True) deleted from Spotify is removed from DB."""
    session.add(Playlist(spotify_id="was_included", name="Fave Mix", is_included=True))
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=False))
    session.commit()

    # Spotify no longer returns "was_included"
    with patch("routers.playlists.spotify_service.get_user_playlists", return_value=[SPOTIFY_PLAYLISTS[0]]):
        r = client.get("/api/v1/playlists")

    assert r.status_code == 200
    ids = [p["spotify_id"] for p in r.json()]
    assert "was_included" not in ids   # removed even though it was included
    assert "abc" in ids
```

---

### Fixture Pattern (identical to Story 3.1 and 2.4)

The test fixture uses:
- **In-memory SQLite** (`sqlite://`) via `StaticPool` — no shared state between tests
- `app.dependency_overrides[get_session]` — replaces the real DB session with the test session
- `patch("routers.playlists.spotify_service.get_user_playlists", ...)` — mocks at import site in router module

This is the established project pattern. Do not deviate from it (see `test_story_3_1.py` and `test_story_2_4.py`).

---

### Architecture Constraints — MUST FOLLOW

- **Business logic in services/** — `routers/playlists.py` delegates Spotify calls to `spotify_service`; never call spotipy directly in routers
- **No camelCase in JSON** — all fields snake_case (`spotify_id`, `is_included`)
- **No wrapper** — response is a plain array `[...]`
- **TanStack Query** — `['playlists']` key; `isPending` (not `isLoading`) in v5

---

### Anti-Patterns to Avoid

- ❌ Modifying `routers/playlists.py` — the upsert logic is correct; do NOT add `is_included` to the existing branch update
- ❌ Adding a new `GET /api/v1/playlists/refresh` endpoint — the existing GET already fetches fresh data from Spotify on every call; a separate refresh endpoint would be redundant
- ❌ Adding `refetchInterval` to the frontend TanStack Query hook — polling is unnecessary; refetch on page mount is sufficient
- ❌ Duplicating test fixtures — use the same `session_fixture` + `client_fixture` pattern as 3.1

---

### Why No Frontend Changes

The frontend `usePlaylists()` hook uses `useQuery` without `staleTime`, so TanStack Query considers data stale immediately after fetching. When the user navigates to the dashboard (component mounts), the query refetches automatically — this is the "reload the dashboard" behavior described in AC2/AC3/AC4. No additional UI or hook changes are needed.

---

### Verification Checklist

```bash
# Run new tests
docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_3_2.py -v
# Expected: 4 tests pass

# Run full suite (no regressions)
docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v
# Expected: all tests pass (was 32 after story 3.1)

# TypeScript build (no frontend changes, but confirm)
docker exec playlist_spotify-frontend-1 npm run build
# Expected: 0 errors
```

---

### Postman — No Update Required

No new endpoints or response shape changes. `GET /api/v1/playlists` and `PATCH /api/v1/playlists/{spotify_id}` are unchanged. The Postman collection already documents them from Story 3.1.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Confirmed that all 4 ACs were already satisfied by Story 3.1's implementation: upsert in `GET /api/v1/playlists` only updates `name` (never `is_included`), delete logic removes playlists absent from Spotify regardless of `is_included`, and SQLite host mount preserves data across Docker restarts.
- Created `backend/tests/test_story_3_2.py` with 4 targeted tests (one per AC): `test_is_included_preserved_on_repeated_get`, `test_new_playlist_appears_with_false_default`, `test_removed_playlist_not_in_list`, `test_included_playlist_removed_when_deleted_from_spotify`.
- Full test suite: 36/36 passed (4 new + 32 existing, 0 regressions).
- TypeScript build: 0 errors (no frontend changes required).

### File List

- `backend/tests/test_story_3_2.py` — NEW (4 tests covering ACs 1–4)

### Change Log

- 2026-05-19: Story 3.2 implemented — 4 backend persistence/library-refresh tests added, 36/36 suite green, TS build clean. No backend or frontend code changes required (logic already in place from Story 3.1).
