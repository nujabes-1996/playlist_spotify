# Story 5.1: Sync History & Log Viewer

Status: review

## Story

As a user,
I want to view the complete history of all syncs on the Logs page,
so that I can track what happened, when, and why any sync may have failed.

## Acceptance Criteria

1. **Given** I navigate to `/logs`, **When** the page loads, **Then** `GET /api/v1/sync/logs` is called and `SyncLogPanel` renders the full sync history.

2. **Given** the sync log list renders, **When** entries are displayed, **Then** each entry shows: timestamp (formatted), status (success/failure), track count delta, and error message when applicable (FR22).

3. **Given** no syncs have run yet, **When** I navigate to `/logs`, **Then** an empty state message is shown (e.g., "No syncs yet — trigger your first sync from the dashboard").

4. **Given** `GET /api/v1/sync/logs`, **When** the endpoint is called, **Then** it returns all `SyncLog` entries ordered by `timestamp` descending (most recent first) (FR24).

5. **Given** the `/logs` page loads, **When** it is measured on a local network, **Then** the initial render completes under 3 seconds (NFR1).

## Tasks / Subtasks

- [x] Task 1: Add `GET /api/v1/sync/logs` endpoint to `backend/routers/sync.py` (AC: #1, #4)
  - [x] Import `SyncLog` from `models.sync_log`, `select` from `sqlmodel`, `SessionDep` from `dependencies`
  - [x] Add `GET /logs` route returning all SyncLog entries ordered by `timestamp` descending
  - [x] Return direct array (no wrapper) per architecture convention
  - [x] No business logic in router — query is simple enough to stay in router (no service needed)

- [x] Task 2: Add `SyncLog` type to `frontend/src/types/index.ts` (AC: #2)
  - [x] Add interface `SyncLog { id: number; status: "success" | "failure"; track_count: number | null; error_message: string | null; timestamp: string }`

- [x] Task 3: Create `frontend/src/hooks/useSyncLogs.ts` (AC: #1)
  - [x] TanStack Query hook using `queryKey: ['sync', 'logs']`
  - [x] `queryFn: () => api.get<SyncLog[]>('/sync/logs')`

- [x] Task 4: Create `frontend/src/features/sync/SyncLogPanel.tsx` (AC: #2, #3)
  - [x] Call `useSyncLogs()` hook
  - [x] Show loading state while `isPending`
  - [x] Show empty state when array is empty: "No syncs yet — trigger your first sync from the dashboard"
  - [x] Render a list of entries, each showing: formatted timestamp, status badge (green for success, red for failure), track count (or "—" if null), error message (only when status="failure")

- [x] Task 5: Update `frontend/src/pages/LogsPage.tsx` (AC: #1, #2, #3)
  - [x] Replace placeholder `<h1>` with `<SyncLogPanel />`
  - [x] Keep `<h1 className="text-2xl font-bold">Sync Logs</h1>` as page title above the panel

- [x] Task 6: Create `backend/tests/test_story_5_1.py` (AC: #1, #3, #4)
  - [x] Use same session + client fixture pattern as `test_story_2_4.py` (StaticPool in-memory SQLite + dependency_overrides)
  - [x] `test_get_logs_empty_returns_empty_array`: GET /api/v1/sync/logs with no logs in DB → `[]`
  - [x] `test_get_logs_returns_entries_ordered_desc`: seed 2 SyncLog entries with different timestamps → response array has most recent first
  - [x] `test_get_logs_success_entry_shape`: seed a success log → verify all fields (id, status, track_count, error_message, timestamp) present and correct
  - [x] `test_get_logs_failure_entry_shape`: seed a failure log with error_message → verify error_message populated, track_count null

- [x] Task 7: Run test suite (no regressions)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_5_1.py -v` — all new tests pass
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` — 0 regressions

- [x] Task 8: Update Postman collection
  - [x] Fetch current collection (`GET https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`)
  - [x] Add `GET /api/v1/sync/logs` request in the "Sync" folder with description and example response
  - [x] Push updated collection

## Dev Notes

### What This Story Adds

Epic 5 opens with the most straightforward observability feature: a static read of `sync_log` table entries. No SSE, no streaming — just a REST endpoint and a list component. Stories 5.2 (failure badge) and 5.3 (SSE streaming) build on top of this foundation.

**Backend delta:** One new GET route in `routers/sync.py`. The `SyncLog` SQLModel and `_write_sync_log` function already exist from Story 3.4 — do NOT recreate them.

**Frontend delta:** One new type, one new hook, one new component, update to `LogsPage.tsx` (currently just a placeholder `<h1>`).

---

### Files to Touch

| File | Action | Notes |
|------|--------|-------|
| `backend/routers/sync.py` | MODIFY | Add `GET /logs` route |
| `backend/tests/test_story_5_1.py` | CREATE | 4 tests |
| `frontend/src/types/index.ts` | MODIFY | Add `SyncLog` interface |
| `frontend/src/hooks/useSyncLogs.ts` | CREATE | TanStack Query hook |
| `frontend/src/features/sync/SyncLogPanel.tsx` | CREATE | List component |
| `frontend/src/pages/LogsPage.tsx` | MODIFY | Replace placeholder with SyncLogPanel |

**Do NOT touch:** `backend/models/sync_log.py` (already correct), `backend/services/sync_engine.py` (not relevant), `backend/scheduler.py` (not relevant).

---

### Implementation: `routers/sync.py`

**Current state:** Only `POST /run` exists. The router imports `sync_engine` but not the DB session.

**New imports to add:**
```python
from sqlmodel import select
from database import get_session
from dependencies import SessionDep
from models.sync_log import SyncLog
```

**New route:**
```python
@router.get("/logs")
def get_sync_logs(session: SessionDep) -> list[SyncLog]:
    logs = session.exec(
        select(SyncLog).order_by(SyncLog.timestamp.desc())
    ).all()
    return list(logs)
```

**Note:** `SessionDep` is the `Annotated[Session, Depends(get_session)]` alias from `dependencies.py` — check `backend/dependencies.py` for the exact import name used by other routers (e.g., `routers/config.py`).

---

### Implementation: `types/index.ts`

Add to the existing file (after the `Playlist` interface):
```typescript
export interface SyncLog {
  id: number
  status: 'success' | 'failure'
  track_count: number | null
  error_message: string | null
  timestamp: string  // ISO 8601
}
```

---

### Implementation: `hooks/useSyncLogs.ts`

```typescript
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { SyncLog } from '@/types'

export function useSyncLogs() {
  return useQuery({
    queryKey: ['sync', 'logs'],
    queryFn: () => api.get<SyncLog[]>('/sync/logs'),
  })
}
```

TanStack Query key: `['sync', 'logs']` — matches the convention defined in architecture doc.

---

### Implementation: `SyncLogPanel.tsx`

```tsx
import { useSyncLogs } from '@/hooks/useSyncLogs'

export default function SyncLogPanel() {
  const { data: logs, isPending, isError } = useSyncLogs()

  if (isPending) return <p className="text-sm text-muted-foreground">Loading logs…</p>
  if (isError) return <p className="text-sm text-red-600">Failed to load sync logs.</p>

  if (!logs || logs.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No syncs yet — trigger your first sync from the dashboard.
      </p>
    )
  }

  return (
    <ul className="space-y-2">
      {logs.map((log) => (
        <li key={log.id} className="border rounded p-3 text-sm space-y-1">
          <div className="flex items-center gap-2">
            <span className={log.status === 'success' ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
              {log.status === 'success' ? 'Success' : 'Failure'}
            </span>
            <span className="text-muted-foreground">{new Date(log.timestamp).toLocaleString()}</span>
          </div>
          <div>Tracks: {log.track_count ?? '—'}</div>
          {log.status === 'failure' && log.error_message && (
            <div className="text-red-600">{log.error_message}</div>
          )}
        </li>
      ))}
    </ul>
  )
}
```

---

### Implementation: `LogsPage.tsx`

```tsx
import SyncLogPanel from '@/features/sync/SyncLogPanel'

export default function LogsPage() {
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold">Sync Logs</h1>
      <SyncLogPanel />
    </div>
  )
}
```

---

### Implementation: `test_story_5_1.py`

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


def test_get_logs_empty_returns_empty_array(client):
    r = client.get("/api/v1/sync/logs")
    assert r.status_code == 200
    assert r.json() == []


def test_get_logs_returns_entries_ordered_desc(client, session):
    session.add(SyncLog(status="success", track_count=10, timestamp="2026-05-01T10:00:00Z"))
    session.add(SyncLog(status="success", track_count=20, timestamp="2026-05-02T10:00:00Z"))
    session.commit()
    r = client.get("/api/v1/sync/logs")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["timestamp"] > data[1]["timestamp"]  # most recent first


def test_get_logs_success_entry_shape(client, session):
    session.add(SyncLog(status="success", track_count=42, error_message=None, timestamp="2026-05-01T12:00:00Z"))
    session.commit()
    r = client.get("/api/v1/sync/logs")
    assert r.status_code == 200
    entry = r.json()[0]
    assert entry["status"] == "success"
    assert entry["track_count"] == 42
    assert entry["error_message"] is None
    assert "timestamp" in entry
    assert "id" in entry


def test_get_logs_failure_entry_shape(client, session):
    session.add(SyncLog(status="failure", track_count=None, error_message="Token expired", timestamp="2026-05-01T13:00:00Z"))
    session.commit()
    r = client.get("/api/v1/sync/logs")
    assert r.status_code == 200
    entry = r.json()[0]
    assert entry["status"] == "failure"
    assert entry["track_count"] is None
    assert entry["error_message"] == "Token expired"
```

**Mock path note:** No mocking needed for this story — no Spotify API calls, no scheduler calls. Pure DB read.

---

### Architecture Rules — MUST FOLLOW

- Return direct array from `GET /logs` — no `{"data": [...]}` wrapper (architecture: "Success: direct resource or array — NO wrapper")
- JSON fields: snake_case (`track_count`, `error_message`, `timestamp`) — never camelCase
- All frontend fetch via `lib/api.ts` — no raw `fetch()` in component
- Business logic in `services/` — this route has no business logic (simple DB read), staying in router is correct
- TanStack Query key: `['sync', 'logs']` as defined in architecture doc
- No Spotify API calls in this story

---

### Anti-Patterns to Avoid

- ❌ Creating a new `SyncLog` SQLModel — it already exists in `backend/models/sync_log.py`, import it
- ❌ Ordering by `id` instead of `timestamp` — use `timestamp` DESC per AC #4 and FR24
- ❌ Wrapping response in `{"logs": [...]}` — architecture mandates direct array
- ❌ Using `isLoading` instead of `isPending` — project uses TanStack Query v5 where `isPending` is the correct flag
- ❌ Raw `fetch('/api/v1/sync/logs')` in component — always use `api.get()` from `lib/api.ts`
- ❌ Adding SSE/streaming to this story — that's Story 5.3

---

### Previous Story Intelligence (from Story 4.2)

- Test fixture pattern: `session_fixture` (StaticPool in-memory) + `client_fixture` (dependency_overrides on `get_session`). Follow exactly — same structure in every story since 2.4.
- Mock at import site: `patch("routers.<module>.<thing>")`, not at definition site. This story needs no mocking.
- `SessionDep` alias: check `backend/dependencies.py` for exact type alias name — other routers (e.g., `config.py`) use it consistently.
- Full test suite at end of Story 4.2: **69 tests passed**. New story should bring total to ~73 (69 + 4).
- No frontend changes were needed in Stories 4.1 and 4.2 — Story 5.1 is the first story since 2.4 to touch the frontend.

---

### Existing Code Context

**`backend/models/sync_log.py` (already exists — do not modify):**
```python
class SyncLog(SQLModel, table=True):
    __tablename__ = "sync_log"
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str  # "success" or "failure"
    track_count: Optional[int] = None
    error_message: Optional[str] = None
    timestamp: str  # ISO 8601 string
```

**`backend/routers/sync.py` (current state — add to this):**
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

**`frontend/src/pages/LogsPage.tsx` (current — replace):**
```tsx
export default function LogsPage() {
  return <h1 className="text-2xl font-bold">Sync Logs</h1>
}
```

**`frontend/src/types/index.ts` (current — add `SyncLog` interface at end):**
Already has `Config`, `ConfigWrite`, `ConfigPatch`, `AuthStatus`, `Playlist`.

**`frontend/src/features/sync/` (current contents):**
Only `SyncButton.tsx` exists — create `SyncLogPanel.tsx` here.

**`frontend/src/hooks/` (current contents):**
`usePlaylists.ts`, `useConfig.ts` — create `useSyncLogs.ts` here.

---

### Postman Collection

- Collection UID: `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`
- API Key: in `.mcp.json` (env `POSTMAN_API_KEY`)
- Add `GET /api/v1/sync/logs` in the "Sync" folder
- Example response body:
```json
[
  {
    "id": 2,
    "status": "success",
    "track_count": 50,
    "error_message": null,
    "timestamp": "2026-05-19T14:30:00Z"
  },
  {
    "id": 1,
    "status": "failure",
    "track_count": null,
    "error_message": "No playlists selected",
    "timestamp": "2026-05-19T10:00:00Z"
  }
]
```

---

### References

- Story 4.2 implementation (previous story): `_bmad-output/implementation-artifacts/4-2-dynamic-schedule-reconfiguration.md`
- SyncLog model: `backend/models/sync_log.py`
- Sync router (current): `backend/routers/sync.py`
- Test fixture pattern: `backend/tests/test_story_2_4.py`
- Architecture: `_bmad-output/planning-artifacts/architecture.md`
- Postman collection UID: `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No blockers encountered. All tasks implemented cleanly in sequence.

### Completion Notes List

- Added `GET /logs` route to `backend/routers/sync.py` using `SessionDep` + `select(SyncLog).order_by(SyncLog.timestamp.desc())`. Direct array response, no wrapper.
- Added `SyncLog` TypeScript interface to `frontend/src/types/index.ts`.
- Created `useSyncLogs` TanStack Query v5 hook with `queryKey: ['sync', 'logs']`.
- Created `SyncLogPanel` component with loading/error/empty states and per-entry display of status badge (green/red), timestamp, track count, and error message.
- Updated `LogsPage.tsx` to embed `<SyncLogPanel />` under the page title.
- 4 new backend tests written and passing; full suite 73/73, 0 regressions.
- Postman collection updated: `GET /api/v1/sync/logs` added to Sync folder with description and example response.

### File List

- `backend/routers/sync.py` — modified (added GET /logs route)
- `backend/tests/test_story_5_1.py` — created (4 tests)
- `frontend/src/types/index.ts` — modified (added SyncLog interface)
- `frontend/src/hooks/useSyncLogs.ts` — created
- `frontend/src/features/sync/SyncLogPanel.tsx` — created
- `frontend/src/pages/LogsPage.tsx` — modified

## Change Log

- 2026-05-20: Story 5.1 implemented — added GET /api/v1/sync/logs endpoint, SyncLogPanel component, useSyncLogs hook, SyncLog type; updated LogsPage; 4 new backend tests (73 total, 0 regressions); Postman collection updated.
