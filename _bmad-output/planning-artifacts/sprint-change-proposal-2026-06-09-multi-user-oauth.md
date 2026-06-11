# Sprint Change Proposal — Multi-User Spotify OAuth (per-user credentials)

**Date:** 2026-06-09
**Author:** kevin (navigated via Correct Course)
**Mode:** Batch
**Change scope classification:** **MAJOR** (strategic pivot — invalidates a core PRD constraint)

---

## Section 1 — Issue Summary

**Problem statement:** The application deployed at `biistoufleex.fr` is single-tenant. Every visitor lands on the owner's data and operates Spotify through the owner's single stored OAuth token. There is no per-visitor login, no session isolation, and no data scoping.

**How it was discovered:** Observed in production after deployment (Caddy/HTTPS prod, commits `3930bdc` → `8ba23f7`).

**Root cause (evidence):**
- `services/spotify.py` → `_get_spotify_oauth()` reads `client_id`/`client_secret` from the **single** `Config` row.
- `services/token_manager.py` → `SQLiteCacheHandler` stores **one** token in `Config.spotify_token_json`.
- `services/spotify.py` → `get_authenticated_client()` returns a Spotify client built from that **one global token** for every request.
- No session/cookie/user concept exists anywhere.
- `Playlist`, `track_blacklist`, `sync_log` tables and the APScheduler job are all **global**, not scoped to any user.

**Issue type:** Strategic pivot — the product was specified as single-user; deploying it publicly created a requirement the design never accounted for.

**Chosen target shape (user decisions, 2026-06-09):**
- Per-user **Spotify OAuth login** — each visitor authenticates with their own Spotify account and sees only their own data.
- **`client_id`/`client_secret` stay in the database, entered per user** (the current setup behaviour is kept, just made per-user — NOT moved to env).
- Scope kept minimal: **add a login flow + a logout button**; everything else follows from per-user data scoping.

---

## Section 2 — Impact Analysis

### 2.1 External constraint (acknowledge)

Spotify apps default to **Development Mode**: up to **25 users** per app, each added manually by email in the Spotify Developer Dashboard.

**Note — per-user credentials change the math:** because each user supplies **their own** `client_id`/`client_secret` (their own Spotify app), each user only needs to allow-list *themselves* in *their own* app. This naturally sidesteps the global 25-user limit and avoids any Extended Quota Mode request — at the cost of each user having to create a Spotify Developer app (this is already the current onboarding burden, kept as-is).

### 2.2 PRD conflicts

| PRD element | Status | Conflict |
|---|---|---|
| "Target user: **Single user** (personal tool)" | ❌ Invalidated | Becomes multi-user. |
| MVP Philosophy: "**No multi-user**" | ❌ Invalidated | Reversed. |
| **NFR7**: "no dashboard authentication layer required" | ❌ Invalidated | A session/login layer is now mandatory. |
| **FR18**: "User can configure Spotify API credentials" | ✅ **Kept** | Stays valid — now **per user** instead of one global config. |
| **AR6**: First-run setup wizard for credentials | ✅ **Kept** | Stays — it becomes the per-user login/setup screen. |
| **NFR5**: tokens server-side only, never to browser | ✅ Preserved & reinforced | Still true; now per-user. |

### 2.3 Architecture conflicts

