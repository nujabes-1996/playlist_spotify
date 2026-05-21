# Story 7.1: Playlist Hidden State — Schema & API

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want a persistent `is_hidden` flag on each playlist exposed via the API,
so that the frontend can render hidden vs visible playlists and the sync engine can honor the exclusion rule.

## Acceptance Criteria

1. **Given** the `playlist` table schema, **When** the backend starts after this story is shipped, **Then** the table has a new column `is_hidden` (bool, NOT NULL, default `false`) — added via SQLModel auto-create on startup (`SQLModel.metadata.create_all()` in [`backend/database.py`](../../backend/database.py)). Existing rows must default to `false` (use `sa_column_kwargs={"server_default": "0"}` on the SQLModel `Field` so SQLite ALTER TABLE on an existing DB does not fail with a NOT NULL violation on legacy rows). [Source: epics.md#Story-7.1 + architecture.md#Data-Architecture]

2. **Given** `GET /api/v1/playlists`, **When** the endpoint is called, **Then** the response is an array (no wrapper) where each object includes the existing fields PLUS `is_hidden` (bool), `image_url` (string | null — playlist cover image URL from Spotify), and `track_count` (int — total tracks in the playlist). Field names use snake_case throughout (no camelCase). [Source: architecture.md#Format-Patterns + CLAUDE.md#Backend]

3. **Given** [`backend/services/spotify.py`](../../backend/services/spotify.py)'s `get_user_playlists()`, **When** it returns the list, **Then** each entry includes `spotify_id`, `name`, `image_url` (taken from `item["images"][0]["url"]` if `images` is non-empty, else `None`), and `track_count` (taken from `item["tracks"]["total"]`). The synthetic "Titres likés" entry (id `LIKED_SONGS_ID = "liked_songs"`) MUST set `image_url=None` and `track_count` equal to `sp.current_user_saved_tracks(limit=1)["total"]` (one extra API call, gated to once per `get_user_playlists()` invocation — do NOT call it inside the playlist loop). All Spotify API calls remain inside `services/spotify.py` — no spotipy import in routers. [Source: architecture.md#Enforcement-Guidelines + existing spotify.py:74-94]

4. **Given** `GET /api/v1/playlists` in [`backend/routers/playlists.py`](../../backend/routers/playlists.py), **When** it upserts rows, **Then** the upsert logic preserves the persisted `is_included` AND `is_hidden` values on existing rows (only `name` is refreshed from Spotify). The `image_url` and `track_count` are NOT persisted in the DB — they are pass-through fields populated from the Spotify response and merged into the response model just-in-time. New rows default to `is_included=False`, `is_hidden=False`. [Source: existing playlists.py:32-47 + Story 3.1 patterns]

5. **Given** `PATCH /api/v1/playlists/{spotify_id}`, **When** the request body contains `{"is_hidden": true}`, **Then** the playlist row updates `is_hidden=true` AND `is_included=false` atomically in a single `session.commit()` (FR27 — hidden implies excluded). The response echoes the updated row (same shape as items in step 2, but `image_url` and `track_count` MAY be omitted or set to `null` in the PATCH response — the frontend re-fetches `['playlists']` after the mutation; keep the PATCH response strictly DB-derived to avoid an extra Spotify call inside the PATCH handler). [Source: epics.md#Story-7.1 AC #3 + FR27]

6. **Given** `PATCH /api/v1/playlists/{spotify_id}`, **When** the request body contains `{"is_hidden": false}` (unhide), **Then** the row updates `is_hidden=false` and leaves `is_included` untouched at its current value (which, per AC #5, will normally be `false` — the user must explicitly re-toggle include — FR29). [Source: epics.md#Story-7.1 AC #4 + FR29]

7. **Given** `PATCH /api/v1/playlists/{spotify_id}`, **When** the request body contains both `{"is_included": ..., "is_hidden": ...}` or only `{"is_included": ...}`, **Then** the existing Story 3.1 behavior is preserved (toggle `is_included`); when ONLY `is_hidden` is supplied, `is_included` is ONLY auto-cleared if `is_hidden` is being set to `true` (AC #5). Both fields are optional on the `PlaylistPatch` Pydantic model (use `Optional[bool]` with default `None`); a request body of `{}` is a no-op that returns the unchanged row with HTTP 200. [Source: existing playlists.py:18-19 + Story 3.1 contract]

8. **Given** [`backend/services/sync_engine.py`](../../backend/services/sync_engine.py) `run_sync()`, **When** it queries selected playlists at line ~69 (`select(Playlist).where(Playlist.is_included == True)`), **Then** the WHERE clause is extended to `where(Playlist.is_included == True, Playlist.is_hidden == False)` so hidden playlists are excluded as defense-in-depth even though the API contract in AC #5 already clears `is_included` on hide. The existing SQLAlchemy boolean comparison style (`== True` / `== False` with `noqa: E712`) is preserved. [Source: epics.md#Story-7.1 AC #5 + existing sync_engine.py:69-71]

9. **Given** the persistence layer (`./data/playlist_spotify.db` host bind mount), **When** the Docker container restarts, **Then** all `is_hidden` values are preserved across restarts (FR30). This is verified implicitly by SQLite persistence + the `server_default` clause from AC #1; no extra wiring required. [Source: epics.md#Story-7.1 AC #6 + architecture.md#Containerization]

10. **Given** the test suite, **When** I run `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_7_1.py -v`, **Then** all tests pass. Tests MUST follow the established fixtures pattern from [`backend/tests/test_story_3_1.py`](../../backend/tests/test_story_3_1.py) (in-memory SQLite engine + `StaticPool` + `dependency_overrides`) and MUST mock all Spotify calls via `patch("routers.playlists.spotify_service.get_user_playlists", return_value=...)`. Test coverage MUST include: (a) GET returns `is_hidden=false` by default, `image_url` and `track_count` populated from mock; (b) GET preserves persisted `is_hidden=true` after a Spotify-side refresh; (c) PATCH `is_hidden=true` sets `is_included=false` atomically; (d) PATCH `is_hidden=false` does NOT flip `is_included` back; (e) PATCH with empty body returns 200 and is a no-op; (f) sync engine query excludes hidden playlists (covered in `services/sync_engine.py` unit test using an in-memory session — see existing engine tests like [`test_story_3_3.py`](../../backend/tests/test_story_3_3.py) or [`test_story_3_4.py`](../../backend/tests/test_story_3_4.py) for the engine-level pattern). [Source: CLAUDE.md#Tests + test_story_3_1.py pattern]

11. **Given** the Postman collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`), **When** this story is shipped, **Then** the `GET /api/v1/playlists` example response is updated to include `is_hidden`, `image_url`, and `track_count` for each item, AND the `PATCH /api/v1/playlists/{spotify_id}` request schema is updated to document the new optional `is_hidden` body field (with a second example body `{"is_hidden": true}` alongside the existing `{"is_included": true}` example). Use the MCP Postman tool if available, otherwise the REST API with the key in `.mcp.json`. Verify the update with a fresh `GET https://api.getpostman.com/collections/{uid}`. [Source: CLAUDE.md#Postman-Mise-à-jour-obligatoire]

12. **Given** any frontend consumer, **When** Story 7.1 ships in isolation (before Stories 7.2–7.5), **Then** the existing `frontend/src/features/playlists/PlaylistList.tsx` still works — the additional response fields (`is_hidden`, `image_url`, `track_count`) are simply ignored by today's TypeScript consumer; **no frontend changes are in scope for this story**. (Story 7.2 will introduce `PlaylistGrid` and consume these fields.) [Source: epics.md#Epic-7 sequencing + Story 6.4 AC #13]

## Tasks / Subtasks

- [x] **Task 1: Add `is_hidden` column to `Playlist` model** (AC: #1, #9)
  - [x] Edit [`backend/models/playlist.py`](../../backend/models/playlist.py): add `is_hidden: bool = Field(default=False, sa_column_kwargs={"server_default": "0"})` after the existing `is_included` line.
  - [x] Verify on a clean container start (`docker-compose down && docker-compose up`) that `SQLModel.metadata.create_all()` creates the column. For an existing `./data/playlist_spotify.db`, SQLite ALTER TABLE is NOT triggered by `create_all` — confirm legacy rows still load (the column will be absent until the DB is recreated; if the user has an existing DB, document in completion notes that they need to either delete `./data/playlist_spotify.db` OR manually `ALTER TABLE playlist ADD COLUMN is_hidden BOOLEAN NOT NULL DEFAULT 0;`). Prefer the simpler "delete the dev DB" path since this is a personal greenfield app — per architecture.md#Data-Architecture line 153–156 the project intentionally rejects Alembic.

- [x] **Task 2: Extend `services/spotify.py::get_user_playlists()` with image + track count** (AC: #3)
  - [x] Update the return-dict shape to `{"spotify_id", "name", "image_url", "track_count"}`.
  - [x] For Spotify-returned playlists: `image_url = item["images"][0]["url"] if item.get("images") else None`; `track_count = item["tracks"]["total"]`.
  - [x] For the synthetic Liked Songs entry: call `sp.current_user_saved_tracks(limit=1)["total"]` ONCE at the top of the function, use `image_url=None`.
  - [x] Do NOT touch [`get_playlist_tracks()`](../../backend/services/spotify.py) or any other function — only `get_user_playlists()` is in scope.

- [x] **Task 3: Update `routers/playlists.py` response + PATCH contract** (AC: #2, #4, #5, #6, #7)
  - [x] Extend `PlaylistRead` (Pydantic): add `is_hidden: bool`, `image_url: str | None = None`, `track_count: int | None = None`.
  - [x] Change `PlaylistPatch`: `is_included: Optional[bool] = None`, `is_hidden: Optional[bool] = None`.
  - [x] In `get_playlists`: build an in-memory map `spotify_id → (image_url, track_count)` from the spotipy result; after the upsert + commit, return rows merged with that map (legacy rows whose spotify_id is no longer in the map have already been deleted by the existing pruning loop, so the merge is total).
  - [x] In `toggle_playlist` (rename internally if you wish — but keep the route signature stable): apply the precedence from AC #5/#6/#7 — when `payload.is_hidden is True`, set `playlist.is_hidden = True` AND `playlist.is_included = False`; when `payload.is_hidden is False`, set `playlist.is_hidden = False` only; when `payload.is_included` is provided, apply it AFTER the hide logic (so an explicit `{"is_included": true, "is_hidden": false}` ends up included). Empty body is a no-op.
  - [x] PATCH response: return `PlaylistRead` with `image_url=None, track_count=None` (do NOT call Spotify inside PATCH — see AC #5).
  - [x] Confirm 404 behavior for unknown `spotify_id` is preserved (existing test in [`test_story_3_1.py`](../../backend/tests/test_story_3_1.py) `test_patch_nonexistent_returns_404`).

- [x] **Task 4: Extend sync engine WHERE clause** (AC: #8)
  - [x] In [`backend/services/sync_engine.py::run_sync()`](../../backend/services/sync_engine.py), change `select(Playlist).where(Playlist.is_included == True)` to `select(Playlist).where(Playlist.is_included == True, Playlist.is_hidden == False)  # noqa: E712`.
  - [x] No other engine logic changes — harvest/dedup/sort/slice/push are out of scope.

- [x] **Task 5: Write tests** (AC: #10)
  - [x] Create `backend/tests/test_story_7_1.py` mirroring the fixtures from [`test_story_3_1.py`](../../backend/tests/test_story_3_1.py).
  - [x] Cover the 6 cases enumerated in AC #10 (a–f). For (f), seed two `Playlist` rows directly via the test session (one with `is_included=True, is_hidden=False`, one with `is_included=True, is_hidden=True`) and assert the engine-side query returns only the first.
  - [x] Run: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_7_1.py -v` — must be all green.
  - [x] Run the full suite: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` — regressions in `test_story_3_1.py`, `test_story_3_3.py`, `test_story_3_4.py` MUST be triaged (the `PlaylistRead` shape changed — adjust expected JSON in those tests if/where they assert on full response objects).

- [x] **Task 6: Update Postman collection** (AC: #11)
  - [x] Pull current collection state: `GET https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`.
  - [x] Update `GET /api/v1/playlists` example response to include the three new fields.
  - [x] Update `PATCH /api/v1/playlists/{spotify_id}` body schema + add a second `{"is_hidden": true}` example.
  - [x] PUT the updated collection and re-GET to verify.

- [x] **Task 7: Manual smoke** (AC: #2, #5, #6, #9)
  - [x] `docker-compose up` (delete `./data/playlist_spotify.db` first if it predates this story).
  - [x] After Spotify OAuth, `curl http://127.0.0.1:8000/api/v1/playlists | jq '.[0]'` — confirm `is_hidden`, `image_url`, `track_count` keys.
  - [x] `curl -X PATCH http://127.0.0.1:8000/api/v1/playlists/<some_id> -H 'Content-Type: application/json' -d '{"is_hidden": true}'` — confirm both `is_hidden=true` AND `is_included=false` in a follow-up GET.
  - [x] Restart the container and re-GET — confirm `is_hidden=true` persists (AC #9).

## Dev Notes

### Architecture & Conventions

- **Models live in `backend/models/`** — one file per domain. `Playlist` already exists with `spotify_id` (unique), `name`, `is_included`. Add `is_hidden` there, NOT in a new file. [Source: architecture.md#Structure-Patterns]
- **Business logic in `services/`, never in `routers/`.** All Spotify calls go through [`services/spotify.py`](../../backend/services/spotify.py). The router stays a thin orchestration layer. [Source: CLAUDE.md#Backend + architecture.md#Enforcement-Guidelines]
- **JSON fields are snake_case at the API boundary** — `is_hidden`, `image_url`, `track_count`. No camelCase. No `{data: [...]}` wrapper — the array is returned directly. [Source: CLAUDE.md#Backend + architecture.md#Format-Patterns]
- **PATCH semantics** — partial update via `Optional[bool] = None`. The Story 3.1 contract `PlaylistPatch{is_included: bool}` becomes `PlaylistPatch{is_included: Optional[bool] = None, is_hidden: Optional[bool] = None}`; the request `{"is_included": true}` still validates (Pydantic ignores the missing optional). This is a backward-compatible change. [Source: existing playlists.py + Pydantic v2 semantics]
- **Sync engine query defense-in-depth** — even though the API contract guarantees `is_hidden=true ⇒ is_included=false`, the engine query checks both columns. This protects against direct DB edits and against future code paths that might set `is_hidden=true` without going through the PATCH handler. [Source: epics.md#Story-7.1 AC #5]

### Source Tree — Files to Touch

- ✏️ [`backend/models/playlist.py`](../../backend/models/playlist.py) — add `is_hidden` column.
- ✏️ [`backend/services/spotify.py`](../../backend/services/spotify.py) — extend `get_user_playlists()` return shape (lines ~74–94).
- ✏️ [`backend/routers/playlists.py`](../../backend/routers/playlists.py) — extend `PlaylistRead`, `PlaylistPatch`, GET, PATCH.
- ✏️ [`backend/services/sync_engine.py`](../../backend/services/sync_engine.py) — extend WHERE clause (line ~69–71).
- ➕ [`backend/tests/test_story_7_1.py`](../../backend/tests/test_story_7_1.py) — new test module.
- 🌐 Postman collection (external) — update via API per CLAUDE.md.

### Testing Standards

- Run tests inside the container: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` (per [CLAUDE.md#Tests](../../CLAUDE.md)).
- Fixtures pattern: in-memory SQLite (`sqlite://`) + `StaticPool` + `app.dependency_overrides[get_session]` — see [`test_story_3_1.py`](../../backend/tests/test_story_3_1.py) lines 12–30 for the canonical template.
- Mock Spotify: `patch("routers.playlists.spotify_service.get_user_playlists", return_value=MOCK)`. Do NOT call the real Spotify API in tests.
- Engine-level test: build the same SQLite session, seed `Playlist` rows directly, exercise the query — see [`test_story_3_3.py`](../../backend/tests/test_story_3_3.py) / [`test_story_3_4.py`](../../backend/tests/test_story_3_4.py) for examples.

### Project Structure Notes

- ✅ Aligns with [`architecture.md#Structure-Patterns`](../planning-artifacts/architecture.md): models → `backend/models/`, business logic → `backend/services/`, routes → `backend/routers/`, tests → `backend/tests/`.
- ✅ Naming: `is_hidden` matches the snake_case Boolean convention already used by `is_included`. Database column name auto-derives to `is_hidden`.
- ⚠️ **No migration tooling.** Per [`architecture.md#Data-Architecture`](../planning-artifacts/architecture.md) line 153–156 the project rejects Alembic and uses `SQLModel.metadata.create_all()` only. On an existing dev DB, the column will NOT be auto-added; the dev (or user) must drop `./data/playlist_spotify.db` OR run a one-shot `ALTER TABLE` manually. Document this in completion notes.
- ⚠️ **The PATCH response intentionally drops `image_url` / `track_count`.** This is a small contract asymmetry (GET has them, PATCH doesn't) to avoid an unnecessary Spotify round-trip inside the mutation handler. The frontend re-queries `['playlists']` after a successful mutation via TanStack Query's `invalidateQueries` pattern (see [`architecture.md#Communication-Patterns`](../planning-artifacts/architecture.md) lines 372–379) — Story 7.3 will own the mutation wiring; this asymmetry is fine for 7.1.

### Previous Story Intelligence

- **Story 6.4** closed Epic 6 with no backend API changes — there is no API drift to reconcile.
- **Story 3.1** established the canonical playlists test fixtures and the upsert behavior preserved in AC #4 here. Reuse its patterns verbatim.
- **Story 3.4 / 3.5** rely on the sync engine WHERE clause modified in Task 4 — verify their tests still pass after the WHERE-clause change (they should, because the new condition `is_hidden == False` matches the default for every existing test row).

### Git Intelligence

- Most recent backend feature commit: `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — this commit introduced the `LIKED_SONGS_ID = "liked_songs"` synthetic playlist handling that AC #3 must respect (the "Titres likés" entry needs `image_url=None` and a one-shot `current_user_saved_tracks(limit=1)["total"]` call).
- The `Playlist` model has been stable since Story 1.2; this story is the first schema change since.

### Latest Tech Information

- **SQLModel** — `Field(default=False, sa_column_kwargs={"server_default": "0"})` is the documented pattern for boolean columns with a SQLite-compatible server-side default (SQLite stores booleans as 0/1). The `default=False` controls Python-side construction; `server_default` controls the DB DDL.
- **spotipy** — `current_user_playlists()` returns items where `images` is either a list `[{url, height, width}, ...]` or an empty list (rarely missing entirely; the `.get("images")` guard handles both); `tracks.total` is always present and is an int.
- **Pydantic v2** — `Optional[bool] = None` on a request model means the field is optional in the JSON body. Sending `{}` produces a model with both fields `None`; sending `{"is_hidden": true}` produces `is_included=None, is_hidden=True`. No discriminator or validator needed.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-7.1 (lines 975–1006)] — story requirements + GWT criteria.
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-7 (lines 967–971)] — FR/AR/NFR map: FR25–FR30, AR10, NFR13.
- [Source: _bmad-output/planning-artifacts/prd.md#FR27 + #FR29 + #FR30] — hide ⇒ exclude, unhide defaults to excluded, persistence.
- [Source: _bmad-output/planning-artifacts/architecture.md#Data-Architecture (lines 146–157)] — SQLModel + `metadata.create_all()`, no Alembic.
- [Source: _bmad-output/planning-artifacts/architecture.md#Format-Patterns (lines 343–350)] — array-not-wrapped response, snake_case.
- [Source: _bmad-output/planning-artifacts/architecture.md#Enforcement-Guidelines (lines 410–425)] — services not routers, all spotipy via `services/spotify.py`.
- [Source: _bmad-output/planning-artifacts/architecture.md#Structure-Patterns (lines 298–339)] — file layout.
- [Source: CLAUDE.md#Backend + #Tests + #Postman-Mise-à-jour-obligatoire] — project-local conventions.
- [Source: backend/models/playlist.py (existing 10 lines)] — current schema baseline.
- [Source: backend/routers/playlists.py (existing 73 lines)] — current router contract baseline.
- [Source: backend/services/spotify.py:74-94] — current `get_user_playlists()` baseline.
- [Source: backend/services/sync_engine.py:69-71] — current sync WHERE clause.
- [Source: backend/tests/test_story_3_1.py] — fixtures + mocking patterns to reuse.
- [Source: commit 069a96c] — Liked Songs / `LIKED_SONGS_ID` synthetic-playlist handling.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (Claude Opus 4.7)

### Debug Log References

- Tests : `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_7_1.py -v` → 6/6 passed.
- Suite complète : 82 passed, 4 failed — les 4 échecs (`test_story_3_3.py::test_run_sync_returns_sliced_tracks`, `test_story_3_4.py::test_get_or_create_creates_when_no_stored_id`, `test_story_3_4.py::test_get_or_create_recreates_on_invalid_stored_id`, `test_story_3_4.py::test_run_sync_success_returns_dict`) pré-existent sur `master` (introduits par commit 069a96c — `new_track_count`). Vérifié via `git stash` : ils échouent identiquement sans nos changements. Pas de régression.
- Smoke local OK : `curl GET /api/v1/playlists` retourne les 12 playlists avec `is_hidden`, `image_url`, `track_count`. PATCH `{"is_hidden": true}` met bien `is_included=false` atomiquement.
- DB dev existante : il a fallu exécuter `ALTER TABLE playlist ADD COLUMN is_hidden BOOLEAN NOT NULL DEFAULT 0;` sur `/data/app.db` (le projet n'a pas d'Alembic, `SQLModel.metadata.create_all()` ne fait pas d'ALTER).
- Robustesse `get_user_playlists()` : ajout de `.get()` défensifs sur `owner`, `tracks`, `images` car la réponse réelle de l'API Spotify peut contenir des items partiels (rencontré pendant le smoke).

### Completion Notes List

- ✅ AC #1–#9 implémentés.
- ✅ AC #10 — 6 tests dans `backend/tests/test_story_7_1.py`, tous verts.
- ✅ AC #11 — collection Postman mise à jour (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`) : `GET /playlists` body example + description enrichis (3 nouveaux champs documentés), `PATCH /playlists/{spotify_id}` renommé "Patch Playlist (Include / Hide)", description mise à jour, exemple `200 OK — is_hidden=true (clears is_included)` ajouté. Vérifié via `GET https://api.getpostman.com/collections/{uid}`.
- ✅ AC #12 — aucun changement frontend dans cette story.
- ⚠️ **Migration DB existante (AC #1)** : pour toute DB dev pré-7.1, il faut soit supprimer `./data/app.db` (réauth Spotify nécessaire), soit appliquer manuellement `ALTER TABLE playlist ADD COLUMN is_hidden BOOLEAN NOT NULL DEFAULT 0;`. La cible host bind-mount est `/data/app.db` côté conteneur (voir `backend/database.py`).
- 📝 Sync engine WHERE clause étendue à `is_hidden == False` en defense-in-depth (AC #8).

### File List

- ✏️ `backend/models/playlist.py` — ajout colonne `is_hidden`.
- ✏️ `backend/services/spotify.py` — `get_user_playlists()` retourne `image_url` et `track_count` ; appel unique à `current_user_saved_tracks(limit=1)` pour le compteur Liked Songs ; gardes défensifs sur la réponse Spotify.
- ✏️ `backend/routers/playlists.py` — `PlaylistRead` étendu (`is_hidden`, `image_url?`, `track_count?`), `PlaylistPatch` avec champs optionnels, logique PATCH hide/include atomique.
- ✏️ `backend/services/sync_engine.py` — WHERE clause étendue avec `is_hidden == False`.
- ➕ `backend/tests/test_story_7_1.py` — 6 tests pour les ACs.
- 🌐 Postman collection (externe) — mise à jour via API.
- 📋 `_bmad-output/implementation-artifacts/sprint-status.yaml` — story `7-1-playlist-hidden-state-schema-api` → `review`.
- 📋 `_bmad-output/implementation-artifacts/7-1-playlist-hidden-state-schema-api.md` — Tasks/subtasks cochées, Dev Agent Record renseigné, Status → `review`.

### Change Log

| Date       | Version | Description                                                                                                      | Author |
| ---------- | ------- | ---------------------------------------------------------------------------------------------------------------- | ------ |
| 2026-05-20 | 0.1     | Story 7.1 implémentée — schéma `is_hidden`, API `GET`/`PATCH` étendus, sync engine + tests + Postman à jour.    | Amelia |

