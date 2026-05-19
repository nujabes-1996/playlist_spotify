---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments: ['_bmad-output/planning-artifacts/prd.md', '_bmad-output/planning-artifacts/architecture.md']
---

# playlist_spotify - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for playlist_spotify, decomposing the requirements from the PRD and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: User can authenticate with Spotify via OAuth2 from the dashboard
FR2: User can re-authenticate with Spotify when the token expires or is revoked
FR3: The system automatically refreshes expired Spotify access tokens without user intervention
FR4: The system harvests all tracks from user-selected source playlists via the Spotify API
FR5: The system deduplicates tracks appearing in multiple playlists, retaining the most recent `added_at` date
FR6: The system sorts harvested tracks by `added_at` date in descending order
FR7: The system selects the top N tracks based on the configured playlist size
FR8: The system creates the target dynamic playlist on Spotify if it does not exist
FR9: The system replaces the target dynamic playlist contents on each sync
FR10: User can view all their user-created Spotify playlists
FR11: User can include or exclude individual playlists from the harvest
FR12: Playlist include/exclude preferences are persisted across sessions
FR13: The playlist list reflects newly added or removed playlists from the user's Spotify library
FR14: The system automatically executes syncs on a user-configured recurring schedule
FR15: User can configure the sync recurrence (interval or cron expression)
FR16: The scheduler persists and resumes after application restart
FR17: User can trigger a sync manually at any time
FR18: User can configure Spotify API credentials (Client ID, Client Secret)
FR19: User can configure the dynamic playlist size (number of tracks to retain)
FR20: All configuration is persisted and survives application restarts
FR21: User can view real-time sync progress during an active sync
FR22: User can view sync log entries including timestamp, status (success/failure), track count delta, and error cause
FR23: The dashboard surfaces a visible failure indicator when the last sync failed
FR24: User can access the full sync log history

### NonFunctional Requirements

NFR1: Dashboard initial page load under 3 seconds on local network
NFR2: Playlist list refresh from Spotify API under 2 seconds
NFR3: Real-time sync log events delivered to UI within 1 second of backend emission
NFR4: Sync engine processes up to 5,000 tracks within 30 seconds
NFR5: Spotify OAuth tokens stored server-side only; never returned to browser or exposed in API responses
NFR6: Spotify API credentials stored in local config (SQLite) with restricted access, not in source code or .env
NFR7: Application intended for local/personal deployment only; no dashboard authentication layer required
NFR8: All Spotify API communication over HTTPS
NFR9: Scheduler resumes configured schedule automatically after application restart
NFR10: Sync failure leaves existing dynamic playlist intact — previous contents preserved on error
NFR11: Every sync operation produces a log entry regardless of outcome
NFR12: HTTP 429 rate limit responses from Spotify API handled with retry and exponential backoff

### Additional Requirements

- AR1: Manual scaffolding (no starter template) — Vite React TS frontend + FastAPI backend + Docker Compose. First implementation story must be project initialization.
- AR2: Docker Compose two-service deployment — frontend service (Vite dev server, port 5173), backend service (uvicorn, port 8000), SQLite persisted via host bind mount at `./data/app.db`
- AR3: APScheduler must use SQLAlchemyJobStore pointing at the same SQLite file — never use default MemoryJobStore (critical for FR16 scheduler persistence across container restarts)
- AR4: spotipy must be initialized with a custom SQLiteCacheHandler (subclass of CacheHandler) implemented in `services/token_manager.py` — default CacheFileHandler does not survive Docker container restarts
- AR5: Python dependency management via `uv` with `pyproject.toml` and `uv.lock`
- AR6: First-run setup wizard — app detects absence of Spotify credentials in SQLite on startup, routes user to setup screen, user enters Client ID + Client Secret, triggers OAuth2 flow. Zero manual file editing required.
- AR7: SSE real-time streaming — backend uses FastAPI `StreamingResponse` with `text/event-stream`; frontend uses native `EventSource` API via `useSyncStream.ts` hook
- AR8: SQLModel auto-create schema — `SQLModel.metadata.create_all()` on app startup (no Alembic migrations)
- AR9: Vite proxy in `vite.config.ts` routes `/api/*` → `http://backend:8000` for local development

