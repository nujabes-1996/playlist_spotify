---
stepsCompleted: ['step-01-init', 'step-02-context', 'step-03-starter', 'step-04-decisions', 'step-05-patterns', 'step-06-structure', 'step-07-validation', 'step-08-complete']
lastStep: 8
status: 'complete'
completedAt: '2026-04-17'
inputDocuments: ['_bmad-output/planning-artifacts/prd.md']
workflowType: 'architecture'
project_name: 'playlist_spotify'
user_name: 'kevin'
date: '2026-04-17'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
24 MVP requirements across 6 functional domains:
- Authentication (FR1–FR3): Spotify OAuth2 with transparent server-side token refresh
- Sync Engine (FR4–FR9): Track harvest, cross-playlist deduplication by `added_at`, sorting, target playlist create/replace
- Playlist Selection (FR10–FR13): View, toggle, persist inclusion preferences; reflect Spotify library changes dynamically
- Scheduler (FR14–FR17): Configurable cron/interval, persists across restarts, manual trigger
- Configuration (FR18–FR20): Spotify credentials, playlist size, all persisted
- Observability (FR21–FR24): Real-time sync log stream, sync history, visible failure indicator

**Non-Functional Requirements:**
- Performance: <3s page load, <2s playlist refresh, <1s real-time event delivery, 5,000 tracks sync in <30s
- Security: OAuth tokens server-side only, credentials in local config (not source code), HTTPS for Spotify API
- Reliability: Scheduler auto-resumes on restart, sync failure preserves existing playlist, retry with exponential backoff on HTTP 429

**Scale & Complexity:**
- Primary domain: Full-stack web application with background scheduler service
- Complexity level: Medium
- Estimated architectural components: 5 (React SPA, FastAPI server, APScheduler process, SQLite, Spotify API client)
- Single-user personal tool — no multi-tenancy, no auth layer on dashboard

### Technical Constraints & Dependencies

- Stack locked by PRD: React (frontend), Python + FastAPI (backend), APScheduler (scheduler), SQLite (persistence)
- **Deployment: Docker-first** — all services (frontend, backend, scheduler) containerized via Docker Compose
- Browser target: latest Chrome and Firefox only
- OAuth callback must be server-side — token never touches the browser
- Spotify API: subject to rate limiting (429), pagination required for libraries >100 tracks, access token expiry ~1h

### Cross-Cutting Concerns Identified

1. **Spotify OAuth Token Lifecycle** — affects sync engine, playlist fetch, all API calls; must be transparent
2. **Real-time Communication** (SSE vs WebSocket) — decision affects both backend streaming implementation and frontend event handling
3. **Error Handling & Resilience** — rate limit backoff, token expiry re-auth flow, sync failure isolation
4. **Scheduler Lifecycle** — process management within Docker container, persistence of schedule state
5. **Configuration & Secrets Management** — Spotify credentials via Docker environment variables or mounted `.env` file

## Starter Template Evaluation

### Primary Technology Domain

Full-stack web application with background scheduler service — separate frontend (React SPA) and backend (Python FastAPI) scaffolded independently.

### Starter Options Considered

- **Official FastAPI Full Stack Template** (fastapi/full-stack-fastapi-template): React + FastAPI + Docker — excellent patterns but mandates PostgreSQL, JWT auth, and Alembic migrations, all overkill for a single-user personal tool with SQLite.
- **Manual scaffolding**: Vite React TS + standard FastAPI structure + custom Docker Compose — minimal, full control, matches project constraints exactly.

### Selected Approach: Manual Scaffolding

**Rationale:** This is a single-user personal tool. SQLite is a first-class requirement (no database server). Pulling in a full-stack template would introduce PostgreSQL, JWT auth layers, and migration tooling that add complexity without value. Manual scaffolding keeps the project minimal and comprehensible.

**Initialization Commands:**

```bash
# Frontend
npm create vite@latest frontend -- --template react-ts

# Backend
mkdir backend && cd backend
python -m venv .venv && pip install "fastapi[standard]" apscheduler spotipy
```

**Architectural Decisions Established by Scaffolding:**

**Language & Runtime:**
- Frontend: TypeScript (via Vite 8 + react-ts template)
- Backend: Python 3.12+, FastAPI 0.136+, async I/O

**Build Tooling:**
- Frontend: Vite 8 with Rolldown (faster production builds)
- Backend: uvicorn (ASGI server, included with `fastapi[standard]`)

