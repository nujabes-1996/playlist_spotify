# Story 10.1: User Model, Session Middleware & Auth Gate

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->
<!-- Source of truth: Epic 10 was NOT added to epics.md, and prd.md/architecture.md were NOT amended.
     This story is built from the Sprint Change Proposal (the authoritative spec for Epic 10) plus
     direct codebase analysis. See References. -->

## Story

As a **multi-tenant platform owner**,
I want **a `User` data model, server-side signed sessions, and an authentication gate that rejects unauthenticated requests**,
so that **the application has the foundation to isolate each visitor's data and Spotify identity instead of exposing the single owner's data to everyone**.

## Context & Scope Boundary (READ FIRST)

This is the **foundation story** of Epic 10 (multi-user OAuth pivot). It builds the plumbing only.

**IN SCOPE (10.1):**
- New `User` SQLModel table.
- Starlette `SessionMiddleware` wired into the app, driven by a `SESSION_SECRET` env var.
- A `get_current_user` FastAPI dependency that resolves the logged-in user from the session cookie.
- An **auth gate**: every data/business router rejects unauthenticated requests with **HTTP 401**.

**EXPLICITLY OUT OF SCOPE — do NOT implement here:**
- The login/setup screen, the `state`-protected OAuth round-trip, and user creation at callback → **Story 10.2**.
- Per-user token storage (`SQLiteCacheHandler` keyed by `user_id`) and per-user `_get_spotify_oauth(user)` → **Story 10.2**.
- Adding `user_id` FK to `Playlist`/`track_blacklist`/`sync_log` and filtering queries → **Story 10.3**.
- Per-user scheduler jobs → **Story 10.4**.
- Prod hardening (Secure/HttpOnly cookie flags verified in prod, redirect URI registration) → **Story 10.5**.

**Critical consequence of this boundary:** Until 10.2 lands there is **no production code path that opens a session**. That is expected and intentional — 10.1 → 10.2 → 10.3 are designed to ship together. In 10.1, a session is only ever populated by tests (via `request.session` or by overriding `get_current_user`). Do NOT invent a login endpoint to "make it work end to end" — that is 10.2's job and would be scope creep.

## Acceptance Criteria

1. **`User` model exists.** A new `User` SQLModel table model is defined with exactly these fields: `id` (int PK, autoincrement), `spotify_user_id` (str, **unique**), `display_name` (str, nullable), `client_id` (str, nullable), `client_secret` (str, nullable), `token_json` (str, nullable), `playlist_size` (int, default 50), `cron_expr` (str, nullable), `target_playlist_id` (str, nullable), `created_at` (str, ISO-8601). It is registered in `models/__init__.py` so `SQLModel.metadata.create_all()` creates the table. **`Config` is NOT removed** (legacy token/credential reads still depend on it until 10.2).

2. **Session middleware is active.** `SessionMiddleware` is added to the FastAPI app. The signing key comes from the `SESSION_SECRET` environment variable. If `SESSION_SECRET` is unset, the app uses a clearly-marked insecure dev default (and does not crash in local dev). The session cookie is configured `HttpOnly`; the `Secure` flag is enabled when running over HTTPS / in prod (env-driven), and `same_site` is set to `lax`.

3. **`get_current_user` dependency resolves the session user.** A dependency reads the `user_id` stored in `request.session`, loads the matching `User` row from the DB, and returns it. If there is no `user_id` in the session, or no matching `User` row exists, it raises `HTTPException(status_code=401, detail="Not authenticated")`.

4. **Auth gate rejects unauthenticated requests.** All data/business routers — `config`, `playlists`, `sync`, `blacklist`, `recently-added` — require a valid session: an unauthenticated request to any of their endpoints returns **HTTP 401**. The `auth` router (`/auth/*`) and `GET /health` remain **publicly accessible** (login lives there in 10.2).

5. **Authenticated requests pass through unchanged.** When a valid session resolves to an existing `User`, the previously-public endpoints behave exactly as before (same response shapes/status codes). No business logic regresses.

6. **No token/secret leakage.** Neither the `User` model serialization nor any new endpoint exposes `client_secret`, `token_json`, `client_id`, or raw token fields to the browser (NFR5 preserved).

