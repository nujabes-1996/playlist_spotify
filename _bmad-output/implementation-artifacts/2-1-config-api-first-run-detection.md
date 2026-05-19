# Story 2.1: Config API & First-Run Detection

Status: review

## Change Log

- 2026-05-19: Story created — Config API & First-Run Detection ready for implementation.
- 2026-05-19: Story implemented — all 8 tasks complete; GET/PUT /api/v1/config operational; frontend SetupWizard + conditional DashboardPage live; all ACs verified.

## Story

As a user,
I want the app to detect when Spotify credentials are missing and display the setup screen,
so that I know exactly what to do the first time I open the app.

## Acceptance Criteria

1. **Given** no credentials are stored in the DB, **When** `GET /api/v1/config` is called, **Then** the response includes `"setup_required": true`.
2. **Given** credentials exist in the DB, **When** `GET /api/v1/config` is called, **Then** the response includes `"setup_required": false` along with `playlist_size` and `cron_expr`.
3. **Given** a `PUT /api/v1/config` request with `{client_id, client_secret, playlist_size, cron_expr}`, **When** the request is made, **Then** the config is persisted in the `config` table and a 200 response is returned.
4. **Given** `setup_required` is `true`, **When** the frontend loads `/`, **Then** `SetupWizard` is rendered instead of the normal dashboard.
5. **Given** `setup_required` is `false`, **When** the frontend loads `/`, **Then** the normal dashboard renders (placeholder content is fine for now).

## Tasks / Subtasks