**Project Structure:**
```
playlist_spotify/
├── docker-compose.yml
├── frontend/                  # Vite React TS app
│   ├── Dockerfile
│   └── src/
├── backend/                   # FastAPI app
│   ├── Dockerfile
│   ├── main.py
│   ├── routers/
│   ├── services/
│   ├── scheduler.py
│   └── db/
└── data/                      # SQLite volume mount
    └── app.db
```

**Docker Compose Strategy:**
- `frontend` service: Vite dev server (port 5173), source volume for HMR
- `backend` service: uvicorn (port 8000), source volume for hot-reload
- SQLite persisted via `./data` host mount (survives container restarts)
- Single `docker-compose up` starts everything

**Code Organization:**
- Feature-based routers in `backend/routers/` (auth, playlists, sync, config)
- Services layer for business logic (sync engine, Spotify client)
- Scheduler as a separate module started at app startup lifecycle

**Note:** Project initialization using these commands should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- SQLModel as ORM (data modeling + validation unified)
- spotipy for Spotify API (OAuth2, pagination, rate limiting handled)
- First-run setup UI for Spotify credentials (stored in SQLite)
- SSE for real-time sync log streaming

**Important Decisions (Shape Architecture):**
- TanStack Query for server state management
- shadcn/ui + Tailwind v4 for UI components
- React Router v7 for SPA routing
- SQLModel auto-create (no Alembic migrations)

**Deferred Decisions (Post-MVP):**
- CI/CD pipeline (personal tool, not needed for MVP)
- Production nginx setup (local deployment only)

---

### Data Architecture

**ORM: SQLModel**
- Decision: SQLModel (SQLAlchemy + Pydantic unified)
- Rationale: Native FastAPI integration — models double as Pydantic validation schemas. No duplication between DB models and API schemas.
- Affects: all backend models (Config, Playlist, SyncLog, Token)

**Schema Migration: SQLModel auto-create**
- Decision: `SQLModel.metadata.create_all()` on app startup
- Rationale: Greenfield personal tool — no production data to preserve during migrations. Alembic adds complexity without value here.
- Affects: backend startup lifecycle

---

### Authentication & Security

**Spotify OAuth2: spotipy library**
- Decision: spotipy (Python Spotify API client)
- Rationale: Handles OAuth2 PKCE flow, automatic token refresh, pagination, and HTTP 429 backoff out of the box.
- Affects: sync engine, playlist fetch, all Spotify API calls

**Credentials Management: First-run Setup UI → SQLite**
- Decision: Spotify Client ID + Client Secret entered via dashboard on first run, stored in SQLite. No `.env` editing required.
- Flow: `docker-compose up` → open browser → setup screen (if no credentials) → enter credentials → "Connect Spotify" → OAuth2 → authenticated
- Security: credentials stored server-side in SQLite only, never returned to browser
- Rationale: Maximum simplicity — zero file editing beyond `docker-compose up`
- Affects: onboarding flow, Config model, first-run detection middleware

---

### API & Communication Patterns

**Real-time: Server-Sent Events (SSE)**
- Decision: SSE for sync log streaming (FR21)
- Rationale: Unidirectional (server→client) matches the use case perfectly. Native HTTP, no WebSocket upgrade handshake, simpler implementation on both ends.
- Implementation: FastAPI `StreamingResponse` with `text/event-stream` content type
- Affects: backend `/api/v1/sync/stream` endpoint, React EventSource client

**API Design: REST with `/api/v1` prefix**
- Decision: RESTful endpoints, versioned under `/api/v1/`
- Rationale: Consistent with FastAPI conventions, easy to consume from TanStack Query

**Error Handling: Structured JSON error responses**
- Decision: Consistent JSON error body `{ "detail": "...", "code": "..." }` across all endpoints via FastAPI HTTPException

---

### Frontend Architecture

**State Management: TanStack Query v5**
- Decision: TanStack Query (React Query) for all server state
- Rationale: Automatic caching, background refetch, loading/error states — eliminates boilerplate for REST data fetching. Ideal for playlist list, config, sync history.
- Affects: all data-fetching hooks

**UI Components: shadcn/ui + Tailwind CSS v4**
- Decision: shadcn/ui components + Tailwind v4 for utility styling
- Rationale: Components are copied into the project (no runtime dependency), accessible by default, mobile-friendly, full design control.
- Affects: all UI components