### UX Design Requirements

No UX Design document provided — no UX-specific requirements to extract.

### FR Coverage Map

FR1: Epic 2 — User authenticates with Spotify via OAuth2 from the dashboard
FR2: Epic 2 — User re-authenticates when token expires or is revoked
FR3: Epic 2 — System auto-refreshes expired tokens transparently
FR4: Epic 3 — System harvests tracks from selected source playlists via Spotify API
FR5: Epic 3 — System deduplicates tracks, retaining most recent added_at date
FR6: Epic 3 — System sorts harvested tracks by added_at descending
FR7: Epic 3 — System selects top N tracks per configured playlist size
FR8: Epic 3 — System creates target dynamic playlist if it does not exist
FR9: Epic 3 — System replaces target playlist contents on each sync
FR10: Epic 3 — User can view all user-created Spotify playlists
FR11: Epic 3 — User can include or exclude individual playlists from the harvest
FR12: Epic 3 — Playlist preferences persisted across sessions
FR13: Epic 3 — Playlist list reflects newly added or removed playlists from Spotify library
FR14: Epic 4 — System auto-executes syncs on user-configured schedule
FR15: Epic 4 — User can configure sync recurrence (interval or cron)
FR16: Epic 4 — Scheduler persists and resumes after application restart
FR17: Epic 3 — User can trigger a sync manually at any time
FR18: Epic 2 — User can configure Spotify API credentials (Client ID, Client Secret)
FR19: Epic 2 — User can configure dynamic playlist size (number of tracks)
FR20: Epic 2 — All configuration persisted and survives restarts
FR21: Epic 5 — User can view real-time sync progress during active sync
FR22: Epic 5 — User can view sync log entries (timestamp, status, track count delta, error cause)
FR23: Epic 5 — Dashboard surfaces visible failure indicator on last sync failure
FR24: Epic 5 — User can access full sync log history

NFR1: Epic 5 — Dashboard initial page load under 3 seconds (Vite build + static assets)
NFR2: Epic 3 — Playlist list refresh from Spotify API under 2 seconds
NFR3: Epic 5 — Real-time SSE events delivered to UI within 1 second
NFR4: Epic 3 — Sync engine processes up to 5,000 tracks within 30 seconds
NFR5: Epic 2 — OAuth tokens server-side only, never returned to browser
NFR6: Epic 2 — Spotify credentials in SQLite, never in source code or .env
NFR7: Epic 1 — No dashboard authentication layer (personal deployment)
NFR8: Epic 2 — All Spotify API communication over HTTPS
NFR9: Epic 4 — Scheduler auto-resumes after application restart
NFR10: Epic 3 — Sync failure preserves existing dynamic playlist
NFR11: Epic 3 — Every sync produces a log entry regardless of outcome
NFR12: Epic 3 — HTTP 429 rate limit handled with retry + exponential backoff