- [x] Task 1: Create `backend/routers/config.py` — Config router (AC: #1, #2, #3)
  - [x] Define Pydantic response model `ConfigRead` with `setup_required: bool`, `playlist_size: int`, `cron_expr: Optional[str]` (never expose `client_id`, `client_secret`, or `spotify_token_json`)
  - [x] Define Pydantic request model `ConfigWrite` with `client_id: str`, `client_secret: str`, `playlist_size: Optional[int] = 50`, `cron_expr: Optional[str] = None`
  - [x] Implement `GET /api/v1/config` — fetch single Config row, return `setup_required=True` if row missing or `client_id` is None/empty
  - [x] Implement `PUT /api/v1/config` — upsert Config row (create if missing, update if exists), return 200 with `ConfigRead`
  - [x] Use `SessionDep` from `dependencies.py` for all DB access

- [x] Task 2: Register router in `backend/main.py` (AC: #1, #2, #3)
  - [x] Import router from `routers.config`
  - [x] `app.include_router(config_router, prefix="/api/v1")`

- [x] Task 3: Create `frontend/src/lib/api.ts` — shared fetch wrapper (AC: #4, #5)
  - [x] Generic `apiFetch<T>` targeting `/api/v1{path}` (relative — Vite proxy handles routing to backend)
  - [x] `Content-Type: application/json` header by default
  - [x] On non-2xx: parse `{detail}` from JSON body and throw `Error(detail)`
  - [x] Export `api` object with `get`, `put`, `post`, `patch` methods

- [x] Task 4: Create `frontend/src/types/index.ts` — shared TypeScript interfaces (AC: #4, #5)
  - [x] `Config` interface: `{ setup_required: boolean; playlist_size: number; cron_expr: string | null }`
  - [x] `ConfigWrite` interface: `{ client_id: string; client_secret: string; playlist_size?: number; cron_expr?: string | null }`

- [x] Task 5: Create `frontend/src/hooks/useConfig.ts` — TanStack Query hook (AC: #4, #5)
  - [x] `useConfig()` — `useQuery({ queryKey: ['config'], queryFn: () => api.get<Config>('/config') })`
  - [x] `useUpdateConfig()` — `useMutation` calling `api.put('/config', payload)` + `queryClient.invalidateQueries({ queryKey: ['config'] })` on success

- [x] Task 6: Create `frontend/src/features/config/SetupWizard.tsx` (AC: #4)
  - [x] Form with `client_id` and `client_secret` text inputs (password type for secret)
  - [x] Submit calls `useUpdateConfig()` mutation with `{ client_id, client_secret }`
  - [x] Show loading state during mutation (`isPending`)
  - [x] Show error message on failure
  - [x] On success: query invalidation triggers automatic re-render of dashboard (no manual navigation needed)
  - [x] Use shadcn `Button` and `Input` components (see Dev Notes for adding Input)

- [x] Task 7: Update `frontend/src/pages/DashboardPage.tsx` — conditional render (AC: #4, #5)
  - [x] Import and call `useConfig()`
  - [x] If `isPending`: show loading skeleton or spinner (not blank)
  - [x] If `data.setup_required === true`: render `<SetupWizard />`
  - [x] If `data.setup_required === false`: render normal placeholder content (e.g., `<h1>Dashboard</h1>`)
  - [x] If `isError`: surface error message

- [x] Task 8: Verify all ACs
  - [x] `docker-compose up` — backend starts, `GET /api/v1/config` returns `{setup_required: true}` on fresh DB
  - [x] `PUT /api/v1/config` with valid payload → 200 + subsequent GET returns `{setup_required: false, ...}`
  - [x] Open http://localhost:5173 → `SetupWizard` renders (fresh DB)
  - [x] Submit form → dashboard placeholder renders
  - [x] Restart Docker → config survives (persisted in SQLite bind mount)
  - [x] No `client_id`, `client_secret`, or `spotify_token_json` in any API response body

## Dev Notes

### Codebase State After Epic 1

**What exists — use it, don't recreate:**

| File | State | Notes |
|------|-------|-------|
| `backend/models/config.py` | ✅ Done | `Config` SQLModel with `id, client_id, client_secret, playlist_size, cron_expr, spotify_token_json` |
| `backend/database.py` | ✅ Done | `engine` + `get_session()` generator |
| `backend/dependencies.py` | ✅ Done | `SessionDep = Annotated[Session, Depends(get_session)]` |
| `backend/main.py` | ✅ Done | FastAPI app, lifespan, CORS — **needs router registration added** |
| `backend/services/token_manager.py` | ✅ Done | `SQLiteCacheHandler` — NOT needed in this story |
| `backend/scheduler.py` | ✅ Done | APScheduler with SQLAlchemyJobStore — NOT touched in this story |
| `backend/routers/` | ⚠️ Empty | Only `__init__.py` — create `config.py` here |
| `frontend/src/App.tsx` | ✅ Done | Routes: `/` → `DashboardPage`, `/config` → `ConfigPage`, `/logs` → `LogsPage` |
| `frontend/src/main.tsx` | ✅ Done | `QueryClient` + `QueryClientProvider` wrapping `App` |
| `frontend/src/lib/utils.ts` | ✅ Done | `cn()` helper — do NOT touch |
| `frontend/src/components/ui/button.tsx` | ✅ Done | shadcn Button |
| `frontend/src/pages/DashboardPage.tsx` | ⚠️ Placeholder | Replace with conditional render logic |
| `frontend/src/lib/api.ts` | ❌ Missing | CREATE in this story — first API call |
| `frontend/src/types/index.ts` | ❌ Missing | CREATE in this story |
| `frontend/src/hooks/useConfig.ts` | ❌ Missing | CREATE in this story |
| `frontend/src/features/config/SetupWizard.tsx` | ❌ Missing | CREATE in this story |

**Vite config:** `@` alias is configured → `@/lib/api`, `@/types`, `@/hooks/useConfig`, `@/features/config/SetupWizard` all work.

---

### Backend: Config Router Implementation

**File:** `backend/routers/config.py`

The `Config` table holds a single row. Always use `.first()` — never `.all()`.

```python
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import select

from dependencies import SessionDep
from models.config import Config

router = APIRouter(tags=["config"])


class ConfigRead(BaseModel):
    setup_required: bool
    playlist_size: int
    cron_expr: Optional[str]


class ConfigWrite(BaseModel):
    client_id: str
    client_secret: str
    playlist_size: Optional[int] = 50
    cron_expr: Optional[str] = None


@router.get("/config", response_model=ConfigRead)
def get_config(session: SessionDep) -> ConfigRead:
    config = session.exec(select(Config)).first()
    if config is None or not config.client_id:
        return ConfigRead(setup_required=True, playlist_size=50, cron_expr=None)
    return ConfigRead(
        setup_required=False,
        playlist_size=config.playlist_size,
        cron_expr=config.cron_expr,
    )


@router.put("/config", response_model=ConfigRead)
def update_config(payload: ConfigWrite, session: SessionDep) -> ConfigRead:
    config = session.exec(select(Config)).first()
    if config is None:
        config = Config()
        session.add(config)
    config.client_id = payload.client_id
    config.client_secret = payload.client_secret
    config.playlist_size = payload.playlist_size if payload.playlist_size is not None else 50
    config.cron_expr = payload.cron_expr
    session.commit()
    session.refresh(config)
    return ConfigRead(
        setup_required=not bool(config.client_id),
        playlist_size=config.playlist_size,
        cron_expr=config.cron_expr,
    )
```

**Register in `backend/main.py`** — add after existing imports and before `@app.get("/health")`:

```python
from routers.config import router as config_router

# inside the app setup block (after middleware):
app.include_router(config_router, prefix="/api/v1")
```

**Critical — never expose these fields in any response:**
- `client_id`, `client_secret` (NFR6: credentials stored in SQLite, never returned to browser)
- `spotify_token_json` (NFR5: tokens server-side only)

---

### Frontend: `api.ts` Fetch Wrapper

**File:** `frontend/src/lib/api.ts`

All TanStack Query hooks must import from here — never use raw `fetch` in components.

```typescript
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error((error as { detail?: string }).detail ?? res.statusText)
  }
  return res.json() as Promise<T>
}

export const api = {
  get: <T>(path: string) => apiFetch<T>(path),
  put: <T>(path: string, body: unknown) =>
    apiFetch<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  post: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: 'POST', body: body != null ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body: unknown) =>
    apiFetch<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
}
```

**Vite proxy note:** `/api/v1/config` → proxied to `http://backend:8000/api/v1/config` — no base URL needed in the fetch call.

---

### Frontend: Types

**File:** `frontend/src/types/index.ts`

```typescript
export interface Config {
  setup_required: boolean
  playlist_size: number
  cron_expr: string | null
}

export interface ConfigWrite {
  client_id: string
  client_secret: string
  playlist_size?: number
  cron_expr?: string | null
}
```

---

### Frontend: `useConfig` Hook

**File:** `frontend/src/hooks/useConfig.ts`

TanStack Query v5 key differences from v4:
- `isPending` replaces `isLoading` as the primary pending state for queries
- `onSuccess`/`onError` callbacks on `useQuery` are **removed** — use `useEffect` or mutation callbacks
- `cacheTime` renamed to `gcTime`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Config, ConfigWrite } from '@/types'

export function useConfig() {
  return useQuery({
    queryKey: ['config'],
    queryFn: () => api.get<Config>('/config'),
  })
}

export function useUpdateConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: ConfigWrite) => api.put<Config>('/config', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] })
    },
  })
}
```

---

### Frontend: `SetupWizard` Component

**File:** `frontend/src/features/config/SetupWizard.tsx`

This story's scope: credential entry form only. The "Connect Spotify" OAuth button is Story 2.2.

```tsx
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useUpdateConfig } from '@/hooks/useConfig'

