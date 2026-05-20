# Story 5.2: Sync Failure Indicator

Status: review

## Story

As a user,
I want a visible failure badge on the dashboard when the last sync failed,
So that I immediately know something needs my attention without navigating to the logs.

## Acceptance Criteria

1. **Given** the last `SyncLog` entry has `status="failure"`, **When** the dashboard loads, **Then** `SyncStatusBadge` is visible with a red failure indicator and the error cause (FR23).

2. **Given** the last `SyncLog` entry has `status="success"`, **When** the dashboard loads, **Then** `SyncStatusBadge` shows a green success indicator with the last sync timestamp.

3. **Given** no syncs have run yet, **When** the dashboard loads, **Then** `SyncStatusBadge` shows a neutral state (e.g., "Never synced").

4. **Given** I trigger a manual sync that succeeds after a previous failure, **When** the sync completes, **Then** `SyncStatusBadge` updates to green — the failure state is cleared.

## Tasks / Subtasks

- [x] Task 1: Add `GET /api/v1/sync/status` endpoint to `backend/routers/sync.py` (AC: #1, #2, #3)
  - [x] Query the last `SyncLog` entry ordered by `timestamp` descending, return only the first (or `null` if none)
  - [x] Return the full `SyncLog` object or `null` — no wrapper
  - [x] No business logic in router — simple DB query stays in router

- [x] Task 2: Add `SyncStatus` type alias to `frontend/src/types/index.ts` (AC: #1, #2, #3)
  - [x] `SyncStatus` = `SyncLog | null` (reuses existing `SyncLog` interface — do NOT create a new interface)

- [x] Task 3: Create `frontend/src/hooks/useSyncStatus.ts` (AC: #1, #2, #3)
  - [x] TanStack Query hook with `queryKey: ['sync', 'status']`
  - [x] `queryFn: () => api.get<SyncLog | null>('/sync/status')`

- [x] Task 4: Create `frontend/src/features/sync/SyncStatusBadge.tsx` (AC: #1, #2, #3, #4)
  - [x] Call `useSyncStatus()` hook
  - [x] `isPending` → show nothing (or skeleton)
  - [x] `data === null` → neutral grey badge: "Never synced"
  - [x] `data.status === "success"` → green badge with formatted timestamp
  - [x] `data.status === "failure"` → red badge with error cause (`data.error_message`)

- [x] Task 5: Update `frontend/src/pages/DashboardPage.tsx` to render `<SyncStatusBadge />` (AC: #1, #2, #3, #4)
  - [x] Import and add `<SyncStatusBadge />` below `<h1>Dashboard</h1>`, above `<PlaylistList />`
  - [x] Do NOT change any existing component logic

- [x] Task 6: Create `backend/tests/test_story_5_2.py` (AC: #1, #2, #3)
  - [x] Use same session + client fixture pattern as `test_story_5_1.py` (StaticPool + dependency_overrides)
  - [x] `test_get_status_no_syncs_returns_null`: no logs in DB → `null`
  - [x] `test_get_status_after_success`: seed a success log → returns the entry with `status="success"`
  - [x] `test_get_status_after_failure`: seed a failure log → returns the entry with error_message populated
  - [x] `test_get_status_returns_most_recent`: seed two logs → returns the one with the later timestamp

- [x] Task 7: Run test suite (no regressions)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_5_2.py -v` — 4 tests passed
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` — 80 passed, 0 regressions

- [x] Task 8: Update Postman collection
  - [x] Fetch current collection (`GET https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`)
  - [x] Add `GET /api/v1/sync/status` in the "Sync" folder with description and example responses (null + success + failure)
  - [x] Push updated collection

## Dev Notes

### What This Story Adds

Story 5.2 adds a single new REST endpoint (`GET /api/v1/sync/status`) and a new frontend badge component. No scheduler changes, no streaming — purely a status read from the `sync_log` table.

**Backend delta:** One new GET route in `routers/sync.py`. The `SyncLog` model already exists from Story 3.4 — do NOT recreate it.

**Frontend delta:** One new type alias, one new hook, one new component, minimal update to `DashboardPage.tsx`.

Story 5.3 (SSE streaming) builds on top of this — `SyncStatusBadge` will auto-refresh its data when 5.3 invalidates the `['sync', 'status']` query.

---

### Files to Touch

| File | Action | Notes |
|------|--------|-------|
| `backend/routers/sync.py` | MODIFY | Add `GET /status` route |
| `backend/tests/test_story_5_2.py` | CREATE | 4 tests |
| `frontend/src/types/index.ts` | MODIFY | Add `SyncStatus` type alias |
| `frontend/src/hooks/useSyncStatus.ts` | CREATE | TanStack Query hook |
| `frontend/src/features/sync/SyncStatusBadge.tsx` | CREATE | Badge component |
| `frontend/src/pages/DashboardPage.tsx` | MODIFY | Add `<SyncStatusBadge />` |

**Do NOT touch:** `backend/models/sync_log.py`, `backend/services/sync_engine.py`, `backend/scheduler.py`, `SyncLogPanel.tsx`, `SyncButton.tsx`.

---

### Implementation: `routers/sync.py`

Current state: has `GET /logs` (added in 5.1) and `POST /run`. All necessary imports already present (`SessionDep`, `SyncLog`, `select`).

**New route to add** (after `get_sync_logs`):
```python
@router.get("/status")
def get_sync_status(session: SessionDep) -> SyncLog | None:
    return session.exec(
        select(SyncLog).order_by(SyncLog.timestamp.desc())
    ).first()
```

This returns `null` (JSON) when no logs exist, or the most recent `SyncLog` object. FastAPI serializes `None` to `null` automatically.

---

### Implementation: `types/index.ts`

Do NOT add a new interface — just add a type alias after the existing `SyncLog` interface:
```typescript
export type SyncStatus = SyncLog | null
```

---

### Implementation: `hooks/useSyncStatus.ts`

```typescript
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { SyncLog } from '@/types'

export function useSyncStatus() {
  return useQuery({
    queryKey: ['sync', 'status'],
    queryFn: () => api.get<SyncLog | null>('/sync/status'),
  })
}
```

TanStack Query key `['sync', 'status']` is pre-defined in the architecture doc — use it exactly.

---

### Implementation: `SyncStatusBadge.tsx`

```tsx
import { useSyncStatus } from '@/hooks/useSyncStatus'

export default function SyncStatusBadge() {
  const { data: status, isPending } = useSyncStatus()

  if (isPending) return null

  if (!status) {
    return (
      <p className="text-sm text-muted-foreground">Last sync: Never synced</p>
    )
  }

  if (status.status === 'success') {
    return (
      <p className="text-sm text-green-600">
        Last sync: Success — {new Date(status.timestamp).toLocaleString()}
        {status.track_count != null && ` (${status.track_count} tracks)`}
      </p>
    )
  }

  return (
    <p className="text-sm text-red-600">
      Last sync: Failed — {status.error_message ?? 'Unknown error'}
    </p>
  )
}
```

---

### Implementation: `DashboardPage.tsx`

Add `<SyncStatusBadge />` immediately below the `<h1>Dashboard</h1>` heading, above `<PlaylistList />`:

```tsx
import SyncStatusBadge from '@/features/sync/SyncStatusBadge'

// Inside the return JSX (authenticated state):
<div className="p-6 space-y-4">
  <h1 className="text-2xl font-bold">Dashboard</h1>
  <SyncStatusBadge />
  <PlaylistList />
  <SyncButton />
</div>
```

Current `DashboardPage.tsx` already imports `SyncButton`, `PlaylistList`, `ReauthBanner`, `SpotifyConnect`, `SetupWizard` — just add the `SyncStatusBadge` import and the JSX element.

---

### Implementation: `test_story_5_2.py`

```python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from models.sync_log import SyncLog


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_get_status_no_syncs_returns_null(client):
    r = client.get("/api/v1/sync/status")
    assert r.status_code == 200
    assert r.json() is None


def test_get_status_after_success(client, session):
    session.add(SyncLog(status="success", track_count=42, error_message=None, timestamp="2026-05-20T10:00:00Z"))
    session.commit()
    r = client.get("/api/v1/sync/status")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["track_count"] == 42
    assert data["error_message"] is None


def test_get_status_after_failure(client, session):
    session.add(SyncLog(status="failure", track_count=None, error_message="Token expired", timestamp="2026-05-20T11:00:00Z"))
    session.commit()
    r = client.get("/api/v1/sync/status")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "failure"
    assert data["error_message"] == "Token expired"
    assert data["track_count"] is None


def test_get_status_returns_most_recent(client, session):
    session.add(SyncLog(status="failure", track_count=None, error_message="Old error", timestamp="2026-05-19T10:00:00Z"))
    session.add(SyncLog(status="success", track_count=30, error_message=None, timestamp="2026-05-20T10:00:00Z"))
    session.commit()
    r = client.get("/api/v1/sync/status")
    assert r.status_code == 200
    data = r.json()
    # Most recent is the success entry
    assert data["status"] == "success"
    assert data["track_count"] == 30
```

---

### Architecture Rules — MUST FOLLOW

- Return `SyncLog | None` directly — no wrapper object (architecture: direct resource, no wrapper)
- JSON fields: snake_case — `track_count`, `error_message`, `timestamp`
- All frontend fetch via `lib/api.ts` — no raw `fetch()`
- TanStack Query key `['sync', 'status']` exactly as defined in architecture doc
- `SyncLog` model: import from `models.sync_log` — do NOT recreate
- No business logic in router — simple DB query is acceptable in router per Story 5.1 precedent

---

### Anti-Patterns to Avoid

- ❌ Creating a new `SyncStatus` SQLModel — use the existing `SyncLog` model
- ❌ Adding a new interface in TypeScript — just a `type SyncStatus = SyncLog | null` alias
- ❌ Wrapping response in `{"status": {...}}` — return direct object or null
- ❌ Using `isLoading` instead of `isPending` — TanStack Query v5 uses `isPending`
- ❌ Showing `SyncStatusBadge` only when authenticated (it's already inside the authenticated branch in `DashboardPage.tsx`)
- ❌ Touching `SyncButton.tsx` — that's Story 5.3's responsibility

---

### Previous Story Intelligence (from Story 5.1)

- Test fixture: `session_fixture` (StaticPool in-memory SQLite) + `client_fixture` (dependency_overrides on `get_session`) — same pattern used since 2.4, follow exactly.
- Mock path: `patch("routers.<module>.<thing>")` — not needed here (no Spotify calls).
- `SessionDep` alias: already imported in `routers/sync.py` from Story 5.1 — no need to re-add the import.
- `SyncLog` model: already imported in `routers/sync.py` — no need to re-add the import.
- Full test suite after Story 5.1: **73 tests passed**. New story should bring total to ~77.
- `SyncLog` TypeScript interface: already in `frontend/src/types/index.ts` from 5.1 — `SyncStatus` is just a type alias on top.

---

### Existing Code State (verified)

**`backend/routers/sync.py` (current — add after `get_sync_logs`):**
```python
from fastapi import APIRouter, HTTPException
from sqlmodel import select

import services.sync_engine as sync_engine
from dependencies import SessionDep
from models.sync_log import SyncLog

router = APIRouter(prefix="/sync", tags=["sync"])

@router.get("/logs")
def get_sync_logs(session: SessionDep) -> list[SyncLog]:
    logs = session.exec(select(SyncLog).order_by(SyncLog.timestamp.desc())).all()
    return list(logs)

@router.post("/run")
def run_sync() -> dict:
    try:
        return sync_engine.run_sync()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

**`frontend/src/types/index.ts` (current — add type alias at end):**
Already has: `Config`, `ConfigWrite`, `ConfigPatch`, `AuthStatus`, `Playlist`, `SyncLog`.

**`frontend/src/pages/DashboardPage.tsx` (current authenticated JSX):**
```tsx
<div className="p-6 space-y-4">
  <h1 className="text-2xl font-bold">Dashboard</h1>
  <PlaylistList />
  <SyncButton />
</div>
```
Add `<SyncStatusBadge />` between `<h1>` and `<PlaylistList />`.

**`frontend/src/features/sync/` (current):**
Contains `SyncButton.tsx` and `SyncLogPanel.tsx` — add `SyncStatusBadge.tsx` here.

**`frontend/src/hooks/` (current):**
Contains `usePlaylists.ts`, `useConfig.ts`, `useSyncLogs.ts` — add `useSyncStatus.ts` here.

---

### Postman Collection

- Collection UID: `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`
- API Key: in `.mcp.json` (env `POSTMAN_API_KEY`)
- Add `GET /api/v1/sync/status` in the "Sync" folder

Example responses:

No syncs: `null`

Success:
```json
{
  "id": 3,
  "status": "success",
  "track_count": 50,
  "error_message": null,
  "timestamp": "2026-05-20T14:30:00Z"
}
```

Failure:
```json
{
  "id": 2,
  "status": "failure",
  "track_count": null,
  "error_message": "No playlists selected",
  "timestamp": "2026-05-20T10:00:00Z"
}
```

---

### References

- Story 5.1 (previous): `_bmad-output/implementation-artifacts/5-1-sync-history-log-viewer.md`
- SyncLog model: `backend/models/sync_log.py`
- Sync router: `backend/routers/sync.py`
- Test fixture pattern: `backend/tests/test_story_5_1.py`
- Architecture TanStack Query keys: `_bmad-output/planning-artifacts/architecture.md` (section "Communication Patterns")
- Postman collection UID: `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No blockers encountered. All 4 tests passed on first run.

### Completion Notes List

- Added `GET /status` route to `routers/sync.py` — queries most recent SyncLog, returns None (→ JSON null) when empty
- Added `SyncStatus = SyncLog | null` type alias to `types/index.ts` (no new interface)
- Created `useSyncStatus.ts` TanStack Query hook with key `['sync', 'status']`
- Created `SyncStatusBadge.tsx` — 3 states: isPending (null render), success (green), failure (red)
- Updated `DashboardPage.tsx` — `<SyncStatusBadge />` inserted between `<h1>` and `<PlaylistList />`
- 4 new backend tests — all pass; full suite: 80 passed, 0 regressions
- Postman: `GET Sync Status` added to Sync folder with example responses

### File List

- `backend/routers/sync.py` — modified (added GET /status route + also SSE routes from 5.3)
- `backend/tests/test_story_5_2.py` — created (4 tests)
- `frontend/src/types/index.ts` — modified (SyncStatus alias + SyncStreamEvent from 5.3)
- `frontend/src/hooks/useSyncStatus.ts` — created
- `frontend/src/features/sync/SyncStatusBadge.tsx` — created
- `frontend/src/pages/DashboardPage.tsx` — modified (SyncStatusBadge import + render)

## Change Log

- 2026-05-20: Story 5.2 created — ready-for-dev
- 2026-05-20: Story 5.2 implemented — all ACs satisfied, status → review