AR1: Epic 1 — Manual scaffolding (Vite React TS + FastAPI); first story = project initialization
AR2: Epic 1 — Docker Compose two-service deployment (frontend:5173, backend:8000, SQLite bind mount)
AR3: Epic 1 — APScheduler SQLAlchemyJobStore configured in scheduler.py
AR4: Epic 1 — Custom SQLiteCacheHandler in services/token_manager.py
AR5: Epic 1 — uv + pyproject.toml for Python dependency management
AR6: Epic 2 — First-run setup wizard (detect no credentials → setup screen → OAuth)
AR7: Epic 5 — SSE: FastAPI StreamingResponse + frontend EventSource in useSyncStream.ts
AR8: Epic 1 — SQLModel.metadata.create_all() on startup (no Alembic)
AR9: Epic 1 — Vite proxy /api/* → http://backend:8000

## Epic List

### Epic 1: Project Foundation & Infrastructure
The development environment is fully operational — `docker-compose up` starts all services, SQLite is initialized with all models, and the app skeleton is accessible in the browser with no errors.
**Requirements covered:** AR1, AR2, AR3, AR4, AR5, AR8, AR9 | NFR7

### Epic 2: Spotify Authentication & App Configuration
User can connect their Spotify account via the first-run setup wizard, configure playlist size and sync schedule, and all settings persist across restarts. The app is fully authenticated and ready to sync.
**FRs covered:** FR1, FR2, FR3, FR18, FR19, FR20 | AR6 | NFR5, NFR6, NFR8

### Epic 3: Playlist Management & Manual Sync
User can view their Spotify playlists, toggle which to include, trigger a manual sync, and see the dynamic playlist created or updated on Spotify with correctly deduplicated and sorted tracks.
**FRs covered:** FR4, FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR17 | NFR2, NFR4, NFR10, NFR11, NFR12

### Epic 4: Scheduler & Automatic Sync
The dynamic playlist stays current automatically — the scheduler runs syncs on the configured cron schedule and resumes after container restarts without user intervention.
**FRs covered:** FR14, FR15, FR16 | NFR9

### Epic 5: Real-Time Observability
User has complete visibility into sync activity — real-time SSE progress during active syncs, a persistent failure badge when the last sync failed, and full sync log history on the dashboard.
**FRs covered:** FR21, FR22, FR23, FR24 | AR7 | NFR1, NFR3

---

## Epic 1: Project Foundation & Infrastructure

The development environment is fully operational — `docker-compose up` starts all services, SQLite is initialized with all models, and the app skeleton is accessible in the browser with no errors.

**Requirements covered:** AR1, AR2, AR3, AR4, AR5, AR8, AR9 | NFR7

---

### Story 1.1: Project Scaffolding & Docker Compose

As a developer,
I want the complete project skeleton initialized with Docker Compose,
So that I can start all services with a single `docker-compose up` command.

**Acceptance Criteria:**

**Given** the repository is cloned,
**When** `docker-compose up` is run,
**Then** both frontend (port 5173) and backend (port 8000) services start without errors.

**Given** the services are running,
**When** I open http://localhost:5173,
**Then** the React app loads in the browser (even if placeholder content).

**Given** the services are running,
**When** I open http://localhost:8000/docs,
**Then** the FastAPI Swagger UI loads successfully.

**Given** the project root,
**When** I review the file structure,
**Then** it matches: `frontend/` (Vite React TS), `backend/` (FastAPI + uv + pyproject.toml), `docker-compose.yml`, two `Dockerfile`s, `.env.example` (ports/CORS only — no Spotify credentials), `.gitignore`, `data/.gitkeep`.

---

### Story 1.2: Database Models & SQLite Initialization

As a developer,
I want SQLModel table models defined and the database auto-created on startup,
So that the application has persistent storage ready for all features.

**Acceptance Criteria:**

**Given** the backend starts,
**When** the FastAPI lifespan executes,
**Then** `SQLModel.metadata.create_all()` runs and creates all tables in `./data/app.db`.

**Given** the database is initialized,
**When** I inspect `app.db`,
**Then** the following tables exist: `config`, `playlist`, `sync_log`.

**Given** the `config` table,
**When** I review the schema,
**Then** it has columns: `id`, `client_id` (str nullable), `client_secret` (str nullable), `playlist_size` (int, default 50), `cron_expr` (str nullable).

**Given** the `playlist` table,
**When** I review the schema,
**Then** it has columns: `id`, `spotify_id` (str unique), `name` (str), `is_included` (bool, default false).

**Given** the `sync_log` table,
**When** I review the schema,
**Then** it has columns: `id`, `status` (str: "success"/"failure"), `track_count` (int nullable), `error_message` (str nullable), `timestamp` (str ISO 8601).

**Given** `./data/app.db` is a host bind mount,
**When** the Docker container is stopped and restarted,
**Then** the database and all its contents persist.

---

### Story 1.3: APScheduler & SQLiteCacheHandler Foundation

As a developer,
I want APScheduler configured with SQLAlchemyJobStore and a custom SQLiteCacheHandler implemented,
So that scheduler persistence and Spotify token storage are production-ready from the start.

**Acceptance Criteria:**

**Given** the backend starts,
**When** the FastAPI lifespan executes,
**Then** APScheduler is initialized with `SQLAlchemyJobStore` pointing to `sqlite:////data/app.db` (not the default MemoryJobStore).

**Given** APScheduler is initialized,
**When** I inspect `app.db`,
**Then** the APScheduler job store table (`apscheduler_jobs`) exists (even if empty — no jobs registered yet).

**Given** `services/token_manager.py`,
**When** I review the code,
**Then** it contains `SQLiteCacheHandler` subclassing spotipy's `CacheHandler` with `get_cached_token()` reading from the `config` table and `save_token_to_cache()` writing to the `config` table.

**Given** no Spotify credentials are configured yet,
**When** the backend starts,
**Then** no errors are raised — APScheduler starts with no jobs, `SQLiteCacheHandler` handles `None` token gracefully.

---

### Story 1.4: Frontend Shell & Navigation

As a user,
I want a navigable app shell with the three main pages,
So that the dashboard structure is in place and ready to receive features.

**Acceptance Criteria:**

**Given** the frontend is running,
**When** I open http://localhost:5173,
**Then** the `AppShell` renders with a `NavBar` containing links to Dashboard (`/`), Config (`/config`), and Logs (`/logs`).

**Given** I am on any route,
**When** I click a NavBar link,
**Then** the corresponding page renders without a full page reload (React Router v7 SPA navigation).

**Given** the three routes,
**When** each page renders,
**Then** it displays a meaningful placeholder — page title visible, no blank pages, no console errors.

**Given** the app entry point,
**When** `main.tsx` loads,
**Then** a `QueryClient` is initialized and available via `QueryClientProvider` wrapping the entire app.

**Given** shadcn/ui is configured,
**When** I inspect the project,
**Then** `components.json` exists and at least one shadcn/ui component is installed (e.g., `Button`).

**Given** the Vite proxy configuration,
**When** the frontend makes a request to `/api/v1/*`,
**Then** it is forwarded to `http://backend:8000/api/v1/*`.

---

## Epic 2: Spotify Authentication & App Configuration

User can connect their Spotify account via the first-run setup wizard, configure playlist size and sync schedule, and all settings persist across restarts. The app is fully authenticated and ready to sync.

**FRs covered:** FR1, FR2, FR3, FR18, FR19, FR20 | AR6 | NFR5, NFR6, NFR8

---

### Story 2.1: Config API & First-Run Detection

As a user,
I want the app to detect when Spotify credentials are missing and display the setup screen,
So that I know exactly what to do the first time I open the app.

**Acceptance Criteria:**

**Given** no credentials are stored in the DB,
**When** `GET /api/v1/config` is called,
**Then** the response includes `"setup_required": true`.

**Given** credentials exist in the DB,
**When** `GET /api/v1/config` is called,
**Then** the response includes `"setup_required": false` along with `playlist_size` and `cron_expr`.

**Given** a `PUT /api/v1/config` request with `{client_id, client_secret, playlist_size, cron_expr}`,
**When** the request is made,
**Then** the config is persisted in the `config` table and a 200 response is returned.

**Given** `setup_required` is `true`,
**When** the frontend loads `/`,
**Then** `SetupWizard` is rendered instead of the normal dashboard.

**Given** `setup_required` is `false`,
**When** the frontend loads `/`,
**Then** the normal dashboard renders.

---

### Story 2.2: Spotify OAuth2 Connect Flow

As a user,
I want to connect my Spotify account from the setup screen,
So that the app can access my playlists and manage my music.

**Acceptance Criteria:**

**Given** `client_id` and `client_secret` are saved in the DB,
**When** `POST /api/v1/auth/connect` is called,
**Then** the response returns a Spotify authorization URL.

**Given** the authorization URL is returned,
**When** I click "Connect Spotify" in `SetupWizard`,
**Then** I am redirected to Spotify's authorization page.

**Given** I grant access on Spotify,
**When** Spotify redirects to `GET /api/v1/auth/callback` with the authorization code,
**Then** the backend exchanges the code for tokens and stores them via `SQLiteCacheHandler` in the `config` table.

**Given** the callback succeeds,
**When** `GET /api/v1/auth/status` is called,
**Then** it returns `{"authenticated": true, "spotify_user_id": "..."}`.

**Given** tokens are stored server-side via `SQLiteCacheHandler`,
**When** I inspect any API response body,
**Then** no `access_token` or `refresh_token` field appears in any response (NFR5).

---

### Story 2.3: Token Re-Authentication Flow

As a user,
I want to reconnect Spotify when my token expires or is revoked,
So that I can restore sync functionality without restarting the app.

**Acceptance Criteria:**

**Given** the token is expired or revoked,
**When** `GET /api/v1/auth/status` is called,
**Then** it returns `{"authenticated": false}`.

**Given** `authenticated` is `false`,
**When** the dashboard loads,
**Then** `ReauthBanner` is displayed prominently with a "Reconnect Spotify" button.

**Given** the `ReauthBanner` is visible,
**When** I click "Reconnect Spotify",
**Then** the OAuth2 flow restarts (same flow as Story 2.2).

**Given** I complete re-authorization,
**When** the callback succeeds,
**Then** `GET /api/v1/auth/status` returns `{"authenticated": true}` and `ReauthBanner` is dismissed.

**Given** a valid token that is about to expire (FR3),
**When** spotipy makes an API call during a sync,
**Then** the token is refreshed transparently via `SQLiteCacheHandler` with no user intervention and no re-auth prompt.

---

### Story 2.4: Playlist Size & Schedule Configuration UI

As a user,
I want to configure playlist size and sync schedule from the dashboard,
So that the app behaves exactly as I want without editing any files.

**Acceptance Criteria:**

**Given** I navigate to `/config`,
**When** the `ConfigForm` loads,
**Then** it displays the current `playlist_size` and `cron_expr` values fetched from `GET /api/v1/config`.

**Given** I enter a new `playlist_size` (e.g., 100) and `cron_expr` (e.g., `"0 */6 * * *"`),
**When** I click Save,
**Then** `PUT /api/v1/config` is called with the new values and a success confirmation is shown.

