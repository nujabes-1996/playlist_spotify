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
FR25: The dashboard displays user playlists as a grid of square cards showing the Spotify cover image, playlist name, and track count
FR26: User can hide a playlist from the main grid via a per-card overflow menu
FR27: Hiding a playlist also excludes it from the next and subsequent syncs (hidden ⇒ excluded)
FR28: Hidden playlists are accessible in a collapsible "Hidden playlists" section showing a count and the same card layout
FR29: User can unhide a playlist from the hidden section, which restores it to the main grid (include/exclude state defaults to excluded; user must explicitly toggle include again)
FR30: Hidden state is persisted across sessions
FR31: User can navigate to a dedicated "Recently Added" page showing the current contents of the dynamic Spotify playlist
FR32: Tracks are displayed in a list view with columns: index, title + artist + cover thumbnail, album, date added, duration
FR33: Each row exposes an overflow menu with a "Hide / Blacklist" action
FR34: Blacklisting a track persistently excludes it from all future syncs
FR35: The next sync after a track is blacklisted removes that track from the dynamic Spotify playlist
FR36: Blacklist state is persisted across sessions

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
NFR13: Playlist grid renders within 1 second of API response for up to 100 playlists; cover images lazy-loaded
NFR14: Recently Added track list renders within 1 second for up to 200 tracks
NFR15: Dashboard adopts a Spotify Desktop-inspired visual language — dark theme, persistent left sidebar, accent green (#1DB954-class), AA contrast, visible keyboard focus rings

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
- AR10: Playlist model gains `is_hidden` boolean (default false); SQLModel auto-migration adds the column on next startup
- AR11: New `track_blacklist` table — `spotify_id` (str, primary key), `blacklisted_at` (str ISO 8601); auto-created via `SQLModel.metadata.create_all()`
- AR12: New `GET /api/v1/recently-added` endpoint reads the current dynamic playlist contents from Spotify (paginated), returning tracks with the columns required by FR32

### UX Design Requirements

UX Design source: [`ux-design/README.md`](./ux-design/README.md) (Claude Design handoff intégré 2026-05-20 via Sprint Change Proposal).

**Composants drop-in fournis** (baseline production): `AppShell.tsx`, `PlaylistCard.tsx`, `TrackRow.tsx`, `HiddenPlaylistsAccordion.tsx` dans `ux-design/snippets/`.

**Tokens CSS**: `ux-design/snippets/index.css` — bloc `:root` à coller dans `frontend/src/index.css`.

**Shadcn additions**: `bash ux-design/snippets/shadcn-add.sh` (Accordion, DropdownMenu, Tooltip, Sheet, Input, Label, Separator).

**Routes (react-router-dom)**: `/`, `/recently-added`, `/settings` (`/config` redirige), `/logs`.

**Override projet — SSE Logs**: l'`EventSource` est ouvert uniquement pendant un sync actif (cf. FR21 + Story 5.3). Le snippet always-on du README handoff section Logs route n'est PAS applicable.

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
FR25: Epic 7 — Dashboard displays playlists as a grid of cover-art cards
FR26: Epic 7 — User can hide a playlist via per-card overflow menu
FR27: Epic 7 — Hiding a playlist also excludes it from sync
FR28: Epic 7 — Hidden playlists accessible in a collapsible section
FR29: Epic 7 — User can unhide a playlist (restores to grid, excluded by default)
FR30: Epic 7 — Hidden state persisted across sessions
FR31: Epic 8 — User can navigate to a Recently Added page showing current dynamic playlist contents
FR32: Epic 8 — Tracks displayed as a list with index, title+artist+thumb, album, date added, duration
FR33: Epic 8 — Each row exposes an overflow menu with "Hide / Blacklist"
FR34: Epic 8 — Blacklisting a track persistently excludes it from future syncs
FR35: Epic 8 — Next sync after blacklisting removes the track from the Spotify playlist
FR36: Epic 8 — Blacklist state persisted across sessions

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
AR10: Epic 7 — Playlist.is_hidden column added via SQLModel auto-migration
AR11: Epic 8 — track_blacklist table created on startup via SQLModel.metadata.create_all()
AR12: Epic 8 — GET /api/v1/recently-added reads current dynamic playlist contents from Spotify

NFR13: Epic 7 — Playlist grid renders <1s for 100 playlists; cover images lazy-loaded
NFR14: Epic 8 — Recently Added list renders <1s for 200 tracks
NFR15: Epic 6 — Spotify Desktop-inspired visual language (dark theme, sidebar, accent green, AA contrast)

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

### Epic 6: Spotify Desktop UI Foundation
The dashboard adopts a Spotify Desktop-inspired visual language — dark theme, persistent left sidebar, accent green, AA contrast — and pivots from mobile-first to desktop-first responsive layout. This epic establishes the design tokens and AppShell v2 that Epics 7 and 8 build on.
**Requirements covered:** NFR15 | UI & Visual Design section of PRD

### Epic 7: Playlist Grid & Hide Management
The playlist list is replaced by a Spotify-style grid of cover-art cards. Users can hide playlists from the main view, which simultaneously excludes them from sync. A collapsible "Hidden playlists" section provides review and unhide flows.
**FRs covered:** FR25, FR26, FR27, FR28, FR29, FR30 | AR10 | NFR13

### Epic 8: Recently Added Page & Track Blacklist
A dedicated "Recently Added" page renders the current contents of the dynamic Spotify playlist as a Spotify-desktop-style track table. Users can blacklist any track from a per-row action; the next sync removes the track and prevents it from ever returning.
**FRs covered:** FR31, FR32, FR33, FR34, FR35, FR36 | AR11, AR12 | NFR14

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

**Design reference:** [`ux-design/README.md`](../ux-design/README.md) section "Logs route" + section "Interactions & Behavior > SSE for logs". ⚠️ **Override projet:** le snippet `useEffect` du README ouvre `EventSource` au mount permanent. Pour ce projet, l'EventSource doit être ouvert **uniquement pendant un sync actif** (FR21).

**Acceptance Criteria:**

**Given** the project SSE policy,
**When** I inspect the `useSyncStream.ts` hook,
**Then** the `EventSource` is opened only when a sync is active (manual trigger or scheduler tick) and is closed on `sync_complete` / `sync_error` — there is NO `useEffect(() => new EventSource(...), [])` opened at component mount.

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

---

## Epic 6: Spotify Desktop UI Foundation

The dashboard adopts a Spotify Desktop-inspired visual language — dark theme, persistent left sidebar, accent green, AA contrast — and pivots from mobile-first to desktop-first responsive layout. This epic establishes the design tokens and AppShell v2 that Epics 7 and 8 build on.

**Requirements covered:** NFR15 | UI & Visual Design section of PRD

---

### Story 6.1: Design Tokens & Dark Theme

As a user,
I want the dashboard to use a dark Spotify-inspired theme by default,
So that the visual language feels familiar and the app is comfortable to use during long sessions.

**Design reference:** [`ux-design/README.md`](../ux-design/README.md) section "Design Tokens" + [`ux-design/snippets/index.css`](../ux-design/snippets/index.css) (à coller tel quel).

**Acceptance Criteria:**

**Given** `frontend/src/index.css`,
**When** I inspect the `:root` block,
**Then** it contains the exact tokens from `ux-design/snippets/index.css`: `--bg-base #0d0d0d`, `--bg-app #121212`, `--bg-elevated #1c1c1c`, `--bg-elevated-2 #232323`, `--bg-hover #2a2a2a`, `--bg-row-hover #1a1a1a`, `--bg-row-active #2a2a2a`, `--text-primary #ffffff`, `--text-secondary #b3b3b3`, `--text-muted #6a6a6a`, `--text-faint #4a4a4a`, `--accent #1DB954`, `--accent-hover #1ed760`, `--accent-fg #000000`, `--accent-soft rgba(29,185,84,0.12)`, `--danger #e22134`, `--warning #f0b400`, `--border-soft rgba(255,255,255,0.06)`, `--border rgba(255,255,255,0.09)`, `--border-strong rgba(255,255,255,0.16)`, `--r-sm 4px`, `--r-md 6px`, `--r-lg 8px`, `--r-xl 12px`, `--r-pill 999px`, `--sidebar-w 248px`, `--header-h 64px`.

**Given** `frontend/index.html`,
**When** I inspect the `<html>` tag,
**Then** it has `class="dark"` hardcoded — there is no theme toggle anywhere in the UI.

**Given** any page of the application,
**When** it renders,
**Then** the page background uses `--bg-base`, elevated surfaces (cards, panels) use `--bg-elevated`, the sidebar uses `--bg-app`, and primary actions use `--accent` with `--accent-fg` text.

**Given** any text/background pairing in the UI,
**When** a contrast audit is run,
**Then** every pairing meets WCAG AA contrast (≥4.5:1 for body text, ≥3:1 for large text and UI components).

**Given** I navigate the UI via keyboard,
**When** focus moves between interactive elements,
**Then** a visible focus ring (≥2px, accent or high-contrast outline) is rendered on the focused element.

**Given** the existing shadcn/ui components (Button, etc.),
**When** they render in the new theme,
**Then** their default variants resolve to the dark/accent palette — no hardcoded white/light backgrounds remain.

---

### Story 6.2: AppShell v2 — Sidebar & Header Layout

As a user,
I want a persistent left sidebar and top header on every page,
So that navigation, sync status, and the manual sync action are always one click away.

**Design reference:** [`ux-design/README.md`](../ux-design/README.md) section "1 · AppShell (layout)" + [`ux-design/snippets/AppShell.tsx`](../ux-design/snippets/AppShell.tsx) (baseline drop-in à reprendre).

**Acceptance Criteria:**

**Given** the frontend renders,
**When** any route loads,
**Then** the layout uses an outer CSS grid: `grid-template-columns: var(--sidebar-w) 1fr; gap: 8px; padding: 8px; height: 100vh; background: var(--bg-base);` — matching `snippets/AppShell.tsx`.

**Given** the `Sidebar`,
**When** I inspect its structure,
**Then** it has: background `var(--bg-app)`, border-radius `8px`, padding `18px 12px 12px`, contains in order — (1) brand block (28×28 gradient square accent→cyan + wordmark `playlist_spotify` weight 700 size 15px), (2) WORKSPACE label (uppercase letter-spacing 0.08em 10px muted), (3) nav items, (4) footer block (mt-auto, border-top, avatar 26×26 + connected-as 3-line block).

**Given** sidebar nav items,
**When** I inspect each item,
**Then** each shows: lucide icon 17px + label 13.5px weight 600. Hover state = `var(--bg-hover)` + white text. Active state = `var(--bg-elevated-2)` + white text + 3px accent vertical bar on the left + accent icon color.

**Given** the topbar inside the main area,
**When** I inspect its structure,
**Then** it is sticky (height 64px, padding `0 32px`, `backdrop-filter: blur(14px)`), contains — left: two 32×32 circular nav buttons disabled (ChevronLeft/ChevronRight); on Dashboard only: search pill (`bg-elevated-2`, rounded-full, width 320px, Search icon, placeholder "Filter playlists…"); right: status badge (rounded-full, `bg-elevated-2`, font-size 12px, accent dot + "Last sync · X ago" — red dot + "Last sync failed" on error) + primary "Sync now" button (RotateCw icon, rounded-full, accent bg, black text, hover lightens + scale 1.03).

**Given** the main area background,
**When** I inspect its CSS,
**Then** it uses `linear-gradient(180deg, var(--bg-elevated) 0%, var(--bg-app) 280px)` for the subtle gradient that fades into the base.

**Given** scrolling the content below the topbar,
**When** `scrollTop > 4`,
**Then** the topbar background becomes solid `rgba(18,18,18,0.92)` with a 1px bottom border (driven by a `scrolled` state from `onScroll` on the scroll container).

**Given** the previous `NavBar` component is no longer used,
**When** I grep the codebase,
**Then** no references to the old top NavBar remain — `AppShell` is the single source of truth for chrome.

**Given** the `Sidebar` is rendered,
**When** I inspect its contents,
**Then** it displays the app logo/title and primary navigation links: Dashboard, Recently Added, Settings, Logs — each with an icon and a label.

**Given** I am on a route,
**When** the sidebar renders,
**Then** the matching nav item is visually highlighted (active state — accent color, background tint, or left border).

**Given** the `Header` is rendered,
**When** I inspect it,
**Then** it contains the current page title (left), a `SyncStatusBadge` (center or right), and the "Sync Now" button (right).

**Given** the previous `NavBar` component is no longer used,
**When** I grep the codebase,
**Then** no references to the old top NavBar remain — `AppShell` is the single source of truth for chrome.

**Given** the AppShell renders on desktop (≥1024px),
**When** I inspect spacing,
**Then** generous padding/gaps are used consistent with Spotify Desktop density (no cramped layouts).

---

### Story 6.3: Routes — Recently Added & Settings Rename

As a user,
I want a dedicated "Recently Added" route in the sidebar and the configuration page named "Settings",
So that the navigation matches the Spotify Desktop information architecture.

**Design reference:** [`ux-design/README.md`](../ux-design/README.md) section "1 · AppShell > Sidebar" — nav items order + icônes.

**Acceptance Criteria:**

**Given** React Router (`react-router-dom`) is configured,
**When** I inspect the route table,
**Then** the routes are: `/` (Dashboard), `/recently-added` (Recently Added — placeholder OK for now, populated by Epic 8), `/settings` (formerly `/config`), `/logs` (Logs). `AppShell` is the layout route parent.

**Given** the sidebar nav items,
**When** I inspect their icons,
**Then** in order: Dashboard → `LayoutDashboard`, Recently Added → `Clock`, Settings → `Settings`, Logs → `ScrollText` (lucide-react, 17px).

**Given** the legacy `/config` route,
**When** a user navigates to it,
**Then** it redirects to `/settings` (no broken bookmarks).

**Given** I click each sidebar item,
**When** the route changes,
**Then** the URL updates, the page renders without full reload, and the active state in the sidebar updates accordingly.

**Given** the Recently Added route is implemented as a placeholder,
**When** I visit `/recently-added` at the end of Epic 6,
**Then** a page title "Recently Added" is shown with an empty-state message (e.g., "Coming soon — your dynamic playlist contents will appear here").

---

### Story 6.4: Desktop-First Responsive Layout

As a user,
I want the dashboard to look its best on desktop and still be usable on a smartphone,
So that I can use the app on my main workstation and occasionally check it from my phone.

**Design reference:** [`ux-design/README.md`](../ux-design/README.md) sections "Layout" et "Variants (Tweaks)".

**Acceptance Criteria:**

**Given** the sidebar width,
**When** I inspect the CSS,
**Then** `--sidebar-w` is set to `248px` by default. The value is exposed as a CSS variable to allow easy tuning in the 200–320px range (no UI control required — variable only).

**Given** the viewport is ≥1024px wide,
**When** any page renders,
**Then** the full two-column layout (sidebar + main) is displayed with desktop spacing.

**Given** the viewport is <768px wide,
**When** any page renders,
**Then** the sidebar collapses (either off-canvas with a hamburger trigger or replaced by a bottom nav bar — implementation choice documented in code) and the main content fills the width.

**Given** the viewport is between 768px and 1024px,
**When** any page renders,
**Then** the layout degrades gracefully — sidebar may narrow (icons-only) or collapse, and the main content remains readable without horizontal scroll.

**Given** I open the app on a smartphone,
**When** I interact with the main controls (Sync Now button, settings form, log viewer),
**Then** they remain reachable and tappable — no overlap, no off-screen elements.

**Given** the legacy "mobile-first" copy in the PRD,
**When** documentation references mobile-first,
**Then** the implementation reflects the new desktop-first stance without sacrificing the smartphone use case.

---

## Epic 7: Playlist Grid & Hide Management

The playlist list is replaced by a Spotify-style grid of cover-art cards. Users can hide playlists from the main view, which simultaneously excludes them from sync. A collapsible "Hidden playlists" section provides review and unhide flows.

**FRs covered:** FR25, FR26, FR27, FR28, FR29, FR30 | AR10 | NFR13

---

### Story 7.1: Playlist Hidden State — Schema & API

As a developer,
I want a persistent `is_hidden` flag on each playlist exposed via the API,
So that the frontend can render hidden vs visible playlists and the sync engine can honor the exclusion rule.

**Acceptance Criteria:**

**Given** the `playlist` table schema,
**When** the backend starts after this story is shipped,
**Then** the table has a new column `is_hidden` (bool, NOT NULL, default `false`) — added via SQLModel auto-create (existing rows default to `false`).

**Given** `GET /api/v1/playlists`,
**When** the endpoint is called,
**Then** the response also includes `is_hidden` for each playlist and additionally returns the playlist cover image URL (`image_url`) from Spotify and `track_count` (total tracks in that playlist).

**Given** `PATCH /api/v1/playlists/{spotify_id}`,
**When** the request body contains `{"is_hidden": true}`,
**Then** the playlist row updates `is_hidden=true` AND `is_included=false` atomically (FR27).

**Given** `PATCH /api/v1/playlists/{spotify_id}`,
**When** the request body contains `{"is_hidden": false}` (unhide),
**Then** the playlist row updates `is_hidden=false` with `is_included` left at `false` (user must explicitly re-toggle include — FR29).

**Given** the sync engine starts harvesting,
**When** it queries selected playlists,
**Then** it considers only playlists where `is_included=true AND is_hidden=false` (defense-in-depth even though hidden ⇒ excluded by the API).

**Given** the persistence layer,
**When** the Docker container restarts,
**Then** all `is_hidden` values are preserved (FR30).

---

### Story 7.2: Playlist Grid — Cover-Art Card Layout

As a user,
I want to see my Spotify playlists as a grid of square cover-art cards,
So that the dashboard looks and feels like the Spotify Desktop app.

**Design reference:** [`ux-design/README.md`](../ux-design/README.md) section "2 · Dashboard route" + sous-section "PlaylistCard". Baseline composant: [`ux-design/snippets/PlaylistCard.tsx`](../ux-design/snippets/PlaylistCard.tsx).

**Acceptance Criteria:**

**Given** the dashboard loads at `/`,
**When** the playlist data is fetched,
**Then** visible playlists (`is_hidden=false`) render in a responsive CSS grid of square cards — each card shows the playlist cover image, name, and track count (FR25).

**Given** the grid container,
**When** I inspect its CSS,
**Then** `grid-template-columns: repeat(auto-fill, minmax(190px, 1fr))` with `gap: 18px` (Comfy density, the chosen production value).

**Given** a `PlaylistCard`,
**When** I inspect its structure (matching `snippets/PlaylistCard.tsx`),
**Then** it has: background `var(--bg-elevated)`, padding 14px, border-radius 8px. The cover image is square (full card width, border-radius 6px, drop-shadow `0 8px 24px rgba(0,0,0,0.5)`, margin-bottom 14px). Title h3 14.5px weight 700 white, `line-clamp: 2`, `min-height: 2.6em`. Meta line 12px secondary color showing `{n} tracks`.

**Given** the card's `included` state,
**When** `is_included === true`,
**Then** a 22×22 accent circle with `Check` icon appears top-left of the cover (z-index 2, shadow `0 2px 6px rgba(0,0,0,0.4)`) AND the card has a 2px solid accent outline (`outline-offset: -1px`).

**Given** I hover over a card (desktop pointer),
**When** the hover state activates,
**Then** (a) card background becomes `var(--bg-hover)` (200ms ease), (b) a 44×44 accent Play FAB appears bottom-right of the cover with `Play` icon 16px black (opacity 0 + translateY(8px) → opacity 1 + translateY(0)), (c) a 32×32 black overflow button (`rgba(0,0,0,0.7)`, `MoreHorizontal` icon) fades in top-right of the cover (150ms).

**Given** the overflow button,
**When** I click it,
**Then** a shadcn `DropdownMenu` opens with items: "Include in sync" / "Remove from sync" (toggle based on state), "Hide playlist" / "Unhide", separator, "Open in Spotify" with `ExternalLink` icon.

**Given** the previous list-based `PlaylistList` component,
**When** the grid view ships,
**Then** the list component is removed (no feature flag — the grid is the only view).

**Given** a playlist has no cover image (rare edge case),
**When** the card renders,
**Then** a deterministic placeholder is shown (e.g., gradient with playlist initials).

**Given** a card renders,
**When** I inspect its layout,
**Then** the cover image is a square (1:1 aspect ratio), the playlist name appears immediately below the image (truncated with ellipsis if too long), and the track count is shown as muted secondary text (e.g., "42 tracks").

**Given** the user hovers over a card (desktop pointer),
**When** the hover state activates,
**Then** the card surfaces an Include toggle and a `⋯` overflow menu (Hide, future actions); the active include state is communicated visually (border ring, badge, or accent overlay).

**Given** the previous list-based `PlaylistList` component,
**When** the grid view ships,
**Then** the list component is removed (or kept only as a fallback under a feature flag — implementation decision documented).

**Given** the page renders on a wide desktop viewport,
**When** I count columns,
**Then** the grid uses 4–6 columns at ≥1280px, 3 columns at ~1024px, 2 columns at ~640px, and 1 column at <480px (auto-fit grid recommended).

**Given** a playlist has no cover image (rare edge case),
**When** the card renders,
**Then** a deterministic placeholder is shown (e.g., gradient with playlist initials).

---

### Story 7.3: Hide Playlist Action

As a user,
I want a "Hide" action on each playlist card,
So that I can remove cluttered playlists from the main grid in one click without losing them.

**Design reference:** [`ux-design/README.md`](../ux-design/README.md) section "PlaylistCard > Overflow menu".

**Acceptance Criteria:**

**Given** I open the `⋯` overflow menu on a visible card,
**When** the menu renders (shadcn `DropdownMenu`),
**Then** it contains items: "Include in sync" / "Remove from sync" (toggle), "Hide playlist" (label changes to "Unhide" in the hidden section), separator, "Open in Spotify" with `ExternalLink` icon (FR26).

**Given** I click "Hide from dashboard",
**When** the action fires,
**Then** the frontend calls `PATCH /api/v1/playlists/{spotify_id}` with `{"is_hidden": true}` and optimistically removes the card from the visible grid.

**Given** the hide request succeeds,
**When** the next sync runs,
**Then** the hidden playlist is NOT harvested even if it had `is_included=true` previously (FR27 — verified by Story 7.1 backend behavior).

**Given** the hide request fails (network/API error),
**When** the error is caught,
**Then** the card is restored to the grid and a toast/banner explains the failure.

**Given** the menu is reachable by keyboard,
**When** I navigate to the card with Tab and press Enter/Space on the `⋯` trigger,
**Then** the menu opens and arrow keys navigate items; Esc closes the menu.

---

### Story 7.4: Hidden Playlists Section & Unhide Flow

As a user,
I want a collapsible "Hidden playlists" section showing what I've hidden,
So that I can review and restore any playlist when I want it back.

**Design reference:** [`ux-design/README.md`](../ux-design/README.md) sous-section "HiddenPlaylistsAccordion". Baseline composant: [`ux-design/snippets/HiddenPlaylistsAccordion.tsx`](../ux-design/snippets/HiddenPlaylistsAccordion.tsx).

**Acceptance Criteria:**

**Given** the dashboard is rendered,
**When** any playlist has `is_hidden=true`,
**Then** a collapsible section labeled `Hidden playlists (N)` (where N is the count) appears below the main grid, default-collapsed (FR28), implemented as shadcn `Accordion` (`type="single", collapsible`).

**Given** the accordion structure,
**When** I inspect it,
**Then** it has: border-top `1px solid var(--border-soft)`, padding-top 24px, margin-top 8px. Trigger = `ChevronRight` 16px (rotates 90° when open, 200ms) + h2 "Hidden playlists ({count})" 22px weight 800 (NO underline on hover).

**Given** the accordion is open,
**When** I inspect content,
**Then** help text appears (13px muted, max-width 720px, margin `10px 0 18px`): "Hidden playlists are excluded from sync and removed from the main grid. Unhide to bring them back." Followed by the same grid as the main section, but every card has the `dimmed` prop (opacity 0.55, returns to 1 on hover).

**Given** cards in the hidden section,
**When** I open their overflow menu,
**Then** the action label is "Unhide" instead of "Hide playlist".

**Given** no playlists are hidden,
**When** the dashboard renders,
**Then** the Hidden section is not displayed at all (no empty accordion).

**Given** I expand the section,
**When** it opens,
**Then** the hidden playlists are rendered with the same card layout as the main grid, but each card surfaces an "Unhide" affordance instead of the include toggle (FR29).

**Given** I click "Unhide" on a hidden card,
**When** the action fires,
**Then** the frontend calls `PATCH /api/v1/playlists/{spotify_id}` with `{"is_hidden": false}`, the card moves from the hidden section back into the main grid optimistically, and the count in the section label decrements.

**Given** the card has been unhidden,
**When** the main grid renders it,
**Then** its `is_included` state is `false` (user must explicitly re-enable inclusion — FR29).

**Given** the section state (expanded/collapsed),
**When** the user navigates away and back to the dashboard within the same session,
**Then** the collapsed/expanded state is preserved in component state (no requirement to persist across page reloads).

---

### Story 7.5: Grid Performance — Lazy Cover Images

As a user,
I want the playlist grid to feel instant even with 100 playlists,
So that opening the dashboard never feels sluggish.

**Acceptance Criteria:**

**Given** `GET /api/v1/playlists` has returned data for up to 100 playlists,
**When** the grid renders,
**Then** the first paint of the grid (cards visible, even if some images still loading) completes within 1 second (NFR13).

**Given** the cover images,
**When** the grid mounts,
**Then** images use `loading="lazy"` (native lazy loading) or an IntersectionObserver-backed approach — off-screen covers are not fetched until they approach the viewport.

**Given** an image fails to load,
**When** the fetch errors,
**Then** the deterministic placeholder from Story 7.2 is rendered — no broken image icon.

**Given** the grid is profiled in DevTools with 100 playlists,
**When** the initial render is measured,
**Then** no layout thrashing or N+1 re-renders occur — TanStack Query caches and React keys are correctly set per `spotify_id`.

---

## Epic 8: Recently Added Page & Track Blacklist

A dedicated "Recently Added" page renders the current contents of the dynamic Spotify playlist as a Spotify-desktop-style track table. Users can blacklist any track from a per-row action; the next sync removes the track and prevents it from ever returning.

**FRs covered:** FR31, FR32, FR33, FR34, FR35, FR36 | AR11, AR12 | NFR14

---

### Story 8.1: Track Blacklist Model & API

As a developer,
I want a persistent blacklist of track Spotify IDs exposed via a CRUD API,
So that the frontend can manage entries and the sync engine can filter them out.

**Acceptance Criteria:**

**Given** the backend starts after this story is shipped,
**When** the DB is inspected,
**Then** a new table `track_blacklist` exists with columns: `spotify_id` (str, primary key), `blacklisted_at` (str ISO 8601 — set on insert) (AR11).

**Given** `GET /api/v1/blacklist`,
**When** the endpoint is called,
**Then** it returns the full blacklist as `[{spotify_id, blacklisted_at}]` ordered by `blacklisted_at` descending.

**Given** `POST /api/v1/blacklist` with body `{"spotify_id": "..."}`,
**When** the request is made,
**Then** the spotify_id is inserted into `track_blacklist` (idempotent — duplicate inserts return 200 without error) and a 201 is returned on first insert.

**Given** `DELETE /api/v1/blacklist/{spotify_id}`,
**When** the request is made,
**Then** the entry is removed (idempotent — deleting a non-existent entry returns 204).

**Given** the Docker container restarts,
**When** the app boots,
**Then** all blacklist entries persist (FR36).

---

### Story 8.2: Recently Added API

As a developer,
I want an endpoint that returns the current contents of the dynamic Spotify playlist,
So that the Recently Added page can render the track list without re-running a sync.

**Acceptance Criteria:**

**Given** the dynamic playlist has been created previously (its Spotify ID is stored in the `config` table),
**When** `GET /api/v1/recently-added` is called,
**Then** the response returns the current tracks of the dynamic playlist as an array of `{spotify_id, title, artists: [name], album, image_url, added_at, duration_ms, explicit: bool, has_video: bool}` (AR12, FR32). Champs `explicit` et `has_video` requis pour l'affichage handoff (tag "E" + icône vidéo dans TrackRow — cf. `ux-design/README.md` section "TrackRow > Sub-line").

**Given** the dynamic playlist does not yet exist (no sync has ever succeeded),
**When** `GET /api/v1/recently-added` is called,
**Then** the response is `[]` with a 200 status (no error).

**Given** the Spotify API returns the playlist in multiple paginated pages,
**When** the endpoint runs,
**Then** all pages are concatenated transparently — the response includes every track up to the configured `playlist_size`.

**Given** the Spotify API returns HTTP 429,
**When** spotipy handles the response,
**Then** the retry/backoff behavior (NFR12) applies as it does in the sync engine — no separate retry code in this router.

**Given** the response is profiled on a local network,
**When** it is measured for a dynamic playlist of 200 tracks,
**Then** the API responds within an interval that allows the frontend to meet NFR14 (typical target: backend <500ms).

---

### Story 8.3: Recently Added Page — Track Table

As a user,
I want a dedicated Recently Added page that lists the current dynamic playlist contents as a Spotify-desktop-style track table,
So that I can see what's in my unified queue at a glance.

**Design reference:** [`ux-design/README.md`](../ux-design/README.md) section "3 · Recently Added route" + sous-section "TrackRow". Baseline composant: [`ux-design/snippets/TrackRow.tsx`](../ux-design/snippets/TrackRow.tsx).

**Acceptance Criteria:**

**Given** I navigate to `/recently-added`,
**When** the page mounts,
**Then** `GET /api/v1/recently-added` is called via TanStack Query and the page renders a hero block + a track table (FR31, FR32).

**Given** the hero block,
**When** I inspect its structure,
**Then** it is full-bleed (breaks out of the page's 32px horizontal padding via negative margins), padding `24px 32px 28px 32px`. Background: `linear-gradient(180deg, color-mix(in oklab, var(--accent-color) 40%, #1a1a1a) 0%, var(--bg-elevated) 100%)`. Flex row gap 26px, `align-items: flex-end`. Cover 232×232 border-radius 4px shadow `0 16px 40px rgba(0,0,0,0.6)`. Meta column: kicker "AUTO-SYNCED PLAYLIST" (12px weight 700 uppercase white) + title `clamp(40px, 5vw, 72px)` weight 900 letter-spacing -0.04em line-height 1 + sub line (13px secondary): `<strong>{email}</strong> • {n} of {N} tracks • about Xh Ym • updated {relative} from {k} source playlists`.

**Given** the hero actions row,
**When** I inspect it,
**Then** it contains: primary "Sync now" button (`RotateCw` icon, rounded-full, accent), secondary "Open in Spotify" button (`ExternalLink` icon, transparent + 1px border), 36×36 icon-only `MoreHorizontal` button.

**Given** the track list header,
**When** I scroll the body,
**Then** the header is sticky (`position: sticky; top: 0; background: rgba(18,18,18,0.92); backdrop-filter: blur(12px); z-index: 5; border-bottom: 1px var(--border-soft)`) with column grid `36px | minmax(220px, 4fr) | minmax(160px, 3fr) | minmax(140px, 2fr) | 60px | 40px` and labels `# | TITLE | ALBUM | DATE ADDED | <Clock icon> | ` (uppercase 11px weight 600 letter-spacing 0.06em muted).

**Given** a `TrackRow`,
**When** I inspect its structure (matching `snippets/TrackRow.tsx`),
**Then** it uses the same 6-column grid as the header, padding `8px 16px`, border-radius 4px, gap 14px. Column 1 = index muted centered (replaced by 12px white `Play` icon on row hover via group-hover swap). Column 2 = 40×40 thumbnail border-radius 3px + title 14.5px weight 500 white ellipsis (with optional accent "NEW" pill if `isNew`) + sub-line 12.5px muted (E tag if `explicit`, video icon if `has_video`, artists with hover underline). Column 3 = album ellipsis 13.5px. Column 4 = date added wrapped in shadcn `Tooltip` showing absolute date. Column 5 = duration tabular-nums right-aligned 13.5px. Column 6 = 32×32 `MoreHorizontal` button opacity 0→1 on row hover.

**Given** row hover,
**When** the pointer enters,
**Then** background becomes `var(--bg-row-hover)` (`#1a1a1a`), no transition (instant).

**Given** the data is loading,
**When** the query is pending,
**Then** a skeleton table is displayed.

**Given** the playlist is empty,
**When** the page renders,
**Then** an empty-state message is shown.

**Given** the table is rendered for 200 tracks,
**When** profiled on a local network,
**Then** the initial paint completes within 1 second (NFR14).

**Given** the table renders,
**When** I inspect each row,
**Then** the `#` column is the 1-based index, the title cell uses a small (≤48px) square cover thumbnail next to the text, the duration is formatted as `m:ss`, and the date added is formatted relative or short ISO (e.g., `2026-05-12`).

**Given** the table header row,
**When** I scroll the body,
**Then** the header remains sticky (visible while scrolling the list).

**Given** the data is loading,
**When** the query is pending,
**Then** a skeleton table (or row placeholders) is displayed — no blank section.

**Given** the playlist is empty (response `[]`),
**When** the page renders,
**Then** an empty-state message is shown (e.g., "No tracks yet — run a sync to populate Recently Added").

**Given** the table is rendered for 200 tracks,
**When** profiled on a local network,
**Then** the initial paint completes within 1 second (NFR14).

---

### Story 8.4: Per-Track Blacklist Action

As a user,
I want a "Hide from Recent Adds" action on each track row,
So that I can permanently remove a track that shouldn't appear in my dynamic playlist.

**Acceptance Criteria:**

**Design reference:** [`ux-design/README.md`](../ux-design/README.md) section "TrackRow > Column 6 (overflow)".

**Given** a row's `⋯` overflow menu (shadcn `DropdownMenu`),
**When** I open it,
**Then** it contains: "Hide from Recent Adds" with `EyeOff` icon (alias: "Blacklist") (FR33) AND "Open in Spotify" with `ExternalLink` icon.

**Given** I click the blacklist action on a row,
**When** the action fires,
**Then** the frontend calls `POST /api/v1/blacklist` with `{"spotify_id": "<id>"}` and optimistically removes the row from the table.

**Given** the request succeeds,
**When** a toast/banner confirms,
**Then** the row stays removed and the message indicates "Will be removed from your Spotify playlist on the next sync."

**Given** the request fails,
**When** the error is caught,
**Then** the row is restored and a toast explains the failure.

**Given** the action is reachable by keyboard,
**When** I navigate the table with Tab/Arrow keys and trigger the `⋯` menu via Enter/Space,
**Then** the menu opens and the action is selectable by keyboard.

**Given** the row hover state,
**When** the pointer enters a row,
**Then** the row gets a subtle background highlight and the `⋯` trigger becomes visible (it can be visually muted at rest).

---

### Story 8.5: Sync Integration — Blacklist Filter

As a user,
I want the next sync to actually remove blacklisted tracks from my Spotify playlist and never let them come back,
So that the blacklist is meaningful — not just a UI state.

**Acceptance Criteria:**

**Given** the sync engine reaches the post-dedup / pre-push stage,
**When** it assembles the final track list,
**Then** it filters out any track whose `spotify_id` is in `track_blacklist` BEFORE applying the top-N slice (FR34).

**Given** a track is blacklisted and the dynamic Spotify playlist currently contains it,
**When** the next sync runs successfully,
**Then** the track is absent from the new playlist contents on Spotify (FR35).

**Given** the blacklist is empty,
**When** a sync runs,
**Then** behavior is identical to the pre-blacklist sync engine — no regression in track count or ordering for existing scenarios.

**Given** the blacklist filtering reduces the candidate pool below `playlist_size`,
**When** the slice is applied,
**Then** the final playlist simply contains fewer tracks — no error is raised.

**Given** the existing sync engine tests,
**When** they run after this story,
**Then** all previously passing tests still pass, AND a new test covers the blacklist filter (mocked `track_blacklist` row, asserts the track is excluded from the final list).

**Given** a blacklisted track is later un-blacklisted (`DELETE /api/v1/blacklist/{id}`),
**When** the next sync runs and that track qualifies for the top-N harvest,
**Then** it is restored to the dynamic playlist (no permanent record of blacklist after deletion).

---

### Story 8.6: Recently Added Performance & Polish

As a user,
I want the Recently Added page to feel instant and behave correctly when I blacklist many tracks in a row,
So that the page is a reliable daily tool.

**Acceptance Criteria:**

**Given** the Recently Added page with 200 tracks,
**When** it is profiled,
**Then** initial render is <1 second (NFR14) and scrolling remains 60fps on a typical desktop browser.

**Given** the cover thumbnails,
**When** the table renders,
**Then** thumbnails use `loading="lazy"` so off-screen images are not fetched until they approach the viewport.

**Given** I blacklist multiple tracks in quick succession,
**When** each `POST /api/v1/blacklist` returns,
**Then** the TanStack Query cache for `/api/v1/recently-added` is NOT re-fetched per click (optimistic updates only) — a refetch only happens after the next sync or on manual user refresh.

**Given** a manual sync completes,
**When** the SSE `sync_complete` event arrives (or the manual sync POST returns),
**Then** the Recently Added query is invalidated and the table refetches automatically.

**Given** the table is rendered,
**When** I tab through rows,
**Then** focus order is row-by-row top-to-bottom and the active focus row is visually indicated.