export default function SetupWizard() {
  const [clientId, setClientId] = useState('')
  const [clientSecret, setClientSecret] = useState('')
  const { mutate, isPending, error } = useUpdateConfig()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    mutate({ client_id: clientId, client_secret: clientSecret })
  }

  return (
    <div className="max-w-md mx-auto mt-16 space-y-6">
      <h1 className="text-2xl font-bold">Spotify Setup</h1>
      <p className="text-sm text-muted-foreground">
        Enter your Spotify app credentials to get started. Create an app at{' '}
        <span className="font-mono">developer.spotify.com</span>.
      </p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1">
          <label htmlFor="client-id" className="text-sm font-medium">Client ID</label>
          <input
            id="client-id"
            type="text"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            required
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="client-secret" className="text-sm font-medium">Client Secret</label>
          <input
            id="client-secret"
            type="password"
            value={clientSecret}
            onChange={(e) => setClientSecret(e.target.value)}
            required
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        {error && (
          <p className="text-sm text-red-600">{error.message}</p>
        )}
        <Button type="submit" disabled={isPending || !clientId || !clientSecret}>
          {isPending ? 'Saving…' : 'Save Credentials'}
        </Button>
      </form>
    </div>
  )
}
```

**shadcn `Input` component:** You can optionally add it with `npx shadcn@latest add input --yes` and replace the plain `<input>` elements above. Either approach passes the ACs.

---

### Frontend: Updated `DashboardPage.tsx`

**File:** `frontend/src/pages/DashboardPage.tsx` — **replace the existing placeholder**

```tsx
import { useConfig } from '@/hooks/useConfig'
import SetupWizard from '@/features/config/SetupWizard'

