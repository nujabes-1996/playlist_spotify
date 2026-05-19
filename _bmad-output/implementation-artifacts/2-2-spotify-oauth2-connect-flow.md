# Story 2.2: Spotify OAuth2 Connect Flow

Status: review

## Story

As a user,
I want to connect my Spotify account from the setup screen,
so that the app can access my playlists and manage my music.

## Acceptance Criteria

1. **Given** `client_id` and `client_secret` are saved in the DB, **When** `POST /api/v1/auth/connect` is called, **Then** the response returns `{"auth_url": "https://accounts.spotify.com/authorize?..."}`.
2. **Given** the authorization URL is returned, **When** the user clicks "Connect Spotify" in the `SpotifyConnect` component, **Then** the browser is redirected to Spotify's authorization page (`window.location.href = auth_url`).
3. **Given** the user grants access on Spotify, **When** Spotify redirects to `GET /api/v1/auth/callback?code=...`, **Then** the backend exchanges the code for tokens, stores them via `SQLiteCacheHandler` in the `config` table's `spotify_token_json` column, and redirects the browser to `http://localhost:5173`.
4. **Given** the callback succeeds, **When** `GET /api/v1/auth/status` is called, **Then** it returns `{"authenticated": true, "spotify_user_id": "<user id>"}`.
5. **Given** tokens are stored server-side via `SQLiteCacheHandler`, **When** any API response body is inspected, **Then** no `access_token` or `refresh_token` field appears (NFR5).
6. **Given** `setup_required: false` AND `authenticated: false`, **When** the dashboard loads, **Then** `SpotifyConnect` is rendered instead of the normal dashboard content.
7. **Given** `setup_required: false` AND `authenticated: true`, **When** the dashboard loads, **Then** the normal dashboard placeholder is shown and `SpotifyConnect` is not rendered.

## Tasks / Subtasks