**Given** the save succeeds,
**When** I reload the page,
**Then** the new values are displayed in the form (persistence confirmed).

**Given** the Docker container is stopped and restarted,
**When** I navigate to `/config`,
**Then** the saved `playlist_size` and `cron_expr` are still present (FR20).

**Given** I enter an invalid cron expression,
**When** I click Save,
**Then** an inline error message is shown and no `PUT` request is made.

**Given** no `cron_expr` is stored yet,
**When** the `ConfigForm` renders,
**Then** a sensible placeholder is displayed (e.g., `"0 * * * *"`).

---

## Epic 3: Playlist Management & Manual Sync

User can view their Spotify playlists, toggle which to include, trigger a manual sync, and see the dynamic playlist created or updated on Spotify with correctly deduplicated and sorted tracks.

**FRs covered:** FR4, FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR17 | NFR2, NFR4, NFR10, NFR11, NFR12

---

### Story 3.1: Playlist List & Toggle UI

As a user,
I want to see all my Spotify playlists and choose which ones to include in the sync,
So that I control exactly which music sources feed my dynamic playlist.

**Acceptance Criteria:**

**Given** the user is authenticated,
**When** `GET /api/v1/playlists` is called,
**Then** the response returns all user-created Spotify playlists as an array `[{spotify_id, name, is_included}]`.

