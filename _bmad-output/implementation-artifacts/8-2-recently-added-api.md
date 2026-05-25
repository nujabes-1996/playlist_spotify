# Story 8.2: Recently Added API

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want an endpoint that returns the current contents of the dynamic Spotify playlist,
so that the Recently Added page can render the track list without re-running a sync.

## Acceptance Criteria

1. **Given** the dynamic playlist has been created previously (its Spotify ID is stored in `config.dynamic_playlist_id`), **When** `GET /api/v1/recently-added` is called, **Then** the response returns the current tracks of that playlist as a JSON array (no wrapper) of objects with exactly these snake_case fields: `spotify_id` (str), `title` (str), `artists` (list[str] — display names, in track order), `album` (str), `image_url` (str | null — album cover, largest available), `added_at` (str — ISO 8601, exactly as returned by Spotify), `duration_ms` (int), `explicit` (bool), `has_video` (bool). Order = playlist insertion order as returned by Spotify (no client-side re-sort). [Source: epics.md#Story-8.2 AC + FR32 + AR12 + CLAUDE.md#Backend "snake_case" + "Réponses sans wrapper"]

2. **Given** the dynamic playlist does not yet exist (`config.dynamic_playlist_id` is `None` or no `Config` row exists at all), **When** `GET /api/v1/recently-added` is called, **Then** the response is `[]` with status **200** — no 404, no 500, no error message. This is a normal first-run state, not an error. [Source: epics.md#Story-8.2 AC]

3. **Given** the dynamic playlist exists in `config` but has been deleted/unfollowed on the Spotify side (Spotify returns 404 for the playlist ID), **When** `GET /api/v1/recently-added` is called, **Then** the response is `[]` with status **200** (graceful degradation — same shape as AC #2). Do NOT try to recreate it here; that is the sync engine's job. Do NOT mutate `config.dynamic_playlist_id`. [Source: services/spotify.py `get_or_create_dynamic_playlist` self-heal pattern — Recently Added is a read-only view and must not trigger writes]

4. **Given** the dynamic playlist contains more than 100 tracks (Spotify's `playlist_items` page size cap), **When** the endpoint runs, **Then** all pages are concatenated transparently — the response includes every track up to `config.playlist_size` (typical max: 200). Reuse the pagination shape used by `services/spotify.py:get_playlist_tracks` (`limit=100`, increment `offset` until `page["next"] is None`). [Source: epics.md#Story-8.2 AC + services/spotify.py:262-281]

5. **Given** the Spotify API returns HTTP 429 (rate limit), **When** spotipy handles the response, **Then** the retry/backoff behavior built into spotipy (NFR12) applies as it does in the sync engine — do NOT add a separate retry loop, do NOT wrap the call in `try/except` for 429 specifically. Other `spotipy.SpotifyException` (auth, network) propagate as **502 Bad Gateway** via a single `try/except` at the router level with a short, non-leaky detail message. **Exception:** `ValueError` from `get_authenticated_client()` (no token) maps to **401 Unauthorized** — match the pattern in [`routers/playlists.py:32-33`](../../backend/routers/playlists.py). [Source: epics.md#Story-8.2 AC + NFR12 + routers/playlists.py error-mapping pattern]

6. **Given** a Spotify `playlist_items` page contains a `null` track (deleted/unavailable) or a track with no `id` (local file), **When** the response is built, **Then** that entry is silently skipped (do NOT raise, do NOT emit a placeholder). Mirror the existing defensive filter in `services/spotify.py:_get_liked_tracks` (`if track and track.get("id")`). [Source: services/spotify.py:203-210 + 248-258]

7. **Given** a track has no album image (`item.album.images == []`), **When** the response is built, **Then** `image_url` is `null`. **Given** a track has multiple album images, **When** the response is built, **Then** `image_url` is the URL of the **first** image (Spotify returns them largest-first — matches the `get_user_playlists` convention in [`services/spotify.py:104-105`](../../backend/services/spotify.py)). [Source: services/spotify.py:104-105]

8. **Given** Spotify returns `track.artists` as a list of `{id, name, ...}` dicts, **When** the response is built, **Then** the API exposes `artists` as `list[str]` containing only the `name` field, in the original order. Empty list if Spotify returns no artists (defensive; shouldn't happen in practice). [Source: UX handoff — TrackRow consumes a single concatenated `artist` string built client-side from this list]

9. **Given** Spotify returns `track.is_local == True` (local files added by the user), **When** the response is built, **Then** those entries are skipped (no `spotify_id` to render, no album metadata reliable). Same skip rule as AC #6. [Source: defensive Spotify hygiene — local tracks have null ids and break the FE row key]

10. **Given** the project's API conventions, **When** the endpoint is registered, **Then** it lives at `backend/routers/recently_added.py` with `router = APIRouter(tags=["recently-added"])`, exposes a single `GET /recently-added` handler, is wired into `main.py` via `app.include_router(recently_added_router, prefix="/api/v1")`, and uses **no** `SessionDep` for the response shaping (the only DB read is `config.dynamic_playlist_id`, which can be done in `services/spotify.py` or via `SessionDep` in the handler — see Dev Notes for the chosen split). Snake_case fields, array-direct response. [Source: CLAUDE.md#Backend + main.py:11-14, 39-43]

11. **Given** the project rule "Business logic dans `services/`, jamais dans `routers/`" and "Tous les appels spotipy passent par `services/spotify.py`", **When** this story is implemented, **Then** all spotipy calls (`sp.playlist_items(...)` and any helpers) are added inside `services/spotify.py` as a new function `get_recently_added_tracks() -> list[dict]` that returns the already-shaped list of dicts (or `[]` for the empty-state cases). The router stays a thin wrapper: read no DB, do no list comprehension on Spotify payloads — just call the service, map `ValueError → 401` and `spotipy.SpotifyException → 502`. [Source: CLAUDE.md#Backend + services/spotify.py pattern]

12. **Given** the new pytest file `backend/tests/test_story_8_2.py`, **When** `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_8_2.py -v` is run, **Then** all tests pass and exercise the cases in Dev Notes → "Testing Standards" → "Test matrix" (one test per row). Mock `routers.recently_added.spotify_service.get_recently_added_tracks` for the router-level tests (status code + JSON shape) and unit-test `services/spotify.get_recently_added_tracks` by patching `services.spotify.get_authenticated_client` to return a `MagicMock` Spotify client with scripted `playlist_items` responses. [Source: CLAUDE.md#Tests + test_story_7_1.py fixture pattern + test_story_3_1.py mock pattern]

13. **Given** the backend response is profiled on a local network for a dynamic playlist of 200 tracks, **When** measured (manual smoke OK — no perf harness), **Then** the endpoint responds within ~500ms p50 so the frontend can meet NFR14 (<1s render for 200 tracks). With `playlist_size=200` (Spotify cap 100/page → 2 sequential page fetches), this is achievable without caching. Do NOT add an HTTP cache layer, ETag, or in-process memoization in this story — Story 8.6 owns performance polish. [Source: epics.md#Story-8.2 AC + NFR14 + Story 8.6 scope]

14. **Given** the Postman collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`), **When** Story 8.2 ships, **Then** one new request is added under a new "Recently Added" folder (or appended to an existing relevant folder if one fits — prefer the new folder for clarity): `GET {{api_v1}}/recently-added`, with a brief description and an example response body (1–2 tracks demonstrating all 9 fields including `explicit: true`, `has_video: false`, an `image_url`, and a multi-artist `artists` array). Verify the PUT update succeeded by GETting the collection and confirming the request appears. [Source: CLAUDE.md#Postman + memory `feedback_postman_sync`]

## Tasks / Subtasks

- [x] **Task 1: Add `get_recently_added_tracks()` to `services/spotify.py`** (AC: #1, #3, #4, #6, #7, #8, #9, #11)
  - [x] At the bottom of [`backend/services/spotify.py`](../../backend/services/spotify.py), add a new function `get_recently_added_tracks() -> list[dict]`. Signature returns a list of fully-shaped dicts (the exact JSON shape from AC #1) — the router does **no** mapping.
  - [x] Inside the function:
    1. Open a `with Session(engine) as session:` block and read `config.dynamic_playlist_id`. If `None` or no `Config` row → `return []` (AC #2 is handled at the router boundary anyway, but defensive return here keeps the helper standalone-callable).
    2. Get authenticated client via `get_authenticated_client()` (raises `ValueError` if not authenticated — let it propagate so the router can map to 401).
    3. Wrap `sp.playlist(playlist_id, fields="id")` in `try/except spotipy.SpotifyException` to detect "playlist gone" (AC #3). On exception → `return []`. Do **not** swallow other errors — re-raise.
    4. Paginate `sp.playlist_items(playlist_id, limit=100, offset=offset, fields="items(added_at,is_local,track(id,name,duration_ms,explicit,is_local,artists(name),album(name,images))),next")` until `page["next"] is None`. (Selecting fields via `fields=` reduces payload size and matches `get_playlist_tracks` style.)
    5. For each item: skip if `item.get("is_local")` OR `track is None` OR `not track.get("id")` OR `track.get("is_local")` (AC #6, #9).
    6. Build the dict with the exact 9 keys from AC #1. For `image_url`: `images[0]["url"] if images else None` (AC #7). For `artists`: `[a.get("name") for a in (track.get("artists") or []) if a.get("name")]` (AC #8). For `has_video`: not directly exposed by Spotify on `track` — set to `track.get("track", {}).get("is_video", False)` if present, else `False`. **Practical default: `False`** (the field exists in the contract for symmetry with the UX TrackRow; Spotify rarely returns video tracks in normal playlists). Document this in a one-line code comment.
  - [x] Do **not** import or touch `models/track_blacklist.py` here. Story 8.5 owns the blacklist filter — this story returns the raw playlist contents.
  - [x] Mirror existing import style and helper locality (see `_get_liked_tracks` / `get_playlist_tracks` as the structural references). No new module — extend the existing file.

- [x] **Task 2: Create the router** (AC: #2, #5, #10, #11)
  - [x] Create new file [`backend/routers/recently_added.py`](../../backend/routers/recently_added.py):
    ```python
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel
    from spotipy import SpotifyException

    from services import spotify as spotify_service

    router = APIRouter(tags=["recently-added"])


    class RecentlyAddedTrack(BaseModel):
        spotify_id: str
        title: str
        artists: list[str]
        album: str
        image_url: str | None = None
        added_at: str
        duration_ms: int
        explicit: bool
        has_video: bool


    @router.get("/recently-added", response_model=list[RecentlyAddedTrack])
    def get_recently_added() -> list[RecentlyAddedTrack]:
        try:
            tracks = spotify_service.get_recently_added_tracks()
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc))
        except SpotifyException as exc:
            raise HTTPException(status_code=502, detail=f"Spotify error: {exc.msg}")
        return [RecentlyAddedTrack(**t) for t in tracks]
    ```
  - [x] Do **not** inject `SessionDep` — the service owns the DB read for `dynamic_playlist_id`. Keeps the router truly thin per CLAUDE.md.
  - [x] Do **not** add `prefix=` on the router itself — `main.py` adds the `/api/v1` prefix at `include_router` time (matches every other router in the project).

- [x] **Task 3: Wire the router into the FastAPI app** (AC: #10)
  - [x] In [`backend/main.py`](../../backend/main.py), add `from routers.recently_added import router as recently_added_router` next to the existing router imports (keep alphabetical-ish ordering with siblings).
  - [x] Add `app.include_router(recently_added_router, prefix="/api/v1")` next to the other `include_router` calls (line ~43).

- [x] **Task 4: Write pytest covering all ACs** (AC: #12)
  - [x] Create [`backend/tests/test_story_8_2.py`](../../backend/tests/test_story_8_2.py) using the **router-level fixture pattern** from [`tests/test_story_7_1.py`](../../backend/tests/test_story_7_1.py) (in-memory SQLite + `StaticPool` + `app.dependency_overrides[get_session]`). Even though the router doesn't read from `session`, the fixtures are needed because the app's lifespan hooks may touch the engine.
  - [x] Implement the test matrix (one test function per row):

    | # | Test name                                                    | Scenario / patch                                                                                              | Assertion                                                                                              | AC |
    |---|--------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|----|
    | 1 | `test_returns_empty_list_when_dynamic_playlist_id_missing`   | patch `routers.recently_added.spotify_service.get_recently_added_tracks` → `[]`                               | 200, `[]`                                                                                              | 2  |
    | 2 | `test_returns_tracks_with_exact_shape`                       | patch service to return one fully-formed dict (all 9 fields)                                                  | 200, single-element array, all keys present in snake_case, types match                                 | 1  |
    | 3 | `test_returns_401_when_not_authenticated`                    | patch service to raise `ValueError("Not authenticated — run OAuth2 flow first")`                              | 401, detail contains "Not authenticated"                                                               | 5  |
    | 4 | `test_returns_502_on_spotify_exception`                      | patch service to raise `SpotifyException(http_status=500, code=-1, msg="boom")`                               | 502, detail contains "boom"                                                                            | 5  |
    | 5 | `test_returns_empty_list_when_playlist_deleted_on_spotify`   | patch service to return `[]` (simulates the service's internal 404 swallow per AC #3)                         | 200, `[]`                                                                                              | 3  |
    | 6 | `test_service_paginates_and_concatenates` (unit)             | patch `services.spotify.get_authenticated_client` + monkey-set `config.dynamic_playlist_id`; script `sp.playlist_items` to return 2 pages (100 + 50 tracks) | service returns 150 dicts in order                                | 4  |
    | 7 | `test_service_skips_null_and_local_tracks` (unit)            | scripted `playlist_items` with one `null` track, one `is_local: True`, one valid track                        | service returns only the 1 valid dict                                                                  | 6, 9 |
    | 8 | `test_service_sets_image_url_null_when_no_album_images` (unit)| scripted track with `album.images = []`                                                                       | dict's `image_url is None`                                                                             | 7  |
    | 9 | `test_service_flattens_artists_to_names` (unit)              | scripted track with `artists = [{"name": "A"}, {"name": "B"}]`                                                | dict's `artists == ["A", "B"]`                                                                         | 8  |
    | 10| `test_service_returns_empty_when_playlist_gone` (unit)       | `sp.playlist(...)` raises `SpotifyException(http_status=404, ...)`                                            | service returns `[]`, **does not** mutate config                                                       | 3  |
    | 11| `test_service_returns_empty_when_no_config` (unit)           | DB has no `Config` row                                                                                        | service returns `[]` without calling `get_authenticated_client`                                        | 2  |

  - [x] For the unit tests (rows 6–11), use `patch("services.spotify.get_authenticated_client", return_value=MagicMock())` and set `mock_sp.playlist_items.side_effect = [page1, page2, ...]`. Insert a `Config` row via the `session` fixture when needed.
  - [x] Run: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_8_2.py -v`. All tests MUST pass before marking the story `review`.

- [x] **Task 5: Manual smoke against the running stack** (AC: #1–#7, #13)
  - [x] `docker-compose up -d`, ensure the user has authenticated (the dev DB at `data/playlist_spotify.db` should already have a valid `config` row from earlier stories).
  - [x] `curl -s http://127.0.0.1:8000/api/v1/recently-added | jq '. | length'` — expect a number ≥ 0.
  - [x] `curl -s http://127.0.0.1:8000/api/v1/recently-added | jq '.[0]'` — verify all 9 fields present, snake_case, types correct.
  - [x] If the dynamic playlist doesn't exist yet (fresh install), expect `[]` (AC #2). Optionally trigger a manual sync first to populate it.
  - [x] Time the call with `time curl -s -o /dev/null http://127.0.0.1:8000/api/v1/recently-added` — note the wall time as a sanity check against AC #13.

- [x] **Task 6: Update Postman collection** (AC: #14)
  - [x] Collection UID: `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`. API key in `.mcp.json` (env `POSTMAN_API_KEY`).
  - [x] `GET https://api.getpostman.com/collections/{uid}` → fetch current JSON.
  - [x] Add a new folder "Recently Added" with one request: `GET {{api_v1}}/recently-added`. Description: "Returns the current contents of the dynamic Spotify playlist (the 'Recent Adds' aggregator). Returns `[]` if the playlist does not yet exist or has been deleted from Spotify." Example response body in the request: a 2-track JSON array exercising all 9 fields (one `explicit: true` track with a 2-element `artists` array; one with `image_url: null` and `has_video: false`).
  - [x] `PUT https://api.getpostman.com/collections/{uid}` with the updated body.
  - [x] Verify: re-`GET` the collection and confirm the new request appears under the "Recently Added" folder.

## Dev Notes

### Architecture & Conventions

- **Backend-only story** — no frontend code, no UX design impact. Story 8.3 will consume this endpoint from the new `/recently-added` page. [Source: epics.md#Epic-8]
- **All spotipy calls live in `services/spotify.py`** — the router is a thin error-mapper. This is the project's hard convention, established in [`routers/playlists.py`](../../backend/routers/playlists.py) and reinforced in CLAUDE.md.
- **No new SQLModel, no schema change** — this endpoint is read-only and read-through to Spotify. Only DB touch is `SELECT dynamic_playlist_id FROM config` inside the service.
- **No service for blacklist filtering yet** — Story 8.5 owns "filter blacklisted tracks out of the response or out of the next sync". Whether 8.5 filters in this endpoint or in the sync engine is 8.5's decision; this story does NOT pre-filter. The contract is "current contents of the Spotify playlist as Spotify sees them", which is exactly what the FE Recently Added page wants for now (a track only disappears from the view after the *next* sync removes it — per Story 8.4 AC).
- **JSON convention** — snake_case everywhere, array-direct response (no `{"data": [...]}` wrapper). [Source: CLAUDE.md#Backend]
- **Error mapping** — `ValueError` (no auth / no token / no config) → 401, `spotipy.SpotifyException` → 502. Do not raise 404 from this endpoint (an empty result is the empty-state contract, not an error).

### Source Tree — Files to Touch

- ✏️ [`backend/services/spotify.py`](../../backend/services/spotify.py) — add `get_recently_added_tracks()` at end of file.
- 🆕 [`backend/routers/recently_added.py`](../../backend/routers/recently_added.py) — new router (single GET endpoint).
- ✏️ [`backend/main.py`](../../backend/main.py) — import + `include_router` with `/api/v1` prefix.
- 🆕 [`backend/tests/test_story_8_2.py`](../../backend/tests/test_story_8_2.py) — pytest suite (router-level mocks + service-level unit tests).
- 🔒 [`backend/services/sync_engine.py`](../../backend/services/sync_engine.py) — **do not touch**. Story 8.5 will integrate the blacklist filter into syncs; this endpoint is independent of the sync flow.
- 🔒 [`backend/models/`](../../backend/models/) — **no new model, no schema change**.
- 🔒 [`backend/routers/blacklist.py`](../../backend/routers/blacklist.py) — **do not touch**. Story 8.1 already shipped this CRUD; 8.4 will wire the FE action against it.
- 🔒 Frontend — **do not touch** (story is backend-only). Story 8.3 owns the React route.

### Code Sketch — Service helper

```python
# Appended to services/spotify.py

def get_recently_added_tracks() -> list[dict]:
    """Return the current contents of the dynamic playlist as shaped dicts.

    Returns [] when the dynamic playlist has not been created yet (fresh install)
    or has been deleted from Spotify. Re-raises ValueError if not authenticated
    and SpotifyException for non-404 Spotify errors.
    """
    with Session(engine) as session:
        config = session.exec(select(Config)).first()
        playlist_id = config.dynamic_playlist_id if config else None
    if not playlist_id:
        return []

    sp = get_authenticated_client()
    try:
        sp.playlist(playlist_id, fields="id")
    except SpotifyException as exc:
        if exc.http_status == 404:
            return []
        raise

    results: list[dict] = []
    offset = 0
    limit = 100
    while True:
        page = sp.playlist_items(
            playlist_id,
            limit=limit,
            offset=offset,
            fields=(
                "items(added_at,is_local,"
                "track(id,name,duration_ms,explicit,is_local,"
                "artists(name),album(name,images))),next"
            ),
        )
        for item in page["items"]:
            if item is None or item.get("is_local"):
                continue
            track = item.get("track")
            if not track or not track.get("id") or track.get("is_local"):
                continue
            album = track.get("album") or {}
            images = album.get("images") or []
            artists = [a.get("name") for a in (track.get("artists") or []) if a.get("name")]
            results.append({
                "spotify_id": track["id"],
                "title": track.get("name", ""),
                "artists": artists,
                "album": album.get("name", ""),
                "image_url": images[0]["url"] if images else None,
                "added_at": item.get("added_at") or "",
                "duration_ms": int(track.get("duration_ms") or 0),
                "explicit": bool(track.get("explicit", False)),
                # Spotify rarely flags `is_video` on normal tracks; default False.
                "has_video": bool(track.get("is_video", False)),
            })
        if page.get("next") is None:
            break
        offset += limit
    return results
```

> Sketch only — adapt naming to match existing helpers in `services/spotify.py`. The shape (DB read → auth → playlist probe → paginated `playlist_items` → defensive filter → dict assembly) is the correct order.

### Testing Standards

- **Test runner**: pytest inside the backend container. Always: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/<file> -v`. [Source: CLAUDE.md#Tests]
- **Router-level tests**: mock the service (`patch("routers.recently_added.spotify_service.get_recently_added_tracks", ...)`). Pattern from [`test_story_3_1.py`](../../backend/tests/test_story_3_1.py).
- **Service-level unit tests**: patch `services.spotify.get_authenticated_client` to return a `unittest.mock.MagicMock()`, then `mock_sp.playlist_items.side_effect = [page1, page2]` to script pagination. Insert a `Config` row via the `session` fixture so the DB read returns a `dynamic_playlist_id`.
- **Fixture pattern**: in-memory SQLite + `StaticPool` + `app.dependency_overrides[get_session]`, copied verbatim from [`test_story_7_1.py`](../../backend/tests/test_story_7_1.py).
- **No real network calls** — every test mocks the boundary. CI does not have Spotify credentials.
- **Status codes are part of the contract** — explicitly assert `r.status_code == 200`, `401`, `502` per the relevant ACs.

### Previous Story Intelligence

- **Story 8.1 (Track Blacklist Model & API)** — just shipped the `/api/v1/blacklist` CRUD. This story is the *other half* of the Epic 8 backend surface. Both endpoints are independent for now; Story 8.5 will join them at the sync engine.
- **Story 7.1 / 3.1** established the fixture pattern reused here.
- **Story 069a96c (delta sync, Liked Songs)** added `get_playlist_tracks(..., since=...)` to `services/spotify.py` — that function is the structural reference for the new `get_recently_added_tracks()` (same pagination shape, same defensive item filter). Do NOT add a `since` parameter to the new function — the Recently Added view always returns the full current contents.
- **Story 7.5 "no premature abstraction"** — keep the response builder inside `services/spotify.py`. Do not extract a `services/recently_added.py` for one function.
- **Story 8.1 "minimal public surface"** — same posture here: one function in the service, one endpoint in the router, no helpers.

### Git Intelligence

- Most recent feature commits (newest first):
  - `76facf6 feat: Epics 6 & 7 — UI refonte + playlist grid avec hide/unhide + dropdown style Spotify` — Story 8.3 will live in the new shell shipped here. Irrelevant to the API change in this story.
  - `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — introduced `get_playlist_tracks(..., since=...)` and the `services/spotify.py` pagination idiom this story should mirror.
  - `ccbbf60 feat: Stories 2-3 → 5-3 — Auth, Playlists, Sync, Scheduler & Observability` — bulk landing of foundation epics; established `routers/` shape used here.
- Working tree currently has the Story 8.1 changes in `review`. Do not amend or rebase them. Commit Story 8.2 as a new commit on top.
- No prior commit references `recently_added` — clean slate for the router and tests.

### Latest Tech Information

- **spotipy `playlist_items`** — supports the `fields` parameter to project only the keys you need (reduces payload, latency, and avoids breakage if Spotify adds new optional fields). Use the same `fields=` style already used in `services/spotify.py:get_playlist_tracks`.
- **spotipy retry/backoff** — the `Spotify` client constructed via `SpotifyOAuth` retries on 429 internally per the spotipy defaults. Adding a hand-rolled retry loop is redundant and risks double-retries. [Source: spotipy `Spotify` constructor defaults — `retries=3`, `status_retries=3`, `backoff_factor=0.3`]
- **`SpotifyException.http_status`** — exposed on the exception; use it to distinguish 404 (silently swallow → `[]`) from 5xx (re-raise → 502).
- **FastAPI `response_model=list[Model]`** — validates the outgoing shape per request. Cheap enough at 200 items; keep it on for the contract guarantee.

### Postman Sync Procedure (Reminder)

Per CLAUDE.md and memory `feedback_postman_sync`, Postman MUST be updated when API surface changes. This story adds 1 endpoint. Use the MCP Postman server if available in this session; otherwise hit the REST API directly:

```bash
# 1. Get current collection
curl -s -H "X-Api-Key: $POSTMAN_API_KEY" \
  https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6 \
  > /tmp/postman-current.json

# 2. Edit /tmp/postman-current.json — add the new "Recently Added" folder + 1 request
#    (preserve the entire existing structure; only append)

# 3. PUT the updated collection back
curl -s -X PUT -H "X-Api-Key: $POSTMAN_API_KEY" \
  -H "Content-Type: application/json" \
  --data @/tmp/postman-updated.json \
  https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6

# 4. Verify the PUT
curl -s -H "X-Api-Key: $POSTMAN_API_KEY" \
  https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6 \
  | jq '.collection.item[] | select(.name=="Recently Added") | .item | length'
# expected: 1
```

### Project Structure Notes

- ✅ Aligns with [`architecture.md`](../planning-artifacts/architecture.md) backend layout: `services/spotify.py` for spotipy, `routers/<entity>.py` for thin HTTP wrappers, `tests/test_story_<X>_<Y>.py` for per-story pytest files.
- ✅ Snake_case JSON, array-direct response, error-mapping pattern — all match existing `routers/playlists.py`.
- ⚠️ **Do NOT** add a `services/recently_added.py` — one function added to the existing `services/spotify.py` is the right granularity (matches `get_user_playlists`, `get_playlist_tracks`, `get_or_create_dynamic_playlist`).
- ⚠️ **Do NOT** filter blacklisted tracks out of the response — Story 8.5 owns that integration. Filtering here pre-empts a design decision that depends on the FE behavior in Story 8.4 (optimistic removal vs. server-side hide).
- ⚠️ **Do NOT** mutate `config.dynamic_playlist_id` from this endpoint, even when the playlist returns 404 on Spotify. Recently Added is a read-only view; self-healing is the sync engine's job (see `get_or_create_dynamic_playlist`).
- ⚠️ **Do NOT** add a cache layer / ETag / in-process memoization — Story 8.6 ("Recently Added Performance & Polish") owns that work. Keep this story minimal.
- ⚠️ **Do NOT** add a `?limit=` or `?offset=` query param — the endpoint always returns the current full playlist contents (bounded by `config.playlist_size`, typically ≤200). Adding pagination is YAGNI and complicates the FE.

### Project Context Reference

See [`CLAUDE.md`](../../CLAUDE.md) for project-wide development rules. Most relevant sections for this story:
- "Backend" — business logic placement (`services/`), snake_case, array-direct responses, all spotipy calls in `services/spotify.py`.
- "Tests" — pytest via `docker exec`, fixture pattern, mock services with `patch("routers.<module>.spotify_service.<fn>", ...)`.
- "Postman — Mise à jour obligatoire" — non-negotiable for any API change.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-8.2] — primary ACs (lines 1217–1244).
- [Source: _bmad-output/planning-artifacts/epics.md#FR32, #AR12, #NFR14] — response shape, source-of-truth statement, performance budget.
- [Source: _bmad-output/planning-artifacts/ux-design/README.md "TrackRow"] — confirms FE consumes `explicit`, `has_video`, `artists`, `image_url`, `added_at`, `duration_ms` (lines 143–164).
- [Source: _bmad-output/planning-artifacts/ux-design/snippets/TrackRow.tsx] — concrete `Track` interface the FE will adapt from this payload.
- [Source: backend/services/spotify.py:217-281] — `get_playlist_tracks` structure to mirror (pagination, defensive item filter, `fields=` projection).
- [Source: backend/routers/playlists.py:30-33] — error-mapping pattern (`ValueError → 401`).
- [Source: backend/main.py:11-14, 39-43] — where to wire the new `include_router` call.
- [Source: backend/tests/test_story_7_1.py] — fixture pattern to copy.
- [Source: backend/tests/test_story_3_1.py] — `patch("routers.<m>.spotify_service.<fn>", ...)` mock pattern.
- [Source: CLAUDE.md#Backend, #Tests, #Postman] — project conventions.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

- `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_8_2.py -v` → 12 passed.
- `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/` → 106 passed, no regressions.
- Smoke: `curl -s http://127.0.0.1:8000/api/v1/recently-added` → `[]` with 200 in 0.71s (empty-state branch, AC #2/#3 confirmed; dev DB has no `dynamic_playlist_id` yet).
- Postman: `PUT https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` → 200; re-`GET` confirms new "Recently Added" folder with `Get Recently Added Tracks`.

### Completion Notes List

- Added `services.spotify.get_recently_added_tracks()` mirroring `get_playlist_tracks` pagination/defensive-filter shape. Reads `config.dynamic_playlist_id` once, probes the playlist with `sp.playlist(..., fields="id")` to detect 404 → `[]`, paginates `sp.playlist_items` with a projected `fields=` selector, and shapes each item into the 9-field snake_case dict from AC #1. Local files / null tracks / null `track.id` are skipped (AC #6, #9). `image_url` is `images[0].url` or `None` (AC #7). `has_video` defaults to `False` and reads `track.is_video` when present.
- `routers/recently_added.py` is a thin wrapper: `ValueError → 401`, `SpotifyException → 502`, no `SessionDep`, no business logic. Wired in `main.py` with `/api/v1` prefix next to siblings.
- Did NOT touch `models/track_blacklist.py`, `services/sync_engine.py`, or `routers/blacklist.py` — Story 8.5 owns blacklist filtering; this endpoint is a raw read of the dynamic playlist.
- Did NOT mutate `config.dynamic_playlist_id` on the 404 self-heal path (Recently Added is read-only — sync engine owns self-healing).
- Pytest suite (`tests/test_story_8_2.py`) covers all 11 matrix rows + extra `test_service_reraises_non_404_spotify_exception` (12 tests, all passing). Service-level tests patch `services.spotify.get_authenticated_client` and `services.spotify.engine` to use the in-memory SQLite engine.
- Postman collection updated: new "Recently Added" folder with the GET request + a 2-track example response demonstrating all 9 fields (`explicit: true` multi-artist track + `image_url: null` track).

### File List

- ✏️ `backend/services/spotify.py` — added `get_recently_added_tracks()` and imported `SpotifyException`.
- 🆕 `backend/routers/recently_added.py` — new thin router (single GET endpoint, error-mapping).
- ✏️ `backend/main.py` — imported and included `recently_added_router` under `/api/v1`.
- 🆕 `backend/tests/test_story_8_2.py` — pytest suite (5 router-level + 7 service-level unit tests).
- ✏️ `_bmad-output/implementation-artifacts/sprint-status.yaml` — `8-2-recently-added-api: in-progress → review`.
- ✏️ Postman collection `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` — added "Recently Added" folder + `Get Recently Added Tracks` request with example response.

## Change Log

- 2026-05-21 — Story 8.2 implemented: `GET /api/v1/recently-added` endpoint backed by `services.spotify.get_recently_added_tracks()`. Returns the dynamic playlist contents as a snake_case JSON array (9 fields per track), with `[]` empty-states for missing/deleted playlists, pagination across Spotify's 100-item pages, defensive skip of null/local tracks, and `ValueError → 401` / `SpotifyException → 502` mapping at the router boundary. Postman collection synced. 12 new pytest cases, 106 backend tests passing.