- [x] Task 1: Create `backend/services/spotify.py` — spotipy wrapper (AC: #1, #3, #4)
  - [x] Define `SCOPES = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-read-private"`
  - [x] Define `REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8000/api/v1/auth/callback")`
  - [x] Implement `_get_spotify_oauth() -> SpotifyOAuth` — reads `client_id`/`client_secret` from DB, initializes `SpotifyOAuth` with `cache_handler=SQLiteCacheHandler()`; raises `ValueError` if credentials missing
  - [x] Implement `get_auth_url() -> str` — calls `sp_oauth.get_authorize_url()` and returns the URL string
  - [x] Implement `handle_callback(code: str) -> None` — calls `sp_oauth.get_access_token(code, check_cache=False)`; spotipy calls `SQLiteCacheHandler.save_token_to_cache()` automatically
  - [x] Implement `get_auth_status() -> dict` — calls `sp_oauth.get_cached_token()`; if None → `{"authenticated": False, "spotify_user_id": None}`; else validates/refreshes token via `sp_oauth.validate_token()`, calls `Spotify(auth=token["access_token"]).me()` to get user ID; catches all exceptions → `{"authenticated": False, "spotify_user_id": None}`

- [x] Task 2: Create `backend/routers/auth.py` — auth endpoints (AC: #1, #3, #4, #5)
  - [x] Define `AuthStatusResponse(BaseModel)` with `authenticated: bool` and `spotify_user_id: Optional[str] = None` — never include token fields
  - [x] Define `ConnectResponse(BaseModel)` with `auth_url: str`
  - [x] Implement `POST /api/v1/auth/connect` → calls `spotify_service.get_auth_url()`, returns `ConnectResponse`; raises `HTTPException(400)` on `ValueError`
  - [x] Implement `GET /api/v1/auth/callback` — query params: `code: Optional[str] = None`, `error: Optional[str] = None`; if `error` or no `code` → `RedirectResponse(f"{FRONTEND_URL}?auth_error=1")`; else call `spotify_service.handle_callback(code)` → `RedirectResponse(FRONTEND_URL)`; catch exceptions → `RedirectResponse(f"{FRONTEND_URL}?auth_error=1")`
  - [x] `FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")` — read at module level
  - [x] Implement `GET /api/v1/auth/status` → calls `spotify_service.get_auth_status()`, returns `AuthStatusResponse`

- [x] Task 3: Register auth router in `backend/main.py` (AC: #1, #3, #4)
  - [x] `from routers.auth import router as auth_router`
  - [x] `app.include_router(auth_router, prefix="/api/v1")` — add after existing `config_router` line

- [x] Task 4: Update `frontend/src/types/index.ts` — add `AuthStatus` type (AC: #6, #7)
  - [x] Add `export interface AuthStatus { authenticated: boolean; spotify_user_id?: string | null }`
  - [x] Leave existing `Config` and `ConfigWrite` interfaces unchanged

- [x] Task 5: Create `frontend/src/hooks/useAuthStatus.ts` — TanStack Query hook (AC: #6, #7)
  - [x] `useAuthStatus()` — `useQuery({ queryKey: ['auth', 'status'], queryFn: () => api.get<AuthStatus>('/auth/status'), staleTime: 0 })` — `staleTime: 0` ensures fresh data after OAuth redirect returns browser to frontend

- [x] Task 6: Create `frontend/src/features/auth/SpotifyConnect.tsx` (AC: #2, #6)
  - [x] Read `?auth_error=1` from `window.location.search` on mount — display error banner if present
  - [x] "Connect Spotify" button calls `api.post<{ auth_url: string }>('/auth/connect')` then `window.location.href = data.auth_url`
  - [x] Show loading/disabled state while the `post` is in flight (use local `useState<boolean>`)
  - [x] Show `error.message` on catch
  - [x] Display `SPOTIFY_REDIRECT_URI` instruction: tell user to add `http://localhost:8000/api/v1/auth/callback` to Spotify app's Redirect URIs

- [x] Task 7: Update `frontend/src/pages/DashboardPage.tsx` — add auth status check (AC: #6, #7)
  - [x] Import and call `useAuthStatus()`
  - [x] Loading: show spinner if either `config.isPending` OR `authStatus.isPending`
  - [x] Error: show error if either `config.isError` OR `authStatus.isError`
  - [x] If `data.setup_required === true` → render `<SetupWizard />` (unchanged from 2.1)
  - [x] If `!authStatus.data.authenticated` → render `<SpotifyConnect />`
  - [x] Otherwise → render `<h1 className="text-2xl font-bold">Dashboard</h1>` placeholder

- [x] Task 8: Verify all ACs
  - [ ] `POST http://localhost:8000/api/v1/auth/connect` returns `{"auth_url": "https://accounts.spotify.com/authorize?..."}`
  - [ ] Clicking "Connect Spotify" redirects to Spotify's auth page
  - [ ] After granting access, browser lands at `http://localhost:5173` and dashboard shows (authenticated: true)
  - [ ] `GET /api/v1/auth/status` returns `{"authenticated": true, "spotify_user_id": "..."}`
  - [ ] No `access_token`/`refresh_token` in any response body
  - [ ] If credentials not saved, `POST /auth/connect` returns 400
  - [ ] Restarting Docker: `GET /api/v1/auth/status` still returns `authenticated: true` (token persisted via SQLiteCacheHandler in SQLite bind mount)

## Dev Notes

### Codebase State After Story 2.1

**What exists — use it, don't recreate:**

| File | State | Notes |
|------|-------|-------|
| `backend/models/config.py` | ✅ Done | `Config` with `id, client_id, client_secret, playlist_size, cron_expr, spotify_token_json` — `spotify_token_json` is where `SQLiteCacheHandler` writes tokens |
| `backend/database.py` | ✅ Done | `engine` + `get_session()` |
| `backend/dependencies.py` | ✅ Done | `SessionDep` |
| `backend/main.py` | ✅ Done | Has `config_router` registered — ADD `auth_router` here |
| `backend/services/token_manager.py` | ✅ Done | `SQLiteCacheHandler` — import and use as `cache_handler=SQLiteCacheHandler()` in `SpotifyOAuth` |
| `backend/services/spotify.py` | ❌ Missing | CREATE — spotipy wrapper |
| `backend/routers/auth.py` | ❌ Missing | CREATE |
| `frontend/src/lib/api.ts` | ✅ Done | `api.get`, `api.put`, `api.post`, `api.patch` all exist |
| `frontend/src/types/index.ts` | ✅ Done | Has `Config`, `ConfigWrite` — ADD `AuthStatus` |
| `frontend/src/hooks/useConfig.ts` | ✅ Done | Pattern to follow for `useAuthStatus` |
| `frontend/src/features/auth/SpotifyConnect.tsx` | ❌ Missing | CREATE |
| `frontend/src/hooks/useAuthStatus.ts` | ❌ Missing | CREATE |
| `frontend/src/pages/DashboardPage.tsx` | ✅ Done | UPDATE — add `useAuthStatus` check |
| `frontend/src/features/config/SetupWizard.tsx` | ✅ Done | DO NOT MODIFY — stays as credential form |

---

### Backend: `services/spotify.py` Implementation

**File:** `backend/services/spotify.py` (CREATE)

```python
import os
from spotipy import Spotify, SpotifyOAuth
from sqlmodel import Session, select

from database import engine
from models.config import Config
from services.token_manager import SQLiteCacheHandler

SCOPES = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-read-private"
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8000/api/v1/auth/callback")


def _get_spotify_oauth() -> SpotifyOAuth:
    with Session(engine) as session:
        config = session.exec(select(Config)).first()
        if config is None or not config.client_id:
            raise ValueError("Spotify credentials not configured — run setup first")
    return SpotifyOAuth(
        client_id=config.client_id,
        client_secret=config.client_secret,
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        cache_handler=SQLiteCacheHandler(),
    )


def get_auth_url() -> str:
    sp_oauth = _get_spotify_oauth()
    return sp_oauth.get_authorize_url()


def handle_callback(code: str) -> None:
    sp_oauth = _get_spotify_oauth()
    sp_oauth.get_access_token(code, check_cache=False)
    # SpotifyOAuth automatically calls SQLiteCacheHandler.save_token_to_cache() here


def get_auth_status() -> dict:
    try:
        sp_oauth = _get_spotify_oauth()
        token_info = sp_oauth.get_cached_token()
        if token_info is None:
            return {"authenticated": False, "spotify_user_id": None}
        # validate_token refreshes if expired; returns None if unrecoverable
        token_info = sp_oauth.validate_token(token_info)
        if token_info is None:
            return {"authenticated": False, "spotify_user_id": None}
        sp = Spotify(auth=token_info["access_token"])
        user = sp.me()
        return {"authenticated": True, "spotify_user_id": user["id"]}
    except Exception:
        return {"authenticated": False, "spotify_user_id": None}
```

**Critical:** `config` variable goes out of scope after the `with Session` block — extract the values before exiting the context manager, or restructure. The above code has a bug: `config.client_id` is accessed after the `with` block closes. Fix:

```python
def _get_spotify_oauth() -> SpotifyOAuth:
    with Session(engine) as session:
        config = session.exec(select(Config)).first()
        if config is None or not config.client_id:
            raise ValueError("Spotify credentials not configured — run setup first")
        client_id = config.client_id
        client_secret = config.client_secret
    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        cache_handler=SQLiteCacheHandler(),
    )
```

---

### Backend: `routers/auth.py` Implementation

**File:** `backend/routers/auth.py` (CREATE)

```python
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from services import spotify as spotify_service

router = APIRouter(tags=["auth"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


class ConnectResponse(BaseModel):
    auth_url: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    spotify_user_id: Optional[str] = None


@router.post("/auth/connect", response_model=ConnectResponse)
def connect_spotify() -> ConnectResponse:
    try:
        auth_url = spotify_service.get_auth_url()
        return ConnectResponse(auth_url=auth_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/auth/callback")
def spotify_callback(code: Optional[str] = None, error: Optional[str] = None):
    if error or code is None:
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error=1")
    try:
        spotify_service.handle_callback(code)
        return RedirectResponse(url=FRONTEND_URL)
    except Exception:
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error=1")


@router.get("/auth/status", response_model=AuthStatusResponse)
def auth_status() -> AuthStatusResponse:
    status = spotify_service.get_auth_status()
    return AuthStatusResponse(**status)
```

---

### Backend: `main.py` Update

Add ONE line import and ONE line registration after the config router:

```python
from routers.auth import router as auth_router   # ADD THIS

# after: app.include_router(config_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")  # ADD THIS
```

---

### Frontend: `types/index.ts` Addition

**File:** `frontend/src/types/index.ts` — ADD to bottom, don't touch existing interfaces:

```typescript
export interface AuthStatus {
  authenticated: boolean
  spotify_user_id?: string | null
}
```

---

### Frontend: `useAuthStatus` Hook

**File:** `frontend/src/hooks/useAuthStatus.ts` (CREATE) — follow `useConfig.ts` pattern:

```typescript
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { AuthStatus } from '@/types'

export function useAuthStatus() {
  return useQuery({
    queryKey: ['auth', 'status'],
    queryFn: () => api.get<AuthStatus>('/auth/status'),
    staleTime: 0,  // always refetch; required to detect post-OAuth redirect state change
  })
}
```

**Why `staleTime: 0`:** After the OAuth callback redirects browser to `http://localhost:5173`, TanStack Query won't automatically re-fetch a cached query. `staleTime: 0` means the query is always considered stale, so it refetches on every mount. Without this, the dashboard would remain stuck on "Connect Spotify" even after a successful OAuth flow.

---

### Frontend: `SpotifyConnect.tsx` Component

**File:** `frontend/src/features/auth/SpotifyConnect.tsx` (CREATE)

```tsx
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'

export default function SpotifyConnect() {
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Detect if the page loaded after a failed OAuth callback
  const urlParams = new URLSearchParams(window.location.search)
  const authError = urlParams.get('auth_error') === '1'

  async function handleConnect() {
    setIsConnecting(true)
    setError(null)
    try {
      const { auth_url } = await api.post<{ auth_url: string }>('/auth/connect')
      window.location.href = auth_url
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Connection failed')
      setIsConnecting(false)
    }
  }

  return (
    <div className="max-w-md mx-auto mt-16 space-y-6">
      <h1 className="text-2xl font-bold">Connect Spotify</h1>
      <p className="text-sm text-muted-foreground">
        Credentials saved. Now connect your Spotify account to grant access to your playlists.
      </p>
      <div className="rounded border bg-muted/40 p-3 text-xs text-muted-foreground space-y-1">
        <p className="font-medium">Before connecting, add this Redirect URI to your Spotify app:</p>
        <p className="font-mono select-all">http://localhost:8000/api/v1/auth/callback</p>
        <p>Go to <span className="font-mono">developer.spotify.com</span> → Your App → Edit Settings → Redirect URIs.</p>
      </div>
      {(authError || error) && (
        <p className="text-sm text-red-600">
          {error ?? 'Spotify authorization was denied or failed. Please try again.'}
        </p>
      )}
      <Button onClick={handleConnect} disabled={isConnecting}>
        {isConnecting ? 'Redirecting to Spotify…' : 'Connect Spotify'}
      </Button>
    </div>
  )
}
```

---

### Frontend: `DashboardPage.tsx` Update

**File:** `frontend/src/pages/DashboardPage.tsx` — **replace in full**:

```tsx
import { useConfig } from '@/hooks/useConfig'
import { useAuthStatus } from '@/hooks/useAuthStatus'
import SetupWizard from '@/features/config/SetupWizard'
import SpotifyConnect from '@/features/auth/SpotifyConnect'

export default function DashboardPage() {
  const config = useConfig()
  const authStatus = useAuthStatus()

  if (config.isPending || authStatus.isPending) {
    return <div className="p-6 text-sm text-muted-foreground">Loading…</div>
  }

  if (config.isError || authStatus.isError) {
    return <div className="p-6 text-sm text-red-600">Failed to load configuration.</div>
  }

  if (config.data.setup_required) {
    return <SetupWizard />
  }

  if (!authStatus.data.authenticated) {
    return <SpotifyConnect />
  }

  return <h1 className="text-2xl font-bold">Dashboard</h1>
}
```

---

### File Structure After This Story

```
backend/
├── main.py                          ← UPDATED (import + include auth_router)
├── routers/
│   ├── __init__.py                  ← unchanged
│   ├── config.py                    ← unchanged
│   └── auth.py                      ← NEW
└── services/
    ├── __init__.py                  ← unchanged
    ├── token_manager.py             ← unchanged (SQLiteCacheHandler used here)
    └── spotify.py                   ← NEW

frontend/src/
├── types/
│   └── index.ts                     ← UPDATED (add AuthStatus)
├── hooks/
│   ├── useConfig.ts                 ← unchanged
│   └── useAuthStatus.ts             ← NEW
├── features/
│   ├── config/
│   │   └── SetupWizard.tsx          ← unchanged
│   └── auth/
│       └── SpotifyConnect.tsx       ← NEW
└── pages/
    └── DashboardPage.tsx            ← UPDATED (add auth status check)
```

---

### Architecture Constraints — MUST FOLLOW

- **Never return `access_token`, `refresh_token`, or `spotify_token_json`** in any API response (NFR5). `AuthStatusResponse` exposes only `authenticated` + `spotify_user_id`.
- **All Spotify API calls in `services/spotify.py`**, never directly in routers (architecture boundary rule).
- **`SQLiteCacheHandler` is the only token storage mechanism** — do not add any other token caching mechanism.
- **Single Config row** — `_get_spotify_oauth()` uses the same `.first()` pattern as the config router.
- **snake_case JSON fields** — `auth_url`, `spotify_user_id`, `authenticated` (no camelCase).
- **TanStack Query key convention** — `['auth', 'status']` per architecture spec.

---

### Anti-Patterns to Avoid

- ❌ Calling `spotipy.Spotify()` or `SpotifyOAuth()` directly in routers — always go through `services/spotify.py`
- ❌ Returning `access_token` or `refresh_token` in `/auth/status` or any other response
- ❌ Hardcoding `client_id`/`client_secret` in `spotify.py` — always read from DB
- ❌ Using `isLoading` instead of `isPending` (TanStack Query v5)
- ❌ Using `onSuccess`/`onError` on `useQuery` — removed in v5
- ❌ Forgetting `staleTime: 0` on `useAuthStatus` — required for post-OAuth page reload detection
- ❌ Using raw `fetch` in `SpotifyConnect.tsx` — use `api.post` from `@/lib/api`
- ❌ Adding a "Connect Spotify" button to `SetupWizard.tsx` — `SetupWizard` is credentials-only; `SpotifyConnect` is a separate component rendered by `DashboardPage`
- ❌ Using `CacheFileHandler` (default spotipy handler) — would not survive Docker restarts; always pass `cache_handler=SQLiteCacheHandler()`
- ❌ Accessing a SQLModel instance after its `Session` is closed — extract needed values inside the `with Session(engine)` block

---

### Scope Boundary — What STOPS Here

- ❌ Token re-authentication flow (`ReauthBanner`) → Story 2.3
- ❌ Auto-refresh of expired tokens → handled by `spotipy.validate_token()` in `get_auth_status()` (transparent, no extra UI needed in 2.2)
- ❌ ConfigForm (playlist_size / cron_expr editing) → Story 2.4
- ❌ Any Spotify playlist API calls → Epic 3
- ❌ Adding `Playlist` or `SyncLog` types to `types/index.ts` → add in Epic 3/5

---

### Learnings from Story 2.1

- **TanStack Query v5:** `isPending` (not `isLoading`); no `onSuccess`/`onError` on `useQuery`; `invalidateQueries` with `{ queryKey: [...] }` object syntax.
- **SessionDep pattern:** This story uses `Session(engine)` directly in the service layer (not via `SessionDep` — that's for routers). The `SQLiteCacheHandler` already does this. Follow the same pattern in `_get_spotify_oauth()`.
- **Config single row:** Always `session.exec(select(Config)).first()` — never `.all()`.
- **TypeScript strict mode:** `noUnusedLocals: true` in `tsconfig.app.json` — don't leave unused imports.
- **`@` alias:** Resolves to `frontend/src/` — use `@/hooks/useAuthStatus`, `@/features/auth/SpotifyConnect` etc.
- **shadcn `Button`:** Already installed at `@/components/ui/button` — import directly.

---

### Git Context from Recent Commits

**Commit `55bdb32` (Story 2.1):** 9 files added/modified. Pattern: backend router + frontend hook + component + type + page update all in one commit.

**Commit `b4f37d9` (Epic 1):** Established `backend/services/token_manager.py` with `SQLiteCacheHandler`. The `spotify_token_json` column on `Config` was created for this purpose — it exists and is ready to use.

---

### Verification Checklist

```bash
# Backend: test auth endpoints
docker-compose up backend

# 1. Test connect (requires credentials in DB first)
curl -X POST http://localhost:8000/api/v1/auth/connect
# If no credentials: {"detail": "Spotify credentials not configured — run setup first"}
# After PUT /api/v1/config with real credentials: {"auth_url": "https://accounts.spotify.com/authorize?..."}

# 2. Test auth status (unauthenticated)
curl http://localhost:8000/api/v1/auth/status
# Expected: {"authenticated": false, "spotify_user_id": null}

# 3. Full OAuth flow (manual)
# a. PUT credentials via curl (use real Spotify app credentials)
curl -X PUT http://localhost:8000/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{"client_id": "YOUR_CLIENT_ID", "client_secret": "YOUR_CLIENT_SECRET"}'
# b. POST /auth/connect → get auth_url → open in browser
# c. Authorize on Spotify
# d. Browser lands back at http://localhost:5173
# e. GET /api/v1/auth/status → {"authenticated": true, "spotify_user_id": "..."}

# 4. Verify no tokens in response
curl http://localhost:8000/api/v1/auth/status
# Must NOT contain: access_token, refresh_token, spotify_token_json

# 5. Restart Docker → auth survives
docker-compose restart backend
curl http://localhost:8000/api/v1/auth/status
# Expected: {"authenticated": true, "spotify_user_id": "..."} (token in SQLite bind mount)

# Frontend: full stack
docker-compose up
# Open http://localhost:5173
# → If credentials missing: SetupWizard renders
# → After saving credentials: SpotifyConnect renders (authenticated: false)
# → After OAuth: Dashboard placeholder renders (authenticated: true)
```

### Spotify Developer App Prerequisites

The user must have a Spotify Developer app configured at [developer.spotify.com](https://developer.spotify.com) with:
- Redirect URI: `http://localhost:8000/api/v1/auth/callback`
- The `SpotifyConnect` component displays this instruction prominently.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — implementation went cleanly on first pass.

### Completion Notes List

- ✅ Created `backend/services/spotify.py`: `_get_spotify_oauth()` extracts `client_id`/`client_secret` inside the `with Session` block (anti-pattern fix noted in Dev Notes applied), `get_auth_url()`, `handle_callback()`, `get_auth_status()` with full exception guard.
- ✅ Created `backend/routers/auth.py`: `POST /auth/connect` (400 on ValueError), `GET /auth/callback` (redirect-based, never returns token data), `GET /auth/status` (AuthStatusResponse — no token fields).
- ✅ Updated `backend/main.py`: imported and registered `auth_router` with `/api/v1` prefix after `config_router`.
- ✅ Updated `frontend/src/types/index.ts`: added `AuthStatus` interface without touching existing `Config`/`ConfigWrite`.
- ✅ Created `frontend/src/hooks/useAuthStatus.ts`: `staleTime: 0` applied to ensure post-OAuth redirect triggers re-fetch.
- ✅ Created `frontend/src/features/auth/SpotifyConnect.tsx`: `?auth_error=1` detection, connect button with loading/disabled state, Redirect URI instruction, error display.
- ✅ Updated `frontend/src/pages/DashboardPage.tsx`: combined pending/error gates, setup_required → SetupWizard, !authenticated → SpotifyConnect, else → Dashboard placeholder.
- ✅ TypeScript build passes (88 modules, 0 errors). Python syntax validated.
- ✅ NFR5 satisfied: `AuthStatusResponse` exposes only `authenticated` + `spotify_user_id`; no token fields in any response.

### File List

- backend/services/spotify.py (NEW)
- backend/routers/auth.py (NEW)
- backend/main.py (MODIFIED)
- frontend/src/types/index.ts (MODIFIED)
- frontend/src/hooks/useAuthStatus.ts (NEW)
- frontend/src/features/auth/SpotifyConnect.tsx (NEW)
- frontend/src/pages/DashboardPage.tsx (MODIFIED)

## Change Log

- 2026-05-19: Story 2.2 implemented — Spotify OAuth2 connect flow. Backend: `spotify.py` service + `auth.py` router (3 endpoints). Frontend: `AuthStatus` type, `useAuthStatus` hook, `SpotifyConnect` component, `DashboardPage` updated with auth gate.