**Routing: React Router v7**
- Decision: React Router v7 (SPA mode) via `react-router-dom`
- Routes: `/` (Dashboard), `/recently-added` (Recently Added), `/settings` (formerly `/config` — redirects), `/logs` (Logs)
- `AppShell` is the layout route parent (sidebar + topbar persistent)
- Affects: App entry point, navigation structure

---

### Design System & UI Primitives

**Source de vérité UX:** [`ux-design/README.md`](./ux-design/README.md) (Claude Design handoff, 2026-05-20).

**Design tokens:** centralisés dans `frontend/src/index.css`. Bloc à reprendre tel quel depuis `ux-design/snippets/index.css`. Tokens majeurs :
- Surfaces : `--bg-base #0d0d0d`, `--bg-app #121212`, `--bg-elevated #1c1c1c`, `--bg-elevated-2 #232323`, `--bg-hover #2a2a2a`
- Texte : `--text-primary #fff`, `--text-secondary #b3b3b3`, `--text-muted #6a6a6a`
- Accent : `--accent #1DB954`, `--accent-hover #1ed760`, `--accent-fg #000`
- Layout : `--sidebar-w 248px`, `--header-h 64px`
- Radius : `--r-md 6px`, `--r-lg 8px`, `--r-pill 999px`

**Theme:** dark forcé (`class="dark"` sur `<html>` dans `index.html`). Pas de toggle utilisateur.

**Composants shadcn/ui requis** (au-delà de Button déjà installé) : `Accordion`, `DropdownMenu`, `Tooltip`, `Sheet`, `Input`, `Label`, `Separator`. Installation via `bash ux-design/snippets/shadcn-add.sh` ou commandes individuelles `npx shadcn@latest add <component>` (cf. CLAUDE.md : toujours via CLI, jamais à la main).

**Composants applicatifs livrés par le handoff (drop-in baselines):**
- `frontend/src/components/AppShell.tsx` — layout grid 2 colonnes (sidebar + main area avec gradient top)
- `frontend/src/components/PlaylistCard.tsx` — carte playlist avec hover Play FAB + overflow menu
- `frontend/src/components/TrackRow.tsx` — ligne de table track 6 colonnes
- `frontend/src/components/HiddenPlaylistsAccordion.tsx` — accordion shadcn collapsé par défaut

**Icônes:** `lucide-react` exclusivement. Liste utilisée : LayoutDashboard, Clock, Settings, ScrollText, ChevronLeft, ChevronRight, ChevronDown, RotateCw, Search, Play, MoreHorizontal, Check, Eye, EyeOff, ExternalLink, Sparkles.

**Override projet — SSE Logs:** le snippet `useEffect` always-on du README handoff (section Logs route) est non-applicable. L'`EventSource` est ouvert uniquement pendant un sync actif (cf. FR21 + Story 5.3).

---

### Infrastructure & Deployment

**Containerization: Docker Compose (two services)**
- `frontend`: Vite dev server (port 5173), hot-reload via volume mount
- `backend`: uvicorn (port 8000), hot-reload via volume mount
- SQLite: persisted via `./data` host bind mount

**Backend Dependency Management: uv**
- Decision: `uv` (modern Python package manager) + `pyproject.toml`
- Rationale: Significantly faster than pip, lockfile support, standard tooling in 2026

**Environment Configuration: `.env` for infrastructure only**
- App-level vars only (ports, CORS origins) — NOT for Spotify credentials
- Spotify credentials managed through the setup UI at runtime

### Decision Impact Analysis

**Implementation Sequence:**
1. Docker Compose + project scaffolding
2. Backend: SQLModel models + SQLite setup
3. Backend: FastAPI app structure + routers
4. Backend: spotipy OAuth2 flow + first-run credential storage
5. Backend: Sync engine (harvest, dedup, sort, push)
6. Backend: APScheduler integration
7. Backend: SSE endpoint for sync logs
8. Frontend: Vite + React Router + TanStack Query + shadcn/ui setup
9. Frontend: Dashboard views (playlists, config, logs)
10. Frontend: OAuth2 connect flow + first-run setup screen

**Cross-Component Dependencies:**
- spotipy token lifecycle → sync engine + scheduler (all Spotify calls share token state)
- SQLite Config model → first-run detection → OAuth flow → all subsequent API calls
- SSE stream → frontend EventSource → real-time log panel