**Given** `GET /api/v1/playlists` is called,
**When** the playlists are fetched from Spotify API,
**Then** they are stored/updated in the `playlist` table in SQLite and the response is served from the DB.

**Given** the dashboard loads,
**When** the playlist list renders,
**Then** `PlaylistList` displays each playlist with its name and a toggle (`PlaylistToggle`) showing its current `is_included` state.

**Given** I toggle a playlist on or off,
**When** `PATCH /api/v1/playlists/{playlist_id}` is called with `{"is_included": true/false}`,
**Then** the `is_included` value is updated in SQLite and the toggle reflects the new state immediately.

**Given** the playlist list is loading,
**When** the TanStack Query fetch is in progress,
**Then** a skeleton or loading indicator is shown (not a blank section).

**Given** the playlist list refresh from Spotify API,
**When** the fetch completes,
**Then** it takes under 2 seconds (NFR2).

---

### Story 3.2: Playlist Preferences Persistence & Library Refresh

As a user,
I want my playlist selections to be remembered and new playlists to appear automatically,
So that I never have to reconfigure after adding music or restarting the app.

**Acceptance Criteria:**

**Given** I have toggled several playlists and the Docker container is restarted,
**When** I navigate to the dashboard,
**Then** all `is_included` preferences are identical to what I set before the restart (FR12).