| Area | Impact |
|---|---|
| **Data model** | The current single-row `Config` becomes a per-user **`User`** table: `id`, `spotify_user_id` (unique), `display_name`, `client_id`, `client_secret`, `token_json`, `playlist_size`, `cron_expr`, `target_playlist_id`, `created_at`. `Playlist`, `track_blacklist`, `sync_log` each gain a `user_id` FK. |
| **Token storage** | `SQLiteCacheHandler` becomes **per-user** (keyed by `user_id`), reading/writing `User.token_json` instead of the global `Config` row. |
| **Sessions** | New signed session cookie (Starlette `SessionMiddleware`, `SESSION_SECRET` env) mapping browser → `user_id`. OAuth `state` param binds the callback to the initiating session (CSRF). |
| **`_get_spotify_oauth` / `get_authenticated_client`** | Take the current user; build `SpotifyOAuth` from that user's `client_id`/`client_secret` and cache handler. |
| **Every router** | `playlists`, `sync`, `config`, `recently-added`, playlist detail — resolve the current user from session and filter all queries by `user_id`. Unauthenticated → 401 / redirect to login. |
| **Scheduler** | One global cron job → **per-user jobs** (`job_id = f"sync_{user_id}"`) from each user's `cron_expr`. |
| **Deployment** | `SPOTIFY_REDIRECT_URI` → `https://biistoufleex.fr/api/v1/auth/callback`, registered in **each user's** Spotify app dashboard (same callback URL for all). Add `SESSION_SECRET` to prod env. |
| **SQLModel auto-create (AR8, no Alembic)** | Adding `user_id` to existing tables with live prod data is not handled by `create_all()`. A one-shot migration/backfill (assign existing rows to the owner) or a dev-data reset is required. |

### 2.4 Login flow design (the "just a login button" wrinkle)

Because credentials are per-user and a not-logged-in visitor has no session, a plain "Login with Spotify" button cannot start OAuth on its own (no `client_id` known yet). **Resolution:**

- **New / returning user (single screen):** the login screen is the existing setup form — enter `client_id` + `client_secret`, click **Connect Spotify**.
- The credentials are held through the OAuth round-trip (in the session, keyed by `state`).
- **At callback:** exchange code → read `spotify_user_id`. If a `User` row with that `spotify_user_id` exists → load it (returning user); else create it. Persist/refresh the credentials + token on that row, open the session.
- **Logout:** button clears the session cookie; data stays in the DB for next login.

### 2.5 UX impact

- New **login/setup screen** for unauthenticated visitors (replaces "already in" behaviour).
- **Logout** button (sidebar footer "connected as" block, already in AppShell v2 design).
- Settings, playlists, logs all become per-user automatically once scoping lands.

### 2.6 Epic impact

| Epic | Impact |
|---|---|
| **Epic 1** (owns NFR7) | NFR7 invalidated; revision note. |
| **Epic 2** (Auth & Config) | OAuth + setup become per-user; session binding + logout added. |
| **Epic 3, 7, 8, 9** | Each needs `user_id` scoping in models, endpoints, queries. |
| **Epic 4** (Scheduler) | Per-user jobs. |
| **Epic 5** (Logs) | Per-user scoping. |
| **NEW Epic 10** (Accounts, Sessions & Multi-Tenancy) | `User` table, sessions, per-user OAuth, login/logout, data-scoping migration. |

---

## Section 3 — Recommended Path Forward

**Selected approach: Hybrid (Option 3 PRD review + new Epic 10).**

- **Option 1 — Direct Adjustment alone:** ❌ The single-user assumption is in the data model, NFR7, and every query — cannot be reached by editing a few stories.
- **Option 2 — Rollback:** ❌ Completed epics are correct; reverting gains nothing.
- **Option 3 — PRD MVP Review:** ✅ Required (amend single-user vision + NFR7).
- **Hybrid (recommended):** Amend PRD (vision + NFR7; FR18/AR6 stay, just per-user), amend Architecture (`User` table, sessions, per-user token, scheduler), add **Epic 10**, add scoping criteria to Epics 3/4/5/7/8/9.

**Effort:** High. **Risk:** Medium-High (data model, every query, live prod DB).

---

## Section 4 — Detailed Change Proposals

### 4.1 PRD changes

```
Executive Summary — "Target user"
OLD: Single user (personal tool).
NEW: Multiple independent users. Each authenticates with their own Spotify
     account and their own Spotify app credentials, and sees only their own data.

MVP Philosophy
OLD: "No multi-user, no deployment complexity."
NEW: "Multi-user via per-account Spotify OAuth. Each user supplies their own
      Client ID/Secret (stored per user in the DB) and logs in with their Spotify
      account."

NFR7
OLD: "Application intended for local/personal deployment only; no dashboard
      authentication layer required."
NEW: "Each request is authenticated via a server-side session bound to a Spotify
      OAuth login. Unauthenticated requests are rejected. Session cookie is
      signed, HttpOnly, Secure (HTTPS prod)."

FR18 / AR6: UNCHANGED in intent — credentials are still entered by the user and
     stored in the DB; the setup wizard now runs per user and doubles as the login
     screen.
```