## Implementation Patterns & Consistency Rules

### Naming Patterns

**Database Naming (SQLModel):**
- Tables: lowercase snake_case singular → `playlist`, `sync_log`, `config`, `token`
- Columns: snake_case → `added_at`, `playlist_id`, `is_included`
- Foreign keys: `{table}_id` → `playlist_id`

**API Naming (FastAPI):**
- Endpoints: plural nouns, snake_case → `/api/v1/playlists`, `/api/v1/sync_logs`
- Path params: snake_case → `/api/v1/playlists/{playlist_id}`
- Query params: snake_case → `?include_only=true`
- JSON fields: snake_case throughout (no camelCase conversion)

**Code Naming:**
- Python files: snake_case → `sync_engine.py`, `spotify_client.py`
- Python functions/vars: snake_case → `get_playlists()`, `added_at`
- React components: PascalCase files + exports → `PlaylistCard.tsx`
- React hooks: camelCase prefixed `use` → `usePlaylists()`, `useSyncStatus()`
- React utils/services: camelCase → `spotifyApi.ts`, `formatDate.ts`

---

### Structure Patterns

**Backend (`backend/`):**
```
backend/
├── main.py              # FastAPI app factory + lifespan
├── database.py          # SQLite engine + session
├── scheduler.py         # APScheduler setup + job registration
├── models/              # SQLModel table models
│   ├── playlist.py
│   ├── sync_log.py
│   └── config.py
├── routers/             # FastAPI APIRouter, one file per domain
│   ├── auth.py          # /api/v1/auth/*
│   ├── playlists.py     # /api/v1/playlists/*
│   ├── sync.py          # /api/v1/sync/*
│   └── config.py        # /api/v1/config/*
├── services/            # Business logic, no HTTP concerns
│   ├── spotify.py       # spotipy wrapper
│   ├── sync_engine.py   # harvest/dedup/sort/push logic
│   └── token_manager.py # OAuth token lifecycle
└── tests/               # pytest, mirrors routers/ structure
```

**Frontend (`frontend/src/`):**
```
frontend/src/
├── main.tsx             # React entry + Router + QueryClient
├── App.tsx              # Route definitions
├── components/          # Shared, reusable UI components
│   ├── ui/              # shadcn/ui generated components
│   └── layout/          # Header, Nav, etc.
├── features/            # Feature-based modules
│   ├── playlists/       # PlaylistList, PlaylistToggle
│   ├── sync/            # SyncButton, SyncLogPanel, SSE hook
│   ├── config/          # ConfigForm, SetupWizard
│   └── auth/            # SpotifyConnect, ReauthBanner
├── hooks/               # Shared TanStack Query hooks
├── lib/                 # API client, utils
│   └── api.ts           # fetch wrapper targeting /api/v1/
└── types/               # Shared TypeScript interfaces
```

---

### Format Patterns

**API Response Format:**
- Success: direct resource or array — NO wrapper `{data: ...}`
  - `GET /api/v1/playlists` → `[{id, name, is_included, ...}]`
  - `GET /api/v1/config` → `{playlist_size, cron_expr, ...}`
- Error: `{"detail": "message", "code": "ERROR_CODE"}`
- HTTP status codes: 200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 404 Not Found, 429 Rate Limited, 500 Server Error

**Date/Time Format:**
- All timestamps: ISO 8601 strings → `"2026-04-17T14:30:00Z"`
- Never Unix timestamps in JSON

**SSE Event Format:**
```
event: sync_log
data: {"level": "info", "message": "Harvested 42 tracks", "timestamp": "2026-04-17T14:30:00Z"}

event: sync_complete
data: {"status": "success", "track_count": 50, "timestamp": "2026-04-17T14:30:01Z"}

event: sync_error
data: {"status": "error", "message": "Token expired", "code": "TOKEN_EXPIRED", "timestamp": "..."}
```

---

### Communication Patterns

**TanStack Query Key Conventions:**
```typescript
['playlists']               // all playlists
['playlists', playlistId]   // single playlist
['config']                  // app config
['sync', 'logs']            // sync history
['sync', 'status']          // last sync status
```

**API Client (`lib/api.ts`):**
- Single fetch wrapper handles base URL + error parsing
- All TanStack Query hooks import from `lib/api.ts`, never raw `fetch`

---

### Process Patterns

