# Story 2.3: Token Re-Authentication Flow

Status: review

## Story

As a user,
I want to reconnect Spotify when my token expires or is revoked,
so that I can restore sync functionality without restarting the app.

## Acceptance Criteria

1. **Given** the token is expired or revoked, **When** `GET /api/v1/auth/status` is called, **Then** it returns `{"authenticated": false, "has_previous_auth": true}`.
2. **Given** `authenticated: false` AND `has_previous_auth: true`, **When** the dashboard loads, **Then** `ReauthBanner` is displayed prominently with a "Reconnect Spotify" button.
3. **Given** the `ReauthBanner` is visible, **When** I click "Reconnect Spotify", **Then** the OAuth2 flow restarts (same `POST /api/v1/auth/connect` → redirect flow as Story 2.2).
4. **Given** I complete re-authorization, **When** the callback succeeds and browser returns to `http://localhost:5173`, **Then** `GET /api/v1/auth/status` returns `{"authenticated": true}` and `ReauthBanner` is no longer rendered.
5. **Given** no token has ever been stored (first-time user), **When** `GET /api/v1/auth/status` is called, **Then** it returns `{"authenticated": false, "has_previous_auth": false}` and `SpotifyConnect` is still shown (not `ReauthBanner`).
6. **Given** a valid token that is about to expire, **When** spotipy makes an API call during a sync, **Then** the token is refreshed transparently via `SQLiteCacheHandler` — no user intervention, no `ReauthBanner` shown (FR3 — already handled by `validate_token()` in `get_auth_status()`).

## Tasks / Subtasks

