# Story 10.2: Per-User Login & Logout

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->
<!-- Source of truth: Epic 10 was NOT added to epics.md, and prd.md/architecture.md were NOT amended.
     This story is built from the Sprint Change Proposal (authoritative spec for Epic 10) + Story 10.1
     (the foundation it builds on) + direct codebase analysis. See References. -->

## Story

As a **Spotify user visiting the deployed app**,
I want **to log in with my own Spotify app credentials and account, and log out again**,
so that **the app operates Spotify as me and stores my own token under my own identity, instead of everyone sharing the owner's single global credentials**.

## Context & Scope Boundary (READ FIRST)

This is the **login story** of Epic 10. Story 10.1 built the plumbing (`User` model, `SessionMiddleware`, `get_current_user`, the 401 auth gate). **Right now there is no code path that ever opens a session** — 10.1 only READS `request.session`. 10.2 is the story that finally **writes** the session: it adds the login round-trip that creates/resolves a `User` and sets `request.session["user_id"]`, plus a logout that clears it.

**IN SCOPE (10.2):**
- **Login flow** = the existing setup form repurposed: enter `client_id` + `client_secret` → **Connect Spotify**. Credentials are held in the (anonymous) session across the OAuth round-trip, bound by a CSRF `state`.
- **`state`-protected callback**: validate `state`, exchange `code`, read `spotify_user_id`/`display_name` via `sp.me()`, **resolve-or-create** the `User` row by `spotify_user_id`, persist creds + token on that row, and **open the session** (`request.session["user_id"] = user.id`).
- **Logout**: a public endpoint that clears the session cookie. Data stays in the DB for next login.
- **Per-user token storage**: `SQLiteCacheHandler` keyed by `user_id`, reading/writing `User.token_json` (no longer the global `Config.spotify_token_json`).
- **Per-user OAuth client**: `_get_spotify_oauth(user)` / `get_authenticated_client(user)` built from the user's `client_id`/`client_secret` + per-user cache handler. Thread `current_user` (the `CurrentUserDep` from 10.1) through the **request-scoped** business routers so a logged-in user operates Spotify **as themselves**.
- **`GET /auth/status`** becomes **session-based** (per-user), not global-`Config`-based.
- **Frontend**: send the session cookie on every request (`credentials: 'include'`); a single **login screen** for unauthenticated visitors (merges SetupWizard + SpotifyConnect — `/config` is now gated, so creds go to `/auth/connect`, not `PUT /config`); a **logout button** in the sidebar footer; show `display_name`; turn a 401 into "show the login screen".

**EXPLICITLY OUT OF SCOPE — do NOT implement here:**
- Adding `user_id` FK to `Playlist`/`track_blacklist`/`sync_log`, filtering DB queries by user, and migrating the **per-user settings** (`dynamic_playlist_id`, `playlist_size`, `cron_expr`, `last_sync_at`) off the global `Config` row onto `User` → **Story 10.3**. In 10.2, the **identity & token are per-user**, but the **settings & data rows stay global** (read from `Config` exactly as today).
- **Per-user scheduler jobs** (`sync_{user_id}`) → **Story 10.4**. The background scheduled sync still runs as one global job in 10.2 (see "Scheduler / background sync" below).
- **Prod hardening**: registering the redirect URI in each user's Spotify dashboard, verifying Secure/HttpOnly cookie flags in prod, returning-user end-to-end verification → **Story 10.5**.
- Do **NOT** delete the `Config` model — legacy settings (`dynamic_playlist_id`, `playlist_size`, `cron_expr`, `last_sync_at`) still live there until 10.3.

**Critical transitional consequence (the "ship together" window):** moving the token from `Config.spotify_token_json` to `User.token_json` means the business routers MUST be threaded with `current_user` **in this story** — otherwise a logged-in user's Spotify calls would look at the (now-empty) global token and break. That router-threading is therefore IN scope here. What stays deferred is the **DB query scoping** (which rows belong to whom) and the **settings migration** — those are 10.3. Per 10.1's note, 10.1 → 10.2 → 10.3 are designed to ship together; full multi-tenant correctness arrives with 10.3.

## Acceptance Criteria