export default function DashboardPage() {
  const { data, isPending, isError } = useConfig()

  if (isPending) {
    return <div className="p-6 text-sm text-muted-foreground">Loading…</div>
  }

  if (isError) {
    return <div className="p-6 text-sm text-red-600">Failed to load configuration.</div>
  }

  if (data.setup_required) {
    return <SetupWizard />
  }

  return <h1 className="text-2xl font-bold">Dashboard</h1>
}
```

---

### File Structure After This Story

```
backend/
├── main.py              ← UPDATED (import + include config_router)
└── routers/
    ├── __init__.py      ← unchanged
    └── config.py        ← NEW

frontend/src/
├── types/
│   └── index.ts         ← NEW
├── lib/
│   ├── utils.ts         ← unchanged
│   └── api.ts           ← NEW
├── hooks/
│   └── useConfig.ts     ← NEW
├── features/
│   └── config/
│       └── SetupWizard.tsx  ← NEW
└── pages/
    └── DashboardPage.tsx    ← UPDATED
```

---

### Architecture Constraints — MUST FOLLOW

- **Never return** `client_id`, `client_secret`, or `spotify_token_json` in API responses (NFR5, NFR6)
- **snake_case JSON fields** throughout — no camelCase at API boundary (e.g., `setup_required`, `playlist_size`, `cron_expr`)
- **Business logic in services/**, not routers — this story's logic is simple enough to stay in the router (no separate service needed)
- **No raw `fetch` in components** — always via `@/lib/api`
- **TanStack Query key:** `['config']` — matches the key convention defined in architecture
- **Single Config row** — always use `.first()`, never `.all()`, never create more than one row
- **SessionDep** from `dependencies.py` — the only way to get a DB session in routers

---

### Anti-Patterns to Avoid

- ❌ Returning `client_id` or `client_secret` in `GET /api/v1/config` response
- ❌ Storing credentials in `.env` or source code
- ❌ Creating a separate `config_service.py` — the logic is minimal, keep it in the router
- ❌ Using `isLoading` in TanStack Query v5 — use `isPending` instead
- ❌ Using `onSuccess`/`onError` callbacks on `useQuery` — removed in v5
- ❌ Using `cacheTime` — renamed to `gcTime` in v5
- ❌ Using raw `fetch` directly in `DashboardPage` or `SetupWizard`
- ❌ Adding `setup_required` check to any route other than `DashboardPage` — Config and Logs pages don't need it
- ❌ Navigating to a different route on setup completion — query invalidation triggers re-render at `/` automatically

---

### Scope Boundary — What STOPS Here

- ❌ OAuth connect flow (`POST /api/v1/auth/connect`) → Story 2.2
- ❌ "Connect Spotify" button in SetupWizard → Story 2.2
- ❌ Token status check (`GET /api/v1/auth/status`) → Story 2.2
- ❌ ReauthBanner → Story 2.3
- ❌ ConfigForm (playlist_size / cron_expr editing) → Story 2.4
- ❌ `lib/api.ts` POST/PATCH methods wired to UI → leave them for future stories
- ❌ `types/index.ts` Playlist / SyncLog interfaces → add in Epic 3/5

---

### Learnings from Epic 1 Stories

**From Story 1.3 — SQLiteCacheHandler + Config table:**
- `Config` table may have 0 rows on a fresh DB — always handle `None` from `.first()` gracefully
- `session.exec(select(Config)).first()` is the established pattern for single-row access
- The `spotify_token_json` field stores serialized OAuth token JSON — never touch it in this story

**From Story 1.4 — Frontend setup:**
- `@` alias resolves to `frontend/src/` — confirmed in `vite.config.ts` + `tsconfig.app.json`
- `noUnusedLocals: true` is set in `tsconfig.app.json` — TypeScript will error on unused imports; clean up any you don't use
- `ignoreDeprecations: "6.0"` is set — don't worry about TS 6.0 deprecation warnings on `baseUrl`

**From Story 1.2 — SQLModel session pattern:**
- `Session.commit()` + `Session.refresh(config)` after mutation ensures the returned object has DB-generated values (e.g., auto-assigned `id`)
- `SQLModel.metadata.create_all()` in lifespan already handles schema — no migration needed

---

### Verification Checklist

```bash
# Backend: run with Docker
docker-compose up backend

