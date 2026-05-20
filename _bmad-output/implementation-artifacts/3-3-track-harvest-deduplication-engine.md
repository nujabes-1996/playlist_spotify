# Story 3.3: Track Harvest & Deduplication Engine

Status: review

## Story

As a user,
I want the sync engine to correctly collect and deduplicate tracks from all my selected playlists,
So that each track appears only once with its most recent addition date.

## Acceptance Criteria

1. **Given** `sync_engine.run_sync()` is called, **When** harvesting begins, **Then** tracks are fetched from all playlists where `is_included=true` using paginated Spotify API calls (100 tracks per request).

2. **Given** a track appears in multiple selected playlists with different `added_at` dates, **When** deduplication runs, **Then** only one entry for that `spotify_id` is kept — the one with the most recent `added_at` (FR5).

3. **Given** deduplication is complete, **When** sorting runs, **Then** the tracks are ordered by `added_at` descending (most recent first) (FR6).

4. **Given** sorting is complete, **When** the slice is applied, **Then** only the top N tracks are selected, where N is the configured `playlist_size` (FR7).

5. **Given** a library of 5,000 tracks across selected playlists, **When** the full harvest runs, **Then** it completes within 30 seconds (NFR4).

6. **Given** no playlists are marked `is_included=true`, **When** `run_sync()` is called, **Then** a `ValueError("No playlists selected")` is raised and no Spotify modification is attempted.

## Tasks / Subtasks