1. **Connect accepts per-user credentials and starts a CSRF-protected flow.** `POST /api/v1/auth/connect` accepts a JSON body `{client_id, client_secret}`. It generates a random `state`, stores the pending credentials **and** the `state` in `request.session`, builds a `SpotifyOAuth` from those credentials, and returns `{auth_url}` where `auth_url` includes the `state` parameter. The endpoint is **public** (no auth gate — the visitor has no session-user yet).

2. **Callback validates `state`, resolves-or-creates the user, and opens the session.** `GET /api/v1/auth/callback?code=…&state=…`:
   - If `error` is present, `code` is missing, or `state` does not match the value stored in the session → redirect to `{FRONTEND_URL}?auth_error=1` and do **not** open a session.
   - On success: exchange `code` for a token (using the pending credentials), call `sp.me()` to read `spotify_user_id` and `display_name`. Look up `User` by `spotify_user_id`: if found, load it (returning user); else create it. Persist `client_id`, `client_secret`, `token_json`, `display_name`, and `created_at` (on create) on that row. Set `request.session["user_id"] = user.id`, clear the pending credentials + `state` from the session, and redirect to `FRONTEND_URL`.

3. **Logout clears the session.** `POST /api/v1/auth/logout` clears `request.session` (at minimum removes `user_id`) and returns success. It is **public** (callable whether or not a valid session exists) and does **not** delete any DB row.

4. **Token storage is per-user.** `SQLiteCacheHandler` is keyed by `user_id` and reads/writes `User.token_json` for that user. It no longer reads/writes the global `Config.spotify_token_json`. A token saved for user A is invisible to user B.

5. **Spotify clients are built per-user.** `_get_spotify_oauth(user)` and `get_authenticated_client(user)` build the client from the given user's `client_id`/`client_secret` and a `SQLiteCacheHandler(user.id)`. Every request-scoped business router that needs Spotify (`playlists`, `sync` manual stream, `recently_added`, playlist-detail tracks) passes the gate-resolved `current_user` through to the service. A logged-in user's Spotify operations act as that user.

6. **Auth status is session-based.** `GET /api/v1/auth/status` (public) returns `authenticated: false` when there is no session user. When a session user exists, it reports `authenticated` based on that user's token validity, and returns the user's `spotify_user_id` and `display_name`.

7. **Frontend gates on session and sends cookies.** `lib/api.ts` sends `credentials: 'include'` on every request. Unauthenticated visitors (401 from the gate, or `authenticated:false`) are shown a **single login screen** that collects `client_id`+`client_secret` and POSTs them to `/auth/connect`, then redirects to the returned `auth_url`. A **logout button** in the sidebar "Connected as" footer calls `POST /auth/logout` and returns the user to the login screen. The footer shows the user's `display_name` when available.

8. **No token/secret leakage.** Neither `/auth/status` nor any other endpoint exposes `client_secret`, `client_id`, `token_json`, or raw token fields to the browser. The session payload only ever holds `user_id` (int) plus the **transient** pending credentials during the connect→callback round-trip, which are removed once the session opens. (NFR5 preserved/reinforced.)

9. **Existing suite stays green; new behavior covered.** All pre-existing tests pass (router-test fixtures from 10.1 already inject an authenticated `User`; update any that break on the new `get_authenticated_client(user)` signature). A new `test_story_10_2.py` covers the connect/callback/logout/status flows, per-user token isolation, returning-user reuse, and no-leak assertions.