**Backend Error Handling:**
- All Spotify API errors caught in `services/spotify.py` → re-raised as typed exceptions
- Routers catch service exceptions → return appropriate HTTPException
- Sync failures: log entry written BEFORE raising — existing playlist preserved

**Frontend Error Handling:**
- TanStack Query `onError` callbacks surface errors to UI
- HTTP 401 → trigger re-auth banner (global query observer)
- Never `console.error` only — always reflect error state in UI

**Loading States:**
- Use TanStack Query `isLoading` / `isFetching` — no manual loading state
- Skeleton components during initial load, spinner for subsequent fetches

**Retry Logic:**
- spotipy handles Spotify API retries (429) internally
- TanStack Query: `retry: 1` for all queries (default)
- No custom retry loops outside of these two mechanisms

---

### Enforcement Guidelines

**All AI Agents MUST:**
- Use snake_case for all JSON fields — never camelCase at the API boundary
- Place business logic in `services/`, never in routers
- Use the shared `lib/api.ts` client — never raw `fetch` in components
- Write SSE events using the exact format defined above
- Use TanStack Query key convention: arrays, general → specific
- Store no Spotify credentials in `.env` or source code

**Anti-Patterns:**
- ❌ `GET /api/v1/playlist` (singular) → use `/api/v1/playlists`
- ❌ `{"playlistId": ...}` in JSON → use `{"playlist_id": ...}`
- ❌ Business logic in routers → move to `services/`
- ❌ Unix timestamps in JSON → use ISO 8601 strings
- ❌ Direct spotipy calls in routers → always via `services/spotify.py`

## Project Structure & Boundaries

### Complete Project Directory Structure

```
playlist_spotify/
├── docker-compose.yml
├── docker-compose.override.yml      # Dev overrides (volumes, hot-reload)
├── .env.example                     # Ports, CORS origins only
├── .gitignore
├── README.md
│
├── data/                            # Host-mounted SQLite persistence
│   └── .gitkeep
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml               # uv dependencies + project metadata
│   ├── uv.lock
│   ├── main.py                      # FastAPI app factory + lifespan hooks
│   ├── database.py                  # SQLite engine, session factory, create_all
│   ├── scheduler.py                 # APScheduler instance + job registration
│   ├── dependencies.py              # FastAPI shared dependencies (DB session)
│   │
│   ├── models/                      # SQLModel table definitions
│   │   ├── __init__.py
│   │   ├── playlist.py              # Playlist (id, spotify_id, name, is_included)
│   │   ├── sync_log.py              # SyncLog (id, status, track_count, error, timestamp)
│   │   └── config.py                # Config (client_id, client_secret, playlist_size, cron_expr)
│   │
│   ├── routers/                     # FastAPI APIRouter, one file per domain
│   │   ├── __init__.py
│   │   ├── auth.py                  # FR1-FR3: POST /api/v1/auth/connect, /callback, /status
│   │   ├── playlists.py             # FR10-FR13: GET/PATCH /api/v1/playlists
│   │   ├── sync.py                  # FR14-FR17, FR21-FR24: POST /api/v1/sync/run, GET /api/v1/sync/stream (SSE), /api/v1/sync/logs
│   │   └── config.py                # FR18-FR20: GET/PUT /api/v1/config
│   │
│   ├── services/                    # Business logic, no HTTP concerns
│   │   ├── __init__.py
│   │   ├── spotify.py               # spotipy client wrapper (init, auth, API calls)
│   │   ├── sync_engine.py           # FR4-FR9: harvest → dedup → sort → push
│   │   └── token_manager.py         # OAuth token read/write/refresh lifecycle
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_playlists.py
│       ├── test_sync_engine.py
│       └── test_config.py
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.ts               # Proxy /api → backend:8000
    ├── tsconfig.json
    ├── tsconfig.app.json
    ├── index.html
    ├── components.json              # shadcn/ui config
    ├── tailwind.config.ts
    │
    └── src/
        ├── main.tsx                 # React entry, QueryClient, Router
        ├── App.tsx                  # Route definitions
        │
        ├── components/
        │   ├── ui/                  # shadcn/ui generated components
        │   └── layout/
        │       ├── AppShell.tsx     # Persistent nav + main content area
        │       └── NavBar.tsx
        │
        ├── features/
        │   ├── auth/                # FR1-FR3
        │   │   ├── SpotifyConnect.tsx
        │   │   └── ReauthBanner.tsx
        │   ├── playlists/           # FR10-FR13
        │   │   ├── PlaylistList.tsx
        │   │   └── PlaylistToggle.tsx
        │   ├── sync/                # FR14-FR17, FR21-FR24
        │   │   ├── SyncButton.tsx
        │   │   ├── SyncStatusBadge.tsx
        │   │   ├── SyncLogPanel.tsx
        │   │   └── useSyncStream.ts # EventSource SSE hook
        │   └── config/              # FR18-FR20
        │       ├── ConfigForm.tsx
        │       └── SetupWizard.tsx  # First-run credential entry
        │
        ├── hooks/                   # Shared TanStack Query hooks
        │   ├── usePlaylists.ts
        │   ├── useSyncLogs.ts
        │   └── useConfig.ts
        │
        ├── lib/
        │   ├── api.ts               # fetch wrapper (base URL, error parsing)
        │   └── utils.ts             # formatDate, cn (shadcn helper)
        │
        └── types/
            └── index.ts             # Shared TS interfaces (Playlist, SyncLog, Config)
```