### 4.2 Architecture changes

- **`Config` → `User` model**: `id`, `spotify_user_id` (unique), `display_name`, `client_id`, `client_secret`, `token_json`, `playlist_size`, `cron_expr`, `target_playlist_id`, `created_at`. (App-global settings, if any remain, stay in a small `Config`.)
- **`Playlist`, `track_blacklist`, `sync_log`**: add `user_id` FK; all queries filtered by current user.
- **`token_manager.SQLiteCacheHandler`**: parameterized by `user_id`, reads/writes `User.token_json`.
- **`services/spotify.py`**: `_get_spotify_oauth(user)` builds `SpotifyOAuth` from the user's `client_id`/`client_secret`; add `state` to the authorize URL, validate on callback; `get_authenticated_client(user)`.
- **Sessions**: add `SessionMiddleware` (`SESSION_SECRET` env); `get_current_user` dependency → 401 / redirect if no valid session.
- **Login flow**: per §2.4 — credentials held via `state` through the round-trip; user resolved by `spotify_user_id` at callback.
- **Scheduler**: one APScheduler job per user (`sync_{user_id}`) from that user's `cron_expr`.
- **Deployment**: `https://biistoufleex.fr/api/v1/auth/callback` registered in each user's Spotify app; `SESSION_SECRET` in prod env.
- **Data migration**: one-shot script — create a `User` row for the existing owner, backfill `user_id` on existing `Playlist`/`track_blacklist`/`sync_log` rows (or reset dev data).

### 4.3 New Epic 10 — Accounts, Sessions & Multi-Tenancy (proposed stories)

- **10.1** — `Config` → `User` model + session middleware (`SessionMiddleware`, `SESSION_SECRET`) + `get_current_user` dependency + auth gate (401 / redirect to login for unauthenticated requests).
- **10.2** — Per-user login + logout: setup/login screen (enter client_id/secret → Connect), `state`-protected callback, user resolved/created by `spotify_user_id`, session opened; logout button clears session.
- **10.3** — Data scoping migration: add `user_id` to `Playlist`/`track_blacklist`/`sync_log`; backfill existing prod rows to the owner; filter every query by current user.
- **10.4** — Per-user scheduler jobs (one APScheduler job per user from their `cron_expr`).
- **10.5** — Prod hardening: redirect URI registered, signed/HttpOnly/Secure session cookie, returning-user flow verified end-to-end.

### 4.4 Existing-epic touch-ups

Stories in Epics 3/4/5/7/8/9 that query the DB or build Spotify clients gain a "scoped to current user" acceptance criterion (covered transversally by Story 10.3, verified per epic).

---

## Section 5 — Implementation Handoff

**Scope classification: MAJOR.** Recommended routing:

1. **Product Manager (`bmad-edit-prd`)** — amend Executive Summary, MVP Philosophy, NFR7 (FR18/AR6 unchanged in intent).
2. **Architect (`bmad-create-architecture` / edit)** — `Config`→`User`, sessions, per-user token, login flow, scheduler, migration.
3. **`bmad-create-epics-and-stories`** — add Epic 10 + scoping criteria; then **`bmad-sprint-planning`** to sequence.
4. **Developer (`bmad-dev-story`)** — implement Epic 10, order 10.1 → 10.2 → 10.3 first (foundation + login + scoping), then 10.4 → 10.5.

**Success criteria:** A visitor with no session is gated to the login screen; after connecting they see only their own playlists/logs and act on Spotify as themselves; the owner's data is no longer exposed to others; a logout button ends the session; existing prod data is preserved (assigned to the owner) or intentionally reset.

**Postman:** per `CLAUDE.md`, update the collection when auth/session routes change (Epic 10.2).
