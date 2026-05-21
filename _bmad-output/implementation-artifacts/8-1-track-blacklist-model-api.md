# Story 8.1: Track Blacklist Model & API

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want a persistent blacklist of track Spotify IDs exposed via a CRUD API,
so that the frontend can manage entries and the sync engine can filter them out.

## Acceptance Criteria

1. **Given** the backend starts after this story is shipped, **When** the SQLite DB is inspected (e.g., `docker exec playlist_spotify-backend-1 /app/.venv/bin/python -c "from sqlmodel import inspect; from database import engine; print(inspect(engine).get_columns('track_blacklist'))"`), **Then** a table named `track_blacklist` exists with exactly two columns: `spotify_id` (TEXT, PRIMARY KEY, NOT NULL) and `blacklisted_at` (TEXT, NOT NULL — ISO 8601). The table is auto-created via `SQLModel.metadata.create_all(engine)` on app startup — no Alembic migration. [Source: epics.md#Story-8.1 AC + AR11 + architecture.md "SQLModel.metadata.create_all()" pattern]

2. **Given** `GET /api/v1/blacklist`, **When** the endpoint is called, **Then** it returns a JSON array (no wrapper) of `[{spotify_id, blacklisted_at}]` ordered by `blacklisted_at` **descending** (most recently blacklisted first). Empty table returns `[]` with status 200. [Source: epics.md#Story-8.1 + CLAUDE.md "Réponses sans wrapper : array direct"]

3. **Given** `POST /api/v1/blacklist` with body `{"spotify_id": "<id>"}`, **When** the spotify_id is NOT already present, **Then** a new row is inserted with `blacklisted_at = datetime.utcnow().isoformat()` and the endpoint returns **201 Created** with body `{spotify_id, blacklisted_at}`. **When** the spotify_id IS already present (duplicate), **Then** the endpoint is **idempotent**: it returns **200 OK** with the existing row's body (do NOT overwrite `blacklisted_at`, do NOT raise). [Source: epics.md#Story-8.1 AC]

4. **Given** `DELETE /api/v1/blacklist/{spotify_id}`, **When** the spotify_id exists, **Then** the row is deleted and the endpoint returns **204 No Content** (empty body). **When** the spotify_id does NOT exist, **Then** the endpoint is **idempotent**: it still returns **204 No Content** (do NOT raise 404). [Source: epics.md#Story-8.1 AC]

5. **Given** the Docker container is stopped and restarted (`docker-compose restart backend`), **When** the app boots, **Then** all `track_blacklist` rows persist (FR36) because the SQLite file lives in the bind-mounted volume (already wired by Story 1.1/1.2). No code change required here — only verify the table is registered via `models/__init__.py` so `SQLModel.metadata.create_all()` reaches it. [Source: epics.md#Story-8.1 AC + FR36 + Story 1.2 SQLite init]

6. **Given** invalid request bodies, **When** `POST /api/v1/blacklist` is called with a missing or empty `spotify_id`, **Then** FastAPI returns **422 Unprocessable Entity** via the Pydantic schema (`spotify_id: str` with `min_length=1`). Do NOT add custom 400 handling — let Pydantic validate. [Source: existing pattern in routers/config.py + routers/playlists.py]

7. **Given** the project's snake_case JSON convention, **When** any blacklist endpoint returns a row, **Then** the field names are exactly `spotify_id` and `blacklisted_at` (snake_case, never camelCase). [Source: CLAUDE.md#Backend "Champs JSON en snake_case partout"]

8. **Given** the new pytest file `backend/tests/test_story_8_1.py`, **When** `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_8_1.py -v` is run, **Then** all tests pass and exercise: (a) GET on empty DB returns `[]`, (b) POST inserts and returns 201 with body, (c) POST duplicate returns 200 (idempotent) without changing `blacklisted_at`, (d) GET returns rows sorted by `blacklisted_at` DESC, (e) DELETE existing returns 204 + row absent from subsequent GET, (f) DELETE non-existent returns 204 (idempotent), (g) POST with empty/missing `spotify_id` returns 422. Use the same fixture pattern as [`tests/test_story_7_1.py`](../../backend/tests/test_story_7_1.py) (in-memory SQLite + `app.dependency_overrides[get_session]`). [Source: CLAUDE.md#Tests + test_story_7_1.py reference pattern]

9. **Given** the Postman collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`), **When** Story 8.1 ships, **Then** three new requests are added under a new (or existing) "Blacklist" folder: `GET /api/v1/blacklist`, `POST /api/v1/blacklist` (body `{"spotify_id": "exampleId"}`), `DELETE /api/v1/blacklist/{{spotify_id}}`. Each request includes a brief description and an example response body. Verify the PUT update succeeded by GETting the collection and confirming the three new requests appear. [Source: CLAUDE.md#Postman + memory `feedback_postman_sync`]

10. **Given** future consumers (Story 8.4 frontend, Story 8.5 sync engine filter), **When** they import the blacklist set, **Then** the public surface is exactly: the SQLModel class `TrackBlacklist` (importable via `models.TrackBlacklist`) and the three HTTP endpoints above. Do NOT pre-emptively add a service layer or helper functions in this story — keep the implementation minimal; Story 8.5 will add a `get_blacklisted_ids() -> set[str]` helper in `services/` when it needs one. [Source: CLAUDE.md#Backend "Business logic dans services/, jamais dans routers/" + project convention "avoid premature abstraction" from 7.5]

## Tasks / Subtasks

- [x] **Task 1: Create the `TrackBlacklist` SQLModel** (AC: #1, #5, #7)
  - [x] Create new file [`backend/models/track_blacklist.py`](../../backend/models/track_blacklist.py) with:
    ```python
    from sqlmodel import Field, SQLModel


    class TrackBlacklist(SQLModel, table=True):
        __tablename__ = "track_blacklist"  # type: ignore[assignment]

        spotify_id: str = Field(primary_key=True)
        blacklisted_at: str  # ISO 8601, set on insert
    ```
    Mirror the conventions of [`models/playlist.py`](../../backend/models/playlist.py) and [`models/sync_log.py`](../../backend/models/sync_log.py).
  - [x] Register the model in [`backend/models/__init__.py`](../../backend/models/__init__.py): add `from .track_blacklist import TrackBlacklist` and append `"TrackBlacklist"` to `__all__`. **This is required** — without it, the table is not registered with `SQLModel.metadata` and `create_all()` will skip it.
  - [x] No new migration tooling. The table is created by the existing `SQLModel.metadata.create_all(engine)` call in [`backend/main.py`](../../backend/main.py) lifespan.

- [x] **Task 2: Create the blacklist router** (AC: #2, #3, #4, #6, #7)
  - [x] Create new file [`backend/routers/blacklist.py`](../../backend/routers/blacklist.py) with three endpoints:
    - `GET /blacklist` → `list[BlacklistRead]` — `session.exec(select(TrackBlacklist).order_by(TrackBlacklist.blacklisted_at.desc())).all()`.
    - `POST /blacklist` with body `BlacklistCreate(spotify_id: str = Field(..., min_length=1))` → idempotent:
      - Look up by `spotify_id`. If exists → return existing row + status 200. Else → insert with `blacklisted_at = datetime.utcnow().isoformat()`, commit, return new row + status 201.
      - Use FastAPI `Response` injection or two `@router` decorators with different `status_code` settings is overkill — easiest pattern: `from fastapi import Response` and set `response.status_code = 200 or 201` inside the handler, returning the model directly.
    - `DELETE /blacklist/{spotify_id}` → idempotent: look up, delete if found, `session.commit()`, return `Response(status_code=204)` either way.
  - [x] Pydantic models inside the router file (do NOT export from `models/` — those are SQLModel table classes only, like done in [`routers/playlists.py`](../../backend/routers/playlists.py:14)):
    ```python
    class BlacklistRead(BaseModel):
        spotify_id: str
        blacklisted_at: str

    class BlacklistCreate(BaseModel):
        spotify_id: str = Field(..., min_length=1)
    ```
  - [x] Use `SessionDep` from [`backend/dependencies.py`](../../backend/dependencies.py) for all handlers — never instantiate a `Session` directly inside a route.
  - [x] Set `router = APIRouter(tags=["blacklist"])` and keep all business logic inline in the router for this story (per AC #10). It's small enough to not warrant a `services/blacklist.py` yet.

- [x] **Task 3: Wire the router into the FastAPI app** (AC: #2, #3, #4)
  - [x] In [`backend/main.py`](../../backend/main.py), add `from routers.blacklist import router as blacklist_router` next to the existing router imports, and `app.include_router(blacklist_router, prefix="/api/v1")` next to the existing `include_router` calls.

- [x] **Task 4: Write pytest covering all ACs** (AC: #8)
  - [x] Create [`backend/tests/test_story_8_1.py`](../../backend/tests/test_story_8_1.py) using the exact fixture pattern from [`tests/test_story_7_1.py`](../../backend/tests/test_story_7_1.py) — copy the `session` and `client` fixtures verbatim (in-memory SQLite + `StaticPool` + `dependency_overrides`).
  - [x] Test cases (one function per AC sub-bullet of AC #8 a–g). For the "POST duplicate is idempotent + does not overwrite timestamp" case, insert manually with a known `blacklisted_at`, POST same id, then assert the response body's `blacklisted_at` is unchanged.
  - [x] For the "ordered DESC" case, insert three rows with `blacklisted_at` values like `"2026-05-19T10:00:00"`, `"2026-05-20T10:00:00"`, `"2026-05-18T10:00:00"` and assert the returned order is `["2026-05-20...", "2026-05-19...", "2026-05-18..."]`.
  - [x] Run: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_8_1.py -v`. All tests MUST pass before marking the story `review`. **→ 8/8 passed.**

- [x] **Task 5: Update Postman collection** (AC: #9)
  - [x] Collection UID: `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`. API key in `.mcp.json` (env `POSTMAN_API_KEY`).
  - [x] `GET https://api.getpostman.com/collections/{uid}` → grab current JSON.
  - [x] Add a new folder "Blacklist" with three requests:
    - `GET {{api_v1}}/blacklist` — description: "Returns blacklisted tracks ordered by blacklisted_at DESC".
    - `POST {{api_v1}}/blacklist` — body raw JSON `{"spotify_id": "3n3Ppam7vgaVa1iaRUc9Lp"}`, description: "Idempotent insert; 201 on first insert, 200 on duplicate".
    - `DELETE {{api_v1}}/blacklist/3n3Ppam7vgaVa1iaRUc9Lp` — description: "Idempotent delete; always returns 204".
  - [x] `PUT https://api.getpostman.com/collections/{uid}` with the updated body.
  - [x] Verify: re-`GET` the collection and confirm the three new requests appear → `['List Blacklist', 'Add to Blacklist', 'Remove from Blacklist']`.

- [x] **Task 6: Manual smoke against the running stack** (AC: #1–#7)
  - [x] Backend started, no metadata errors.
  - [x] `GET /api/v1/blacklist` → `[]` (200).
  - [x] `POST /api/v1/blacklist {"spotify_id":"abc"}` → 201, body `{"spotify_id":"abc","blacklisted_at":"2026-05-20T21:23:55.613355"}`.
  - [x] Same POST again → 200, **same `blacklisted_at`** preserved.
  - [x] `GET` → `[{"spotify_id":"abc","blacklisted_at":"2026-05-20T21:23:55.613355"}]`.
  - [x] `DELETE /api/v1/blacklist/abc` → 204.
  - [x] Same DELETE again → 204 (idempotent).
  - [x] `POST /api/v1/blacklist {}` → 422.
  - [x] After `docker-compose restart backend`, row inserted before restart still present (AC #5 persistence verified).

## Dev Notes

### Architecture & Conventions

- **Backend-only story** — no frontend code, no UX design impact. Story 8.4 will consume these endpoints. [Source: epics.md#Epic-8]
- **Business logic in `routers/` is acceptable here** — the CRUD is trivial enough that a `services/blacklist.py` would be empty boilerplate. CLAUDE.md "Business logic dans services/" applies when there is non-trivial logic (Spotify API calls, sync orchestration, etc.). Story 8.5 will introduce a `services/` helper when needed. [Source: CLAUDE.md#Backend + AC #10]
- **No Alembic / migration framework** — every table in this project is auto-created via `SQLModel.metadata.create_all(engine)` on startup. Adding migration tooling is out of scope. [Source: architecture.md + main.py:21]
- **JSON convention** — snake_case everywhere, array-direct responses (no `{"data": [...]}` wrapper). [Source: CLAUDE.md#Backend]
- **`SessionDep` everywhere** — never `with Session(engine) as session:` inside a request handler; that is only for background jobs (e.g., `sync_engine._write_sync_log`). [Source: dependencies.py + routers/playlists.py + routers/config.py]

### Source Tree — Files to Touch

- 🆕 [`backend/models/track_blacklist.py`](../../backend/models/track_blacklist.py) — new SQLModel.
- ✏️ [`backend/models/__init__.py`](../../backend/models/__init__.py) — register `TrackBlacklist` import + `__all__`.
- 🆕 [`backend/routers/blacklist.py`](../../backend/routers/blacklist.py) — new router with GET/POST/DELETE.
- ✏️ [`backend/main.py`](../../backend/main.py) — import and `include_router` the new router (with `/api/v1` prefix).
- 🆕 [`backend/tests/test_story_8_1.py`](../../backend/tests/test_story_8_1.py) — new pytest file (copy fixtures from `test_story_7_1.py`).
- 🔒 [`backend/services/sync_engine.py`](../../backend/services/sync_engine.py) — **do not touch**. Story 8.5 will integrate the blacklist filter; touching it here mixes concerns.
- 🔒 [`backend/services/spotify.py`](../../backend/services/spotify.py) — **do not touch**.
- 🔒 [`backend/models/playlist.py`](../../backend/models/playlist.py) — **do not touch**. The blacklist is a *track* concept, decoupled from `Playlist`.
- 🔒 Frontend — **do not touch** (story is backend-only).

### Code Sketch — Router

```python
# backend/routers/blacklist.py
from datetime import datetime

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field
from sqlmodel import select

from dependencies import SessionDep
from models.track_blacklist import TrackBlacklist

router = APIRouter(tags=["blacklist"])


class BlacklistRead(BaseModel):
    spotify_id: str
    blacklisted_at: str


class BlacklistCreate(BaseModel):
    spotify_id: str = Field(..., min_length=1)


@router.get("/blacklist", response_model=list[BlacklistRead])
def get_blacklist(session: SessionDep) -> list[BlacklistRead]:
    rows = session.exec(
        select(TrackBlacklist).order_by(TrackBlacklist.blacklisted_at.desc())
    ).all()
    return [BlacklistRead(spotify_id=r.spotify_id, blacklisted_at=r.blacklisted_at) for r in rows]


@router.post("/blacklist", response_model=BlacklistRead)
def add_to_blacklist(
    payload: BlacklistCreate, session: SessionDep, response: Response
) -> BlacklistRead:
    existing = session.exec(
        select(TrackBlacklist).where(TrackBlacklist.spotify_id == payload.spotify_id)
    ).first()
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return BlacklistRead(spotify_id=existing.spotify_id, blacklisted_at=existing.blacklisted_at)

    row = TrackBlacklist(
        spotify_id=payload.spotify_id,
        blacklisted_at=datetime.utcnow().isoformat(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    response.status_code = status.HTTP_201_CREATED
    return BlacklistRead(spotify_id=row.spotify_id, blacklisted_at=row.blacklisted_at)


@router.delete("/blacklist/{spotify_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_blacklist(spotify_id: str, session: SessionDep) -> Response:
    row = session.exec(
        select(TrackBlacklist).where(TrackBlacklist.spotify_id == spotify_id)
    ).first()
    if row is not None:
        session.delete(row)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

> Sketch only — adapt naming to match existing conventions, but the shape (single-handler-per-route, `SessionDep`, Pydantic models in-router, no service layer) is correct for this story's scope.

### Testing Standards

- **Test runner**: pytest inside the backend container. Always: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/<file> -v`. [Source: CLAUDE.md#Tests]
- **Fixture pattern**: in-memory SQLite + `StaticPool` + `app.dependency_overrides[get_session]`. Exactly as in [`test_story_7_1.py`](../../backend/tests/test_story_7_1.py) and [`test_story_3_1.py`](../../backend/tests/test_story_3_1.py).
- **No mocks needed** — the blacklist endpoints do not call `spotify_service` or any external API. Pure DB CRUD.
- **Status codes are part of the contract** — explicitly assert `r.status_code == 201`, `200`, `204`, `422` per the relevant ACs. Do not rely on default 200.

### Previous Story Intelligence

- **Story 1.2 (DB models + SQLite init)** established the `SQLModel.metadata.create_all(engine)` pattern at startup. Registering the new model in `models/__init__.py` is mandatory for it to be picked up — same gotcha that caught earlier epics.
- **Story 3.1 / 7.1** established the test fixture pattern (`session` + `client` + `app.dependency_overrides[get_session]` + `StaticPool`). Reuse it verbatim.
- **Story 7.1** showed that adding a new column / table requires NO migration tooling — just bump the model and let `create_all()` handle it on next restart. Existing rows survive because `create_all()` is additive.
- **Story 7.5 "no premature abstraction"** decision: keep duplicates rather than extracting a shared module when the surface is tiny. Applies here — no `services/blacklist.py` yet.

### Git Intelligence

- Most recent feature commits (newest first):
  - `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — sync engine now supports a `since` parameter and a separate `new_track_count`. Irrelevant to this story but informs Story 8.5.
  - `ccbbf60 feat: Stories 2-3 → 5-3 — Auth, Playlists, Sync, Scheduler & Observability` — bulk landing of the foundation epics.
- Working tree is dirty with Epic 6 + 7 frontend changes; do not amend or rebase them. Add Story 8.1 files as new files and commit separately when ready.
- No prior commit touched `track_blacklist`, `blacklist.py`, or `models/track_blacklist.py` — clean slate.

### Latest Tech Information

- **SQLModel (≥0.0.14) + SQLite**: `Field(primary_key=True)` on a `str` column produces a `TEXT PRIMARY KEY NOT NULL` column. `unique=True` is implied by `primary_key=True` — do not set both.
- **FastAPI dynamic status codes**: the cleanest way to return *either* 200 or 201 from the same handler is to inject `response: Response` and mutate `response.status_code` before returning. The alternative (declaring `status_code=201` at decorator level and raising / returning early) is uglier for an idempotent endpoint. [Source: FastAPI docs "Response Status Code"]
- **DELETE 204 idempotency**: returning `Response(status_code=204)` with no body is the standard idiom; FastAPI will not try to serialize anything else. Do NOT declare `response_model=` on a 204 endpoint.
- **`datetime.utcnow().isoformat()`** — produces `"2026-05-20T13:42:01.123456"` (no trailing `Z`). Consistent with how `sync_log.timestamp` is stored elsewhere in the project. Do NOT switch to `datetime.now(UTC)` mid-project; match the existing pattern.

### Postman Sync Procedure (Reminder)

Per CLAUDE.md and memory `feedback_postman_sync`, Postman MUST be updated when API surface changes. This story adds 3 endpoints. Use the MCP Postman server if available in this session; otherwise hit the REST API directly:

```bash
# 1. Get current collection
curl -s -H "X-Api-Key: $POSTMAN_API_KEY" \
  https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6 \
  > /tmp/postman-current.json

# 2. Edit /tmp/postman-current.json — add the new folder + 3 requests
#    (preserve the entire existing structure; only append)

# 3. PUT the updated collection back
curl -s -X PUT -H "X-Api-Key: $POSTMAN_API_KEY" \
  -H "Content-Type: application/json" \
  --data @/tmp/postman-updated.json \
  https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6

# 4. Verify the PUT
curl -s -H "X-Api-Key: $POSTMAN_API_KEY" \
  https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6 \
  | jq '.collection.item[] | select(.name=="Blacklist") | .item | length'
# expected: 3
```

### Project Structure Notes

- ✅ Aligns with [`architecture.md`](../planning-artifacts/architecture.md) backend layout: `models/<entity>.py`, `routers/<entity>.py`, `tests/test_story_<X>_<Y>.py`.
- ✅ Snake_case JSON, array-direct responses, `SessionDep` injection — all match existing conventions in [`routers/playlists.py`](../../backend/routers/playlists.py).
- ⚠️ **Do NOT** add a `services/blacklist.py` in this story — the CRUD is too small to justify. Story 8.5 will add `get_blacklisted_ids() -> set[str]` when the sync engine needs it. [Source: AC #10 + 7.5 "no premature abstraction"]
- ⚠️ **Do NOT** modify [`services/sync_engine.py`](../../backend/services/sync_engine.py) — Story 8.5 owns that integration. Mixing it in here makes Story 8.5's diff harder to review and blurs ownership.
- ⚠️ **Do NOT** add an Alembic / migration step — every other table in this project relies on `create_all()`. Diverging here would be the start of an inconsistent persistence strategy.
- ⚠️ **Do NOT** invent a "soft delete" or `deleted_at` column for un-blacklisting — Story 8.5 AC explicitly says `DELETE /api/v1/blacklist/{id}` purges the entry and the track is restored to syncs. No tombstones.
- ⚠️ **Do NOT** add a foreign key from `track_blacklist.spotify_id` to any `Track` table — there is no `Track` table in this project. Tracks live in Spotify; we only persist the IDs we want to exclude.

### Project Context Reference

See [`CLAUDE.md`](../../CLAUDE.md) for project-wide development rules. Most relevant sections for this story:
- "Backend" — business logic placement, snake_case, array-direct responses.
- "Tests" — pytest via `docker exec`, fixture pattern.
- "Postman — Mise à jour obligatoire" — the Postman update is non-negotiable for any API change.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-8.1] — primary ACs (lines 1187–1213).
- [Source: _bmad-output/planning-artifacts/epics.md#AR11] — table schema requirement (line 83 + 162).
- [Source: _bmad-output/planning-artifacts/epics.md#FR36] — persistence across sessions (line 136).
- [Source: _bmad-output/planning-artifacts/architecture.md#L455] — `models/config.py` example of an existing model file structure.
- [Source: CLAUDE.md#Backend, #Tests, #Postman] — project conventions.
- [Source: backend/tests/test_story_7_1.py] — fixture pattern to mirror.
- [Source: backend/routers/playlists.py] — router shape (Pydantic schemas in-file, `SessionDep`, snake_case fields).
- [Source: backend/main.py:36–40] — where to wire the new `include_router` call.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

- `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_8_1.py -v` → 8/8 passed (1 deprecation warning on `datetime.utcnow()`, kept intentionally per Dev Notes consistency with `sync_log.timestamp`).
- Full backend test suite is OOM-killed on this host beyond ~45 tests; pre-existing infra issue unrelated to this story. Story 8.1 tests verified in isolation and alongside neighbouring suites (7_1, 2_4, 5_3) — 23/23 passed, no regression.

### Completion Notes List

- Story 8.1 implements a minimal CRUD blacklist surface (1 SQLModel table, 3 endpoints) consumed later by Stories 8.4 (frontend) and 8.5 (sync engine filter).
- Idempotency: POST returns 201 on first insert, 200 on duplicate (existing row returned unchanged, `blacklisted_at` not overwritten). DELETE returns 204 in all cases (existent or not).
- No service layer (`services/blacklist.py`) was introduced — per AC #10 and Story 7.5 "no premature abstraction"; Story 8.5 will add a `get_blacklisted_ids() -> set[str]` helper when needed.
- No migration tooling — table auto-created on app startup via existing `SQLModel.metadata.create_all(engine)` lifespan hook (registration in `models/__init__.py` is what makes it discoverable).
- Manual smoke (curl):
  - `GET /api/v1/blacklist` → 200 `[]`
  - `POST {"spotify_id":"abc"}` → 201 `{"spotify_id":"abc","blacklisted_at":"2026-05-20T21:23:55.613355"}`
  - `POST {"spotify_id":"abc"}` again → 200 same body (idempotent)
  - `DELETE /api/v1/blacklist/abc` → 204; repeat → 204
  - `POST {}` → 422 (Pydantic `min_length=1`)
  - Restart backend, row persisted (AC #5 verified)
- Postman collection updated (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`) — new "Blacklist" folder with `List Blacklist`, `Add to Blacklist`, `Remove from Blacklist`. Verified via re-GET.

### File List

- 🆕 `backend/models/track_blacklist.py`
- ✏️ `backend/models/__init__.py`
- 🆕 `backend/routers/blacklist.py`
- ✏️ `backend/main.py`
- 🆕 `backend/tests/test_story_8_1.py`

### Change Log

- 2026-05-20 — Story 8.1 implemented: `track_blacklist` SQLModel, blacklist CRUD router, app wiring, pytest suite, Postman collection updated. Status → review.