---

### Architectural Boundaries

**API Boundary (Backend → Frontend):**
- All communication via `/api/v1/*` REST endpoints
- Vite dev proxy: `vite.config.ts` proxies `/api` → `http://backend:8000`
- Real-time: `GET /api/v1/sync/stream` returns `text/event-stream`
- No direct frontend access to SQLite or spotipy

**Service Boundary (Routers → Services):**
- Routers handle HTTP: request parsing, response formatting, HTTPException
- Services handle logic: Spotify API calls, sync computation, token management
- Routers NEVER import spotipy directly — always via `services/spotify.py`

**Scheduler Boundary:**
- `scheduler.py` imports `sync_engine` from services — not routers
- Scheduler started/stopped in FastAPI `lifespan` context manager in `main.py`
- Manual sync trigger (FR17) calls same `sync_engine` function as scheduler

**Data Boundary:**
- `database.py` is the only file that creates the SQLite engine
- All DB access via SQLModel sessions from `dependencies.py`
- `data/app.db` mounted from host — never inside container filesystem

---

### Requirements to Structure Mapping

| FR Category | Backend | Frontend |
|---|---|---|
| Auth (FR1–FR3) | `routers/auth.py` + `services/token_manager.py` | `features/auth/` |
| Sync Engine (FR4–FR9) | `services/sync_engine.py` | — |
| Playlist Selection (FR10–FR13) | `routers/playlists.py` | `features/playlists/` |
| Scheduler (FR14–FR17) | `scheduler.py` + `routers/sync.py` | `features/sync/SyncButton` |
| Configuration (FR18–FR20) | `routers/config.py` + `models/config.py` | `features/config/` |
| Observability (FR21–FR24) | `routers/sync.py` (SSE + logs) | `features/sync/SyncLogPanel` + `useSyncStream` |
| First-run onboarding | `routers/config.py` (no-credentials check) | `features/config/SetupWizard` |

---

### Integration Points

**Internal Communication:**
- Frontend ↔ Backend: REST + SSE via `/api/v1/`
- Scheduler → Sync Engine: direct function call (same process)
- Routers → Services: direct import (same process)

**External Integration (Spotify API):**
- All calls via `services/spotify.py` (spotipy wrapper)
- OAuth callback: `GET /api/v1/auth/callback` (server-side, browser redirect)
- Token stored in `models/config.py` (SQLite), never in browser

**Data Flow — Sync Operation:**
```
Scheduler trigger (or manual)
  → sync_engine.run_sync()
    → spotify.get_tracks(selected_playlists)  # paginated
    → dedup by spotify_id, keep latest added_at
    → sort descending, slice top N
    → spotify.replace_playlist(target_id, track_uris)
  → write SyncLog (success/failure)
  → emit SSE event → frontend SyncLogPanel
```

---

### Development Workflow

**Start everything:** `docker-compose up`
- Frontend: http://localhost:5173 (Vite HMR)
- Backend: http://localhost:8000 (uvicorn --reload)
- API docs: http://localhost:8000/docs (FastAPI Swagger)

**SQLite location:** `./data/app.db` (host mount, survives restarts)

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:** All technology choices are compatible.
- SQLModel works natively with SQLite via SQLAlchemy
- APScheduler integrates via FastAPI `lifespan` context manager
- spotipy + custom CacheHandler stores tokens in SQLite (consistent with credentials decision)
- TanStack Query + SSE: `EventSource` is natively supported in all target browsers
- Tailwind v4 + shadcn/ui: shadcn/ui v2+ supports Tailwind v4