# Test GET (fresh DB — should show setup_required: true)
curl http://localhost:8000/api/v1/config
# Expected: {"setup_required": true, "playlist_size": 50, "cron_expr": null}

# Test PUT
curl -X PUT http://localhost:8000/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{"client_id": "abc123", "client_secret": "secret456"}'
# Expected: {"setup_required": false, "playlist_size": 50, "cron_expr": null}

# Test GET after PUT
curl http://localhost:8000/api/v1/config
# Expected: {"setup_required": false, "playlist_size": 50, "cron_expr": null}

# Frontend: full stack
docker-compose up
# Open http://localhost:5173
# → SetupWizard should render (fresh DB)
# → Fill in client_id + client_secret → click Save
# → Dashboard placeholder should render (setup_required now false)
# → Restart Docker → navigate to / → still shows Dashboard (not SetupWizard)
# → Backend API response: confirm NO client_id/client_secret in body
```

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — implementation was straightforward, no blockers.

### Completion Notes List

- Created `backend/routers/config.py` with `ConfigRead` / `ConfigWrite` Pydantic models; GET returns `setup_required=true` when no row or empty `client_id`; PUT upserts single Config row using `session.exec(select(Config)).first()` pattern; neither endpoint exposes `client_id`, `client_secret`, or `spotify_token_json`.
- Registered config router in `backend/main.py` with prefix `/api/v1`.
- Created `frontend/src/lib/api.ts` generic fetch wrapper with `get/put/post/patch` methods; non-2xx throws `Error(detail)` from JSON body.
- Created `frontend/src/types/index.ts` with `Config` and `ConfigWrite` interfaces.
- Created `frontend/src/hooks/useConfig.ts` with `useConfig()` (TanStack Query v5 `useQuery`) and `useUpdateConfig()` (`useMutation` + `invalidateQueries` on success).
- Created `frontend/src/features/config/SetupWizard.tsx` — credential form using native `<input>` elements + shadcn `Button`; on success query invalidation auto-re-renders DashboardPage without navigation.
- Updated `frontend/src/pages/DashboardPage.tsx` — conditional render: loading → error → SetupWizard → Dashboard placeholder.
- All backend ACs verified via `curl`; frontend build passes TypeScript compile (Node 22).
- Config persists across Docker restart (SQLite bind mount at `data/app.db`).

### File List

- `backend/routers/config.py` — NEW
- `backend/main.py` — MODIFIED (import + include config_router)
- `frontend/src/lib/api.ts` — NEW
- `frontend/src/types/index.ts` — NEW
- `frontend/src/hooks/useConfig.ts` — NEW
- `frontend/src/features/config/SetupWizard.tsx` — NEW
- `frontend/src/pages/DashboardPage.tsx` — MODIFIED (conditional render with useConfig)