10. **Postman updated.** `/auth/connect` (now with body), `/auth/callback` (now with `state`), and the new `/auth/logout` are added/updated in the collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`), and `/auth/status` is re-documented as session-based.

## Tasks / Subtasks

- [x] **Task 1: Per-user token cache handler** (AC: #4)
  - [x] In `backend/services/token_manager.py`, change `SQLiteCacheHandler.__init__(self, user_id: int)`. `get_cached_token` reads `User.token_json` for that `user_id`; `save_token_to_cache` loads the `User` row and writes `json.dumps(token_info)` to `user.token_json` and commits. Import `User` from `models.user` (drop the `Config` import).
  - [x] Decide behavior when the `User` row doesn't exist yet on save (callback persists the token directly on the row — see Task 3 — so the cache handler is only used once a `user_id` exists). Keep it defensive: no-op or create nothing silently if the row is missing.

- [x] **Task 2: Per-user OAuth + threaded `get_authenticated_client`** (AC: #5)
  - [x] In `backend/services/spotify.py`, change `_get_spotify_oauth(user: User) -> SpotifyOAuth`: build from `user.client_id`/`user.client_secret` (raise `ValueError` if missing) and `cache_handler=SQLiteCacheHandler(user.id)`. Keep `REDIRECT_URI`/`SCOPES` as-is.
  - [x] Change `get_authenticated_client(user: User) -> Spotify` to take the user and pass it to `_get_spotify_oauth`.
  - [x] Thread `user` through the service functions that internally call `get_authenticated_client`: `get_user_playlists(user)`, `get_playlist_tracks(playlist_id, sp=None, since=None, user=None)`, `get_playlist_tracks_full(playlist_id, user)`, `get_playlist_tracks_page(playlist_id, limit, offset, user)`, `get_recently_added_tracks(user)`. Where `sp` is already passed in (e.g. from the sync stream), keep using it; only resolve a fresh client from `user` when `sp is None`.
  - [x] **Do NOT** change the global-`Config` reads for settings inside these functions (`dynamic_playlist_id`, `playlist_size`) — those stay on `Config` until 10.3.

- [x] **Task 3: Rewrite the auth router + service for the login round-trip** (AC: #1, #2, #3, #6)
  - [x] `POST /auth/connect`: accept body `ConnectRequest(client_id: str, client_secret: str)`. In the service, add `start_login(request_session: dict, client_id, client_secret) -> str`: generate `state` (e.g. `secrets.token_urlsafe(32)`), stash `request.session["pending_client_id"/"pending_client_secret"/"oauth_state"]`, build a **transient** `SpotifyOAuth(client_id, client_secret, redirect_uri=REDIRECT_URI, scope=SCOPES, state=state, cache_handler=MemoryCacheHandler())`, return `sp_oauth.get_authorize_url()`. (Use `spotipy.cache_handler.MemoryCacheHandler` — no DB write before the user exists.)
  - [x] `GET /auth/callback`: accept `code`, `state`, `error`. Validate `state == request.session.get("oauth_state")`; on mismatch/error/missing-code → `RedirectResponse(f"{FRONTEND_URL}?auth_error=1")`. Otherwise call a service `complete_login(request.session, code) -> None` that: rebuilds the transient `SpotifyOAuth` from the session's pending creds, `token_info = oauth.get_access_token(code, check_cache=False)`, `me = Spotify(auth=token_info["access_token"]).me()`, resolve-or-create `User` by `spotify_user_id`, persist `client_id`/`client_secret`/`token_json=json.dumps(token_info)`/`display_name`/`created_at`(on create), commit, then set `request.session["user_id"] = user.id` and pop the pending keys + `oauth_state`. Redirect to `FRONTEND_URL`. Wrap in try/except → `?auth_error=1` on failure.
  - [x] `POST /auth/logout`: `request.session.clear()` (or pop `user_id`); return `{"ok": true}` (200). Public route.
  - [x] `GET /auth/status`: read `request.session.get("user_id")`; if absent → `{authenticated: false, has_previous_auth: false, spotify_user_id: null, display_name: null}`. If present, load the `User`, build `get_authenticated_client(user)` and check token validity (mirror the existing `get_auth_status` logic but per-user), returning `spotify_user_id` + `display_name`.
  - [x] These four routes stay on `auth_router` (already public — NOT under the 10.1 auth gate). `request: Request` must be a parameter so the handlers can touch `request.session`.

- [x] **Task 4: Thread `current_user` through the business routers** (AC: #5)
  - [x] `routers/playlists.py`: inject `current_user: CurrentUserDep`, pass to `spotify_service.get_user_playlists(current_user)`.
  - [x] `routers/sync.py`: the manual SSE path calls `get_authenticated_client()` — resolve `current_user` at the endpoint (the gate guarantees one), thread it into the generator, and pass to `get_authenticated_client(current_user)`. The downstream `harvest_tracks`/`get_playlist_tracks` already receive the built `sp`, so no change there.
  - [x] `routers/recently_added.py` and the playlist-detail tracks endpoints (`routers/playlists.py` detail route): inject `current_user`, pass to `get_recently_added_tracks(current_user)` / `get_playlist_tracks_full(..., current_user)` / `get_playlist_tracks_page(..., current_user)`.
  - [x] Keep global-`Config` settings reads untouched (10.3 migrates them).

- [x] **Task 5: Scheduler / background sync transitional bridge** (AC: #5; defers to 10.4)
  - [x] `services/sync_engine.py` calls `get_authenticated_client()` with no user. The scheduled job has no request session. Add a clearly-tagged transitional resolver (e.g. `_resolve_scheduled_user()` returning the single/first `User` row) used ONLY by the background path, and pass it to `get_authenticated_client(user)`. **Tag it `# TODO(10.4): replace with per-user scheduled jobs`.** If no `User` exists yet, the job should no-op/skip gracefully (don't crash the scheduler).
  - [x] Do not build per-user jobs here — that is 10.4.

