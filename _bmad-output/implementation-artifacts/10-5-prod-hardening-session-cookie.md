# Story 10.5: Production Hardening — Redirect URI, Session Cookie & Returning-User Flow

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->
<!-- Source of truth: Epic 10 was NOT added to epics.md, and prd.md/architecture.md were NOT amended.
     This story is built from the Sprint Change Proposal (authoritative spec for Epic 10) §4.3 "10.5"
     + Stories 10.1/10.2 (the session + login machinery this story hardens, and their deferred-to-10.5
     open flags) + direct codebase analysis of main.py / routers/auth.py / services/spotify.py /
     LoginScreen.tsx / docker-compose.prod.yml / Caddyfile / DEPLOIEMENT.md. See References. -->

## Story

As the **operator of the multi-tenant deployed app (and every user who logs in)**,
I want **production to enforce a strong session secret, show each user the exact Redirect URI they must register, harden the session cookie behind HTTPS, and have the returning-user login round-trip verified end-to-end**,
so that **sessions cannot be forged, new users can complete OAuth on the first try, and a returning user lands back on their own data instead of hitting `auth_error` or a duplicated account**.

## Context & Scope Boundary (READ FIRST)

This is the **final story of Epic 10** — pure **production hardening + end-to-end verification** of the multi-user OAuth pivot built across 10.1→10.4. The mechanics already exist and work in dev; 10.5 closes the gaps that only bite in the deployed HTTPS environment. **It re-architects nothing.** It tightens config/secrets, makes the Redirect-URI hint correct in prod, hardens the session cookie, fixes stale deploy docs, and verifies the returning-user flow.

Two prior stories explicitly deferred their prod concerns here:
- **10.1** deferred: "Prod hardening (Secure/HttpOnly cookie flags verified in prod, redirect URI registration)."
- **10.2** deferred its **open flag #1** (the cookie-domain / `127.0.0.1`-vs-`localhost` nuance) and "returning-user end-to-end verification" → **explicitly to 10.5.**

**The four concrete gaps this story closes (each is a real, verified defect, not hypothetical):**