**Given** I create a new playlist on Spotify,
**When** I reload the dashboard (triggering `GET /api/v1/playlists`),
**Then** the new playlist appears in the list with `is_included: false` by default (FR13).

**Given** I delete a playlist from my Spotify library,
**When** `GET /api/v1/playlists` is called,
**Then** the deleted playlist no longer appears in the returned list.

**Given** a playlist was previously included (`is_included: true`) and is then deleted from Spotify,
**When** `GET /api/v1/playlists` is called,
**Then** it is removed from the DB and does not appear in the list.

---

### Story 3.3: Track Harvest & Deduplication Engine

As a user,
I want the sync engine to correctly collect and deduplicate tracks from all my selected playlists,
So that each track appears only once with its most recent addition date.

**Acceptance Criteria:**

**Given** `sync_engine.run_sync()` is called,
**When** harvesting begins,
**Then** tracks are fetched from all playlists where `is_included=true` using paginated Spotify API calls (100 tracks per request).

**Given** a track appears in multiple selected playlists with different `added_at` dates,
**When** deduplication runs,
**Then** only one entry for that `spotify_id` is kept — the one with the most recent `added_at` (FR5).

**Given** deduplication is complete,
**When** sorting runs,
**Then** the tracks are ordered by `added_at` descending (most recent first) (FR6).

**Given** sorting is complete,
**When** the slice is applied,
**Then** only the top N tracks are selected, where N is the configured `playlist_size` (FR7).

**Given** a library of 5,000 tracks across selected playlists,
**When** the full harvest runs,
**Then** it completes within 30 seconds (NFR4).

**Given** no playlists are marked `is_included=true`,
**When** `run_sync()` is called,
**Then** an error is logged (`error_message: "No playlists selected"`) and no Spotify playlist modification is attempted.

---

### Story 3.4: Dynamic Playlist Push & Sync Logging

As a user,
I want the sync engine to update my Spotify dynamic playlist and log every outcome,
So that I always have an up-to-date playlist and full traceability of what happened.

**Acceptance Criteria:**

**Given** the harvest and dedup are complete,
**When** the target "Recent Adds" playlist does not exist on Spotify,
**Then** it is created and its Spotify ID is stored in the DB (FR8).

