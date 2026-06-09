# Story 9.1: Playlist Tracks API Endpoint

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want a `GET /api/v1/playlists/{spotify_id}/tracks` endpoint that returns every track of a given Spotify playlist in the exact same JSON shape as `GET /api/v1/recently-added`,
So that the upcoming Playlist Detail page (Story 9.3) and the shared track-list components (Story 9.2) can reuse the existing `TrackRow` / `RecentlyAddedTable` / adapter pipeline with **zero shape adaptation**.

## Acceptance Criteria

1. **Given** the FastAPI app is running with a valid Spotify session, **When** the client issues `GET /api/v1/playlists/{spotify_id}/tracks` with a real Spotify playlist id (e.g. `37i9dQZF1DXcBWIGoYBM5M`), **Then** the response is HTTP 200 with `Content-Type: application/json` and the body is a **JSON array (no wrapper)** whose element shape is **identical** to `/api/v1/recently-added`:
   ```json
   [
     {
       "spotify_id": "string",
       "title": "string",
       "artists": ["string", "..."],
       "album": "string",
       "image_url": "string | null",
       "added_at": "ISO-8601 string",
       "duration_ms": 0,
       "explicit": false,
       "has_video": false
     }
   ]
   ```
   Every key in this set must be present on every element (no missing fields). Field names are snake_case per `CLAUDE.md#Backend`. No wrapper key like `{"data": [...]}` or `{"tracks": [...]}`. [Source: epics.md#Story-9.1 (paragraph 2) + recently_added.py:10-30 (`RecentlyAddedTrack` Pydantic model) + CLAUDE.md#Backend "Réponses sans wrapper"]

2. **Given** the path parameter `spotify_id` equals the sentinel value **`liked_songs`** (defined as `LIKED_SONGS_ID = "liked_songs"` in [`backend/services/spotify.py:12`](../../backend/services/spotify.py#L12)), **When** the endpoint runs, **Then** the underlying service call must use `sp.current_user_saved_tracks(limit=50, offset=offset)` and walk pagination via the `next` field — **NOT** `sp.playlist_items()` (which would 404 since "Liked Songs" is not a real playlist in Spotify's API). The response shape must still match AC #1 exactly. Note: the epic hint mentions `"liked"` (or similar sentinel) — the correct sentinel actually in use across the codebase is **`liked_songs`** (verify via `grep -n LIKED_SONGS_ID backend/services/spotify.py`). Use **`liked_songs`**, not `"liked"`. [Source: epics.md#Story-9.1 hint #2 + services/spotify.py:12 (`LIKED_SONGS_ID = "liked_songs"`) + services/spotify.py:195-214 (`_get_liked_tracks` existing helper) + frontend/src/features/playlists/PlaylistGrid.tsx:19 (`spotifyId === 'liked_songs'` UI sentinel — must match)]

3. **Given** the path parameter `spotify_id` references a playlist the user does not own / cannot access (Spotify returns 404), **When** the endpoint runs, **Then** the API responds with HTTP **404** and body `{"detail": "Playlist not found"}` (or a similar concise message). Do **NOT** return `[]` on 404 — Recently Added returns `[]` because it gracefully degrades when the dynamic playlist was deleted, but a user-requested playlist id that 404s is a real client error and must surface as 404. [Source: epics.md#Story-9.1 (implicit — endpoint is user-facing, not the dynamic playlist) + services/spotify.py:298-303 (existing 404 handling pattern, but here translate to HTTP 404 instead of swallowing)]

4. **Given** the user is not authenticated (`get_authenticated_client()` raises `ValueError`), **When** the endpoint runs, **Then** the API responds with HTTP **401** and body `{"detail": "..."}` containing the ValueError message — exactly mirroring the existing pattern at [`backend/routers/recently_added.py:26-27`](../../backend/routers/recently_added.py#L26-L27). [Source: recently_added.py:23-30 + Story 8.2 AC pattern]

5. **Given** Spotify returns a non-404 `SpotifyException` (rate limit, 500, network error, etc.), **When** the endpoint runs, **Then** the API responds with HTTP **502** and body `{"detail": "Spotify error: <msg>"}` — exactly mirroring the existing pattern at [`backend/routers/recently_added.py:28-29`](../../backend/routers/recently_added.py#L28-L29). [Source: recently_added.py:23-30 + consistent error-translation convention]

6. **Given** a real playlist with **more than 100 tracks**, **When** the endpoint runs, **Then** the underlying service paginates via `sp.playlist_items(playlist_id, limit=100, offset=offset)` until `page["next"] is None` and concatenates all pages into a single flat list. The HTTP response returns the **complete** list in a single payload (no client-side pagination, no `Link` header, no `limit`/`offset` query params on the FastAPI route). This mirrors `get_recently_added_tracks()` ([`services/spotify.py:305-345`](../../backend/services/spotify.py#L305-L345)). [Source: epics.md#Story-9.1 (paragraph 2) "paginated server-side, full list returned to client" + spotify.py:305-345 reference impl]

7. **Given** the playlist contains **local tracks** (uploaded by the user — `is_local: true` at the item level or track level) or **null track entries** (e.g. removed from Spotify), **When** the endpoint runs, **Then** those entries are **skipped silently** — they do not appear in the response and do not raise. Mirror the filter logic at [`services/spotify.py:322-326`](../../backend/services/spotify.py#L322-L326):
   ```python
   if item is None or item.get("is_local"):
       continue
   track = item.get("track") or item.get("item")
   if not track or not track.get("id") or track.get("is_local"):
       continue
   ```
   [Source: services/spotify.py:322-326 + tests/test_story_8_2.py::test_service_skips_null_and_local_tracks for the proven precedent]

8. **Given** a track in the response, **When** the album has no images, **Then** `image_url` is `null` (Python `None` → JSON `null`). Mirror [`services/spotify.py:335`](../../backend/services/spotify.py#L335) (`images[0]["url"] if images else None`). [Source: services/spotify.py:335 + tests/test_story_8_2.py::test_service_sets_image_url_null_when_no_album_images]

9. **Given** a track with multiple artists, **When** the response is built, **Then** `artists` is a flat list of artist name strings, in Spotify's returned order, **never** a list of objects. Mirror [`services/spotify.py:329`](../../backend/services/spotify.py#L329) — `[a.get("name") for a in (track.get("artists") or []) if a.get("name")]`. [Source: services/spotify.py:329 + tests/test_story_8_2.py::test_service_flattens_artists_to_names]

10. **Given** the `current_user_saved_tracks` Spotify endpoint (used for `liked_songs`), **When** the service paginates, **Then** for each page item:
    - skip when `item is None`
    - the track lives directly under `item["track"]` (saved tracks API does **not** use the `item` fallback key — only `track`)
    - skip when `track is None` or `track.get("id") is None` or `track.get("is_local")` is true
    - `added_at` is read from `item["added_at"]`
    - all other fields (`title`, `artists`, `album`, `image_url`, `duration_ms`, `explicit`, `has_video`) are read from the same `track` sub-dict in the same way as the playlist path

    The transformation function must produce dicts whose key set is identical to AC #1 — the only difference between the playlist branch and the liked-songs branch is **the iterator source**, not the row shape. [Source: spotipy `current_user_saved_tracks` reference + services/spotify.py:_get_liked_tracks for the iteration pattern (note: that helper returns only `{spotify_id, uri, added_at}` for sync purposes — your new code path needs the **full** shape from AC #1)]

11. **Given** the implementation must avoid duplication of the rich-row builder logic between the playlist branch and the liked-songs branch, **When** structuring the service, **Then** extract the per-track dict construction into a small **module-level helper** in `services/spotify.py` (e.g. `_build_track_row(track: dict, added_at: str) -> dict`) and call it from both branches. Do **NOT** copy-paste the field-mapping block twice. Do **NOT** refactor the existing `get_recently_added_tracks()` to share this helper in the same story — that's a follow-up refactor (could be folded into Story 9.2 if convenient, but is out of scope here). [Source: project DRY pragmatic stance + CLAUDE.md#Backend "Business logic dans services/"]

12. **Given** the FastAPI route surface, **When** wiring the endpoint, **Then** add it **inside the existing `playlists` router** at [`backend/routers/playlists.py`](../../backend/routers/playlists.py) (do **NOT** create a new router file). The route is `@router.get("/playlists/{spotify_id}/tracks", response_model=list[PlaylistTrack])`. Path collision check: the existing routes in this router are `/playlists` (GET, line 28) and any PATCH/PUT for `is_included`/`is_hidden` — `/playlists/{spotify_id}/tracks` does not collide. [Source: epics.md#Story-9.1 + main.py:42 (`playlists_router` mounted at `/api/v1`) + CLAUDE.md#Backend layering]

13. **Given** the response model defined for the new endpoint, **When** choosing where to declare the Pydantic model, **Then** declare a new `PlaylistTrack(BaseModel)` class **inside `backend/routers/playlists.py`** with the exact same fields as `RecentlyAddedTrack` (`spotify_id: str`, `title: str`, `artists: list[str]`, `album: str`, `image_url: str | None = None`, `added_at: str`, `duration_ms: int`, `explicit: bool`, `has_video: bool`). Do **NOT** import `RecentlyAddedTrack` from `routers/recently_added.py` — keeping the two routers decoupled lets future shape changes diverge cleanly per route. The epic hint floats "rename to a shared `Track` Pydantic model if convenient" — **defer** that consolidation; it lives more naturally in Story 9.2's frontend refactor (where the shared component is born) than in this backend story. [Source: epics.md#Story-9.1 hint #3 + project YAGNI stance + recently_added.py:10-19 reference]

14. **Given** the service function added to `services/spotify.py`, **When** naming and signature are chosen, **Then** add `get_playlist_tracks_full(playlist_id: str) -> list[dict]` (the `_full` suffix disambiguates from the existing `get_playlist_tracks(playlist_id, sp=None, since=None)` at line 217 which returns the **minimal `{spotify_id, uri, added_at}` shape** used by the sync engine — a name collision would be catastrophic). The new function returns the **full rich shape** of AC #1. It must:
    - call `get_authenticated_client()` (raises `ValueError` → router translates to 401 per AC #4)
    - branch on `playlist_id == LIKED_SONGS_ID` to use `current_user_saved_tracks` (AC #2)
    - otherwise call `sp.playlist(playlist_id, fields="id")` first as an existence probe — `SpotifyException` with `http_status == 404` re-raises (router translates to 404 per AC #3); other `SpotifyException`s re-raise (router → 502 per AC #5)
    - paginate via `sp.playlist_items(...)` with the same `fields=...` mask as `get_recently_added_tracks()` (line 313-319) so we get artists, album, images, duration, explicit, is_video, etc.
    - skip null + local entries (AC #7)
    - return a flat list of full-shape dicts (no pagination wrapper)
    [Source: services/spotify.py:217 (existing minimal `get_playlist_tracks`) + services/spotify.py:284-345 (`get_recently_added_tracks` shape pattern) + AC #3, #4, #5 error contracts]

15. **Given** the FastAPI route, **When** receiving the request, **Then** the router handler must wrap the service call exactly like [`routers/recently_added.py:23-30`](../../backend/routers/recently_added.py#L23-L30) — catch `ValueError` → 401, catch `SpotifyException` with `http_status == 404` → 404 with `"Playlist not found"`, catch any other `SpotifyException` → 502 with `f"Spotify error: {exc.msg}"`. Order of `except` blocks matters: put `SpotifyException` 404 check inside one except block that branches on `http_status`, or use two separate `except SpotifyException as exc` clauses (Python disallows duplicate except types — must use one block with `if exc.http_status == 404`). [Source: routers/recently_added.py:23-30 + services/spotify.py:298-303 reference 404 pattern]

16. **Given** the new file `backend/tests/test_story_9_1.py`, **When** the developer runs `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_9_1.py -v`, **Then** all tests pass. The test file must cover:
    - **Router-level (service mocked):**
      - `test_returns_200_and_array_for_regular_playlist` — mock service returns 2-track payload, assert 200 + exact JSON shape (all keys present, no wrapper, snake_case).
      - `test_returns_404_when_playlist_not_found` — mock service raises `SpotifyException(http_status=404, ...)`, assert 404 + detail.
      - `test_returns_401_when_not_authenticated` — mock service raises `ValueError("Not authenticated")`, assert 401.
      - `test_returns_502_on_non_404_spotify_error` — mock service raises `SpotifyException(http_status=500, ..., msg="boom")`, assert 502 + "boom" in detail.
      - `test_liked_songs_sentinel_routes_to_service` — call `GET /api/v1/playlists/liked_songs/tracks`, verify the service is called with `playlist_id="liked_songs"` (or that the right code path runs — assert via mock).
    - **Service-level (spotipy mocked):**
      - `test_service_paginates_and_concatenates_for_regular_playlist` — mock `sp.playlist_items` to return two pages (e.g. 100 + 50), assert flat list of 150 with correct order.
      - `test_service_skips_null_and_local_tracks` — mirror `test_story_8_2.py::test_service_skips_null_and_local_tracks` adapted for the new function.
      - `test_service_sets_image_url_null_when_no_album_images` — mirror Story 8.2 precedent.
      - `test_service_flattens_artists_to_names` — mirror Story 8.2 precedent.
      - `test_service_liked_songs_uses_saved_tracks_api` — when `playlist_id == "liked_songs"`, assert `sp.current_user_saved_tracks` is called (not `sp.playlist_items`), and that the rich shape is still produced.
      - `test_service_raises_spotify_exception_on_404_probe` — when `sp.playlist(...)` probe raises 404, assert the service re-raises `SpotifyException` (so the router can translate to 404).
      - `test_service_reraises_non_404_spotify_exception` — mirror Story 8.2 precedent.

    Use the **exact same fixtures pattern** as `tests/test_story_8_2.py` (session + client + dependency_overrides + `_make_track` helper). Mock spotipy via `patch.object(svc, "engine", engine), patch.object(svc, "get_authenticated_client", return_value=mock_sp)`. Mock the router-level service via `patch("routers.playlists.spotify_service.get_playlist_tracks_full", ...)`. [Source: CLAUDE.md#Tests "Pattern fixtures établi dans test_story_2_4.py / test_story_3_1.py" + tests/test_story_8_2.py as the direct precedent]

17. **Given** the full backend regression suite, **When** the developer runs `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`, **Then** **all existing tests still pass** (current count: 115+ per Story 8.6's record). Story 9.1 must not modify any existing service function, model, router, or test — only add new artifacts. [Source: CLAUDE.md#Tests + Story 8.6 final test count]

18. **Given** the Postman collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`, key in `.mcp.json`), **When** Story 9.1 ships, **Then** **add a new request** named **`GET Playlist Tracks`** under a sensible folder:
    - First, `GET https://api.getpostman.com/collections/{uid}` to find the existing folder structure (Stories 8.x landed Recently Added / Blacklist folders — the "Playlists" folder exists per Story 3.1).
    - Add the new request **inside the existing "Playlists" folder**:
      - Method: `GET`
      - URL: `{{baseUrl}}/api/v1/playlists/:spotify_id/tracks` (use Postman's path-variable syntax with `:spotify_id`)
      - Path variable: `spotify_id` with description "Spotify playlist id, or `liked_songs` for the user's Liked Songs library"
      - Description (request body): "Returns every track of the given playlist in the same JSON shape as `GET /recently-added`. Pass the sentinel `liked_songs` to fetch the user's Liked Songs library. Returns 200 + array, 401 if not authenticated, 404 if playlist not found, 502 on Spotify error."
      - Example response (200, success): one or two example tracks matching AC #1 shape exactly.
    - `PUT https://api.getpostman.com/collections/{uid}` with the modified collection.
    - Verify by re-GETting the collection and confirming the new request appears.
    - Document the Postman change in "Completion Notes List" with the request name and folder location.

    [Source: CLAUDE.md#Postman "à chaque story qui ajoute ou modifie des routes API, mettre à jour la collection Postman" + memory `feedback_postman_sync` (PUT required because API surface changes) + .mcp.json (POSTMAN_API_KEY)]

19. **Given** the running stack via `docker-compose up`, **When** the developer manually smokes the endpoint, **Then**:
    - (a) `curl -s http://127.0.0.1:8000/api/v1/playlists/{some_real_playlist_id}/tracks | jq '. | length'` → returns a positive integer matching the playlist's track count (within the bounds of skipped null/local entries).
    - (b) `curl -s http://127.0.0.1:8000/api/v1/playlists/{id}/tracks | jq '.[0] | keys'` → returns the exact 9-key set from AC #1.
    - (c) `curl -s http://127.0.0.1:8000/api/v1/playlists/liked_songs/tracks | jq '. | length'` → returns the user's Liked Songs count (e.g. 535 for the user's account per epics.md note).
    - (d) `curl -i http://127.0.0.1:8000/api/v1/playlists/nonexistent_id/tracks` → HTTP `404` with `{"detail":"Playlist not found"}`.
    - (e) `curl -i http://127.0.0.1:8000/api/v1/playlists/{id}/tracks` after revoking auth → HTTP `401`.
    - Paste outputs into Completion Notes List.
    [Source: CLAUDE.md#Lancer-le-projet (Docker stack) + AC #1, #2, #3, #4 contracts]

20. **Given** TypeScript / frontend, **When** Story 9.1 ships, **Then** **zero frontend code changes**. The new endpoint is purely backend — Story 9.2 (component refactor) and Story 9.3 (new page + hook) own all frontend integration. Do **NOT** add a hook, do **NOT** add a route, do **NOT** touch `lib/api.ts`. Verify by running `git status` after implementation — only `backend/**`, `_bmad-output/**`, and (if applicable) the Postman side effect should appear. [Source: epics.md#Story-9.1 vs Story-9.3 scope split + CLAUDE.md#Frontend "Tous les fetch via lib/api.ts" — applies when the consumer exists, here it doesn't yet]

## Tasks / Subtasks

- [x] **Task 1: Add `get_playlist_tracks_full` to `services/spotify.py`** (AC: #1, #2, #6, #7, #8, #9, #10, #11, #14)
  - [x] Open [`backend/services/spotify.py`](../../backend/services/spotify.py) and locate `get_recently_added_tracks()` at line 284 — use it as the reference template.
  - [x] At module scope (above or near `get_recently_added_tracks`), add a small private helper:
    ```python
    def _build_track_row(track: dict, added_at: str) -> dict:
        album = track.get("album") or {}
        images = album.get("images") or []
        artists = [a.get("name") for a in (track.get("artists") or []) if a.get("name")]
        return {
            "spotify_id": track["id"],
            "title": track.get("name", ""),
            "artists": artists,
            "album": album.get("name", ""),
            "image_url": images[0]["url"] if images else None,
            "added_at": added_at or "",
            "duration_ms": int(track.get("duration_ms") or 0),
            "explicit": bool(track.get("explicit", False)),
            "has_video": bool(track.get("is_video", False)),
        }
    ```
  - [x] Add the new function:
    ```python
    def get_playlist_tracks_full(playlist_id: str) -> list[dict]:
        """Return every track of a playlist (or Liked Songs) as full rich-shape dicts.

        Mirrors get_recently_added_tracks shape. For LIKED_SONGS_ID, uses the
        saved-tracks API. Re-raises SpotifyException on 404 (router translates to
        HTTP 404) and on other Spotify errors (router → 502).
        """
        sp = get_authenticated_client()
        results: list[dict] = []
        limit = 50 if playlist_id == LIKED_SONGS_ID else 100
        offset = 0

        if playlist_id == LIKED_SONGS_ID:
            while True:
                page = sp.current_user_saved_tracks(limit=limit, offset=offset)
                for item in page["items"]:
                    if item is None:
                        continue
                    track = item.get("track")
                    if not track or not track.get("id") or track.get("is_local"):
                        continue
                    results.append(_build_track_row(track, item.get("added_at") or ""))
                if page.get("next") is None:
                    break
                offset += limit
            return results

        # Existence probe — let SpotifyException propagate (router handles 404 vs 502)
        sp.playlist(playlist_id, fields="id")

        while True:
            page = sp.playlist_items(
                playlist_id,
                limit=limit,
                offset=offset,
                fields=(
                    "items(added_at,is_local,"
                    "track(id,name,duration_ms,explicit,is_local,is_video,"
                    "artists(name),album(name,images)),"
                    "item(id,name,duration_ms,explicit,is_local,is_video,"
                    "artists(name),album(name,images))),next"
                ),
            )
            for item in page["items"]:
                if item is None or item.get("is_local"):
                    continue
                track = item.get("track") or item.get("item")
                if not track or not track.get("id") or track.get("is_local"):
                    continue
                results.append(_build_track_row(track, item.get("added_at") or ""))
            if page.get("next") is None:
                break
            offset += limit
        return results
    ```
  - [x] Do **NOT** refactor `get_recently_added_tracks()` to share `_build_track_row` in this story. (Optional follow-up only — keep diffs surgical.)

- [x] **Task 2: Add the route to `routers/playlists.py`** (AC: #1, #3, #4, #5, #12, #13, #15)
  - [x] Open [`backend/routers/playlists.py`](../../backend/routers/playlists.py).
  - [x] Add `from spotipy import SpotifyException` to the imports (currently absent — check existing imports first).
  - [x] Add the response model below the existing `PlaylistRead` / `PlaylistPatch`:
    ```python
    class PlaylistTrack(BaseModel):
        spotify_id: str
        title: str
        artists: list[str]
        album: str
        image_url: Optional[str] = None
        added_at: str
        duration_ms: int
        explicit: bool
        has_video: bool
    ```
  - [x] Add the route handler:
    ```python
    @router.get("/playlists/{spotify_id}/tracks", response_model=list[PlaylistTrack])
    def get_playlist_tracks(spotify_id: str) -> list[PlaylistTrack]:
        try:
            tracks = spotify_service.get_playlist_tracks_full(spotify_id)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc))
        except SpotifyException as exc:
            if exc.http_status == 404:
                raise HTTPException(status_code=404, detail="Playlist not found")
            raise HTTPException(status_code=502, detail=f"Spotify error: {exc.msg}")
        return [PlaylistTrack(**t) for t in tracks]
    ```
  - [x] Do **NOT** import `RecentlyAddedTrack` from `routers.recently_added`. Per AC #13, the two response models stay decoupled.

- [x] **Task 3: Write `backend/tests/test_story_9_1.py`** (AC: #16)
  - [x] Copy the fixture block (`engine`, `session`, `client`) from [`backend/tests/test_story_8_2.py:13-36`](../../backend/tests/test_story_8_2.py#L13-L36) verbatim.
  - [x] Reuse / adapt the `_make_track` and `_seed_config` helpers from `test_story_8_2.py:131-149`.
  - [x] Implement all 11 test cases listed in AC #16 (5 router-level + 6 service-level). (12 implemented — added an extra liked-songs router-level routing assertion.)
  - [x] For router-level mocks: `patch("routers.playlists.spotify_service.get_playlist_tracks_full", ...)`.
  - [x] For service-level: `patch.object(svc, "get_authenticated_client", return_value=mock_sp)` (no engine patch needed since the new function does not touch SQLModel — unlike `get_recently_added_tracks` which reads `Config.dynamic_playlist_id`).
  - [x] For the `liked_songs` test: mock `mock_sp.current_user_saved_tracks` and assert `mock_sp.playlist_items.assert_not_called()` to prove the branch.

- [x] **Task 4: Run tests** (AC: #16, #17)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_9_1.py -v` → all green.
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → 115+ → 127 all green, zero regressions.
  - [x] Paste counts into Completion Notes.

- [x] **Task 5: Manual smoke against the running stack** (AC: #19)
  - [x] `docker-compose up -d` (if not already running).
  - [x] Run curl probes (a)–(e) from AC #19. Paste outputs into Completion Notes.
  - [x] If `(c)` Liked Songs takes >10s, document the timing — Story 9.6 will introduce virtualization but server-side time is still relevant.

- [x] **Task 6: Update Postman collection** (AC: #18)
  - [x] `GET https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` (use `POSTMAN_API_KEY` from `.mcp.json`).
  - [x] Locate the "Playlists" folder. Add a new request **`GET Playlist Tracks`** following the spec in AC #18 (method, URL with path var, description, 200 example).
  - [x] `PUT` the modified collection.
  - [x] Re-GET to verify the new request appears under "Playlists".
  - [x] Document name + folder in Completion Notes.

- [x] **Task 7: Final verification** (AC: #20)
  - [x] `git status` — confirm only `backend/services/spotify.py`, `backend/routers/playlists.py`, `backend/tests/test_story_9_1.py`, and BMad output files appear. Zero frontend changes.
  - [x] Move story to `review` in `sprint-status.yaml` (done by the wrap-up step of the dev workflow).

## Dev Notes

### Architecture & Conventions

- **Backend-only story.** Story 9.1 ships a backend API surface; Stories 9.2 (component refactor) and 9.3 (Playlist Detail page + hook) consume it. Resist the urge to scaffold frontend ahead of those stories.
- **Endpoint shape is the contract.** AC #1 fixes the response shape **identical** to `/recently-added`. That is the entire point of this story — Story 9.2 and 9.3 are free of any backend adapter once this shape lands.
- **Two distinct `get_playlist_tracks*` functions in `services/spotify.py`.** The existing `get_playlist_tracks(playlist_id, sp=None, since=None)` (line 217) is the **sync engine's** lean fetcher returning only `{spotify_id, uri, added_at}`. The new `get_playlist_tracks_full(playlist_id)` returns the **rich UI shape**. They serve orthogonal callers; the naming suffix `_full` is the disambiguator. **Do NOT** merge them — the sync engine path has an `since=` early-stop optimization that would bloat the UI path.
- **404 translation differs from `/recently-added`.** Recently Added swallows a 404 (`return []`) because that endpoint represents "current contents of the dynamic playlist, which may have been deleted" — empty is a valid state. For Story 9.1, a 404 means the user asked for a playlist that doesn't exist (or isn't accessible) — that's a real client error and surfaces as HTTP 404 (AC #3).
- **`liked_songs` sentinel literal — match the codebase, not the epic hint.** Epics says `"liked"` (or similar) — the actual constant is `LIKED_SONGS_ID = "liked_songs"` ([`services/spotify.py:12`](../../backend/services/spotify.py#L12)) and the frontend already filters on `spotifyId === 'liked_songs'` ([`PlaylistGrid.tsx:19`](../../frontend/src/features/playlists/PlaylistGrid.tsx#L19), [`HiddenPlaylistsAccordion.tsx:14`](../../frontend/src/features/playlists/HiddenPlaylistsAccordion.tsx#L14)). Use **`liked_songs`**.
- **`current_user_saved_tracks` ≠ `playlist_items` schema.** The saved-tracks endpoint returns items with a `track` key only (no `item` fallback like the playlist endpoint provides). The pagination cap is 50 (not 100). Mirror these in the liked-songs branch.
- **Pydantic model layering.** `PlaylistTrack` is declared inside `routers/playlists.py` (AC #13) — duplicating the field list with `RecentlyAddedTrack` once is cheaper than coupling the two routers. Story 9.2 may collapse them on the frontend; the backend stays decoupled.

### Source Tree — Files to Touch

- ✏️ [`backend/services/spotify.py`](../../backend/services/spotify.py) — add `_build_track_row` helper and `get_playlist_tracks_full(playlist_id)`. ~70 lines added. Do NOT modify the existing `get_recently_added_tracks` or `get_playlist_tracks`.
- ✏️ [`backend/routers/playlists.py`](../../backend/routers/playlists.py) — add `from spotipy import SpotifyException`, add `PlaylistTrack` Pydantic model, add `get_playlist_tracks` handler. ~30 lines added.
- ➕ [`backend/tests/test_story_9_1.py`](../../backend/tests/test_story_9_1.py) — new test file mirroring `test_story_8_2.py` structure. ~250 lines.
- 🔒 [`backend/routers/recently_added.py`](../../backend/routers/recently_added.py) — **do not touch**. Keep the two endpoints decoupled (AC #13).
- 🔒 `frontend/**` — **do not touch** (AC #20).
- 🔒 `backend/models/**`, `backend/database.py`, `backend/scheduler.py`, `backend/services/sync_engine.py`, `backend/services/blacklist_service.py`, `backend/services/token_manager.py` — no change.

### Code Sketches

(See Task 1 and Task 2 for full code blocks.)

**Router-level test pattern (mirror of `test_story_8_2.py::test_returns_tracks_with_exact_shape`):**

```python
def test_returns_200_and_array_for_regular_playlist(client):
    payload = [
        {
            "spotify_id": "t1", "title": "Song", "artists": ["A"],
            "album": "Album", "image_url": "https://i.scdn.co/x.jpg",
            "added_at": "2026-05-20T10:00:00Z", "duration_ms": 200000,
            "explicit": False, "has_video": False,
        }
    ]
    with patch(
        "routers.playlists.spotify_service.get_playlist_tracks_full",
        return_value=payload,
    ):
        r = client.get("/api/v1/playlists/abc123/tracks")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert set(body[0].keys()) == {
        "spotify_id", "title", "artists", "album", "image_url",
        "added_at", "duration_ms", "explicit", "has_video",
    }
```

**Service-level test for `liked_songs` branch:**

```python
def test_service_liked_songs_uses_saved_tracks_api():
    from services import spotify as svc

    mock_sp = MagicMock()
    mock_sp.current_user_saved_tracks.return_value = {
        "items": [
            {"added_at": "2026-05-20T10:00:00Z", "track": {
                "id": "t1", "name": "Liked",
                "duration_ms": 180000, "explicit": False, "is_local": False, "is_video": False,
                "artists": [{"name": "A"}],
                "album": {"name": "Alb", "images": [{"url": "https://img/t1.jpg"}]},
            }},
        ],
        "next": None,
    }

    with patch.object(svc, "get_authenticated_client", return_value=mock_sp):
        result = svc.get_playlist_tracks_full("liked_songs")

    assert len(result) == 1
    assert result[0]["spotify_id"] == "t1"
    assert result[0]["title"] == "Liked"
    mock_sp.playlist_items.assert_not_called()
    mock_sp.playlist.assert_not_called()
```

### Testing Standards

- **Test harness:** `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` per CLAUDE.md.
- **Fixture pattern:** `tests/test_story_8_2.py` is the canonical precedent — copy `engine`/`session`/`client` fixtures verbatim (CLAUDE.md notes `test_story_2_4.py` / `test_story_3_1.py` as the original pattern; `test_story_8_2.py` is the freshest expression of it for a router that mocks a service).
- **Mock strategy:** Router-level tests mock `spotify_service.get_playlist_tracks_full` directly. Service-level tests mock `get_authenticated_client` to return a `MagicMock` Spotify client. No real network calls.
- **No frontend tests** for this story (frontend is untouched).

### Previous Story Intelligence

- **Story 8.2 (Recently Added API)** — direct architectural twin. `routers/recently_added.py` (30 lines) + `services/spotify.get_recently_added_tracks()` (60 lines) + `tests/test_story_8_2.py` (290 lines) is the template. Story 9.1 essentially clones that triangle for `/playlists/{id}/tracks`, with three deltas: (1) 404 surfaces as HTTP 404 instead of `[]`, (2) `liked_songs` sentinel routing, (3) lives in `routers/playlists.py` instead of a new router file.
- **Story 8.6 (Recently Added Performance & Polish)** — established the final 115-test count baseline and the "no-PUT when no API surface change" Postman discipline. Story 9.1 inverts that: it **does** change the API surface, so a Postman PUT **is** required (AC #18).
- **Story 8.5 (Sync Integration — Blacklist Filter)** — proves the sync engine + spotipy mocking patterns used in `tests/test_story_8_5.py`. Useful reference if any test wants to assert spotipy call args precisely.
- **Story 7.1 (Playlist Hidden State Schema/API)** — last story to touch `routers/playlists.py`. Confirms the file is the right home for playlist-scoped routes.
- **Story 1.4 / 3.1** — established the `LIKED_SONGS_ID = "liked_songs"` sentinel via the playlists-list endpoint surfacing "Titres likés" as a synthetic row. Story 9.1 extends that convention to the tracks-of-playlist endpoint.

### Git Intelligence

Recent commits (newest first, via `git log --oneline -5`):

- `18dea64 feat: Epic 8 — page Recently Added avec table, blacklist par track et hooks dédiés` — landed Stories 8.x including the `routers/recently_added.py` template you're cloning. **Read `routers/recently_added.py:1-30` and `services/spotify.py:284-345` first** — they are the single most relevant 90 lines in the repo for this story.
- `f1a7caa fix: adaptation au changement d'API Spotify (track → item) + backfill sync` — taught us that Spotify's playlist-items API can return tracks under EITHER `item["track"]` OR `item["item"]` (legacy/new). The `track = item.get("track") or item.get("item")` line at `services/spotify.py:324` reflects that. **Mirror this fallback in `get_playlist_tracks_full`'s playlist branch** — the liked-songs branch needs only `item["track"]` (saved-tracks API does not use the `item` fallback).
- `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — introduced `LIKED_SONGS_ID` and `_get_liked_tracks` (minimal shape, sync-only). Confirms `liked_songs` is the codebase sentinel.
- `76facf6 feat: Epics 6 & 7 — UI refonte` — frontend-only, irrelevant.
- `ccbbf60 feat: Stories 2-3 → 5-3 — Auth, Playlists, Sync, Scheduler & Observability` — the foundational backend layer. `spotipy` and `SpotifyException` exception handling pattern dates from here.

Working tree status at story creation time: Epic 8 work is committed; sprint-status.yaml, epics.md, prd.md, ux-design/README.md, and a sprint-change-proposal-2026-05-25.md have uncommitted edits (the Epic 9 planning artifacts — already on disk, do not re-edit).

### Latest Tech Information

- **`spotipy` library** — `Spotify.playlist_items(playlist_id, limit, offset, fields)` and `Spotify.current_user_saved_tracks(limit, offset)` are stable Spotify Web API wrappers. `playlist_items` caps at `limit=100`, `current_user_saved_tracks` caps at `limit=50`. Both return `{items: [...], next: <url|null>, total: int, limit, offset}`. Pagination via incrementing `offset` until `next is None` is the canonical pattern (used at `services/spotify.py:309-344`). [Source: spotipy reference docs + Spotify Web API "Get Playlist Items" / "Get User's Saved Tracks"]
- **`SpotifyException` shape** — `spotipy.exceptions.SpotifyException(http_status: int, code: int, msg: str, ...)`. `http_status` is the HTTP status of the failing call. The 404 branch in `services/spotify.py:298-303` (existence probe) is the precedent for AC #3 / AC #15 translation logic.
- **FastAPI path params with literal sentinels** — no special declaration needed. The handler signature `def get_playlist_tracks(spotify_id: str)` accepts both real Spotify ids (alphanumeric base62) and the `liked_songs` sentinel. The service does the branch, not the router. Avoids URL design contortions like `/playlists/liked-songs/tracks` (which would also work but mismatches the existing PlaylistGrid wiring).
- **`response_model=list[PlaylistTrack]`** — FastAPI will validate the outgoing payload and **strip any extra keys** the dicts might carry. Since `_build_track_row` returns exactly the 9 keys of `PlaylistTrack`, no stripping happens — but the validator still catches type drift early (e.g. if Spotify ever returns `duration_ms: None`, the `int(... or 0)` cast in the helper prevents the validation error).

### Project Structure Notes

- ✅ Backend layering preserved: business logic in `services/`, only orchestration + HTTP translation in `routers/` (per CLAUDE.md#Backend).
- ✅ Snake_case JSON throughout (per CLAUDE.md#Backend).
- ✅ Array response, no wrapper (per CLAUDE.md#Backend).
- ✅ All spotipy calls go through `services/spotify.py` (per CLAUDE.md#Backend).
- ⚠️ **Do NOT** add `Depends(get_session)` to the new handler — `get_playlist_tracks_full` does not read from SQLite (unlike `get_recently_added_tracks` which reads `Config.dynamic_playlist_id`). Adding `session: SessionDep` would be a no-op signature pollution.
- ⚠️ **Do NOT** add query params (`?limit=`, `?offset=`) to the FastAPI route — AC #6 mandates a single full payload. Pagination happens server-side, not at the HTTP boundary.
- ⚠️ **Do NOT** introduce caching (Redis, in-memory LRU, etc.) — out of scope. Story 9.6 owns performance; Story 9.1 is correctness only.
- ⚠️ **Do NOT** rename `LIKED_SONGS_ID` or the `liked_songs` literal anywhere — frontend `PlaylistGrid.tsx` and `HiddenPlaylistsAccordion.tsx` already filter on it; the playlists-list endpoint emits it. Any rename is a multi-story coordinated change.

### Project Context Reference

See [`CLAUDE.md`](../../CLAUDE.md) for project-wide development rules. Most relevant sections for this story:

- **Backend** — "Business logic dans `services/`, jamais dans `routers/`"; "Tous les appels spotipy passent par `services/spotify.py`"; "Champs JSON en snake_case partout"; "Réponses sans wrapper : array direct". All four enforced by ACs #1, #11, #14, #15.
- **Tests** — `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`. Pattern fixture: `test_story_2_4.py` / `test_story_3_1.py` (CLAUDE.md) — `test_story_8_2.py` is the freshest direct precedent.
- **Postman** — full procedure for the PUT lives in CLAUDE.md#Postman; AC #18 lays out the per-request spec.

User-memory rules in effect for this story:

- [`feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md) — N/A (no frontend, no shadcn).
- [`feedback_node_version`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_node_version.md) — N/A (no frontend build).
- [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md) — **applies**: new endpoint = mandatory PUT (AC #18).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-9.1] — primary ACs (lines 1443–1453).
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-9] — epic framing (lines 1435–1441) + FR/AR/NFR map (line 1439).
- [Source: _bmad-output/planning-artifacts/prd.md lines 146-150, 181-183] — FR44–FR48 / AR13–AR14 / NFR16 origin.
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-05-25.md Section 3] — Epic 9 effort + risk estimate; confirms Story 9.1 is "S (1–2h), Bas risque — pattern `recently_added.py` réutilisable presque tel quel".
- [Source: _bmad-output/implementation-artifacts/8-2-recently-added-api.md] — twin story; not re-read end-to-end here but referenced as the template.
- [Source: backend/routers/recently_added.py:1-30] — router + Pydantic model template.
- [Source: backend/services/spotify.py:12] — `LIKED_SONGS_ID = "liked_songs"` constant.
- [Source: backend/services/spotify.py:195-214] — `_get_liked_tracks` minimal-shape precedent (sync-only).
- [Source: backend/services/spotify.py:217-281] — existing `get_playlist_tracks` (minimal shape; do NOT collide names).
- [Source: backend/services/spotify.py:284-345] — `get_recently_added_tracks` rich-shape template.
- [Source: backend/routers/playlists.py:1-50] — existing router structure; `PlaylistTrack` model + handler land here.
- [Source: backend/tests/test_story_8_2.py] — direct test-file template (fixtures + router-mock + service-mock layout).
- [Source: backend/main.py:42] — `playlists_router` mounted at `/api/v1`.
- [Source: frontend/src/features/playlists/PlaylistGrid.tsx:19] — confirms `'liked_songs'` UI sentinel literal.
- [Source: CLAUDE.md#Backend, #Tests, #Postman] — project conventions.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

- Smoke probe (d) initially returned HTTP 502 with `"Unsupported URL / URI."` for the placeholder id `nonexistent_id`. That is correct behavior: Spotify rejects a malformed id with a non-404 status, so the router correctly translates to 502. Re-running the probe with a syntactically valid but unused base62 id (`0000000000000000000000`) returned HTTP 404 + `{"detail":"Playlist not found"}` as specified by AC #3.

### Completion Notes List

- **Service**: added `_build_track_row(track, added_at)` helper and `get_playlist_tracks_full(playlist_id)` in [`backend/services/spotify.py`](../../backend/services/spotify.py). `get_recently_added_tracks` left untouched as instructed (no shared-helper refactor in this story).
- **Router**: added `from spotipy import SpotifyException`, `PlaylistTrack` Pydantic model, and `GET /playlists/{spotify_id}/tracks` handler in [`backend/routers/playlists.py`](../../backend/routers/playlists.py). Lives inside the existing `playlists` router; no new router file.
- **Tests**: [`backend/tests/test_story_9_1.py`](../../backend/tests/test_story_9_1.py) — 12 tests (5 router + 7 service). All green. Full suite: **127 passed** (up from 115; +12 new).
- **Smoke** (live stack, real Spotify session):
  - (a) `GET /api/v1/playlists/2NHiKi28QEBvBXbUhMyTuM/tracks` → 200, `len = 50`.
  - (b) Keys returned: `['added_at','album','artists','duration_ms','explicit','has_video','image_url','spotify_id','title']` — exact 9-key set per AC #1.
  - (c) `GET /api/v1/playlists/liked_songs/tracks` → 200, `len = 535` (matches user's Liked Songs total, sub-second response — no timing issue worth flagging for Story 9.6).
  - (d) `GET /api/v1/playlists/0000000000000000000000/tracks` → `HTTP 404` + `{"detail":"Playlist not found"}`. (See Debug Log re: malformed-id behavior.)
  - (e) 401 path covered by router-level unit test (`test_returns_401_when_not_authenticated`); not re-tested live since the live session is currently authenticated.
- **Postman**: added request **`GET Playlist Tracks`** under the **`Playlists`** folder in collection UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`. URL uses `:spotify_id` path variable; description covers the `liked_songs` sentinel and the 200 / 401 / 404 / 502 contracts; 200 / 404 / 401 example responses included. PUT returned 200 OK; re-GET confirms the request is present alongside `List Playlists` and `Patch Playlist (Include / Hide)`.
- **Scope discipline**: zero frontend changes (verified — only `backend/services/spotify.py`, `backend/routers/playlists.py`, `backend/tests/test_story_9_1.py`, sprint-status.yaml, and this story file changed). No DB models, no migrations, no scheduler/sync-engine edits.

### File List

- `backend/services/spotify.py` (modified) — added `_build_track_row` helper and `get_playlist_tracks_full`.
- `backend/routers/playlists.py` (modified) — added `SpotifyException` import, `PlaylistTrack` model, and `GET /playlists/{spotify_id}/tracks` handler.
- `backend/tests/test_story_9_1.py` (new) — 12 router + service tests.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified) — story status transitions.
- `_bmad-output/implementation-artifacts/9-1-playlist-tracks-api.md` (modified) — Dev Agent Record / status / task checkboxes.
- Postman collection `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` (side-effect, external) — added `GET Playlist Tracks` under `Playlists`.

### Change Log

| Date       | Change                                                              |
|------------|---------------------------------------------------------------------|
| 2026-05-26 | Implemented Story 9.1: `GET /api/v1/playlists/{spotify_id}/tracks` endpoint, `liked_songs` sentinel branch, 12 new tests (127 total, zero regressions), Postman request added. |
| 2026-05-26 | Spec superseded by Story 9.8: the "full list returned to client" contract is replaced by paginated response (`?limit&offset` → `{items, next_offset, total}`). See `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-26-playlist-tracks-pagination.md`. |