1. **The Redirect-URI hint shown to users is hardcoded to DEV.** [LoginScreen.tsx:6](frontend/src/features/auth/LoginScreen.tsx#L6) hardcodes `http://127.0.0.1:8000/api/v1/auth/callback`. The backend's *actual* `REDIRECT_URI` is env-driven and is `https://<DOMAIN>/api/v1/auth/callback` in prod ([docker-compose.prod.yml:9](docker-compose.prod.yml#L9)). A prod visitor is therefore told to register the **wrong** URI in their Spotify dashboard → Spotify rejects the callback → `auth_error`. The fix: the **backend is the source of truth** for the Redirect URI; expose it so the login screen always displays exactly what the backend sends to Spotify.

2. **`SESSION_SECRET` fails OPEN in prod.** [main.py:52](backend/main.py#L52) falls back to the literal `"insecure-dev-secret-change-me"` when `SESSION_SECRET` is unset/empty. Because the session cookie is **signed, not encrypted** (Starlette + `itsdangerous`), a publicly-known signing key lets anyone forge a `{"user_id": N}` cookie and impersonate any user. Compose passes `${SESSION_SECRET}` but `.env.prod.example` never defines it — so a real deploy silently runs on the public dev key. The fix: in the prod posture, **fail fast at startup** if the secret is missing or equals the dev default.

3. **`.env.prod.example` + `DEPLOIEMENT.md` are missing `SESSION_SECRET` and are stale for multi-user.** The deploy doc still describes a single-user "wizard de setup" (§7) and never mentions generating a session secret. A first-time operator following the guide produces an insecure, single-user-worded deploy.

4. **The returning-user round-trip is unverified behind HTTPS.** The code (resolve-or-create by `spotify_user_id`, `SameSite=lax` cookie surviving the top-level callback redirect) exists from 10.2 but was only smoke-tested over dev's split-origin (`127.0.0.1` vs `localhost`). 10.5 verifies it on the real same-origin Caddy/HTTPS deployment and pins the invariant with a test.

**IN SCOPE (10.5):**
- **Expose the backend Redirect URI to the frontend** (source of truth) and render it in `LoginScreen` instead of the hardcoded dev string.
- **Fail-fast `SESSION_SECRET` guard** in prod posture (missing or == dev default → refuse to boot).
- **Session-cookie hardening review**: confirm `HttpOnly` (always), `Secure` (prod via `SESSION_COOKIE_SECURE=true`), `same_site="lax"` (required for OAuth — see below), and set an **explicit `max_age`** instead of relying on Starlette's silent default.
- **Behind-proxy correctness check**: Caddy terminates TLS and forwards HTTP to the backend; confirm `https_only=True` still emits the `Secure` flag (it sets the cookie attribute, it does *not* inspect request scheme), and that the Caddy `@api` matcher routes `/api/v1/auth/callback`.
- **Returning-user verification**: a test pinning resolve-or-create (same `spotify_user_id` → same `User` row, no duplicate; creds/token re-persisted; data preserved) + a documented manual prod smoke-test checklist (real OAuth can't be unit-tested).
- **Docs/config**: add `SESSION_SECRET` (with `openssl rand -hex 32`) to `.env.prod.example`, `docker-compose.prod.yml` comment, and `DEPLOIEMENT.md`; update `DEPLOIEMENT.md` §7 + troubleshooting for the per-user login screen.
- **Tests + Postman** for any contract change (the redirect-URI exposure).

**EXPLICITLY OUT OF SCOPE — do NOT implement here:**
- **Any new product feature, model change, or query change.** 10.1–10.4 own identity/token/scoping/scheduler; 10.5 touches none of that logic.
- **Per-user scheduler jobs / sync logic** (done in 10.4). **Data scoping** (done in 10.3).
- **Removing the dev `SESSION_SECRET` default** — local dev must keep working over plain HTTP with the insecure default. The guard fires **only** in the prod posture.
- **Encrypting the session cookie / switching session backends.** Signed-cookie sessions are the chosen design (10.2 §"Session payload & security"); 10.5 hardens, not replaces.
- **Rate-limiting, brute-force protection, CSP, or other broad web-hardening** not named in the proposal's 10.5 line. Keep the scope to the four gaps above.
- **Cleaning up vestigial `PUT /config` credential fields** (10.2 open flag #2) — that is `Config` cleanup, not prod hardening.

**Default design decisions (committed; re-flagged as Open Questions at the end):**
1. **Expose the Redirect URI by adding a `redirect_uri` field to the existing public `GET /auth/status` response.** The login screen already fetches `/auth/status` via the public `useAuthStatus` hook (it renders for unauthenticated visitors), so no new endpoint or new fetch is needed. The value is `services.spotify.REDIRECT_URI` (the exact string the backend passes to `SpotifyOAuth`). The Redirect URI is **public, non-secret** information.
2. **Prod posture is detected via the existing `SESSION_COOKIE_SECURE` env** (already `true` only in prod compose) — no new env flag. When `SESSION_COOKIE_SECURE` is truthy AND `SESSION_SECRET` is missing/empty/equal-to-the-dev-default → raise at import/startup with a clear message.
3. **Set an explicit `max_age`** on `SessionMiddleware` (default **14 days = 1_209_600s**, matching Starlette's own default but now intentional and visible). Flagged as Open Question #3.

## Acceptance Criteria

1. **Prod refuses to boot on an insecure session secret.** When the prod posture is active (`SESSION_COOKIE_SECURE` truthy) and `SESSION_SECRET` is unset, empty, or equal to the dev default (`"insecure-dev-secret-change-me"`), the application **raises a clear `RuntimeError`** at startup (e.g. `"SESSION_SECRET must be set to a strong random value in production"`) instead of silently using the public dev key. In dev posture (`SESSION_COOKIE_SECURE` falsy/unset), the insecure default is still allowed and local boot is unaffected.

2. **The backend exposes its actual Redirect URI; the login screen renders it.** `GET /api/v1/auth/status` (public) includes a `redirect_uri` field equal to `services.spotify.REDIRECT_URI` (the exact value used to build `SpotifyOAuth`). `LoginScreen.tsx` displays **that** value in the "Add this Redirect URI to your Spotify app" block instead of the hardcoded `http://127.0.0.1:8000/...`. In prod this shows `https://<DOMAIN>/api/v1/auth/callback`; in dev it shows the backend default `http://127.0.0.1:8000/api/v1/auth/callback`. The hardcoded `REDIRECT_URI` constant in `LoginScreen.tsx` is removed.

3. **Session cookie is hardened and the flags are correct in each posture.** `SessionMiddleware` keeps `session_cookie="session"`, `same_site="lax"`, `HttpOnly` on (Starlette default), `https_only` driven by `SESSION_COOKIE_SECURE` (→ `Secure` flag in prod), and now an **explicit `max_age`**. A prod-posture request emits a `Set-Cookie: session=…` with `HttpOnly`, `Secure`, `SameSite=Lax`, and a `Max-Age`/`expires`. A dev-posture request emits the same **without** `Secure`. `same_site` is **`lax`, not `strict`** — documented in code because `strict` would drop the cookie on the top-level GET callback redirect from Spotify and break login.

4. **The flow works behind the TLS-terminating proxy.** It is confirmed (in code comments + the manual checklist) that Caddy terminates TLS and forwards plain HTTP to the backend, that `https_only=True` still sets the cookie's `Secure` attribute (Starlette sets the attribute; it does not inspect the request scheme, so a proxied HTTP request still gets a `Secure` cookie), and that the Caddy `@api path /api/* /health` matcher routes `/api/v1/auth/callback` to the backend. No `ProxyHeadersMiddleware` or scheme-rewrite is required for the cookie to be correct.

5. **Returning-user round-trip is correct and verified.** Logging in again with the same Spotify account (same `spotify_user_id`) resolves the **existing** `User` row — it does **not** create a duplicate — re-persists `client_id`/`client_secret`/`token_json`/`display_name`, opens a fresh session, and the user sees their previously-stored data. After `POST /auth/logout` (clears the cookie, keeps the DB row), reconnecting restores the same identity. This is covered by an automated test against the resolve-or-create path and by a manual prod smoke-test step.

6. **Deploy config + docs are complete and multi-user-correct.** `.env.prod.example` defines `SESSION_SECRET` with a generation hint (`openssl rand -hex 32`) and a "never commit a real value" note. `DEPLOIEMENT.md` §4 includes generating/setting `SESSION_SECRET`; §7 ("Premier lancement") describes the **per-user login screen** (enter Client ID/Secret → Connect Spotify), not a single-user wizard; the §9 troubleshooting `auth_error` row notes the Redirect URI shown in-app must match the Spotify dashboard entry exactly, and that **each user** registers the **same** callback URL in **their own** Spotify app. The `docker-compose.prod.yml` `SESSION_SECRET` comment already exists — keep it accurate.

7. **No secret/token leakage (NFR5 preserved).** The new `redirect_uri` field exposes only the public callback URL — never `client_id`/`client_secret`/`token_json`/tokens. No other field is added to any response. The session payload still holds only `user_id` (+ the transient pending creds during the round-trip, popped on success).

8. **Full suite green; new behavior covered.** A new `backend/tests/test_story_10_5.py` proves: (a) the `SESSION_SECRET` prod-guard raises when secure+missing/empty/default and does **not** raise in dev posture or when a strong secret is set; (b) `GET /auth/status` returns the `redirect_uri` field (both unauthenticated and authenticated); (c) returning-user resolve-or-create reuses the row (no duplicate) and re-persists creds/token; (d) no `client_secret`/`token_json` appears in the status response. All pre-existing backend tests still pass via Docker; `frontend npm run build` passes.

9. **Postman updated.** `GET /auth/status` is re-documented to include the new `redirect_uri` field (and an example), in the collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`), verified via a follow-up GET. No new routes are added.

10. **Manual prod smoke-test checklist is recorded.** Because real Spotify OAuth cannot be exercised in pytest, `DEPLOIEMENT.md` (or the story's Completion Notes) records a short, ordered manual checklist the operator runs once after deploy: (1) `SESSION_SECRET` set → container boots; (2) open `https://<DOMAIN>`, the in-app Redirect URI matches what's registered in Spotify; (3) new user connects → lands on their dashboard; (4) DevTools → the `session` cookie is `Secure` + `HttpOnly` + `SameSite=Lax`; (5) logout → cookie cleared → reconnect with the same account → same data, no duplicate user.

## Tasks / Subtasks

- [x] **Task 1: Fail-fast `SESSION_SECRET` guard in prod posture** (AC: #1)
  - [x] In `backend/main.py`, before constructing `SessionMiddleware`, compute the prod posture from the existing `SESSION_COOKIE_SECURE` env (`os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"`).
  - [x] Read `SESSION_SECRET` once. If prod posture AND (`SESSION_SECRET` is `None`/empty OR equals the dev default `"insecure-dev-secret-change-me"`) → `raise RuntimeError("SESSION_SECRET must be set to a strong random value in production (e.g. `openssl rand -hex 32`)")`.
  - [x] Keep the dev fallback for the non-prod posture (local HTTP must still work). Reuse the resolved secret + posture for the middleware kwargs (don't re-read env twice).
  - [x] Add a short comment explaining the guard exists because the cookie is *signed, not encrypted* — a known key = forgeable sessions.

- [x] **Task 2: Harden the session cookie + explicit max_age** (AC: #3, #4)
  - [x] In `backend/main.py` `SessionMiddleware(...)`, add `max_age=1_209_600` (14 days; intentional, was Starlette's silent default). Keep `session_cookie="session"`, `same_site="lax"`, `https_only=<prod posture>`.
  - [x] Upgrade the existing middleware comment: state explicitly **why `same_site="lax"` (NOT `strict`)** — the OAuth callback is a top-level GET navigation back from `accounts.spotify.com`; `lax` sends the session cookie on it (so the `oauth_state` validation in `routers/auth.py` can read it), `strict` would not and login would always `auth_error`.
  - [x] Add a comment that `https_only=True` sets the cookie `Secure` *attribute* and does not inspect the request scheme, so it is correct behind Caddy (which terminates TLS and proxies plain HTTP).

- [x] **Task 3: Expose the Redirect URI from the backend** (AC: #2, #7)
  - [x] In `backend/routers/auth.py`, add `redirect_uri: str` to `AuthStatusResponse`. Populate it from `spotify_service.REDIRECT_URI` in **both** return branches of `auth_status` (unauthenticated and authenticated) so the login screen (which renders pre-auth) always receives it.
  - [x] Do NOT add any credential/token field. `redirect_uri` is the only new field.
  - [x] (`REDIRECT_URI` is already a module-level constant in `services/spotify.py`; import the module as `spotify_service` is already done — reference `spotify_service.REDIRECT_URI`.)

- [x] **Task 4: Render the backend Redirect URI in the login screen** (AC: #2)
  - [x] In `frontend/src/features/auth/LoginScreen.tsx`, **remove** the hardcoded `const REDIRECT_URI = 'http://127.0.0.1:8000/...'`.
  - [x] Source the value from auth status. `LoginScreen` currently takes only `hasPreviousAuth`; pass the `redirect_uri` from the same `useAuthStatus` data already used by `AppShell`/the gate (add a `redirectUri?: string` prop, OR read `useAuthStatus()` inside `LoginScreen`). Prefer threading it as a prop from wherever `LoginScreen` is rendered (consistent with how `hasPreviousAuth` is passed) to avoid a second hook call. Render it in the "Add this Redirect URI" block; if absent (status still loading), fall back to a neutral placeholder or hide the line until loaded.
  - [x] `frontend/src/types/index.ts`: add `redirect_uri?: string` to the `AuthStatus` type.
  - [x] `frontend npm run build` (Docker, Node 22) must pass.

- [x] **Task 5: Deploy config + docs** (AC: #6, #10)
  - [x] `.env.prod.example`: add `SESSION_SECRET=` with a comment: generate via `openssl rand -hex 32`, must be strong/random, never commit a real value. (Keep the existing DOMAIN/ACME_EMAIL entries.)
  - [x] `DEPLOIEMENT.md` §4: add a step to generate and set `SESSION_SECRET` in `.env.prod` (`openssl rand -hex 32`). §7: reword "wizard de setup" → the **per-user login screen** (Client ID/Secret → Connect Spotify); note the in-app Redirect URI must match the Spotify dashboard entry. §9 troubleshooting: update the `auth_error` row to say the Redirect URI shown in the app must match the dashboard exactly, and that each user registers the same `https://<DOMAIN>/api/v1/auth/callback` in their **own** Spotify app. §5 already documents the correct prod Redirect URI — leave it.
  - [x] Record the **manual prod smoke-test checklist** (AC#10) — add it to `DEPLOIEMENT.md` (a new short subsection, e.g. under §7) and mirror it in this story's Completion Notes.
  - [x] Verify the `docker-compose.prod.yml` `SESSION_SECRET` / `SESSION_COOKIE_SECURE` block is accurate (it already exists from 10.1) — adjust only if wording drifted. (Already accurate; left unchanged.)

- [x] **Task 6: Tests** (AC: #8)
  - [x] New `backend/tests/test_story_10_5.py`:
    - (a) **Prod guard**: with `monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")` and `SESSION_SECRET` unset/empty/`"insecure-dev-secret-change-me"`, (re)importing/constructing the app raises `RuntimeError`; with a strong secret it does not; with `SESSION_COOKIE_SECURE` unset (dev) and no secret it does not. (Use `importlib.reload(main)` under `monkeypatch.context()` — see Testing standards for the reload caveat.)
    - (b) **`redirect_uri` exposed**: `GET /api/v1/auth/status` (no session) returns `redirect_uri` == the configured value; with an authenticated user it still returns it. Patch/set `SPOTIFY_REDIRECT_URI` (or assert against `services.spotify.REDIRECT_URI`) to confirm it reflects the env.
    - (c) **Returning user**: call the resolve-or-create path twice for the same `spotify_user_id` (mock `services.spotify.SpotifyOAuth` + `services.spotify.Spotify` as in `test_story_10_2.py`) → exactly one `User` row, creds/token re-persisted on the existing row.
    - (d) **No leak**: assert `client_secret`/`client_id`/`token_json` are absent from the `/auth/status` JSON.
  - [x] Run the FULL suite: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → all green (**202 passed** = 192 baseline from 10.4 + 10 new 10.5 tests).
  - [x] If adding `redirect_uri` to `AuthStatusResponse` breaks any `/auth/status` assertion in `test_story_2_3.py` / `test_story_10_2.py`, update those expectations (additive field; most dict-subset assertions tolerate it). (No breakage — existing assertions are dict-subset; left unchanged.)

- [x] **Task 7: Postman** (AC: #9)
  - [x] Update `GET /auth/status` in the collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`): document the new `redirect_uri` field and refresh the example response. Verify via a follow-up GET. No new routes.

## Dev Notes

### Authoritative spec & how 10.5 fits
- **Source of truth = the Sprint Change Proposal** (Epic 10 was never written into `epics.md`; PRD/architecture were not amended).
- §4.3 line: *"**10.5** — Prod hardening: redirect URI registered, signed/HttpOnly/Secure session cookie, returning-user flow verified end-to-end."* — these three clauses map 1:1 to AC#2 (redirect URI), AC#1+#3+#4 (signed/HttpOnly/Secure cookie), AC#5 (returning-user end-to-end).
- §2.3 (deployment): *"`SPOTIFY_REDIRECT_URI` → `https://biistoufleex.fr/api/v1/auth/callback`, registered in **each user's** Spotify app dashboard (same callback URL for all). Add `SESSION_SECRET` to prod env."* — the same callback URL serves all users; each must register it in their own app (AC#6).
- §2.4 (login flow): the returning-user resolution by `spotify_user_id` at callback — the invariant AC#5 verifies.
- §5 success criteria: *"existing prod data is preserved … a logout button ends the session."* — returning-user + logout, hardened here.

### What 10.1/10.2 already built that 10.5 hardens (do NOT rebuild)
- **10.1**: `SessionMiddleware` in [main.py:50-56](backend/main.py#L50-L56) (`secret_key` from `SESSION_SECRET` w/ insecure dev default, `session_cookie="session"`, `same_site="lax"`, `https_only` from `SESSION_COOKIE_SECURE`). `SESSION_SECRET` + `SESSION_COOKIE_SECURE=true` already in `docker-compose.prod.yml`. **10.5 adds the prod guard + explicit `max_age`; it does not move or rename the middleware.**
- **10.2**: the whole login round-trip — [`start_login`](backend/services/spotify.py#L34) (transient `MemoryCacheHandler` + CSRF `state`), [`complete_login`](backend/services/spotify.py#L57) (resolve-or-create `User` by `spotify_user_id`, persist creds/token, open session), [`/auth/callback`](backend/routers/auth.py#L45) (`state` validation → `auth_error` redirect on mismatch), [`/auth/logout`](backend/routers/auth.py#L62), session-based [`/auth/status`](backend/routers/auth.py#L69). `LoginScreen.tsx` + `credentials: 'include'` in `lib/api.ts`. **10.5 fixes the hardcoded URI hint and verifies the round-trip; the round-trip logic is correct as-is.**
- **10.2 open flag #1** (verbatim): *"the default `SPOTIFY_REDIRECT_URI` points at `127.0.0.1:8000` (direct backend) while the app runs on `localhost:5173` via the Vite proxy … Full returning-user end-to-end verification is deferred to **10.5**."* → AC#5 + the manual checklist resolve this. In **prod** there is no split origin: Caddy serves the SPA and proxies `/api` on the **same** `https://<DOMAIN>` origin, so the `lax` cookie set on the callback is the same cookie the SPA sends — the dev-only nuance disappears.

### Why the Redirect-URI hint must come from the backend (the core fix)
Spotify requires the `redirect_uri` sent in **both** the authorize request and the token exchange to **exactly** match a URI registered in the app's dashboard. The backend builds `SpotifyOAuth(redirect_uri=REDIRECT_URI, …)` from `SPOTIFY_REDIRECT_URI` ([services/spotify.py:18](backend/services/spotify.py#L18)). So the **only** correct string to tell the user to register is the backend's `REDIRECT_URI` — not `window.location.origin`-derived (the SPA origin and the backend's configured callback can differ in dev) and not a frontend constant (which is currently wrong in prod). Surfacing `REDIRECT_URI` via `/auth/status` makes the in-app instruction provably match what the backend will send. This is exactly the "redirect URI registered" clause of the 10.5 spec.

### Session cookie facts the dev must rely on (verified against the installed stack)
- **Signed, not encrypted.** Starlette `SessionMiddleware` serializes the session dict and signs it with `itsdangerous` (already in `pyproject.toml`/`uv.lock` from 10.1). Contents are tamper-proof but base64-readable. ⇒ A known `SESSION_SECRET` = forgeable `user_id` ⇒ the AC#1 guard. ⇒ Never put tokens/secrets in the session (only `user_id`, already the case).
- **`https_only` sets the cookie attribute, period.** It does not check `request.url.scheme`. Behind Caddy (TLS terminated, backend sees HTTP) the `Secure` flag is still emitted — correct. No `ProxyHeadersMiddleware` needed for the cookie. (It *would* be needed if the app generated absolute `https://` URLs itself, but the Redirect URI is taken from `SPOTIFY_REDIRECT_URI` env, not from the request, so this is moot.)
- **`same_site="lax"` is mandatory, not a preference.** The callback `GET /api/v1/auth/callback?...` is a top-level navigation initiated by `accounts.spotify.com`. With `lax`, the browser sends the `session` cookie on top-level GET navigations, so `request.session["oauth_state"]` is present and the CSRF check passes. With `strict`, the cookie would be withheld → `state != session.get("oauth_state")` → `auth_error` on every login. Do not "harden" it to `strict`.
- **`HttpOnly`** is on by default in Starlette's `SessionMiddleware` (not exposed as a kwarg) — JS cannot read the cookie. Verify in the manual checklist via DevTools.

### Behind-proxy topology (from Caddyfile + compose, already deployed)
- [Caddyfile](frontend/Caddyfile): `@api path /api/* /health` → `reverse_proxy backend:8000`; everything else serves the SPA with `try_files … /index.html`. `/api/v1/auth/callback` matches `/api/*` ✓. `www.<domain>` 301→ apex. TLS auto via Let's Encrypt.
- Backend is **not** internet-exposed (`expose: "8000"`, no `ports:`) — only Caddy reaches it. So all browser↔app traffic is same-origin HTTPS on `<DOMAIN>`; cookies and CORS-with-credentials behave straightforwardly (`allow_credentials=True` + explicit `CORS_ORIGINS=https://<DOMAIN>` already set).

### The reload caveat for the SESSION_SECRET guard test
The guard runs at module import / app construction time (`main.py` top-level), not inside a request. To test it, set env with `monkeypatch` then `importlib.reload(main)` inside a `monkeypatch.context()` (or build the app via a small factory if you prefer — but do NOT refactor `main.py` into a factory just for the test if a reload works; keep the change minimal). Reloading `main` re-runs middleware registration; assert it raises (or not). Restore module state after. Keep these env-sensitive tests isolated so they don't leak `SESSION_COOKIE_SECURE`/`SESSION_SECRET` into other tests.

### Testing standards (match the repo)
- Tests ONLY via Docker: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`. Baseline after 10.4 = **192 passed**.
- Auth-flow tests mock at the service boundary: `patch("services.spotify.SpotifyOAuth")` + `patch("services.spotify.Spotify")` (canonical: `test_story_10_2.py`). `MemoryCacheHandler` is real/safe. For `/auth/status`, the route reads `request.session` directly — use a `TestClient` and either set the session via the connect→callback round-trip (cookies persist on the client) or override `get_current_user` only where appropriate (status is public and reads the session, not the gate).
- Fixture pattern (canonical: `test_story_9_1.py` + the 10.1/10.2 additions): in-memory SQLite + `StaticPool`, `create_all`, `session` fixture, `client` fixture overriding `get_session` (+ `get_current_user` for gated routes). Clear `app.dependency_overrides` on teardown.
- snake_case JSON; arrays returned directly (no wrapper). The new field is `redirect_uri` (snake_case) ✓.

### Anti-patterns to avoid
- ❌ Do NOT derive the displayed Redirect URI from `window.location.origin` — it can differ from the backend's configured `SPOTIFY_REDIRECT_URI` and would re-introduce the mismatch. Take it from the backend.
- ❌ Do NOT change `same_site` to `"strict"` — it breaks the OAuth callback (cookie withheld on the cross-site top-level redirect).
- ❌ Do NOT remove the dev `SESSION_SECRET` default — local HTTP dev must keep working; the guard fires only in prod posture.
- ❌ Do NOT add `ProxyHeadersMiddleware`/`uvicorn --proxy-headers` to "fix HTTPS" — the cookie `Secure` flag is env-driven and already correct; the Redirect URI is env-driven, not request-derived. Adding it is scope creep with no benefit here.
- ❌ Do NOT expose `client_id`/`client_secret`/`token_json` when adding `redirect_uri` — only the public callback URL.
- ❌ Do NOT touch token storage, query scoping, or scheduler jobs (10.2/10.3/10.4). This is config/docs/verification only.
- ❌ Do NOT refactor `main.py` into an app-factory unless strictly necessary for the guard test — prefer `importlib.reload` and a minimal inline guard.

### Project Structure Notes
- **Backend edits:** `backend/main.py` (SESSION_SECRET guard + `max_age` + comments), `backend/routers/auth.py` (`redirect_uri` on `AuthStatusResponse`).
- **Frontend edits:** `frontend/src/features/auth/LoginScreen.tsx` (render backend `redirect_uri`, drop the constant), `frontend/src/types/index.ts` (`redirect_uri?` on `AuthStatus`), and the render site of `LoginScreen` if threading the prop (likely `AppShell.tsx` or wherever the auth gate renders it).
- **Docs/config:** `.env.prod.example`, `DEPLOIEMENT.md`, (verify) `docker-compose.prod.yml`.
- **New test:** `backend/tests/test_story_10_5.py`. Possible touch-ups: `test_story_2_3.py`, `test_story_10_2.py` (additive `/auth/status` field).
- **Conventions (CLAUDE.md):** business logic in `services/` not routers (this story's logic is config/middleware in `main.py` + a constant passthrough — no new business logic in routers); spotipy only via `services/spotify.py` (untouched); snake_case JSON; arrays direct; Docker-only tests; Postman synced on any contract change; shadcn via CLI / Node 22 for frontend.

### Open questions for the user (do not block implementation; flag in PR)
1. **Redirect-URI exposure surface.** Default = add `redirect_uri` to the existing public `GET /auth/status` (no new endpoint, login screen already fetches it). Alternative = a dedicated `GET /auth/config` returning `{redirect_uri}`. Default chosen for minimal surface + zero extra fetch.
2. **Prod-posture signal.** Default = reuse `SESSION_COOKIE_SECURE` (already prod-only) to gate the guard. Alternative = a separate `APP_ENV=production` flag. Default avoids a new env var.
3. **`max_age`.** Default = 14 days (`1_209_600s`, Starlette's own default, now explicit). Alternatives: 7 days (tighter) or 30 days (fewer re-logins). Tokens refresh server-side regardless of session age (the refresh token lives in `User.token_json`), so session length is purely a re-login-frequency/security trade-off.
4. **Guard strictness.** Default = raise only when `SESSION_COOKIE_SECURE` is truthy. A stricter alternative would also warn (log, not raise) in dev when the default secret is used. Default keeps dev silent.

### References
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09-multi-user-oauth.md#4.3] — Epic 10 breakdown; 10.5 = prod hardening (redirect URI / signed-HttpOnly-Secure cookie / returning-user end-to-end).
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09-multi-user-oauth.md#2.3] — deployment: prod `SPOTIFY_REDIRECT_URI`, same callback URL per user, add `SESSION_SECRET`.
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09-multi-user-oauth.md#2.4] — login flow / returning-user resolution by `spotify_user_id`.
- [Source: _bmad-output/implementation-artifacts/10-1-user-model-sessions-auth-gate.md#Session-middleware-specifics] — `SessionMiddleware` config, `https_only`, dev default, deferral of prod hardening to 10.5.
- [Source: _bmad-output/implementation-artifacts/10-2-per-user-login-logout.md] — login round-trip, `state` CSRF, resolve-or-create, `LoginScreen`, open flag #1 (cookie-domain nuance deferred to 10.5).
- [Source: backend/main.py:50-66] — `SessionMiddleware` + auth gate wiring (the guard + `max_age` land here).
- [Source: backend/routers/auth.py:26-31,69-83] — `AuthStatusResponse` + session-based `/auth/status` (add `redirect_uri`).
- [Source: backend/services/spotify.py:18,34-99] — `REDIRECT_URI` constant; `start_login`/`complete_login` (resolve-or-create) the round-trip 10.5 verifies.
- [Source: frontend/src/features/auth/LoginScreen.tsx:6,68-72] — hardcoded dev Redirect-URI hint to replace with the backend value.
- [Source: docker-compose.prod.yml:6-13] — prod env: `SPOTIFY_REDIRECT_URI`, `SESSION_SECRET`, `SESSION_COOKIE_SECURE=true`.
- [Source: frontend/Caddyfile] — `@api path /api/* /health` proxy (routes the callback), TLS termination, SPA fallback.
- [Source: .env.prod.example + DEPLOIEMENT.md] — deploy config/docs to complete (add `SESSION_SECRET`, multi-user wording, smoke-test checklist).
- [Source: backend/tests/test_story_10_2.py + test_story_2_3.py] — canonical auth/`/auth/status` test patterns to extend.
- [Source: CLAUDE.md] — backend conventions, Docker-only tests, Postman sync rule, Node 22 / shadcn frontend rules.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Code / dev-story)

### Debug Log References

- Full backend suite via Docker: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → **202 passed** (192 baseline + 10 new).
- Frontend build via Docker: `docker exec playlist_spotify-frontend-1 npm run build` → green (tsc -b + vite build).
- Postman verified via follow-up `GET /collections/{uid}` — `redirect_uri` present in the Auth Status description + all 3 example bodies.

### Completion Notes List

- **AC#1 (prod guard):** `main.py` now computes prod posture from `SESSION_COOKIE_SECURE`, reads `SESSION_SECRET` once, and raises `RuntimeError("SESSION_SECRET must be set to a strong random value in production …")` when secure-posture + secret is missing/empty/dev-default. Dev posture keeps the insecure default so local HTTP is unaffected. Comment explains the cookie is *signed, not encrypted*.
- **AC#3/#4 (cookie hardening):** added explicit `max_age=1_209_600` (14 days). Kept `same_site="lax"` with a code comment on why `strict` would break the top-level OAuth callback, and a comment that `https_only` sets the Secure *attribute* (scheme-independent) so it is correct behind Caddy. No `ProxyHeadersMiddleware` added.
- **AC#2/#7 (redirect_uri):** `AuthStatusResponse` gains `redirect_uri: str` (default `""`), populated explicitly from `spotify_service.REDIRECT_URI` at request time in all three return branches so the value reflects the env and the pre-auth login screen always receives it. No credential/token field added.
- **AC#2 (frontend):** removed the hardcoded `REDIRECT_URI` constant from `LoginScreen.tsx`; the value is threaded as a `redirectUri` prop from `AppShell` (using the same `useAuthStatus` data as the gate, no second fetch); falls back to a neutral "Loading…" line until status resolves. `AuthStatus` type gains `redirect_uri?: string`.
- **AC#6/#10 (docs/config):** `.env.prod.example` defines `SESSION_SECRET=` with the `openssl rand -hex 32` hint + never-commit note. `DEPLOIEMENT.md` §4 adds the secret-generation step, §7 reworded to the per-user login screen (+ in-app Redirect URI matching), §9 troubleshooting updated (`auth_error` row + a new `SESSION_SECRET` boot-failure row), and §10/recap de-singled. `docker-compose.prod.yml` block already accurate — unchanged.
- **AC#5/#8 (tests):** `backend/tests/test_story_10_5.py` covers the guard (5 cases via `importlib.reload(main)` inside `monkeypatch.context()` + restore reload), `redirect_uri` exposure (unauth/auth/env-reflected), returning-user resolve-or-create (single row, creds/token re-persisted), and no-leak. No edits needed to `test_story_2_3.py`/`test_story_10_2.py` (their `/auth/status` assertions are dict-subset).

**Manual prod smoke-test checklist (AC#10 — run once after deploy; also recorded in `DEPLOIEMENT.md` §7 bis):**
1. `SESSION_SECRET` set in `.env.prod` → `backend` container boots (`make ps` → healthy); if missing it refuses to boot.
2. Open `https://<DOMAIN>` → the in-app Redirect URI matches what's registered in the Spotify dashboard.
3. New user enters Client ID/Secret + connects → lands on their dashboard.
4. DevTools → Cookies: `session` is `Secure` + `HttpOnly` + `SameSite=Lax`.
5. Logout → cookie cleared → reconnect with the same account → same data, no duplicate user row.

### File List

- `backend/main.py` (modified — SESSION_SECRET prod guard + explicit `max_age` + hardening comments)
- `backend/routers/auth.py` (modified — `redirect_uri` on `AuthStatusResponse`, populated in all return branches)
- `backend/tests/test_story_10_5.py` (new — guard / redirect_uri / returning-user / no-leak tests)
- `frontend/src/features/auth/LoginScreen.tsx` (modified — render backend `redirectUri` prop, dropped hardcoded constant)
- `frontend/src/components/layout/AppShell.tsx` (modified — thread `redirectUri` prop into `LoginScreen`)
- `frontend/src/types/index.ts` (modified — `redirect_uri?` on `AuthStatus`)
- `.env.prod.example` (modified — add `SESSION_SECRET` with generation hint)
- `DEPLOIEMENT.md` (modified — §4 secret step, §7 per-user login + smoke-test checklist, §9 troubleshooting, §10/recap multi-user wording)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified — 10-5 → in-progress → review)
- Postman collection `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` (updated — `GET /auth/status` `redirect_uri` doc + examples)

### Change Log

| Date | Change |
|------|--------|
| 2026-06-11 | Implemented Story 10.5 (prod hardening). SESSION_SECRET fail-fast guard + explicit cookie `max_age` in main.py; `redirect_uri` exposed on `GET /auth/status` and rendered in LoginScreen (hardcoded dev string removed); `.env.prod.example` + `DEPLOIEMENT.md` updated for multi-user + secret generation + manual smoke-test checklist; new `test_story_10_5.py` (full suite **202 passed**); frontend build green; Postman `/auth/status` re-documented. Status → review. |
| 2026-06-11 | Story created (context engine analysis — Epic 10 final story: prod hardening. Built from Sprint Change Proposal §4.3/§2.3/§2.4 + Stories 10.1/10.2 (and their deferred-to-10.5 flags) + exhaustive codebase analysis of main.py / routers/auth.py / services/spotify.py / LoginScreen.tsx / docker-compose.prod.yml / Caddyfile / DEPLOIEMENT.md). Four verified gaps targeted: hardcoded dev Redirect-URI hint, SESSION_SECRET fails-open in prod, missing/stale deploy docs, unverified returning-user flow. |