**Given** the target playlist exists,
**When** the push runs,
**Then** its contents are fully replaced with the harvested top-N tracks (FR9).

**Given** a successful sync,
**When** `run_sync()` completes,
**Then** a `SyncLog` entry is written with `status="success"`, `track_count=N`, `timestamp=ISO8601`, `error_message=null` (NFR11).

**Given** any error occurs during the sync (e.g., Spotify API error, token failure),
**When** the exception is caught,
**Then** the existing dynamic playlist contents are left unchanged (NFR10) and a `SyncLog` entry is written with `status="failure"` and the `error_message` populated.

**Given** Spotify API returns HTTP 429,
**When** spotipy handles the response,
**Then** the request is retried with exponential backoff automatically — no manual retry loop in `sync_engine.py` (NFR12).

---

### Story 3.5: Manual Sync Trigger

As a user,
I want to trigger a sync on demand from the dashboard,
So that I can update my playlist immediately without waiting for the scheduled run.

**Acceptance Criteria:**

**Given** I am on the dashboard and authenticated,
**When** I click "Sync Now",
**Then** `POST /api/v1/sync/run` is called and `sync_engine.run_sync()` executes.

**Given** a sync is in progress,
**When** the `SyncButton` is in its loading state,
**Then** it is disabled and shows a loading indicator — no duplicate syncs can be triggered.

**Given** the sync completes successfully,
**When** `POST /api/v1/sync/run` returns,
**Then** the response includes `{"status": "success", "track_count": N}` and the button returns to its normal state.

**Given** the sync fails,
**When** `POST /api/v1/sync/run` returns,
**Then** the response includes `{"status": "failure", "error": "..."}` and the error is surfaced in the UI.

**Given** no playlists are selected,
**When** I click "Sync Now",
**Then** the request returns a 400 error and the UI shows "No playlists selected — enable at least one playlist to sync."

---

## Epic 4: Scheduler & Automatic Sync

The dynamic playlist stays current automatically — the scheduler runs syncs on the configured cron schedule and resumes after container restarts without user intervention.

**FRs covered:** FR14, FR15, FR16 | NFR9

---

### Story 4.1: Scheduler Bootstrap & Job Persistence

As a user,
I want sync jobs to run automatically on my configured schedule and survive container restarts,
So that my playlist stays current without any manual intervention.

**Acceptance Criteria:**

**Given** the backend starts and a `cron_expr` is stored in the DB,
**When** the FastAPI lifespan executes,
**Then** APScheduler registers a cron job using the stored `cron_expr` that calls `sync_engine.run_sync()`.

**Given** the APScheduler job is registered with `SQLAlchemyJobStore`,
**When** the Docker container is stopped and restarted,
**Then** the job is restored from the DB and continues firing on schedule without re-registration (FR16, NFR9).

**Given** no `cron_expr` is stored yet,
**When** the backend starts,
**Then** no job is registered — APScheduler starts empty with no errors.

**Given** the scheduler is running and the cron fires,
**When** `sync_engine.run_sync()` executes,
**Then** the same sync logic as the manual trigger runs, including sync logging.

**Given** a scheduled sync runs while another sync is already in progress,
**When** the job fires,
**Then** the concurrent execution is skipped or queued — no duplicate sync runs simultaneously.

---

### Story 4.2: Dynamic Schedule Reconfiguration

As a user,
I want changes to the sync schedule to take effect immediately without restarting the app,
So that I can adjust the frequency at any time from the dashboard.

**Acceptance Criteria:**

**Given** a cron job is currently registered in APScheduler,
**When** I update `cron_expr` via `PUT /api/v1/config` with a new value,
**Then** the existing APScheduler job is removed and a new job is registered with the updated schedule immediately.

**Given** I set `cron_expr` to `"0 */6 * * *"` (every 6 hours),
**When** the schedule is updated,
**Then** the next sync fires at the next 6-hour boundary — not at the old schedule.