- [x] Task 1: Update `backend/services/spotify.py` — add `has_previous_auth` to `get_auth_status()` (AC: #1, #5, #6)
  - [x] Separate the `_get_spotify_oauth()` call into its own try/except block — `ValueError` (no credentials) returns `has_previous_auth: False` immediately
  - [x] After obtaining `sp_oauth`, call `get_cached_token()` — if `None` → `{"authenticated": False, "has_previous_auth": False, "spotify_user_id": None}`
  - [x] If token exists, call `validate_token()` — if returns `None` (revoked/unrecoverable) → `{"authenticated": False, "has_previous_auth": True, "spotify_user_id": None}`
  - [x] On success → `{"authenticated": True, "has_previous_auth": True, "spotify_user_id": user["id"]}`
  - [x] Inner except block (network errors, Spotify API errors): return `{"authenticated": False, "has_previous_auth": True, "spotify_user_id": None}` — token was stored but network failed; treat as re-auth needed

- [x] Task 2: Update `backend/routers/auth.py` — add `has_previous_auth` to `AuthStatusResponse` (AC: #1, #5)
  - [x] Add `has_previous_auth: bool = False` field to `AuthStatusResponse` Pydantic model
  - [x] No endpoint logic change needed — `AuthStatusResponse(**status)` already unpacks the dict

- [x] Task 3: Update `frontend/src/types/index.ts` — add `has_previous_auth` to `AuthStatus` (AC: #2, #5)
  - [x] Add `has_previous_auth?: boolean` to `AuthStatus` interface
  - [x] Leave `Config`, `ConfigWrite` interfaces unchanged

- [x] Task 4: Create `frontend/src/features/auth/ReauthBanner.tsx` (AC: #2, #3, #4)
  - [x] Prominent banner layout (yellow/warning color scheme using Tailwind)
  - [x] "Reconnect Spotify" button calls `api.post<{ auth_url: string }>('/auth/connect')` then `window.location.href = auth_url` — identical logic to `SpotifyConnect`
  - [x] Loading/disabled state while `post` is in flight
  - [x] Error message on catch

- [x] Task 5: Update `frontend/src/pages/DashboardPage.tsx` — differentiate `ReauthBanner` vs `SpotifyConnect` (AC: #2, #5)
  - [x] Import `ReauthBanner` from `@/features/auth/ReauthBanner`
  - [x] Replace the single `!authStatus.data.authenticated` check with: `has_previous_auth && !authenticated` → `<ReauthBanner />`, `!has_previous_auth && !authenticated` → `<SpotifyConnect />`

- [x] Task 6: Verify all ACs
  - [x] With no token in DB: `GET /api/v1/auth/status` → `{"authenticated": false, "has_previous_auth": false}` → dashboard shows `SpotifyConnect`
  - [x] After full OAuth flow: `GET /api/v1/auth/status` → `{"authenticated": true, "has_previous_auth": true}`
  - [x] Simulate revoked token: manually delete/corrupt `spotify_token_json` in SQLite → `GET /api/v1/auth/status` → `{"authenticated": false, "has_previous_auth": false}` (no token stored)
  - [x] Simulate expired+unrefreshable token: manually set an expired `spotify_token_json` with a bad `refresh_token` → `GET /api/v1/auth/status` → `{"authenticated": false, "has_previous_auth": true}` → `ReauthBanner` shown
  - [x] Click "Reconnect Spotify" on `ReauthBanner` → full OAuth flow → banner dismissed on return

## Dev Notes

### Codebase State After Story 2.2

**What exists — use it, don't recreate:**

| File | State | Notes |
|------|-------|-------|
| `backend/services/spotify.py` | ✅ Exists | MODIFY `get_auth_status()` only — all other functions unchanged |
| `backend/routers/auth.py` | ✅ Exists | MODIFY `AuthStatusResponse` only — all endpoints unchanged |
| `backend/services/token_manager.py` | ✅ Exists | Unchanged — `SQLiteCacheHandler` is still the only token store |
| `backend/models/config.py` | ✅ Exists | Unchanged — `spotify_token_json` column holds token data |
| `frontend/src/types/index.ts` | ✅ Exists | MODIFY `AuthStatus` only — `Config`/`ConfigWrite` unchanged |
| `frontend/src/hooks/useAuthStatus.ts` | ✅ Exists | Unchanged — `staleTime: 0` already handles post-OAuth refetch |
| `frontend/src/features/auth/SpotifyConnect.tsx` | ✅ Exists | Unchanged — still shown for first-time connect |
| `frontend/src/pages/DashboardPage.tsx` | ✅ Exists | MODIFY — add `has_previous_auth` branch |
| `frontend/src/features/auth/ReauthBanner.tsx` | ❌ Missing | CREATE |

---

### Backend: `services/spotify.py` Change

**Only `get_auth_status()` changes.** Replace the current implementation:

```python
def get_auth_status() -> dict:
    try:
        sp_oauth = _get_spotify_oauth()
    except ValueError:
        # No credentials configured — first-run state
        return {"authenticated": False, "has_previous_auth": False, "spotify_user_id": None}

    try:
        token_info = sp_oauth.get_cached_token()
        if token_info is None:
            return {"authenticated": False, "has_previous_auth": False, "spotify_user_id": None}
        token_info = sp_oauth.validate_token(token_info)
        if token_info is None:
            # Token stored but revoked/unrecoverable — re-auth needed
            return {"authenticated": False, "has_previous_auth": True, "spotify_user_id": None}
        sp = Spotify(auth=token_info["access_token"])
        user = sp.me()
        return {"authenticated": True, "has_previous_auth": True, "spotify_user_id": user["id"]}
    except Exception:
        # Network error or Spotify API failure — token likely exists but unreachable
        return {"authenticated": False, "has_previous_auth": True, "spotify_user_id": None}
```

**Why split the try/except:** `ValueError` from `_get_spotify_oauth()` means credentials are missing (pre-setup state) → `has_previous_auth: False`. Any other exception after obtaining `sp_oauth` means token exists but network/API failed → `has_previous_auth: True` (show ReauthBanner, not SpotifyConnect).

---

### Backend: `routers/auth.py` Change

**Only `AuthStatusResponse` changes.** Add one field:

```python
class AuthStatusResponse(BaseModel):
    authenticated: bool
    has_previous_auth: bool = False
    spotify_user_id: Optional[str] = None
```

The `auth_status()` endpoint stays exactly as is — `AuthStatusResponse(**status)` unpacks the dict automatically.

**NFR5 still satisfied:** `has_previous_auth` is a boolean flag, not a token. No token data in any response.

---

### Frontend: `types/index.ts` Change

Add one optional field to `AuthStatus`:

```typescript
export interface AuthStatus {
  authenticated: boolean
  has_previous_auth?: boolean
  spotify_user_id?: string | null
}
```

`has_previous_auth` is optional (`?`) so code compiled against the old type still works — defensive in case of stale cache serving old response shape.

---

### Frontend: `ReauthBanner.tsx` Implementation

**File:** `frontend/src/features/auth/ReauthBanner.tsx` (CREATE)

```tsx
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'

export default function ReauthBanner() {
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleReconnect() {
    setIsConnecting(true)
    setError(null)
    try {
      const { auth_url } = await api.post<{ auth_url: string }>('/auth/connect')
      window.location.href = auth_url
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Reconnection failed')
      setIsConnecting(false)
    }
  }

  return (
    <div className="rounded border border-yellow-300 bg-yellow-50 p-4 flex items-center justify-between gap-4">
      <div>
        <p className="font-medium text-yellow-900">Spotify disconnected</p>
        <p className="text-sm text-yellow-700">
          {error ?? 'Your Spotify session has expired or been revoked. Reconnect to resume syncing.'}
        </p>
      </div>
      <Button variant="outline" onClick={handleReconnect} disabled={isConnecting}>
        {isConnecting ? 'Redirecting…' : 'Reconnect Spotify'}
      </Button>
    </div>
  )
}
```

**Reuses:** same `api.post('/auth/connect')` → `window.location.href` pattern as `SpotifyConnect.tsx`. Do NOT duplicate by calling a new endpoint — the OAuth connect flow is identical for both first-connect and re-auth.

---

### Frontend: `DashboardPage.tsx` Change

**Replace the single `!authStatus.data.authenticated` branch with two branches:**

```tsx
import { useConfig } from '@/hooks/useConfig'
import { useAuthStatus } from '@/hooks/useAuthStatus'
import SetupWizard from '@/features/config/SetupWizard'
import SpotifyConnect from '@/features/auth/SpotifyConnect'
import ReauthBanner from '@/features/auth/ReauthBanner'

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
    return authStatus.data.has_previous_auth ? <ReauthBanner /> : <SpotifyConnect />
  }

  return <h1 className="text-2xl font-bold">Dashboard</h1>
}
```

**Why ternary vs separate if blocks:** Single `!authenticated` gate avoids repeating the check. `has_previous_auth` defaults to `false` (TypeScript optional field + Pydantic default) so the ternary evaluates safely if old API response is cached.

---

### File Structure After This Story

```
backend/
└── services/
    └── spotify.py          ← UPDATED (get_auth_status split try/except + has_previous_auth)

backend/
└── routers/
    └── auth.py             ← UPDATED (AuthStatusResponse + has_previous_auth field)

frontend/src/
├── types/
│   └── index.ts            ← UPDATED (AuthStatus + has_previous_auth?)
├── features/
│   └── auth/
│       ├── SpotifyConnect.tsx  ← UNCHANGED
│       └── ReauthBanner.tsx    ← NEW
└── pages/
    └── DashboardPage.tsx   ← UPDATED (ReauthBanner vs SpotifyConnect branch)
```

---

### Architecture Constraints — MUST FOLLOW

- **No new endpoints.** Re-auth uses the same `POST /api/v1/auth/connect` → OAuth redirect flow. Do NOT add a `/auth/reconnect` endpoint.
- **No token data in responses.** `has_previous_auth` is a boolean flag only. Never add `spotify_token_json` or token fields to any response (NFR5).
- **Business logic stays in `services/spotify.py`**, not in routers — `get_auth_status()` is already there.
- **`useAuthStatus` hook unchanged.** `staleTime: 0` already handles post-OAuth redirect refetch — `ReauthBanner` dismisses automatically when `useAuthStatus` detects `authenticated: true` on refetch.
- **`SpotifyConnect.tsx` unchanged.** It still handles the first-time connect state (`has_previous_auth: false`).

---

### Anti-Patterns to Avoid

- ❌ Creating a new `/auth/reconnect` endpoint — same connect endpoint works for both first-connect and re-auth
- ❌ Storing auth error state in global state / context — `useAuthStatus` with `staleTime: 0` is the source of truth; no extra state needed
- ❌ Using `isLoading` instead of `isPending` in TanStack Query v5
- ❌ Adding `onSuccess`/`onError` to `useQuery` — removed in TanStack Query v5
- ❌ Checking `!authStatus.data?.authenticated` without also checking `has_previous_auth` — this would always show `SpotifyConnect` instead of the correct banner
- ❌ Making `has_previous_auth` a required field in TypeScript — use optional (`?`) for backwards compatibility
- ❌ Duplicating connect logic in `ReauthBanner.tsx` — import pattern from `SpotifyConnect.tsx` but don't import the component itself (different UX layout)
- ❌ Accessing a SQLModel instance after its `Session` is closed (already fixed in 2.2's `_get_spotify_oauth()` — do not change that pattern)

---

### Scope Boundary — What STOPS Here

- ❌ `ConfigForm` (playlist_size / cron_expr editing) → Story 2.4
- ❌ Any Spotify playlist API calls → Epic 3
- ❌ Real-time SSE streaming → Epic 5
- ✅ FR3 (transparent token auto-refresh) is fully covered by `validate_token()` in `get_auth_status()` — no additional work needed

---

### Learnings from Stories 2.1 & 2.2

- **TanStack Query v5:** `isPending` (not `isLoading`); no `onSuccess`/`onError` on `useQuery`
- **`staleTime: 0` on `useAuthStatus`:** Already set — ensures post-OAuth redirect triggers re-fetch, which auto-dismisses `ReauthBanner` without any extra code
- **SQLModel session scope:** Values must be extracted inside `with Session(engine)` block — see `_get_spotify_oauth()` pattern
- **TypeScript strict mode:** `noUnusedLocals: true` — don't leave unused imports in any file
- **`@` alias:** Resolves to `frontend/src/` — use `@/features/auth/ReauthBanner`
- **shadcn `Button`:** Already installed at `@/components/ui/button` — import directly
- **`SpotifyConnect` uses local `useState<boolean>` for loading state** — `ReauthBanner` should follow the same pattern (no global state needed)
- **`REDIRECT_URI` in `spotify.py`:** Was updated to use `127.0.0.1` not `localhost` — do NOT change this

---

### Verification Checklist

```bash
# 1. No token stored — should show SpotifyConnect (not ReauthBanner)
curl http://localhost:8000/api/v1/auth/status
# Expected: {"authenticated": false, "has_previous_auth": false, "spotify_user_id": null}
# Frontend: SpotifyConnect visible

# 2. Simulate revoked/expired-unrefreshable token in SQLite
# (Set spotify_token_json to a JSON with expired access_token and invalid refresh_token)
# Then:
curl http://localhost:8000/api/v1/auth/status
# Expected: {"authenticated": false, "has_previous_auth": true, "spotify_user_id": null}
# Frontend: ReauthBanner visible with "Reconnect Spotify" button

# 3. Click "Reconnect Spotify" → full OAuth flow → browser returns to http://localhost:5173
curl http://localhost:8000/api/v1/auth/status
# Expected: {"authenticated": true, "has_previous_auth": true, "spotify_user_id": "..."}
# Frontend: ReauthBanner dismissed, Dashboard placeholder visible

# 4. No access_token/refresh_token/spotify_token_json in any response
curl http://localhost:8000/api/v1/auth/status | grep -E "access_token|refresh_token|spotify_token_json"
# Expected: no output (NFR5)

# 5. TypeScript build passes
docker-compose exec frontend npm run build
# Expected: 0 errors
```

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Fixed `ModuleNotFoundError` in pytest by adding `[tool.pytest.ini_options] pythonpath = ["."]` to `backend/pyproject.toml` — existing test suite was also affected and now passes correctly.

### Completion Notes List

- ✅ `get_auth_status()` split into two try/except blocks: outer for `ValueError` (no credentials → `has_previous_auth: False`), inner for network/API errors (token exists but unreachable → `has_previous_auth: True`)
- ✅ `AuthStatusResponse` Pydantic model extended with `has_previous_auth: bool = False` — endpoint unchanged, dict unpacking works automatically
- ✅ `AuthStatus` TypeScript interface extended with `has_previous_auth?: boolean` (optional for backwards-compatibility)
- ✅ `ReauthBanner.tsx` created — yellow/warning banner, same OAuth connect pattern as `SpotifyConnect`, local loading/error state
- ✅ `DashboardPage.tsx` updated — single `!authenticated` gate with ternary on `has_previous_auth` to route to `ReauthBanner` or `SpotifyConnect`
- ✅ 9 unit/integration tests added covering all 5 AC branches
- ✅ 19/19 tests pass (including 10 regression tests from story 1.3), 0 TypeScript errors, build successful

### File List

- `backend/services/spotify.py` — updated `get_auth_status()` (split try/except, `has_previous_auth`)
- `backend/routers/auth.py` — updated `AuthStatusResponse` (`has_previous_auth: bool = False`)
- `backend/pyproject.toml` — added `[tool.pytest.ini_options] pythonpath = ["."]`
- `backend/tests/test_story_2_3.py` — new test file (9 tests)
- `frontend/src/types/index.ts` — updated `AuthStatus` interface (`has_previous_auth?: boolean`)
- `frontend/src/features/auth/ReauthBanner.tsx` — new component
- `frontend/src/pages/DashboardPage.tsx` — updated with `ReauthBanner` vs `SpotifyConnect` branch

### Change Log

- 2026-05-19 — Story 2.3 implemented: token re-authentication flow with `has_previous_auth` field, `ReauthBanner` component, and routing logic in `DashboardPage`. 9 tests added. Backend pythonpath configuration fixed as bonus.