**Pattern Consistency:** snake_case throughout (Python native + explicit frontend convention). Naming, structure, and communication patterns are internally consistent.

**Structure Alignment:** All FR categories map to specific files. Boundaries (routers → services, scheduler → services) prevent logic leakage.

---

### Requirements Coverage Validation ✅

| FR Category | Coverage | Location |
|---|---|---|
| Auth (FR1–FR3) | ✅ Full | `routers/auth.py`, `services/token_manager.py` |
| Sync Engine (FR4–FR9) | ✅ Full | `services/sync_engine.py` |
| Playlist Selection (FR10–FR13) | ✅ Full | `routers/playlists.py` |
| Scheduler (FR14–FR17) | ✅ Full (with job store fix) | `scheduler.py` (SQLAlchemyJobStore) |
| Configuration (FR18–FR20) | ✅ Full | `routers/config.py`, `models/config.py` |
| Observability (FR21–FR24) | ✅ Full | `routers/sync.py` SSE + `useSyncStream.ts` |

**NFR Coverage:**
- Performance <3s load: Vite build + static assets via Docker ✅
- Performance 5,000 tracks/30s: spotipy pagination (100 tracks/request) ✅
- Security: tokens SQLite-only, never in API responses ✅
- Reliability: APScheduler SQLAlchemyJobStore + sync failure preserves playlist ✅

---

### Gap Analysis — Issues Identified & Resolved

**Gap 1 (Critical) — APScheduler job persistence (FR16):**
- Issue: Default `MemoryJobStore` loses jobs on container restart
- Resolution: Use `SQLAlchemyJobStore(url='sqlite:////data/app.db')` in `scheduler.py`
- Impact: `scheduler.py` must configure job store before registering any jobs

**Gap 2 (Critical) — spotipy token storage:**
- Issue: Default `CacheFileHandler` writes to filesystem (not persisted in Docker)
- Resolution: Implement `SQLiteCacheHandler(CacheHandler)` in `services/token_manager.py`
- Interface: `get_cached_token()` reads from SQLite Config, `save_token_to_cache()` writes to SQLite Config
- Impact: spotipy client must be initialized with `cache_handler=SQLiteCacheHandler(db)`

---

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified (Docker-first, SQLite, single-user)
- [x] Cross-cutting concerns mapped (token lifecycle, SSE, scheduler, secrets)

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Full technology stack specified (FastAPI 0.136, Vite 8, SQLModel, spotipy, APScheduler, uv)
- [x] Integration patterns defined (REST + SSE, Vite proxy)
- [x] Performance and reliability considerations addressed

**✅ Implementation Patterns**
- [x] Naming conventions established (snake_case throughout)
- [x] Structure patterns defined (routers/services/models/features)
- [x] Communication patterns specified (SSE format, TanStack Query keys)
- [x] Process patterns documented (error handling, loading states, retry)

**✅ Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established (routers → services, scheduler → services)
- [x] All integration points mapped
- [x] Requirements to structure mapping complete

---

### Architecture Readiness Assessment

**Overall Status: READY FOR IMPLEMENTATION**

**Confidence Level: High**

**Key Strengths:**
- Stack is minimal and well-suited to a personal tool — no over-engineering
- Docker Compose enables zero-config startup (`docker-compose up`)
- Single-responsibility boundaries prevent implementation drift across AI agents
- SQLite for everything (app data + APScheduler jobs + OAuth tokens) keeps deployment simple

**Areas for Future Enhancement (Post-MVP):**
- Multi-stage Docker build for production (nginx serves built frontend assets)
- Preview mode (FR25) will require a read-only sync simulation path in `sync_engine.py`

---

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries (routers never contain business logic)
- `services/token_manager.py` must implement `SQLiteCacheHandler` before any spotipy usage
- `scheduler.py` must use `SQLAlchemyJobStore` — never default MemoryJobStore

**First Implementation Steps:**
1. `docker-compose.yml` + `Dockerfile` × 2 (project scaffolding)
2. `backend/database.py` + SQLModel models + `SQLModel.metadata.create_all()`
3. `backend/services/token_manager.py` with `SQLiteCacheHandler`
4. `backend/scheduler.py` with `SQLAlchemyJobStore`