- [x] Task 1: Add `get_playlist_tracks(playlist_id, sp)` to `backend/services/spotify.py` (AC: #1)
  - [x] Paginated fetch via `sp.playlist_items()` with `limit=100`
  - [x] Filter out local tracks (track or track.id can be None for local files)
  - [x] Return `[{spotify_id, uri, added_at}]`

- [x] Task 2: Create `backend/services/sync_engine.py` with harvest/dedup/sort logic (AC: #1–#6)
  - [x] `harvest_tracks(included_playlists, sp)` — collects all tracks from each playlist, returns flat list
  - [x] `deduplicate(tracks)` — dict keyed by `spotify_id`, keep entry with latest `added_at`
  - [x] `sort_and_slice(tracks, playlist_size)` — sort by `added_at` desc, return top N
  - [x] `run_sync()` — orchestrates: reads DB, validates, calls harvest → dedup → sort → returns sliced track list (push/logging added in Story 3.4)

- [x] Task 3: Create `backend/tests/test_story_3_3.py` with unit tests for sync engine logic (AC: #1–#6)
  - [x] `test_harvest_collects_all_tracks`: mock `get_playlist_tracks`, verify all tracks from all playlists are returned
  - [x] `test_dedup_keeps_latest_added_at`: same `spotify_id` in two playlists → most recent `added_at` wins
  - [x] `test_dedup_no_collision`: tracks from different playlists with different IDs → no tracks lost
  - [x] `test_sort_and_slice_order`: sorted descending by `added_at`, top N returned
  - [x] `test_sort_and_slice_respects_playlist_size`: 10 tracks, `playlist_size=5` → 5 returned
  - [x] `test_run_sync_no_playlists_raises`: no `is_included=true` playlists → `ValueError("No playlists selected")`
  - [x] `test_run_sync_returns_sliced_tracks`: happy path with mocked spotify and seeded DB

- [x] Task 4: Run full test suite and confirm no regressions (AC: all)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`

## Dev Notes

### Scope of This Story

Story 3.3 is **backend-only** and implements the **harvest → dedup → sort → slice** pipeline in `services/sync_engine.py`. It does NOT include:
- Spotify playlist push/replace (Story 3.4)
- SyncLog DB writes (Story 3.4)
- `POST /api/v1/sync/run` endpoint (Story 3.5)
- Frontend SyncButton (Story 3.5)

`run_sync()` returns the sliced track list for now. Story 3.4 will extend it to push to Spotify and write a `SyncLog`.

---

### New File: `backend/services/sync_engine.py`

```python
import services.spotify as spotify_service
from sqlmodel import Session, select
from database import engine
from models.config import Config
from models.playlist import Playlist


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


def run_sync() -> list[dict]:
    """
    Orchestrates: harvest → dedup → sort → slice.
    Returns the sliced track list.
    Raises ValueError("No playlists selected") if none are included.
    Story 3.4 extends this function to push to Spotify and write a SyncLog.
    """
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
    return sort_and_slice(deduped, playlist_size)
```

**Key decisions:**
- Import `services.spotify as spotify_service` (module-level import) so tests can mock `services.sync_engine.spotify_service.get_playlist_tracks` and `services.sync_engine.spotify_service.get_authenticated_client` at the right location.
- ISO 8601 string comparison (`"2026-05-19T10:00:00Z" > "2026-05-01T00:00:00Z"`) works correctly for dedup and sort — no `datetime.fromisoformat()` needed.
- No retry loops — spotipy handles HTTP 429 backoff automatically (NFR12).

---

### Modification: `backend/services/spotify.py`

Add this function at the bottom of the file:

```python
def get_playlist_tracks(playlist_id: str, sp: Spotify = None) -> list[dict]:
    """Fetch all tracks from a playlist, paginated (100/page). Returns [{spotify_id, uri, added_at}]."""
    if sp is None:
        sp = get_authenticated_client()
    results = []
    offset = 0
    limit = 100
    while True:
        page = sp.playlist_items(
            playlist_id,
            limit=limit,
            offset=offset,
            fields="items(track(id,uri),added_at),next",
        )
        for item in page["items"]:
            track = item.get("track")
            if track and track.get("id"):  # skip local tracks (id is None)
                results.append({
                    "spotify_id": track["id"],
                    "uri": track["uri"],
                    "added_at": item["added_at"],
                })
        if page["next"] is None:
            break
        offset += limit
    return results
```

**Why `sp` parameter:** `sync_engine` calls `get_authenticated_client()` once and passes `sp` to avoid creating a new OAuth session for every playlist (performance, and single token validation for the full harvest).

---

### New File: `backend/tests/test_story_3_3.py`

```python
import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from models.playlist import Playlist
from models.config import Config
import services.sync_engine as sync_engine


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


PLAYLIST_A = [
    {"spotify_id": "t1", "uri": "spotify:track:t1", "added_at": "2026-05-10T00:00:00Z"},
    {"spotify_id": "t2", "uri": "spotify:track:t2", "added_at": "2026-05-08T00:00:00Z"},
]
PLAYLIST_B = [
    {"spotify_id": "t1", "uri": "spotify:track:t1", "added_at": "2026-05-15T00:00:00Z"},  # t1 newer here
    {"spotify_id": "t3", "uri": "spotify:track:t3", "added_at": "2026-05-01T00:00:00Z"},
]


# --- Unit tests for pure functions ---

def test_dedup_keeps_latest_added_at():
    tracks = PLAYLIST_A + PLAYLIST_B  # t1 appears twice
    result = sync_engine.deduplicate(tracks)
    by_id = {t["spotify_id"]: t for t in result}
    assert by_id["t1"]["added_at"] == "2026-05-15T00:00:00Z"  # latest wins
    assert len(result) == 3  # t1, t2, t3


def test_dedup_no_collision():
    tracks = [
        {"spotify_id": "a", "uri": "spotify:track:a", "added_at": "2026-05-01T00:00:00Z"},
        {"spotify_id": "b", "uri": "spotify:track:b", "added_at": "2026-05-02T00:00:00Z"},
    ]
    result = sync_engine.deduplicate(tracks)
    assert len(result) == 2


def test_sort_and_slice_order():
    tracks = [
        {"spotify_id": "a", "uri": "u", "added_at": "2026-05-01T00:00:00Z"},
        {"spotify_id": "b", "uri": "u", "added_at": "2026-05-10T00:00:00Z"},
        {"spotify_id": "c", "uri": "u", "added_at": "2026-05-05T00:00:00Z"},
    ]
    result = sync_engine.sort_and_slice(tracks, 10)
    assert result[0]["spotify_id"] == "b"
    assert result[1]["spotify_id"] == "c"
    assert result[2]["spotify_id"] == "a"


def test_sort_and_slice_respects_playlist_size():
    tracks = [
        {"spotify_id": str(i), "uri": "u", "added_at": f"2026-05-{i:02d}T00:00:00Z"}
        for i in range(1, 11)
    ]
    result = sync_engine.sort_and_slice(tracks, 5)
    assert len(result) == 5


def test_harvest_collects_all_tracks():
    mock_playlists = [
        MagicMock(spotify_id="pl1"),
        MagicMock(spotify_id="pl2"),
    ]
    side_effects = [PLAYLIST_A, PLAYLIST_B]
    with patch("services.sync_engine.spotify_service.get_playlist_tracks", side_effect=side_effects):
        result = sync_engine.harvest_tracks(mock_playlists, sp=MagicMock())
    assert len(result) == 4  # 2 + 2, duplicates NOT yet removed


# --- Integration tests for run_sync ---

def test_run_sync_no_playlists_raises(session):
    # No is_included=true playlists in DB
    with patch("services.sync_engine.engine", session.get_bind()):
        with pytest.raises(ValueError, match="No playlists selected"):
            sync_engine.run_sync()


def test_run_sync_returns_sliced_tracks(session):
    session.add(Playlist(spotify_id="pl1", name="Mix", is_included=True))
    session.add(Playlist(spotify_id="pl2", name="Chill", is_included=True))
    session.add(Config(playlist_size=2))
    session.commit()

    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", side_effect=[PLAYLIST_A, PLAYLIST_B]),
    ):
        result = sync_engine.run_sync()

    assert len(result) == 2  # playlist_size=2
    assert result[0]["added_at"] >= result[1]["added_at"]  # sorted descending
```

---

### Codebase State Entering This Story

| File | State | Action |
|------|-------|--------|
| `backend/services/spotify.py` | ✅ Complete (Stories 2.2, 3.1) | MODIFY — add `get_playlist_tracks()` |
| `backend/services/sync_engine.py` | ❌ Missing | CREATE |
| `backend/tests/test_story_3_3.py` | ❌ Missing | CREATE |
| `backend/routers/sync.py` | ❌ Missing | NOT YET (Story 3.5) |
| `backend/main.py` | ✅ Complete | UNCHANGED |
| All other files | ✅ Complete | UNCHANGED |

---

### Established Patterns — MUST FOLLOW

**Mock pattern from Stories 2.4, 3.1, 3.2:**
- Fixture: in-memory SQLite via `StaticPool`, `app.dependency_overrides[get_session]` for router tests
- For `sync_engine` unit tests: no FastAPI client needed — test functions directly
- `patch` target uses the **import site** in the tested module: `"services.sync_engine.spotify_service.get_playlist_tracks"`

**Architecture rules:**
- Business logic in `services/`, never in `routers/`
- All spotipy calls go through `services/spotify.py` — never import spotipy directly in `sync_engine.py`
- No camelCase in JSON, no wrapper objects
- No manual retry loops — spotipy handles HTTP 429 (NFR12)

---

### Anti-Patterns to Avoid

- ❌ Creating a `POST /api/v1/sync/run` endpoint in this story — that's Story 3.5
- ❌ Writing to `SyncLog` table in `run_sync()` — that's Story 3.4
- ❌ Calling `sp.playlist_tracks()` instead of `sp.playlist_items()` — `playlist_items()` is the correct current spotipy method
- ❌ Importing spotipy directly in `sync_engine.py` — always via `services.spotify`
- ❌ Using `datetime.fromisoformat()` for comparison — ISO 8601 strings compare lexicographically correctly
- ❌ Fetching 50 tracks per page — the correct limit for `playlist_items` is 100 (Spotify's maximum per page)
- ❌ Storing `is_included` state for excluded playlists — query `Playlist.is_included == True` with `==`, not `is_(True)`, to avoid SQLModel comparison warning (use `# noqa: E712` as shown)

---

### Postman — No Update Required

No new HTTP endpoints in this story. `POST /api/v1/sync/run` is Story 3.5.

---

### Verification Checklist

```bash
# Run new tests
docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_3_3.py -v
# Expected: 7 tests pass

# Run full suite (no regressions)
docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v
# Expected: all previous tests still pass (was 36 after story 3.2)

# TypeScript build (no frontend changes)
docker exec playlist_spotify-frontend-1 npm run build
# Expected: 0 errors
```

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Ajout de `get_playlist_tracks(playlist_id, sp)` dans `services/spotify.py` : pagination 100 tracks/page via `sp.playlist_items()`, filtre les tracks locaux (id=None), retourne `[{spotify_id, uri, added_at}]`.
- Création de `services/sync_engine.py` avec 4 fonctions : `harvest_tracks()`, `deduplicate()`, `sort_and_slice()`, `run_sync()`. Le moteur orchestre harvest → dedup → sort → slice. Push Spotify et SyncLog sont délibérément hors scope (Story 3.4). `run_sync()` lève `ValueError("No playlists selected")` si aucune playlist n'est incluse.
- Comparaison ISO 8601 en string pour la déduplication et le tri : fonctionne correctement sans `datetime.fromisoformat()`.
- Import module-level `import services.spotify as spotify_service` pour permettre le mock ciblé dans les tests.
- 7 nouveaux tests dans `test_story_3_3.py` : 5 tests unitaires des fonctions pures + 2 tests d'intégration de `run_sync()` avec patch de l'engine SQLite.
- Suite complète : **43/43 tests passent**, 0 régressions.

### File List

- `backend/services/spotify.py` — MODIFIED (ajout de `get_playlist_tracks()`)
- `backend/services/sync_engine.py` — NEW
- `backend/tests/test_story_3_3.py` — NEW (7 tests)

### Change Log

- 2026-05-19: Story 3.3 implémentée — `sync_engine.py` créé (harvest/dedup/sort/slice), `get_playlist_tracks()` ajouté dans `spotify.py`, 7 tests unitaires + intégration ajoutés, 43/43 suite verte, 0 régressions.