**Given** I clear `cron_expr` (set to null or empty),
**When** the config is saved,
**Then** the APScheduler job is removed and no more scheduled syncs run until a new schedule is configured.

**Given** I enter an invalid cron expression in the `ConfigForm`,
**When** I click Save,
**Then** the backend returns a 400 error, the job is not modified, and the previous schedule remains active.

---

## Epic 5: Real-Time Observability

User has complete visibility into sync activity — real-time SSE progress during active syncs, a persistent failure badge when the last sync failed, and full sync log history on the dashboard.

**FRs covered:** FR21, FR22, FR23, FR24 | AR7 | NFR1, NFR3

---

### Story 5.1: Sync History & Log Viewer

As a user,
I want to view the complete history of all syncs on the Logs page,
So that I can track what happened, when, and why any sync may have failed.

**Acceptance Criteria:**

**Given** I navigate to `/logs`,
**When** the page loads,
**Then** `GET /api/v1/sync/logs` is called and `SyncLogPanel` renders the full sync history.

**Given** the sync log list renders,
**When** entries are displayed,
**Then** each entry shows: timestamp (formatted), status (success/failure), track count delta, and error message when applicable (FR22).

**Given** no syncs have run yet,
**When** I navigate to `/logs`,
**Then** an empty state message is shown (e.g., "No syncs yet — trigger your first sync from the dashboard").

**Given** `GET /api/v1/sync/logs`,
**When** the endpoint is called,
**Then** it returns all `SyncLog` entries ordered by `timestamp` descending (most recent first) (FR24).

**Given** the `/logs` page loads,
**When** it is measured on a local network,
**Then** the initial render completes under 3 seconds (NFR1).

---

### Story 5.2: Sync Failure Indicator

As a user,
I want a visible failure badge on the dashboard when the last sync failed,
So that I immediately know something needs my attention without navigating to the logs.

**Acceptance Criteria:**

**Given** the last `SyncLog` entry has `status="failure"`,
**When** the dashboard loads,
**Then** `SyncStatusBadge` is visible with a red failure indicator and the error cause (FR23).

**Given** the last `SyncLog` entry has `status="success"`,
**When** the dashboard loads,
**Then** `SyncStatusBadge` shows a green success indicator with the last sync timestamp.

**Given** no syncs have run yet,
**When** the dashboard loads,
**Then** `SyncStatusBadge` shows a neutral state (e.g., "Never synced").

**Given** I trigger a manual sync that succeeds after a previous failure,
**When** the sync completes,
**Then** `SyncStatusBadge` updates to green — the failure state is cleared.

---

### Story 5.3: Real-Time SSE Sync Streaming

As a user,
I want to watch sync progress live on the dashboard while a sync is running,
So that I have immediate feedback without refreshing the page.

**Acceptance Criteria:**

**Given** a sync is triggered (manually or by scheduler),
**When** `GET /api/v1/sync/stream` is connected via `EventSource`,
**Then** the backend streams `text/event-stream` events as the sync progresses (FR21, AR7).

**Given** the SSE stream is active,
**When** the sync engine emits a log event,
**Then** it arrives in the `SyncLogPanel` within 1 second of backend emission (NFR3).

**Given** the SSE stream receives a `sync_log` event,
**When** the `useSyncStream.ts` hook processes it,
**Then** the event is appended to the live log panel in real time without a page reload.

**Given** the sync completes,
**When** a `sync_complete` or `sync_error` event is received,
**Then** the SSE connection is closed gracefully and `SyncButton` returns to its normal state.

**Given** the SSE connection drops unexpectedly,
**When** `EventSource` detects the disconnect,
**Then** the frontend does not crash — the log panel retains previously received events.

**Given** no sync is in progress,
**When** I navigate to the dashboard,
**Then** no SSE connection is open (connection is established only when a sync is active).