7. **Dependency & config declared.** `itsdangerous` (required by `SessionMiddleware`) is added to `backend/pyproject.toml` dependencies. `SESSION_SECRET` is documented/added to both `docker-compose.yml` (dev) and `docker-compose.prod.yml` (prod) environment.

8. **Existing test suite is green.** All pre-existing backend tests pass. Router tests that now hit the auth gate are updated to inject an authenticated user via the established `app.dependency_overrides` pattern.

## Tasks / Subtasks

- [x] **Task 1: Define the `User` model** (AC: #1, #6)
  - [x] Create `backend/models/user.py` with the `User(SQLModel, table=True)` class and the exact fields listed in AC#1. Mirror the style of `models/config.py` / `models/playlist.py` (`Optional[int]` PK, `Field(unique=True)` for `spotify_user_id`).
  - [x] Register `User` in `backend/models/__init__.py` (`from .user import User`, add to `__all__`).
  - [x] Confirm `SQLModel.metadata.create_all(engine)` (called in `main.py` lifespan) creates the `user` table — `models` is already side-effect-imported in `main.py`.

- [x] **Task 2: Add session middleware** (AC: #2, #7)
  - [x] Add `itsdangerous` to `[project].dependencies` in `backend/pyproject.toml`. **This is a new dependency — it was approved as part of this story's scope.**
  - [x] In `backend/main.py`, add `from starlette.middleware.sessions import SessionMiddleware` and register it on `app` with `secret_key=os.getenv("SESSION_SECRET", "<insecure-dev-default>")`, `https_only=<env-driven>`, `same_site="lax"`, and an explicit `session_cookie` name (e.g. `session`).
  - [x] Drive `https_only` from an env signal (reuse the prod posture — e.g. `os.getenv("SESSION_COOKIE_SECURE")` or infer from an existing prod-only env var). Default `False` in dev so the cookie works over plain HTTP on `localhost`.
  - [x] Add `SESSION_SECRET` (and the secure-cookie flag if introduced) to `docker-compose.yml` and `docker-compose.prod.yml` `environment:` blocks. In prod, document that it must be a strong random secret (do NOT hardcode a real secret in the compose file — use `${SESSION_SECRET}`).

- [x] **Task 3: Implement `get_current_user` dependency** (AC: #3, #5)
  - [x] In `backend/dependencies.py`, add `get_current_user(request: Request, session: SessionDep) -> User`: read `request.session.get("user_id")`; if falsy → raise `HTTPException(401, "Not authenticated")`; else `session.get(User, user_id)`; if `None` → raise `HTTPException(401, "Not authenticated")`; else return the `User`.
  - [x] Export an annotated alias `CurrentUserDep = Annotated[User, Depends(get_current_user)]` alongside the existing `SessionDep`.

- [x] **Task 4: Apply the auth gate** (AC: #4, #5)
  - [x] Protect the business routers. Prefer applying the dependency at include-time in `main.py` so each endpoint isn't touched individually:
        `app.include_router(config_router, prefix="/api/v1", dependencies=[Depends(get_current_user)])` for `config`, `playlists`, `sync`, `blacklist`, `recently_added`.
  - [x] Do **NOT** add the dependency to `auth_router` or `GET /health` — they stay public.
  - [x] Verify the 401 emitted by the gate is distinguishable from the existing `ValueError`→401 "Not authenticated — run OAuth2 flow first" Spotify-auth 401 in router code (different `detail` string is fine; both are 401).

- [x] **Task 5: Repair existing router tests against the gate** (AC: #8)
  - [x] For every test file whose `client` fixture calls a protected router (`test_story_2_4`, `test_story_3_1`, `test_story_3_2`, `test_story_3_4`, `test_story_3_5`, `test_story_5_1`, `test_story_5_2`, `test_story_5_3`, `test_story_7_1`, `test_story_8_*`, `test_story_9_1`, `test_story_9_7`, `test_story_9_8`, and any other router-level test), add `app.dependency_overrides[get_current_user] = lambda: <fake User>` in the client fixture so requests are treated as authenticated. Use a minimal `User(id=1, spotify_user_id="test_user")` instance.
  - [x] Run the FULL suite and confirm no regressions: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`.

- [x] **Task 6: New tests for this story** (AC: #1–#6)
  - [x] `test_story_10_1.py`: (a) `User` table is created and a row round-trips with all fields; (b) unauthenticated request to one endpoint per protected router → 401; (c) `GET /health` and `GET /api/v1/auth/status` → NOT 401 (public); (d) with `get_current_user` overridden → protected endpoint returns its normal status; (e) `get_current_user` raises 401 when session has no `user_id` and when `user_id` points to a missing row; (f) no `client_secret`/`token_json` leaks in any new response.

- [x] **Task 7: Postman + docs** (AC: #4)
  - [x] No new routes are added in 10.1, but the auth behaviour of existing routes changes (now 401 without session). Per `CLAUDE.md`, update the Postman collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`) to note that protected routes now require a session cookie. (Full login routes land in 10.2.)

## Dev Notes

### Authoritative spec & why it's the change proposal (not epics.md)
Epic 10 was created via Correct Course but **never written into `epics.md`**, and `prd.md`/`architecture.md` were **not** amended (the proposal's handoff steps 1–3 were skipped). The **Sprint Change Proposal** is therefore the source of truth for this story. Story 10.1 = proposal §4.3 bullet "10.1" + the model in §4.2/§2.3.
- 10.1 line: *"`Config` → `User` model + session middleware (`SessionMiddleware`, `SESSION_SECRET`) + `get_current_user` dependency + auth gate (401 / redirect to login for unauthenticated requests)."*
- The "redirect to login" half of the gate is a **frontend** concern handled in 10.2's UX; the **backend** gate returns 401 (the frontend turns 401 into a redirect once the login screen exists).

### Current (single-user) architecture — what you are extending, NOT replacing
- **`Config`** (`backend/models/config.py`): single global row holding `client_id`, `client_secret`, `playlist_size`, `cron_expr`, `spotify_token_json`, `dynamic_playlist_id`, `last_sync_at`. **Leave it in place.** `token_manager.py` and `services/spotify.py` still read it; those move to per-user in 10.2/10.3. The proposal renames `Config`→`User` conceptually, but doing the rename + rewiring atomically here would drag 10.2/10.3 into this story. Instead: **add `User` alongside `Config`**, and let 10.2 migrate token/credential reads onto `User`. Note `User` intentionally has its own `playlist_size`/`cron_expr`/`target_playlist_id` (≈ `Config.dynamic_playlist_id`) so 10.2/10.3 can migrate cleanly.
- **DB**: SQLite at `sqlite:////data/app.db`, single engine in `backend/database.py`. Tables auto-created via `SQLModel.metadata.create_all(engine)` in `main.py` lifespan. **No Alembic** (AR8). Adding a brand-new `User` table is safe with `create_all` (it only creates missing tables); the destructive part — adding `user_id` columns to *existing* tables — is deferred to 10.3 and is NOT your problem here.
- **Session dependency**: `backend/dependencies.py` currently only defines `SessionDep = Annotated[Session, Depends(get_session)]`. Add `get_current_user` here next to it.
- **App wiring**: `backend/main.py` builds the app, adds `CORSMiddleware` (with `allow_credentials=True` already — good, cookies will flow), and includes 6 routers under `/api/v1`. Lifespan bootstraps the scheduler from `Config.cron_expr`.

### Routers and the gate (exact targets)
Protected (require session → 401 if absent): `config_router`, `playlists_router`, `sync_router` (prefix `/sync`), `blacklist_router`, `recently_added_router`.
Public (NO gate): `auth_router` (`/auth/connect`, `/auth/callback`, `/auth/status`), `GET /health`.
All protected routers already inject `SessionDep`; the gate is additive (a router-level `dependencies=[...]`), so endpoint signatures don't need editing.

### Session middleware specifics (Starlette)
- `SessionMiddleware` lives in `starlette.middleware.sessions` and **requires `itsdangerous`**, which is NOT currently installed (verified absent from `uv.lock`). Add it to `pyproject.toml`. Starlette 1.0.0 is already a transitive dep via `fastapi[standard]`.
- Signature highlights: `SessionMiddleware(app, secret_key, session_cookie="session", max_age=..., same_site="lax", https_only=False)`. Set `https_only=True` only in prod (HTTPS) — otherwise the cookie won't be sent over `localhost` HTTP and dev breaks.
- `request.session` is a plain dict-like; 10.2 will do `request.session["user_id"] = user.id`. In 10.1 you only READ it.
- **NFR5/AC#6**: never put tokens or secrets in the session payload or in any response model. The session only needs to hold `user_id` (an int).

### CORS / cookies caveat
`allow_credentials=True` is already set and `CORS_ORIGINS` is explicit (not `*`) — that's the correct combo for cookie-bearing cross-origin requests. The **frontend fetch** in `lib/api.ts` does NOT currently send cookies (no `credentials: 'include'`). Sending the session cookie from the browser is a **10.2 frontend task** (login). In 10.1, backend tests exercise the gate via `TestClient` + `dependency_overrides`, not via real browser cookies, so you do not need to touch the frontend.

### Testing standards (match the repo)
- Run tests ONLY via Docker: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`.
- Fixture pattern (see `test_story_9_1.py`): in-memory SQLite engine with `StaticPool`, `SQLModel.metadata.create_all(engine)`, a `session` fixture, and a `client` fixture that overrides `get_session` via `app.dependency_overrides[get_session]` and clears overrides on teardown.
- **The new wrinkle**: the same `client` fixture must ALSO override `get_current_user` to return a fake authenticated `User`, otherwise every protected-route test gets 401. Add this to the new test's client fixture AND to all existing router-test fixtures (Task 5). Example:
  ```python
  from dependencies import get_current_user
  from models.user import User
  def client_fixture(session):
      app.dependency_overrides[get_session] = lambda: session
      app.dependency_overrides[get_current_user] = lambda: User(id=1, spotify_user_id="test_user")
      ...
      yield TestClient(app)
      app.dependency_overrides.clear()
  ```
- For the **401 gate tests**, build a `TestClient(app)` WITHOUT the `get_current_user` override (only `get_session`) and assert 401.
- Service mocking pattern: `patch("routers.<module>.spotify_service.<fn>", ...)`. JSON is snake_case, arrays returned directly (no `{"data": ...}`) — keep these conventions.

### Red-green-refactor expectation
The workflow runs TDD. Suggested order: write `test_story_10_1.py` gate tests first (they fail because no gate exists) → add middleware + dependency + gate → green. Then run the full suite, watch existing router tests go red from the gate, and fix them in Task 5.

### Anti-patterns to avoid
- ❌ Do NOT delete/rename `Config` or rewire `token_manager`/`spotify.py` — that's 10.2/10.3 and will break the running app.
- ❌ Do NOT add `user_id` columns to existing tables here — 10.3.
- ❌ Do NOT build a login endpoint or write to the session in production code — 10.2.
- ❌ Do NOT gate `/auth/*` or `/health` — they must stay public or 10.2's login can never run.
- ❌ Do NOT hardcode a real `SESSION_SECRET` in compose; use `${SESSION_SECRET}` in prod.
- ❌ Do NOT expose `client_secret`/`token_json` in any response.

### Project Structure Notes
- New file: `backend/models/user.py` (mirrors existing one-model-per-file convention).
- Edits: `backend/models/__init__.py`, `backend/main.py`, `backend/dependencies.py`, `backend/pyproject.toml`, `docker-compose.yml`, `docker-compose.prod.yml`.
- New test: `backend/tests/test_story_10_1.py`. Edits to existing `test_story_*.py` client fixtures (Task 5).
- No conflicts with the unified structure: business logic stays out of routers; the gate is a dependency, not logic.

### References
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09-multi-user-oauth.md#4.3] — Epic 10 story breakdown (10.1 definition).
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09-multi-user-oauth.md#4.2] — `User` model fields, session middleware, `get_current_user`.
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09-multi-user-oauth.md#2.3] — architecture conflicts (data model, sessions, every-router scoping).
- [Source: backend/models/config.py] — legacy `Config` model (kept).
- [Source: backend/dependencies.py] — where `get_current_user` goes.
- [Source: backend/main.py] — app/middleware/router wiring; lifespan `create_all`.
- [Source: backend/services/token_manager.py + backend/services/spotify.py] — current single-token reads (migrate in 10.2, untouched here).
- [Source: backend/tests/test_story_9_1.py] — canonical TestClient + `dependency_overrides` fixture pattern.
- [Source: CLAUDE.md] — backend conventions (services vs routers, snake_case, no wrapper), Docker-only tests, Postman sync rule.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Code, dev-story workflow)

### Debug Log References

- Full suite before gate: 85 passed / 71 failed (existing router tests hit the new 401 gate as expected).
- After fixture repair (`get_current_user` override added to 15 router-test fixtures): 156 passed / 0 failed.
- Live smoke test (running container): `GET /health` → 200, `GET /api/v1/auth/status` → 200, `GET /api/v1/config` → 401 `{"detail":"Not authenticated"}`, `GET /api/v1/playlists` → 401.

### Completion Notes List

- **User model** added alongside (NOT replacing) `Config` per scope boundary; `Config` left intact for legacy token/credential reads (migrated in 10.2/10.3). `created_at` modeled as `Optional[str]` to avoid requiring it before 10.2 creates users.
- **SessionMiddleware** wired in `main.py`: `secret_key` from `SESSION_SECRET` (insecure dev default `insecure-dev-secret-change-me`), `session_cookie="session"`, `same_site="lax"`, `https_only` driven by `SESSION_COOKIE_SECURE` env (true in prod compose). `HttpOnly` is on by default in Starlette.
- **`get_current_user`** added to `dependencies.py` reading `request.session["user_id"]` → loads `User` → 401 `"Not authenticated"` on missing session or missing row. Exported `CurrentUserDep` alias.
- **Auth gate** applied at include-time via a shared `dependencies=[Depends(get_current_user)]` on the 5 business routers; `auth_router` and `GET /health` left public. Gate's 401 detail (`"Not authenticated"`) is distinct from the legacy Spotify `ValueError`→401 (`"Not authenticated — run OAuth2 flow first"`); both 401, different detail strings.
- **Tests**: new `test_story_10_1.py` (14 tests). 15 existing router-test fixtures patched to inject a fake authenticated `User` via `app.dependency_overrides[get_current_user]`. `test_story_2_3` and `test_story_1_3` left untouched (they only hit public `/auth/status` and `/health`).
- **AC#6 (no leakage)**: session payload only ever holds `user_id` (int); no `User` serializer or new endpoint exposes `client_secret`/`token_json`/`client_id`/tokens.
- **Postman**: collection `31411470-...` updated — top-level description + 5 protected-folder descriptions note the 401 session requirement; Auth & Health folders left public. Verified via GET.
- **Scope respected**: no login endpoint, no session writes in production code, no `user_id` FKs on existing tables, `Config`/`token_manager`/`spotify.py` untouched — all deferred to 10.2/10.3.

### File List

- `backend/models/user.py` (new)
- `backend/models/__init__.py` (modified — register `User`)
- `backend/dependencies.py` (modified — `get_current_user`, `CurrentUserDep`)
- `backend/main.py` (modified — `SessionMiddleware`, auth gate on 5 routers)
- `backend/pyproject.toml` (modified — add `itsdangerous>=2.0`)
- `backend/uv.lock` (modified — `itsdangerous==2.2.0` resolved)
- `docker-compose.yml` (modified — backend `SESSION_SECRET` env)
- `docker-compose.prod.yml` (modified — `SESSION_SECRET` + `SESSION_COOKIE_SECURE` env)
- `backend/tests/test_story_10_1.py` (new — 14 tests)
- `backend/tests/test_story_2_4.py`, `test_story_3_1.py`, `test_story_3_2.py`, `test_story_3_5.py`, `test_story_4_2.py`, `test_story_5_1.py`, `test_story_5_2.py`, `test_story_5_3.py`, `test_story_7_1.py`, `test_story_8_1.py`, `test_story_8_2.py`, `test_story_8_3.py`, `test_story_9_1.py`, `test_story_9_7.py`, `test_story_9_8.py` (modified — inject authenticated `User` in client fixtures)

### Change Log

| Date | Change |
|------|--------|
| 2026-06-09 | Story created (context engine analysis — Epic 10 foundation, built from Sprint Change Proposal + codebase). |
| 2026-06-09 | Implemented 10.1: `User` model, `SessionMiddleware`, `get_current_user` dependency, auth gate (401) on 5 business routers. Added `itsdangerous`. New `test_story_10_1.py` (14 tests); 15 router-test fixtures repaired. Full suite green (156 passed). Postman collection annotated. Status → review. |