- [x] **Task 6: Frontend — cookies, login screen, logout** (AC: #7)
  - [x] `lib/api.ts`: add `credentials: 'include'` to both `apiFetch` and `apiFetchNoBody`.
  - [x] Login screen: repurpose `features/config/SetupWizard.tsx` (or a new `features/auth/LoginScreen.tsx`) to collect `client_id` + `client_secret` and `POST /auth/connect` **with that body**, then `window.location.href = auth_url`. Because `/config` is gated, the credential entry must POST to `/auth/connect`, NOT `PUT /config`. `SpotifyConnect.tsx`'s separate "Connect" step collapses into this one screen (no creds-then-connect two-step, since the visitor has no session yet). Keep the redirect-URI helper note.
  - [x] App gating: an unauthenticated visitor (401 or `authenticated:false`) must see the login screen instead of the dashboard/sidebar. Decide the cleanest gate point — `useAuthStatus` is public and already drives `DashboardPage`; extend the gate so the whole `AppShell` (sidebar + routes) is replaced by the login screen when there is no session user. Make `lib/api.ts` 401s resolve to "show login" rather than a generic error toast.
  - [x] Logout: add a button in the `AppShell` sidebar footer "Connected as" block → `POST /auth/logout` → invalidate auth queries / redirect to login. Use `display_name` (fallback `spotify_user_id`) for the footer label.
  - [x] `types/index.ts`: add `display_name?: string | null` to `AuthStatus`; add a `ConnectRequest` type if useful. `frontend npm run build` must pass (Node 22 — see project memory).

- [x] **Task 7: Tests** (AC: #9)
  - [x] New `backend/tests/test_story_10_2.py`: (a) `POST /auth/connect` with creds → 200, `auth_url` contains `state`, session holds pending creds + `oauth_state` (assert by mocking `SpotifyOAuth.get_authorize_url`); (b) callback with mismatched `state` → redirect `?auth_error=1`, no `user_id` in session; (c) callback happy path (mock `get_access_token` + `Spotify.me`) → creates `User`, sets `user_id`, redirects to `FRONTEND_URL`; (d) returning user (same `spotify_user_id`) → reuses the row, no duplicate; (e) token persisted to the right `User.token_json`, creds persisted; (f) `POST /auth/logout` → subsequent gated request returns 401; (g) `/auth/status`: no session → `authenticated:false`; with session+valid token → `authenticated:true` + `spotify_user_id`/`display_name`; (h) `SQLiteCacheHandler(user_id)` round-trips a token on the correct row and is isolated per user; (i) no `client_secret`/`token_json` in any response.
  - [x] Run the FULL suite: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`. Fix fallout from the new `get_authenticated_client(user)` signature in the existing router tests (they mock at the router boundary via `patch("routers.<m>.spotify_service.<fn>")`, so most `MagicMock`s tolerate the extra arg; adjust any that assert call args).
  - [x] For auth tests, mock at the service boundary: `patch("services.spotify.SpotifyOAuth")` and `patch("services.spotify.Spotify")`. The connect/callback handlers need `Request`; use `TestClient` which persists cookies across calls so the `state`/pending-creds round-trip works in one test.

- [x] **Task 8: Compose / env + Postman + docs** (AC: #10)
  - [x] Dev `docker-compose.yml` relies on code defaults for `FRONTEND_URL` (`http://localhost:5173`) and `SPOTIFY_REDIRECT_URI` (`http://127.0.0.1:8000/api/v1/auth/callback`). Prod compose already sets both (`https://${DOMAIN}/...`). No new env needed beyond 10.1's `SESSION_SECRET`. Align the redirect-URI hint string in the login screen with the actual default (`127.0.0.1` vs `localhost` — pick one and note it must match the Spotify dashboard entry).
  - [x] Update Postman (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`): `POST /auth/connect` now takes `{client_id, client_secret}`; `GET /auth/callback` documents `state`; add `POST /auth/logout`; re-document `GET /auth/status` as session-based. Verify via a follow-up GET.

## Dev Notes

### Authoritative spec & how 10.2 fits
- **Source of truth = the Sprint Change Proposal** (Epic 10 was never written into `epics.md`; PRD/architecture were not amended). Story 10.2 = proposal **§2.4** (login-flow design, the "just a login button" wrinkle) + **§4.3 "10.2"** + the per-user token/OAuth lines in **§4.2**.
- §4.3 line: *"10.2 — Per-user login + logout: setup/login screen (enter client_id/secret → Connect), `state`-protected callback, user resolved/created by `spotify_user_id`, session opened; logout button clears session."*
- §2.4 is the key design constraint: a plain "Login with Spotify" button cannot start OAuth because no `client_id` is known for an anonymous visitor. **Resolution:** the login screen *is* the credential form; creds are held in the session across the round-trip, bound by `state`; the user is resolved/created at callback by `spotify_user_id`.

### What 10.1 already built (do NOT redo)
- `backend/models/user.py` — the `User` table with `spotify_user_id` (unique), `client_id`, `client_secret`, `token_json`, `display_name`, `playlist_size`, `cron_expr`, `target_playlist_id`, `created_at`. Already registered in `models/__init__.py`.
- `backend/dependencies.py` — `get_current_user(request, session)` (401 if no `user_id`/no row) and `CurrentUserDep`.
- `backend/main.py` — `SessionMiddleware` (`SESSION_SECRET`, `session_cookie="session"`, `same_site="lax"`, `https_only` via `SESSION_COOKIE_SECURE`), CORS `allow_credentials=True` with explicit origins, and the **auth gate** (`dependencies=[Depends(get_current_user)]`) on the 5 business routers. `auth_router` and `GET /health` are public.
- `itsdangerous` already in `pyproject.toml` / `uv.lock`. Router-test fixtures (15 files) already override `get_current_user`.

### The chicken-and-egg the dev MUST get right
The OAuth round-trip needs an OAuth client *before* a `User` exists. So:
1. **connect**: build a **transient** `SpotifyOAuth` from the just-entered creds with a `MemoryCacheHandler` (NOT `SQLiteCacheHandler` — there's no `user_id` yet). Stash creds + `state` in the anonymous session (Starlette issues the cookie automatically on first write).
2. **callback**: rebuild that transient OAuth from the session creds, exchange the code in-hand (`get_access_token(code, check_cache=False)` returns the token dict), call `sp.me()`, resolve/create the `User`, then **write the token directly onto `User.token_json`** (don't rely on the cache handler for this first write). Only after the row exists does `SQLiteCacheHandler(user.id)` take over for refreshes.

### Current single-user auth flow you are replacing
- `routers/auth.py` today: `POST /auth/connect` (no body) → `get_auth_url()`; `GET /auth/callback?code` → `handle_callback(code)`; `GET /auth/status` → global `get_auth_status()`. **No `state`, no logout, no session writes.** All three read the global `Config`.
- `services/spotify.py` `_get_spotify_oauth()` reads `client_id`/`client_secret` from the single `Config` row and uses a no-arg `SQLiteCacheHandler()`. `get_authenticated_client()` builds the client from the one global token.
- `services/token_manager.py` `SQLiteCacheHandler` reads/writes `Config.spotify_token_json`.
- **Frontend gating today** (`pages/DashboardPage.tsx`): `if setup_required → SetupWizard` (PUT /config) → `if !authenticated → has_previous_auth ? ReauthBanner : SpotifyConnect` (POST /auth/connect). After 10.2, `/config` is gated, so this chain must move to the public `/auth/status` + the login screen. `SetupWizard`'s `PUT /config` credential write is **replaced** by `POST /auth/connect` with a body. `ReauthBanner`/`SpotifyConnect`'s no-body `POST /auth/connect` must also send the body now (or be folded into the single login screen).

### Settings stay on `Config` in 10.2 (this is intentional)
`get_or_create_dynamic_playlist`, `_persist_dynamic_playlist_id`, the sync stream's `playlist_size`/`last_sync_at` reads, and `routers/config.py` all keep reading/writing the global `Config` row. The `User` model has its own `playlist_size`/`cron_expr`/`target_playlist_id` columns (added in 10.1) but they are **dormant until 10.3** migrates settings onto them. Do not wire them up here — that drags 10.3 in.

### Scheduler / background sync
The APScheduler job is global (one job) until 10.4. `services/sync_engine.py` runs with no request session, so it can't use `current_user`. Bridge it transitionally (resolve the single/first `User` row) and tag for removal in 10.4. Manual sync (`routers/sync.py`, request-scoped) uses `current_user`. If zero users exist, the scheduled job must skip without crashing.

### Session payload & security (NFR5 / AC#8)
- Permanent session keys: only `user_id` (int).
- Transient session keys (connect→callback only): `pending_client_id`, `pending_client_secret`, `oauth_state` — **popped** once the session opens. They live in the signed (not encrypted) Starlette cookie, so they are tamper-proof but readable; this is the documented cost of the §2.4 design and is acceptable for the round-trip. Never put the **token** in the session.
- No response model exposes `client_secret`/`client_id`/`token_json`/tokens. `/auth/status` returns only `authenticated`, `has_previous_auth`, `spotify_user_id`, `display_name`.

### CORS / cookies
`allow_credentials=True` + explicit `CORS_ORIGINS` (not `*`) is already correct for cookie-bearing cross-origin requests. The only frontend change needed for cookies to flow is `credentials: 'include'` in `lib/api.ts` (currently absent). In dev, Vite proxies `/api/v1` to the backend (same-origin from the browser's view), so the cookie works over `localhost` HTTP with `https_only=false`.

### Testing standards (match the repo)
- Tests ONLY via Docker: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`.
- Fixture pattern (canonical: `test_story_9_1.py`, and the 10.1 additions): in-memory SQLite + `StaticPool`, `create_all`, `session` fixture, `client` fixture overriding `get_session` (and, for protected routes, `get_current_user`). Clear `app.dependency_overrides` on teardown.
- For the **auth flow** tests, do NOT override `get_current_user` (you're testing the real session round-trip). Use a `TestClient(app)` that persists cookies, and mock `services.spotify.SpotifyOAuth` / `services.spotify.Spotify` so no real Spotify calls happen. `MemoryCacheHandler` is real and safe to use.
- Service mocking convention: `patch("routers.<module>.spotify_service.<fn>", ...)`. JSON is snake_case; arrays returned directly (no `{"data": ...}`).
- TDD: write the connect/callback/logout/status tests first (red), implement, then run the full suite and fix existing-router fallout from the new `get_authenticated_client(user)` signature.

### Anti-patterns to avoid
- ❌ Do NOT add `user_id` columns to `Playlist`/`track_blacklist`/`sync_log` or filter queries by user — that is 10.3.
- ❌ Do NOT migrate `dynamic_playlist_id`/`playlist_size`/`cron_expr`/`last_sync_at` onto `User` — that is 10.3.
- ❌ Do NOT build per-user scheduler jobs — that is 10.4.
- ❌ Do NOT delete the `Config` model or `routers/config.py` — settings still live there.
- ❌ Do NOT use `SQLiteCacheHandler` before a `User` row exists (no `user_id` to key on) — use `MemoryCacheHandler` for the pre-login round-trip and write `token_json` directly at callback.
- ❌ Do NOT gate `/auth/*` (connect/callback/logout/status) or `/health` — they must stay public or login can never run.
- ❌ Do NOT skip `state` validation — it is the CSRF protection for the callback (§2.3).
- ❌ Do NOT expose `client_secret`/`token_json` in any response or put the token in the session.

### Project Structure Notes
- Edits: `backend/services/token_manager.py`, `backend/services/spotify.py`, `backend/services/sync_engine.py`, `backend/routers/auth.py`, `backend/routers/playlists.py`, `backend/routers/sync.py`, `backend/routers/recently_added.py`.
- New test: `backend/tests/test_story_10_2.py`. Possible edits to existing router tests (signature fallout).
- Frontend edits: `frontend/src/lib/api.ts`, `frontend/src/features/config/SetupWizard.tsx` (or new `features/auth/LoginScreen.tsx`), `frontend/src/features/auth/SpotifyConnect.tsx` + `ReauthBanner.tsx` (send body / fold into login), `frontend/src/components/layout/AppShell.tsx` (logout button, `display_name`), `frontend/src/pages/DashboardPage.tsx` (gating), `frontend/src/hooks/useAuthStatus.ts` (maybe a `useLogout` mutation), `frontend/src/types/index.ts`.
- Business logic stays in `services/`, not routers (CLAUDE.md). Spotipy calls only through `services/spotify.py`. snake_case JSON, no response wrapper.

### Open questions for the user (do not block implementation; flag in PR)
1. **Login UX**: collapse SetupWizard + SpotifyConnect into one screen (recommended, since the visitor has no session and creds must accompany connect), or keep a two-step "save creds → connect"? This story assumes one screen.
2. **`config.py` credential write**: `PUT /config` still writes `client_id`/`client_secret` to the global `Config` and is now gated. It becomes vestigial for credentials (creds flow through `/auth/connect`). Leave it for now (10.3 cleans up `Config`), or strip the credential fields from `ConfigWrite` here? This story leaves it.
3. **Logout scope**: `session.clear()` (drops everything) vs `session.pop("user_id")` (keeps nothing else of value anyway). This story uses `clear()`.

### References
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09-multi-user-oauth.md#2.4] — login flow design (creds held via `state` through the round-trip; user resolved by `spotify_user_id` at callback).
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09-multi-user-oauth.md#4.3] — Epic 10 story breakdown (10.2 = login + logout; 10.3 = scoping; 10.4 = per-user jobs).
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09-multi-user-oauth.md#4.2] — per-user token storage (`SQLiteCacheHandler` keyed by `user_id`), `_get_spotify_oauth(user)`, `get_authenticated_client(user)`, sessions, `state`.
- [Source: _bmad-output/implementation-artifacts/10-1-user-model-sessions-auth-gate.md] — foundation this builds on (User model, SessionMiddleware, get_current_user, auth gate, fixture pattern).
- [Source: backend/routers/auth.py] — current connect/callback/status (being rewritten).
- [Source: backend/services/spotify.py] — `_get_spotify_oauth`, `get_authenticated_client`, and all functions that call it (thread `user`).
- [Source: backend/services/token_manager.py] — `SQLiteCacheHandler` (make per-user).
- [Source: backend/services/sync_engine.py + backend/routers/sync.py] — background vs manual sync client construction.
- [Source: backend/main.py] — session middleware + auth gate wiring (public vs gated routers).
- [Source: frontend/src/pages/DashboardPage.tsx] — current setup/connect gating chain (move to /auth/status + login screen).
- [Source: frontend/src/lib/api.ts] — add `credentials: 'include'`.
- [Source: frontend/src/components/layout/AppShell.tsx] — "Connected as" footer (add logout, use display_name).
- [Source: frontend/src/features/config/SetupWizard.tsx + features/auth/SpotifyConnect.tsx + ReauthBanner.tsx] — login screen source material.
- [Source: docker-compose.yml + docker-compose.prod.yml] — `FRONTEND_URL`/`SPOTIFY_REDIRECT_URI`/`SESSION_*` env.
- [Source: CLAUDE.md] — backend conventions, Docker-only tests, Postman sync rule, shadcn CLI / Node 22 frontend rules.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Opus 4.8)

### Debug Log References

- Full backend suite (Docker): `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → **168 passed**.
- Frontend build (Docker): `docker exec playlist_spotify-frontend-1 npm run build` → **tsc + vite build OK** (pre-existing >500 kB chunk warning only).

### Completion Notes List

- **Per-user token cache** (`SQLiteCacheHandler(user_id)`): reads/writes `User.token_json`; defensive no-op when the row is missing (the callback writes the first token directly on the row).
- **Per-user OAuth**: `_get_spotify_oauth(user)` + `get_authenticated_client(user)` build from `user.client_id/secret` and a per-user cache handler. Consumer service fns take `user` (defaulted `None` so service-level unit tests that patch `get_authenticated_client` stay valid; routers always pass the gate-resolved `current_user`).
- **Login round-trip**: `start_login` (transient `MemoryCacheHandler` + CSRF `state` stashed in the anonymous session) → `complete_login` (state validated in the router, code exchanged, `sp.me()` → resolve-or-create `User`, token/creds persisted on the row, `session["user_id"]` opened, transients popped). Logout = `session.clear()`. `/auth/status` is now session-based and returns `display_name`.
- **Router threading**: `playlists` (list + detail tracks), `recently_added`, and the manual `sync/stream` SSE pass `current_user` through. Settings/data reads stay on the global `Config` (deferred to 10.3).
- **Scheduler bridge**: `_resolve_scheduled_user()` (tagged `TODO(10.4)`) resolves the single/first `User`; `run_sync` skips gracefully (`{"status":"skipped"}`) when no user has logged in. The 3 sync-engine test files now seed a `User` in their session fixture.
- **Frontend**: `credentials: 'include'` on every fetch; new merged `LoginScreen` (creds + connect in one form, posts body to `/auth/connect`); `AppShell` gates the whole shell on session auth and shows a logout button in the "Connected as" footer (uses `display_name`); `DashboardPage` gating removed (now shell-level). Orphaned `SetupWizard`/`SpotifyConnect`/`ReauthBanner` deleted.
- **Postman**: Auth folder updated — Connect (body), Callback (`state`), new Logout, session-based Status (verified via GET).
- **Open flags for review (not blockers):**
  1. Dev cookie-domain nuance — the default `SPOTIFY_REDIRECT_URI` points at `127.0.0.1:8000` (direct backend) while the app runs on `localhost:5173` via the Vite proxy; the session cookie set on the callback host is only shared if the visitor uses the matching host. Full returning-user end-to-end verification is deferred to **10.5**. LoginScreen hint uses `127.0.0.1:8000` to match the backend default.
  2. `PUT /config` still writes `client_id/secret` to the global `Config` and is now gated — left vestigial (10.3 cleans up `Config`).
  3. Logout uses `session.clear()` (per story assumption).

### File List

**Backend (modified):**
- `backend/services/token_manager.py` — `SQLiteCacheHandler(user_id)`, per-user `User.token_json`.
- `backend/services/spotify.py` — `_get_spotify_oauth(user)`, `start_login`, `complete_login`, `get_auth_status(user)`, `get_authenticated_client(user)`, `user` threaded through consumer fns.
- `backend/services/sync_engine.py` — `_resolve_scheduled_user()` + graceful skip; `get_authenticated_client(user)`.
- `backend/routers/auth.py` — rewritten: `ConnectRequest` body, `state`-protected callback, `/auth/logout`, session-based `/auth/status`.
- `backend/routers/playlists.py` — `current_user` threaded into list + tracks endpoints.
- `backend/routers/recently_added.py` — `current_user` threaded.
- `backend/routers/sync.py` — `current_user` threaded into the SSE stream.

**Backend (tests):**
- `backend/tests/test_story_10_2.py` — **new**, full connect/callback/logout/status + per-user token isolation + no-leak coverage.
- `backend/tests/test_story_1_3.py` — `SQLiteCacheHandler` tests re-baselined per-user.
- `backend/tests/test_story_2_3.py` — `get_auth_status(user)` + session-based `/auth/status`.
- `backend/tests/test_story_9_1.py` — `assert_called_once_with(..., ANY)` for the new `user` arg.
- `backend/tests/test_story_3_3.py`, `test_story_3_4.py`, `test_story_8_5.py` — seed a `User` in the session fixture (scheduled-sync resolver).

**Frontend (modified):**
- `frontend/src/lib/api.ts` — `credentials: 'include'`.
- `frontend/src/types/index.ts` — `display_name` on `AuthStatus`, new `ConnectRequest`.
- `frontend/src/hooks/useAuthStatus.ts` — new `useLogout`.
- `frontend/src/components/layout/AppShell.tsx` — auth gate + logout button + `display_name`.
- `frontend/src/pages/DashboardPage.tsx` — gating removed.

**Frontend (new):**
- `frontend/src/features/auth/LoginScreen.tsx` — merged credential + connect login screen.

**Frontend (deleted):**
- `frontend/src/features/config/SetupWizard.tsx`, `frontend/src/features/auth/SpotifyConnect.tsx`, `frontend/src/features/auth/ReauthBanner.tsx` — folded into `LoginScreen`.

**Other:**
- Postman collection `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` (Auth folder).

### Change Log

| Date | Change |
|------|--------|
| 2026-06-09 | Story created (context engine analysis — Epic 10 login/logout, built from Sprint Change Proposal §2.4/§4.2/§4.3 + Story 10.1 + codebase). |
| 2026-06-09 | Implemented per-user login/logout: per-user token cache + OAuth, state-protected login round-trip, session-based status, router threading, scheduler bridge, frontend login screen + logout + cookies. 168 backend tests pass, frontend builds, Postman updated. Status → review. |
</content>
</invoke>
