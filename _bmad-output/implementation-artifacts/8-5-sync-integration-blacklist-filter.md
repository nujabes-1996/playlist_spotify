# Story 8.5: Sync Integration — Blacklist Filter

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want the next sync to actually remove blacklisted tracks from my Spotify playlist and never let them come back,
so that the blacklist is meaningful — not just a UI state.

## Acceptance Criteria

1. **Given** the sync pipeline in [`backend/services/sync_engine.py`](../../backend/services/sync_engine.py), **When** `run_sync()` executes, **Then** after deduplication and **BEFORE** `sort_and_slice()` applies the `playlist_size` top-N cut, the candidate track list is filtered to exclude every track whose `spotify_id` is present in the `track_blacklist` table (FR34). Order of operations: harvest → dedup → **blacklist filter** → sort → slice → push. [Source: epics.md#Story-8.5 AC #1 + FR34 + services/sync_engine.py:57-95]

2. **Given** a track was previously in the dynamic Spotify playlist AND its `spotify_id` is in `track_blacklist`, **When** the next sync runs successfully, **Then** the track is absent from the final `track_uris` list passed to `spotify_service.replace_playlist_tracks()` (FR35) — so the user's dynamic playlist on Spotify no longer contains it after the sync. [Source: epics.md#Story-8.5 AC #2 + FR35]

3. **Given** `track_blacklist` is empty, **When** `run_sync()` runs, **Then** behavior is byte-identical to the pre-8.5 engine — same harvest, same dedup, same sort, same slice, same `replace_playlist_tracks` call, same `SyncLog` row shape (`status`, `track_count`, `new_track_count`, `error_message`, `timestamp`). Verify by ensuring all existing `test_story_3_3.py`, `test_story_3_4.py`, and Epic 4/5 sync tests still pass without modification. [Source: epics.md#Story-8.5 AC #3 + no-regression invariant]

4. **Given** the blacklist filter shrinks the candidate pool below `playlist_size` (e.g., 200 candidates, 250 blacklisted matches across the harvest, leaves <playlist_size), **When** `sort_and_slice()` runs, **Then** the final list simply contains fewer tracks — **no `ValueError`, no log entry escalation, no fallback re-harvest**. The slice operator on a shorter list naturally yields the shorter list; no extra branching required. [Source: epics.md#Story-8.5 AC #4 + Python slice semantics]

5. **Given** the delta-sync incremental code path (`last_sync_at` set in `Config`), **When** `run_sync()` merges `new_tracks + existing_tracks` and then dedups, **Then** the blacklist filter runs on the **merged + deduped** list — this guarantees that previously-added tracks already on the dynamic playlist are ALSO filtered out (not only newly-harvested ones). Otherwise a track blacklisted between syncs would persist on Spotify until a full re-harvest. [Source: services/sync_engine.py:83-89 (delta path) + Story 8.4 user expectation: "Will be removed from your Spotify playlist on the next sync"]

6. **Given** a previously-blacklisted track is removed from the blacklist via `DELETE /api/v1/blacklist/{spotify_id}` (Story 8.1, [`backend/routers/blacklist.py:57-65`](../../backend/routers/blacklist.py)), **When** the next sync runs and that track is harvested from a source playlist and would qualify for the top-N slice, **Then** it is restored to the dynamic playlist (no permanent "ever-blacklisted" memory — only current rows in `track_blacklist` are enforced). The filter must read the blacklist fresh on each `run_sync()` invocation. [Source: epics.md#Story-8.5 AC #6 + FR34/35 + Story 8.1 idempotent DELETE]

7. **Given** the project convention `Business logic dans services/, jamais dans routers/` (CLAUDE.md#Backend), **When** the blacklist filter is implemented, **Then** a new pure helper `get_blacklisted_ids(session: Session) -> set[str]` is added to a service module (NEW file [`backend/services/blacklist_service.py`](../../backend/services/blacklist_service.py)) that returns `{row.spotify_id for row in session.exec(select(TrackBlacklist)).all()}`. The helper takes a `Session` (do NOT open a new one inside — `run_sync()` already manages session lifecycle). [Source: CLAUDE.md#Backend + Story 8.1 AC #10 explicit deferral: "Story 8.5 will add a get_blacklisted_ids() -> set[str] helper in services/ when it needs one"]

8. **Given** the helper is consumed by `run_sync()`, **When** the filter is wired, **Then** inside the **first** `with Session(engine) as session:` block at [`sync_engine.py:68-77`](../../backend/services/sync_engine.py) (where `playlists` and `config` are already loaded), the blacklist set is fetched in the same session: `blacklisted_ids = blacklist_service.get_blacklisted_ids(session)`. This avoids opening a second session for one trivial query. Pass `blacklisted_ids` (a `set[str]`) down to the filter step. [Source: services/sync_engine.py:67-77 existing session usage pattern]

9. **Given** the filter step itself, **When** placed in the pipeline, **Then** it is implemented inline in `run_sync()` (not as a new top-level function — YAGNI per the project's "no premature abstraction" pattern from Story 7.5 / Story 8.1 AC #10) as: `filtered = [t for t in deduped if t["spotify_id"] not in blacklisted_ids]`, immediately after `deduped = deduplicate(raw_tracks)` and before `sliced = sort_and_slice(filtered, playlist_size)`. Update the `sort_and_slice` call argument from `deduped` to `filtered`. [Source: services/sync_engine.py:89-90 + project YAGNI pattern]

10. **Given** the `new_track_count` calculation at [`sync_engine.py:91`](../../backend/services/sync_engine.py) (`sum(1 for t in sliced if t["spotify_id"] not in existing_ids)`), **When** the filter is added, **Then** the calculation is unchanged — it operates on `sliced` (already blacklist-filtered) and `existing_ids` (the previous dynamic playlist contents). The semantics remain: "how many of the tracks we're about to push were not on the playlist before". A blacklisted track that was on the playlist before will NOT appear in `sliced`, so it does NOT count as "new" — and the playlist's track count will reflect its removal correctly via `len(sliced)`. [Source: services/sync_engine.py:91 logic preservation]

11. **Given** a new test file [`backend/tests/test_story_8_5.py`](../../backend/tests/test_story_8_5.py), **When** `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_8_5.py -v` is run, **Then** all of the following cases pass:
    - **(a)** `get_blacklisted_ids` on empty table returns `set()`.
    - **(b)** `get_blacklisted_ids` on populated table returns the exact set of `spotify_id` values.
    - **(c)** `run_sync()` with an empty blacklist produces the same `sliced` track URIs as a baseline run (regression guard for AC #3).
    - **(d)** `run_sync()` with one blacklisted `spotify_id` matching a harvested track excludes that track from the URIs passed to `replace_playlist_tracks` (AC #1, #2).
    - **(e)** `run_sync()` where blacklist filtering reduces candidates below `playlist_size` completes successfully (status="success") with `track_count` < `playlist_size` — no error raised (AC #4).
    - **(f)** Delta path: with `Config.last_sync_at` set + harvested `new_tracks` + existing playlist tracks that include a blacklisted ID, the blacklisted ID is excluded from the final URIs (AC #5).
    - **(g)** A blacklist entry deleted (`session.delete`) between two `run_sync()` calls causes the second sync to **include** the previously-blocked track (AC #6).
    Use the same fixture pattern as [`tests/test_story_3_4.py:13-21`](../../backend/tests/test_story_3_4.py) (in-memory SQLite + `patch("services.sync_engine.engine", session.get_bind())` + `patch("services.sync_engine.spotify_service.*", ...)`). [Source: CLAUDE.md#Tests + test_story_3_4.py reference pattern]

12. **Given** the regression invariant in AC #3, **When** the full test suite runs (`docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`), **Then** all 108+ existing tests still pass with zero modifications to their fixtures or assertions — including `test_story_3_3.py`, `test_story_3_4.py`, `test_story_3_5.py`, `test_story_4_1.py`, `test_story_4_2.py`, `test_story_5_1.py`, `test_story_5_2.py`, `test_story_5_3.py`. The new file adds tests; it does not modify any existing one. [Source: CLAUDE.md#Tests + no-regression invariant]

13. **Given** the Postman collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`), **When** Story 8.5 ships, **Then** **NO Postman update is required** — this story is internal to the sync engine; no HTTP route is added, removed, or modified. The existing `POST /sync`, `GET /sync-logs`, `GET /blacklist`, `POST /blacklist`, `DELETE /blacklist/{id}` requests are unchanged. Verify by GETting the collection: confirm the "Blacklist" and "Sync" folders are intact; do NOT issue a PUT. [Source: CLAUDE.md#Postman + memory `feedback_postman_sync` ("modifie une API" — no API surface change here)]

14. **Given** the frontend, **When** Story 8.5 ships, **Then** **NO frontend code change is required** — `useRecentlyAdded` and `useBlacklistTrack` from Story 8.4 continue to work unchanged. The optimistic UI already promises "Will be removed from your Spotify playlist on the next sync" — Story 8.5 fulfills that promise without any UI rewiring. [Source: 8-4-per-track-blacklist-action.md Dev Notes + epic 8 scope]

15. **Given** structured concurrency concerns, **When** the blacklist set is captured at the start of `run_sync()`, **Then** a snapshot of the blacklist taken inside the first session is **acceptable** even if a user blacklists more tracks mid-sync — the next scheduled or manual sync will catch them. Do NOT add session re-reads or locks. The blacklist is eventually consistent across syncs. [Source: services/sync_engine.py session usage pattern + APScheduler single-shot per-job semantics]

16. **Given** the sync engine never raises on a normal blacklist filter operation, **When** an unexpected exception happens (e.g., `select(TrackBlacklist)` somehow fails — disk full, DB locked), **Then** the existing `except Exception` block at [`sync_engine.py:112-120`](../../backend/services/sync_engine.py) catches it, writes a failure `SyncLog`, and re-raises — same behavior as any other sync error. Do NOT add a dedicated try/except around the helper. The blacklist read is just another SQLModel query inside the existing session. [Source: services/sync_engine.py:112-120 existing error handling]

17. **Given** `services/blacklist_service.py` is new, **When** it is imported in `sync_engine.py`, **Then** the import line follows the same style as the existing `import services.spotify as spotify_service` at [`sync_engine.py:3`](../../backend/services/sync_engine.py): use `import services.blacklist_service as blacklist_service`. [Source: services/sync_engine.py:3 import style + project convention]

## Tasks / Subtasks

- [x] **Task 1: Create the blacklist service helper** (AC: #7, #11(a)(b), #17)
  - [x] Create new file [`backend/services/blacklist_service.py`](../../backend/services/blacklist_service.py) with the following content (minimal, single-purpose):
    ```python
    from sqlmodel import Session, select

    from models.track_blacklist import TrackBlacklist


    def get_blacklisted_ids(session: Session) -> set[str]:
        """Return the current set of blacklisted spotify_ids.

        Caller owns the Session — do NOT open a new one here.
        Sync engine consumes this once per run_sync() invocation.
        """
        rows = session.exec(select(TrackBlacklist)).all()
        return {row.spotify_id for row in rows}
    ```
  - [x] Do NOT add a setter, a "blacklist a track" helper, or any caching. The single read-only getter is the entire public surface (per AC #7).

- [x] **Task 2: Wire the filter into `run_sync()`** (AC: #1, #5, #8, #9, #10, #17)
  - [x] In [`backend/services/sync_engine.py`](../../backend/services/sync_engine.py):
    - Add import (near line 3, alongside `import services.spotify as spotify_service`):
      ```python
      import services.blacklist_service as blacklist_service
      ```
    - Inside the first `with Session(engine) as session:` block (currently lines 68-77), after loading `playlists` and `config`, fetch the blacklist snapshot in the same session:
      ```python
      blacklisted_ids = blacklist_service.get_blacklisted_ids(session)
      ```
      Make sure this line is **inside** the `with` block (the session must be open when the query runs).
    - Between `deduped = deduplicate(raw_tracks)` and `sliced = sort_and_slice(deduped, playlist_size)` (currently lines 89-90), insert the filter step:
      ```python
      filtered = [t for t in deduped if t["spotify_id"] not in blacklisted_ids]
      sliced = sort_and_slice(filtered, playlist_size)
      ```
      Replace the `deduped` argument in the `sort_and_slice` call with `filtered`.
  - [x] Verify visually that the order is **harvest → dedup → blacklist filter → sort → slice → push**. Do NOT filter before dedup (wasteful) or after slice (would re-introduce the order-dependence bug — a blacklisted track in the top-N would shrink the result silently regardless, but filtering pre-slice keeps semantics aligned with FR34 "persistently excludes from all future syncs").
  - [x] Do NOT modify `harvest_tracks`, `deduplicate`, `sort_and_slice`, `_write_sync_log`, or any of the existing top-level helpers. The filter is inline (per AC #9 YAGNI).

- [x] **Task 3: Add tests in `tests/test_story_8_5.py`** (AC: #11)
  - [x] Create new file [`backend/tests/test_story_8_5.py`](../../backend/tests/test_story_8_5.py) using the **exact same fixture pattern** as [`tests/test_story_3_4.py:13-21`](../../backend/tests/test_story_3_4.py):
    ```python
    import pytest
    from unittest.mock import patch, MagicMock
    from sqlmodel import SQLModel, Session, create_engine, select
    from sqlmodel.pool import StaticPool

    from models.config import Config
    from models.playlist import Playlist
    from models.sync_log import SyncLog
    from models.track_blacklist import TrackBlacklist
    import services.sync_engine as sync_engine
    import services.blacklist_service as blacklist_service


    @pytest.fixture(name="session")
    def session_fixture():
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            yield session
    ```
  - [x] Test **(a)** `test_get_blacklisted_ids_empty(session)` — assert `blacklist_service.get_blacklisted_ids(session) == set()`.
  - [x] Test **(b)** `test_get_blacklisted_ids_returns_all_ids(session)` — insert two `TrackBlacklist` rows, assert the helper returns `{"id1", "id2"}` (set equality, ordering-agnostic).
  - [x] Test **(c)** `test_run_sync_unchanged_when_blacklist_empty(session)` — baseline: 1 playlist with 2 tracks, `playlist_size=2`, empty `track_blacklist`. Patch `services.sync_engine.engine`, `get_authenticated_client`, `get_playlist_tracks`, `get_or_create_dynamic_playlist`, `replace_playlist_tracks`. Capture the `track_uris` arg passed to `replace_playlist_tracks` via `mock_replace.call_args[0][1]`. Assert the URIs equal `["spotify:track:t1", "spotify:track:t2"]` (sorted by `added_at` desc — t1 first because more recent).
  - [x] Test **(d)** `test_run_sync_excludes_blacklisted_track(session)` — same setup as (c) but seed `TrackBlacklist(spotify_id="t1", blacklisted_at="2026-05-20T00:00:00Z")`. Assert the URIs passed to `replace_playlist_tracks` equal `["spotify:track:t2"]` only — and `len(sliced)` reflected in `SyncLog.track_count` is `1`.
  - [x] Test **(e)** `test_run_sync_completes_when_blacklist_drains_candidates(session)` — 1 playlist with 2 tracks (`t1`, `t2`), both in `TrackBlacklist`, `playlist_size=50`. Assert `run_sync()` returns `{"status": "success", "track_count": 0, "new_track_count": 0}` and `replace_playlist_tracks` was called with `[]`. Assert one `SyncLog` row with `status="success"`, `track_count=0`. NO exception raised.
  - [x] Test **(f)** `test_run_sync_delta_path_excludes_blacklisted_existing_track(session)` — seed `Config(playlist_size=10, dynamic_playlist_id="dyn_id", last_sync_at="2026-05-19T00:00:00Z")`, 1 included playlist. Mock `get_playlist_tracks` to return: when called for the dynamic playlist (`target_id="dyn_id"`) → `[{spotify_id: "old_track", uri: "spotify:track:old_track", added_at: "2026-05-15T00:00:00Z"}]` (this represents `existing_tracks`); when called for the source playlist (with `since="2026-05-19T00:00:00Z"`) → `[{spotify_id: "new_track", uri: "spotify:track:new_track", added_at: "2026-05-20T00:00:00Z"}]`. Seed `TrackBlacklist(spotify_id="old_track", ...)`. Assert the URIs passed to `replace_playlist_tracks` are `["spotify:track:new_track"]` only — the previously-on-playlist blacklisted track is dropped (proves AC #5: the filter runs on the merged+deduped list, not just on freshly-harvested tracks). Use `side_effect` on the `get_playlist_tracks` mock to differentiate calls (or `MagicMock` per-call return values).
  - [x] Test **(g)** `test_run_sync_restores_track_after_blacklist_delete(session)` — initial state: blacklist contains `t1`, 1 playlist with `t1` + `t2`, `playlist_size=2`. Call `run_sync()` once → assert URIs are `["spotify:track:t2"]`. Then `session.delete(blacklist_row); session.commit()`. Call `run_sync()` again → assert URIs are `["spotify:track:t1", "spotify:track:t2"]` (both restored). Proves AC #6 (no "ever-blacklisted" memory).
  - [x] Common patterns for these tests, mirroring `test_story_3_4.py:106-127`:
    ```python
    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", return_value=PLAYLIST_TRACKS),
        patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", return_value="dyn_id"),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks") as mock_replace,
    ):
        sync_engine.run_sync()
    captured_uris = mock_replace.call_args[0][1]
    ```
  - [x] Do NOT mock `blacklist_service.get_blacklisted_ids` — the test seeds real `TrackBlacklist` rows in the in-memory DB, and the helper reads them. This is an **integration**-flavored test by design (cheap and correct).

- [x] **Task 4: Full-suite regression + manual smoke** (AC: #3, #12)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` — expect **all 108+ existing tests still passing + 7 new tests passing** = ~115+ total. Zero failures, zero modifications to other test files.
  - [x] Manual smoke (after a successful sync produces a populated `/recently-added`):
    - Open `http://localhost:5173/recently-added` → click `⋯` → "Hide from Recent Adds" on one track.
    - Trigger a manual sync via the "Sync now" button on the Recently Added page (or `POST /api/v1/sync`).
    - Verify in Spotify (web/desktop client) that the blacklisted track is **no longer** in the dynamic playlist.
    - Verify in the backend logs (`docker-compose logs backend`) that the sync completed successfully (`status: success`).
    - Verify via the SQLite shell (`docker exec playlist_spotify-backend-1 /app/.venv/bin/python -c "from sqlmodel import Session, select; from database import engine; from models.track_blacklist import TrackBlacklist; print([(r.spotify_id, r.blacklisted_at) for r in Session(engine).exec(select(TrackBlacklist)).all()])"`) that the row persists across the sync.
    - Optional restore path: `DELETE /api/v1/blacklist/{id}` (via Postman or curl), trigger another sync → confirm the track returns to the playlist (AC #6).

- [x] **Task 5: Postman verification (no-op expected)** (AC: #13)
  - [x] GET the collection from `https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` using the `POSTMAN_API_KEY` from `.mcp.json`.
  - [x] Confirm the "Blacklist" folder is intact (`GET /blacklist`, `POST /blacklist`, `DELETE /blacklist/{spotify_id}`) and the "Sync" folder is intact. **Do NOT issue a PUT** — this story changes no HTTP surface.
  - [x] Document the outcome in "Dev Notes > Completion Notes" (e.g., "Postman collection verified: no surface change, no PUT issued.").

## Dev Notes

### Architecture & Conventions

- **Single new file + 4 added lines in `sync_engine.py`.** This story is deliberately small: one helper module (`services/blacklist_service.py`), one filter step inline in `run_sync()`, and one test file. No new HTTP routes, no new SQLModel tables, no frontend changes.
- **Pure-function service.** `blacklist_service.get_blacklisted_ids(session)` is a pure read — no side effects, no session-opening, no caching. Caller (the sync engine) owns the session lifetime. This matches the project's "Business logic dans services/, jamais dans routers/" rule (CLAUDE.md#Backend) and Story 8.1 AC #10's explicit forward-pointer.
- **Filter ordering matters (and is documented).** The filter runs **after** dedup and **before** sort/slice. Rationale: (a) filtering before dedup is wasteful, (b) filtering after slice would let a blacklisted track silently shrink the result while still occupying a "top-N" slot earlier in the pipeline. Filtering at the dedup→slice boundary preserves the FR34 invariant ("persistently excludes from all future syncs") cleanly.
- **Snapshot semantics.** The blacklist set is captured once per `run_sync()` inside the first session block. If the user blacklists more tracks mid-sync, the next sync handles them — this is the "eventual consistency" behavior the UX already advertises ("on the next sync"). Do NOT add re-reads, locks, or transactions.
- **Delta-sync correctness.** The existing delta path (`last_sync_at` set) merges `new_tracks + existing_tracks` before dedup. The filter runs **after** that merge, so a track blacklisted between syncs that was already on the playlist will be removed on the next sync — which is exactly the behavior Story 8.4's optimistic UI promises.
- **`new_track_count` invariant.** `new_track_count` is computed AFTER the filter (on `sliced`), so a blacklisted track that was previously on the playlist will neither appear in `sliced` nor contribute to `new_track_count` — the SSE-streamed counter Story 5.3 exposes remains accurate.
- **Error handling parity.** A failure inside the blacklist read (DB locked, disk full) falls through the existing `except Exception` in `run_sync()`, gets logged as a failure `SyncLog`, and re-raised — same as any other sync error. No bespoke handling.

### Source Tree — Files to Touch

- 🆕 [`backend/services/blacklist_service.py`](../../backend/services/blacklist_service.py) — new module with the single `get_blacklisted_ids(session) -> set[str]` helper.
- ✏️ [`backend/services/sync_engine.py`](../../backend/services/sync_engine.py) — add import line; fetch blacklist snapshot inside the first session block; insert one-line list comprehension filter between `deduped` and `sliced`; swap the `sort_and_slice` arg from `deduped` to `filtered`. ~4 added lines, 1 swapped argument.
- 🆕 [`backend/tests/test_story_8_5.py`](../../backend/tests/test_story_8_5.py) — 7 new tests using the `test_story_3_4.py` fixture pattern.
- 🔒 [`backend/models/track_blacklist.py`](../../backend/models/track_blacklist.py) — **do not touch**. The model shipped in Story 8.1 (`spotify_id` PK, `blacklisted_at` ISO 8601). Read-only here.
- 🔒 [`backend/routers/blacklist.py`](../../backend/routers/blacklist.py) — **do not touch**. The CRUD shipped in Story 8.1; no API change.
- 🔒 [`backend/services/spotify.py`](../../backend/services/spotify.py), [`backend/routers/sync.py`](../../backend/routers/sync.py), [`backend/main.py`](../../backend/main.py) — **do not touch**.
- 🔒 `frontend/**` — **do not touch**. Story 8.4 wired the UI; this story silently fulfills the "on the next sync" promise.

### Code Sketch — The Full Change in `sync_engine.py`

```python
# backend/services/sync_engine.py (excerpt — only the changed lines, in context)
import services.spotify as spotify_service
import services.blacklist_service as blacklist_service  # NEW

# ... inside run_sync() ...
try:
    with Session(engine) as session:
        playlists = session.exec(
            select(Playlist).where(Playlist.is_included == True, Playlist.is_hidden == False)  # noqa: E712
        ).all()
        if not playlists:
            raise ValueError("No playlists selected")
        config = session.exec(select(Config)).first()
        playlist_size = config.playlist_size if config else 50
        last_sync_at = config.last_sync_at if config else None
        blacklisted_ids = blacklist_service.get_blacklisted_ids(session)  # NEW

    sp = spotify_service.get_authenticated_client()
    target_id = spotify_service.get_or_create_dynamic_playlist(sp)
    existing_tracks = spotify_service.get_playlist_tracks(target_id, sp)
    existing_ids = {t["spotify_id"] for t in existing_tracks}

    if last_sync_at:
        new_tracks = harvest_tracks(playlists, sp, since=last_sync_at)
        raw_tracks = new_tracks + existing_tracks
    else:
        raw_tracks = harvest_tracks(playlists, sp)

    deduped = deduplicate(raw_tracks)
    filtered = [t for t in deduped if t["spotify_id"] not in blacklisted_ids]  # NEW
    sliced = sort_and_slice(filtered, playlist_size)                            # CHANGED arg
    new_track_count = sum(1 for t in sliced if t["spotify_id"] not in existing_ids)
    # ... rest unchanged ...
```

### Testing Standards

- **Tests run via Docker:** `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_8_5.py -v` for the new file; `pytest tests/ -v` for the full regression sweep (per CLAUDE.md#Tests).
- **Fixture pattern:** in-memory SQLite + `StaticPool` + `SQLModel.metadata.create_all` per test, mirroring `test_story_3_4.py`. The `track_blacklist` table is auto-created because the model is registered in `models/__init__.py` (Story 8.1).
- **Mocking strategy:** mock `services.sync_engine.spotify_service.*` (the 4 spotipy-facing functions). Do NOT mock `blacklist_service.get_blacklisted_ids` — seed real rows in the in-memory DB and let the helper read them. This is the integration that matters.
- **Capture pattern:** `mock_replace.call_args[0][1]` returns the second positional arg (`track_uris`) passed to `replace_playlist_tracks(target_id, track_uris, sp)` — the canonical assertion target for "what got pushed to Spotify".
- **No frontend tests.** No frontend changes in this story.

### Previous Story Intelligence

- **Story 8.1 (Track Blacklist Model & API)** — shipped the `TrackBlacklist` SQLModel, the `/blacklist` CRUD endpoints, and explicitly punted the service-layer helper to this story (AC #10: *"Story 8.5 will add a `get_blacklisted_ids() -> set[str]` helper in `services/` when it needs one"*). Use this exact signature.
- **Story 8.4 (Per-Track Blacklist Action)** — wired the frontend optimistic UI: `useBlacklistTrack` POST to `/api/v1/blacklist`, optimistic row removal, toast: *"Will be removed from your Spotify playlist on the next sync."* Story 8.5 is what makes that promise true.
- **Story 3.3 (Track Harvest & Dedup)** — established the `harvest_tracks`, `deduplicate`, `sort_and_slice` pure functions in `services/sync_engine.py`. Filter step goes between dedup and slice (the dedup is pure-function and reused; the filter is a 1-line list comprehension inline in `run_sync()`).
- **Story 3.4 (Dynamic Playlist Push)** — established the `run_sync()` orchestrator, the `SyncLog` write pattern, and the fixture style for sync-engine tests. Reuse the fixture pattern verbatim.
- **Delta-sync commit `069a96c`** — introduced the `last_sync_at` incremental code path that merges `new_tracks + existing_tracks` pre-dedup. The blacklist filter sits **after** that merge, so it cleans up both newly-harvested AND already-on-playlist blacklisted tracks (AC #5).

### Git Intelligence

- Recent commits (newest first):
  - `76facf6 feat: Epics 6 & 7 — UI refonte + playlist grid avec hide/unhide + dropdown style Spotify` — irrelevant to backend sync engine.
  - `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — **directly relevant**: introduced the delta path in `run_sync()`. The filter must run after the merge to handle the case where a previously-pushed track gets blacklisted between syncs.
  - `ccbbf60 feat: Stories 2-3 → 5-3 — Auth, Playlists, Sync, Scheduler & Observability` — established `run_sync()` and the `SyncLog` pattern.
- Working tree currently has Stories 8.1–8.4 changes uncommitted (`backend/routers/blacklist.py`, `backend/services/spotify.py` get_recently_added_tracks helper, frontend Recently Added page). Story 8.5 commits on top of those without conflict — `services/sync_engine.py` is not modified by any uncommitted Story 8.x change.
- No prior commit touches `backend/services/blacklist_service.py` — clean slate for the new file.

### Latest Tech Information

- **SQLModel / SQLAlchemy 2.x** — `session.exec(select(TrackBlacklist)).all()` returns rows directly (no `.scalars()` needed when the select target is the model class). Set comprehension `{row.spotify_id for row in rows}` is the idiomatic conversion. [Source: SQLModel docs + existing pattern in `routers/blacklist.py:23-26`]
- **Python set membership** — `if t["spotify_id"] not in blacklisted_ids` on a `set[str]` is O(1) average; even with 10k blacklisted IDs and 10k harvested tracks, the filter is microseconds. No need for a generator-based optimization. [Source: CPython set hashing]
- **APScheduler single-shot per-job** — the scheduler invokes `run_sync()` once per scheduled tick; there is no concurrent `run_sync()` execution in the current configuration. The blacklist snapshot is therefore safe without locking. [Source: APScheduler default executor + Story 4.1 single-job config]

### Project Structure Notes

- ✅ Aligns with `backend/services/<domain>.py` pattern (see `spotify.py`, `sync_engine.py`, `token_manager.py`).
- ✅ Reuses existing SQLModel + session pattern; no new dependencies; no new HTTP routes.
- ✅ Test file naming follows convention: `test_story_<epic>_<story>.py` (mirrors `test_story_8_1.py`, `test_story_8_2.py`, `test_story_8_3.py` already present).
- ⚠️ **Do NOT** extract the filter into a top-level function (`def filter_blacklisted(tracks, blacklisted_ids) -> list[dict]`) — it is one line. Per the project's "no premature abstraction" stance and Story 8.1 AC #10 deferral, the inline list comprehension is the right granularity. If Story 8.6 or a future story needs to reuse this filter, **then** extract it; not before.
- ⚠️ **Do NOT** introduce a cache or memoization on `get_blacklisted_ids`. The helper is called once per `run_sync()` (every few minutes to hourly). Caching would just introduce stale-read risk.
- ⚠️ **Do NOT** modify the `Config` model to track "last_blacklist_sync_at" or similar. The blacklist is a simple table; no synchronization metadata is needed.
- ⚠️ **Do NOT** add a sync trigger when a track is blacklisted (from the POST endpoint). The Story 8.4 UX is explicit: removal applies "on the next sync". Auto-triggering would surprise the user and double the sync rate.
- ⚠️ **Do NOT** filter inside `harvest_tracks` or `deduplicate` — those are pure data-transforming functions that shouldn't know about persistent state. The filter belongs in `run_sync()` where the session is already open.

### Project Context Reference

See [`CLAUDE.md`](../../CLAUDE.md) for project-wide development rules. Most relevant sections for this story:
- **Backend** — "Business logic dans `services/`, jamais dans `routers/`"; "Tous les appels spotipy passent par `services/spotify.py`"; snake_case JSON.
- **Tests** — `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`; fixture pattern from `test_story_2_4.py` / `test_story_3_1.py`; mocking via `patch("routers.<module>.spotify_service.<function>", ...)` (analogue here: `patch("services.sync_engine.spotify_service.<function>", ...)`).
- **Postman** — verify no-op expected (no API surface change).

User-memory rules in effect for this story (will silently shape decisions):
- [`feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md) — irrelevant; no frontend work.
- [`feedback_node_version`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_node_version.md) — irrelevant; no frontend work.
- [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md) — applies: verify the collection is intact, but no PUT (no API surface change).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-8.5] — primary ACs (lines 1351–1382).
- [Source: _bmad-output/planning-artifacts/prd.md#FR34, #FR35, #FR36] — feature-requirement framing for persistent blacklist exclusion.
- [Source: _bmad-output/implementation-artifacts/8-1-track-blacklist-model-api.md AC #10] — explicit forward-pointer to `get_blacklisted_ids()` helper in this story.
- [Source: _bmad-output/implementation-artifacts/8-4-per-track-blacklist-action.md Dev Notes "No sync trigger"] — the UX promise this story fulfills.
- [Source: backend/services/sync_engine.py:57-120] — `run_sync()` pipeline to wire into.
- [Source: backend/services/sync_engine.py:3] — import-style precedent (`import services.spotify as spotify_service`).
- [Source: backend/models/track_blacklist.py] — `TrackBlacklist` model schema.
- [Source: backend/routers/blacklist.py] — existing CRUD (unchanged by this story).
- [Source: backend/tests/test_story_3_4.py:13-21, :106-127] — fixture + mocking pattern to mirror.
- [Source: CLAUDE.md#Backend, #Tests, #Postman] — project conventions.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

- `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_8_5.py -v` → 7/7 passing.
- `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/` → 115/115 passing (108 legacy + 7 new), zero regressions.

### Completion Notes List

- Added `services/blacklist_service.py` with `get_blacklisted_ids(session) -> set[str]` (single read-only helper, caller owns session).
- Wired filter into `run_sync()`: import added, blacklist snapshot fetched inside the first session block alongside `playlists`/`config`, inline list comprehension placed between `deduplicate(raw_tracks)` and `sort_and_slice(...)`. Pipeline order is now harvest → dedup → blacklist filter → sort → slice → push.
- `new_track_count` semantics preserved — it still operates on `sliced` (now blacklist-filtered) and `existing_ids` (previous playlist contents).
- Delta path (AC #5) handled implicitly: filter runs on merged `new_tracks + existing_tracks` after dedup, so a track blacklisted between syncs is dropped on the next sync.
- AC #4 covered by Python slice semantics — empty/short candidate list slices to itself without error.
- AC #6 covered: helper reads fresh on each `run_sync()`, so DELETE on the blacklist restores tracks on the next sync.
- Tests use the `test_story_3_4.py` fixture pattern (in-memory SQLite + `StaticPool` + `patch("services.sync_engine.engine", session.get_bind())`); blacklist rows seeded directly in DB (no mock on the helper).
- Postman collection verified: GET on UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` confirms `Blacklist` (List/Add/Remove) and `Sync` (Logs/Run/Status/Stream) folders intact. No PUT issued — this story changes no HTTP surface.
- No frontend changes — Story 8.4's optimistic UI promise ("removed on next sync") is now fulfilled by the backend.

### File List

- `backend/services/blacklist_service.py` (new)
- `backend/services/sync_engine.py` (modified — 1 import, 1 line in session block, 1 line filter, 1 arg swap)
- `backend/tests/test_story_8_5.py` (new — 7 tests)

### Change Log

- 2026-05-21 — Story 8.5 implemented: sync engine now filters out blacklisted tracks between dedup and sort/slice; 7 new tests in `test_story_8_5.py`; full suite green at 115 tests.
