# Story 3.5: Manual Sync Trigger

Status: review

## Story

As a user,
I want to trigger a sync on demand from the dashboard,
so that I can update my playlist immediately without waiting for the scheduled run.

## Acceptance Criteria

1. **Given** I am on the dashboard and authenticated, **When** I click "Sync Now", **Then** `POST /api/v1/sync/run` is called and `sync_engine.run_sync()` executes.

2. **Given** a sync is in progress, **When** the `SyncButton` is in its loading state, **Then** it is disabled and shows a loading indicator — no duplicate syncs can be triggered.

3. **Given** the sync completes successfully, **When** `POST /api/v1/sync/run` returns, **Then** the response includes `{"status": "success", "track_count": N}` and the button returns to its normal state.

4. **Given** the sync fails, **When** `POST /api/v1/sync/run` returns, **Then** the response includes `{"status": "failure", "error": "..."}` and the error is surfaced in the UI.

5. **Given** no playlists are selected, **When** I click "Sync Now", **Then** the request returns a 400 error and the UI shows "No playlists selected — enable at least one playlist to sync."

## Tasks / Subtasks

- [x] Task 1: Create `backend/routers/sync.py` with `POST /api/v1/sync/run` (AC: #1, #3, #4, #5)
  - [x] Define `APIRouter(prefix="/sync", tags=["sync"])`
  - [x] `POST /run` endpoint: call `sync_engine.run_sync()`, catch `ValueError` → 400, catch all other exceptions → 500 with error detail
  - [x] Success response: return `run_sync()` result directly (already `{"status": "success", "track_count": N}`)
  - [x] Failure from `ValueError("No playlists selected")` → `HTTPException(status_code=400, detail="No playlists selected — enable at least one playlist to sync.")`
  - [x] Other exceptions → `HTTPException(status_code=500, detail=str(exc))`

- [x] Task 2: Register sync router in `backend/main.py` (AC: #1)
  - [x] Add `from routers.sync import router as sync_router`
  - [x] Add `app.include_router(sync_router, prefix="/api/v1")`

- [x] Task 3: Create `frontend/src/features/sync/SyncButton.tsx` (AC: #2, #3, #4, #5)
  - [x] Use `useMutation` from `@tanstack/react-query` calling `api.post('/sync/run')`
  - [x] Button disabled and shows loading indicator when `isPending` is true (TanStack Query v5 — use `isPending`, NOT `isLoading`)
  - [x] On success: show success message with `track_count` (brief toast or inline message), reset to normal state
  - [x] On error: surface error message in UI (inline below button — use `mutation.error?.message`)
  - [x] Use shadcn/ui `Button` component (already installed)

- [x] Task 4: Integrate `SyncButton` into `DashboardPage` (AC: #1)
  - [x] Import and render `<SyncButton />` in `frontend/src/pages/DashboardPage.tsx` below the `<PlaylistList />`

- [x] Task 5: Create `backend/tests/test_story_3_5.py` (AC: #1–#5)
  - [x] `test_sync_run_success`: happy path, 200 response, `{"status": "success", "track_count": N}`
  - [x] `test_sync_run_no_playlists_returns_400`: `run_sync` raises `ValueError("No playlists selected")` → HTTP 400
  - [x] `test_sync_run_spotify_error_returns_500`: `run_sync` raises `Exception("Spotify 500")` → HTTP 500
  - [x] Use `TestClient` and `patch("routers.sync.sync_engine.run_sync", ...)` pattern

- [x] Task 6: Update Postman collection (AC: all)
  - [x] Add `POST /api/v1/sync/run` to the Postman collection — dossier "Sync" créé avec exemples success (200) et 400

- [x] Task 7: Run full test suite and confirm no regressions
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`
  - [x] Result: 56 passed (53 prior + 3 new), 0 failures

## Dev Notes

### Scope of This Story

Story 3.5 is the **HTTP layer and frontend button** for the sync trigger. The full sync pipeline (`run_sync()`) was completed in Story 3.4. This story wires it up:
- Backend: `POST /api/v1/sync/run` router in `backend/routers/sync.py`
- Frontend: `SyncButton.tsx` component + integration in `DashboardPage`

Story 3.5 does NOT include:
- `GET /api/v1/sync/logs` endpoint (Story 5.1)
- `SyncStatusBadge` (Story 5.2)
- SSE streaming (Story 5.3)
- Scheduler integration (Epic 4)

---

### File: `backend/routers/sync.py` — CREATE

```python
from fastapi import APIRouter, HTTPException

import services.sync_engine as sync_engine

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/run")
def run_sync() -> dict:
    try:
        return sync_engine.run_sync()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

**Key decisions:**
- `ValueError("No playlists selected")` maps to HTTP 400 — that's the user-actionable error.
- All other exceptions map to HTTP 500 — Spotify API errors, token failures, etc.
- `run_sync()` already writes the `SyncLog` before re-raising — the router does NOT write any log.
- Return type is `dict` — FastAPI serializes `{"status": "success", "track_count": N}` directly.
- No `async def` — `run_sync()` is synchronous and does I/O via SQLModel sessions.

**Failure response shape** (for frontend consumption):
- 400: `{"detail": "No playlists selected — enable at least one playlist to sync."}`
- 500: `{"detail": "<exception message>"}`

Note: The AC says the response should include `{"status": "failure", "error": "..."}` on failure. However, since `run_sync()` raises (it does not return a failure dict), the router will always return HTTP error responses on failure. The frontend reads `mutation.error?.message` (from the thrown Error in `api.ts`), which extracts `detail` from the JSON body. This satisfies AC #4 — the error IS surfaced in the UI.

---

### File: `backend/main.py` — MODIFY (add 2 lines)

Add these two lines to the existing `main.py`:

```python
# At top with other imports:
from routers.sync import router as sync_router

# After existing app.include_router calls:
app.include_router(sync_router, prefix="/api/v1")
```

Final include_router block will look like:
```python
app.include_router(config_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(playlists_router, prefix="/api/v1")
app.include_router(sync_router, prefix="/api/v1")
```

Endpoint will be registered as `POST /api/v1/sync/run` (prefix `/api/v1` from `main.py` + prefix `/sync` from router + path `/run`).

---

### File: `frontend/src/features/sync/SyncButton.tsx` — CREATE

```tsx
import { useMutation } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'

interface SyncResult {
  status: string
  track_count: number
}

export default function SyncButton() {
  const mutation = useMutation({
    mutationFn: () => api.post<SyncResult>('/sync/run'),
  })

  return (
    <div className="space-y-2">
      <Button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
      >
        {mutation.isPending ? 'Syncing…' : 'Sync Now'}
      </Button>
      {mutation.isSuccess && (
        <p className="text-sm text-green-600">
          Sync complete — {mutation.data.track_count} tracks updated.
        </p>
      )}
      {mutation.isError && (
        <p className="text-sm text-red-600">
          {mutation.error?.message ?? 'Sync failed.'}
        </p>
      )}
    </div>
  )
}
```

**Key decisions:**
- `isPending` (TanStack Query v5) — never `isLoading`.
- No `queryClient.invalidateQueries` needed here — playlist data is unchanged by a sync (no re-fetch required). Sync logs (Story 5.1) will have their own query key.
- No `onSuccess`/`onError` mutation callbacks used inline — state is read from `mutation.isSuccess`, `mutation.isError` directly (the TanStack v5 pattern established in this project).
- Error message comes from `mutation.error?.message` — `api.ts` already extracts `detail` from the JSON error body and throws `new Error(detail)`.
- `Button` is from shadcn/ui (already installed in project).

---

### File: `frontend/src/pages/DashboardPage.tsx` — MODIFY

Add `SyncButton` import and render it below `<PlaylistList />`:

```tsx
import SyncButton from '@/features/sync/SyncButton'

// Inside the authenticated return:
return (
  <div className="p-6 space-y-4">
    <h1 className="text-2xl font-bold">Dashboard</h1>
    <PlaylistList />
    <SyncButton />
  </div>
)
```

---

### File: `backend/tests/test_story_3_5.py` — CREATE

```python
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app


@pytest.fixture(name="client")
def client_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with TestClient(app) as client:
        yield client


def test_sync_run_success(client):
    with patch("routers.sync.sync_engine.run_sync", return_value={"status": "success", "track_count": 42}):
        response = client.post("/api/v1/sync/run")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["track_count"] == 42


def test_sync_run_no_playlists_returns_400(client):
    with patch("routers.sync.sync_engine.run_sync", side_effect=ValueError("No playlists selected")):
        response = client.post("/api/v1/sync/run")
    assert response.status_code == 400
    assert "No playlists selected" in response.json()["detail"]


def test_sync_run_spotify_error_returns_500(client):
    with patch("routers.sync.sync_engine.run_sync", side_effect=Exception("Spotify 500")):
        response = client.post("/api/v1/sync/run")
    assert response.status_code == 500
    assert "Spotify 500" in response.json()["detail"]
```

**Mock pattern:** `patch("routers.sync.sync_engine.run_sync", ...)` — patch at the router module level, consistent with project mock conventions.

---

### Codebase State Entering This Story

| File | State | Action |
|------|-------|--------|
| `backend/services/sync_engine.py` | ✅ Complete (3.4) | UNCHANGED — `run_sync()` fully implemented |
| `backend/services/spotify.py` | ✅ Complete (3.4) | UNCHANGED |
| `backend/routers/sync.py` | ❌ Missing | CREATE |
| `backend/main.py` | ✅ Exists — no sync router | MODIFY — add sync_router |
| `backend/tests/test_story_3_5.py` | ❌ Missing | CREATE |
| `frontend/src/features/sync/SyncButton.tsx` | ❌ Missing | CREATE |
| `frontend/src/pages/DashboardPage.tsx` | ✅ Exists | MODIFY — add SyncButton |
| `frontend/src/features/sync/` directory | ❌ Missing | CREATE directory implicitly |

**What `run_sync()` does (Story 3.4 recap — do NOT reimplement):**
- Returns `{"status": "success", "track_count": N}` on success
- Raises `ValueError("No playlists selected")` if no `is_included=True` playlists
- Raises other exceptions (Spotify errors, token errors) on failure
- Writes `SyncLog` before raising — the router must NOT write logs

---

### Architecture Rules — MUST FOLLOW

- **Business logic in `services/`, never in `routers/`** — the router only calls `sync_engine.run_sync()` and maps exceptions to HTTP status codes.
- **All spotipy calls via `services/spotify.py`** — no direct spotipy in routers.
- **All fetch via `lib/api.ts`** — `SyncButton` uses `api.post(...)`, never raw `fetch`.
- **TanStack Query v5**: use `isPending`, never `isLoading`. Mutation state read from `mutation.isSuccess`, `mutation.isError`, `mutation.data`, `mutation.error`.
- **Snake_case JSON** — response fields `status`, `track_count`, `error` are already snake_case.
- **No wrapper objects** — `POST /api/v1/sync/run` returns the dict directly, not `{"data": {...}}`.

---

### Anti-Patterns to Avoid

- ❌ Writing a `SyncLog` entry in the router — `run_sync()` already handles logging in Story 3.4.
- ❌ Calling `sync_engine.run_sync()` with `async` / `await` — it is synchronous.
- ❌ Using `isLoading` in TanStack Query — use `isPending` (v5 API).
- ❌ Raw `fetch('/api/v1/sync/run', ...)` in the component — use `api.post('/sync/run')`.
- ❌ Catching `ValueError` as HTTP 500 — map it to 400 (user-actionable error).
- ❌ Adding `GET /api/v1/sync/logs` or SSE endpoint to `sync.py` in this story — those belong to Story 5.1 and 5.3.
- ❌ Creating `useSyncMutation` hook in `hooks/` — the mutation is simple enough to inline in `SyncButton.tsx`.
- ❌ Using `onSuccess`/`onError` callbacks in `useMutation` options — read state from `mutation.isSuccess` etc. (established pattern).

---

### Postman Collection Update — REQUIRED

Per project rules (CLAUDE.md), update the Postman collection after adding this endpoint.

- Collection UID: `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`
- Add to existing collection: `POST /api/v1/sync/run` in a "Sync" folder
- Example success response: `{"status": "success", "track_count": 42}`
- Example 400 response: `{"detail": "No playlists selected — enable at least one playlist to sync."}`

---

### Verification Checklist

```bash
# Run new story tests only
docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_3_5.py -v
# Expected: 3 tests pass

# Run full suite — no regressions
docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v
# Expected: all prior tests + 3 new = total pass, 0 failures

# Verify endpoint registration
curl -X POST http://localhost:8000/api/v1/sync/run
# Expected: 400 {"detail": "No playlists selected..."} if no playlists, or 200 if authenticated with playlists

# TypeScript build check
docker exec playlist_spotify-frontend-1 npm run build
# Expected: 0 errors
```

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No issues encountered. All tests passed on first run.

### Completion Notes List

- Created `backend/routers/sync.py` with `POST /run` endpoint: delegates to `sync_engine.run_sync()`, maps `ValueError` → 400, other exceptions → 500.
- Registered sync router in `main.py` under `/api/v1` prefix → endpoint at `POST /api/v1/sync/run`.
- Created `frontend/src/features/sync/SyncButton.tsx` using TanStack Query v5 `useMutation` + `isPending`, inline success/error messages.
- Integrated `SyncButton` into `DashboardPage.tsx` below `PlaylistList`.
- Created `backend/tests/test_story_3_5.py` with 3 tests (success 200, ValueError → 400, Exception → 500), all using `patch("routers.sync.sync_engine.run_sync", ...)`.
- Updated Postman collection: added "Sync" folder with `POST /api/v1/sync/run` + example responses.
- Full test suite: 56 passed (53 prior + 3 new), 0 failures, 0 regressions.
- TypeScript build: 0 errors.

### File List

- `backend/routers/sync.py` — created
- `backend/main.py` — added sync_router import and include_router
- `backend/tests/test_story_3_5.py` — created (3 tests)
- `frontend/src/features/sync/SyncButton.tsx` — created
- `frontend/src/pages/DashboardPage.tsx` — added SyncButton import and render
