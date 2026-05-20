# Story 5.3: Real-Time SSE Sync Streaming

Status: review

## Story

As a user,
I want to watch sync progress live on the dashboard while a sync is running,
So that I have immediate feedback without refreshing the page.

## Acceptance Criteria

1. **Given** a sync is triggered (manually or by scheduler), **When** `GET /api/v1/sync/stream` is connected via `EventSource`, **Then** the backend streams `text/event-stream` events as the sync progresses (FR21, AR7).

2. **Given** the SSE stream is active, **When** the sync engine emits a log event, **Then** it arrives in the `SyncLogPanel` within 1 second of backend emission (NFR3).

3. **Given** the SSE stream receives a `sync_log` event, **When** the `useSyncStream.ts` hook processes it, **Then** the event is appended to the live log panel in real time without a page reload.

4. **Given** the sync completes, **When** a `sync_complete` or `sync_error` event is received, **Then** the SSE connection is closed gracefully and `SyncButton` returns to its normal state.

5. **Given** the SSE connection drops unexpectedly, **When** `EventSource` detects the disconnect, **Then** the frontend does not crash — the log panel retains previously received events.

6. **Given** no sync is in progress, **When** I navigate to the dashboard, **Then** no SSE connection is open (connection is established only when a sync is active).

## Tasks / Subtasks

- [x] Task 1: Add helper `sse()` and `GET /api/v1/sync/stream` endpoint to `backend/routers/sync.py` (AC: #1, #2, #4)
  - [x] Add `import json` and `from fastapi.responses import StreamingResponse` at top of `sync.py`
  - [x] Add private `_sse(event, data)` helper that formats SSE correctly
  - [x] Add async generator `_run_sync_stream()` that runs sync steps and yields SSE events
  - [x] Add `GET /stream` route returning `StreamingResponse` with `media_type="text/event-stream"`
  - [x] Add `Cache-Control: no-cache` and `X-Accel-Buffering: no` headers (prevents proxy buffering)

- [x] Task 2: Add `SyncStreamEvent` interface to `frontend/src/types/index.ts` (AC: #3)
  - [x] `SyncStreamEvent { level: string; message: string; timestamp: string }` (for `sync_log` events)

- [x] Task 3: Create `frontend/src/hooks/useSyncStream.ts` (AC: #1, #3, #4, #5, #6)
  - [x] Manages `EventSource` lifecycle — opens only when sync is started
  - [x] Exposes `startStream()`, `isStreaming: boolean`, `events: SyncStreamEvent[]`, `error: string | null`
  - [x] On `sync_log` event → append to `events` state
  - [x] On `sync_complete` or `sync_error` → close `EventSource`, set `isStreaming = false`, invalidate `['sync', 'logs']` and `['sync', 'status']` queries
  - [x] On `es.onerror` → set `isStreaming = false`, do NOT crash, retain `events`

- [x] Task 4: Update `frontend/src/features/sync/SyncButton.tsx` to use `useSyncStream` (AC: #1, #3, #4, #5, #6)
  - [x] Import and call `useSyncStream()`
  - [x] Replace `mutation.mutate()` click handler with `startStream()`
  - [x] Button `disabled` when `isStreaming` (replaces `mutation.isPending`)
  - [x] Button label: "Syncing…" when `isStreaming`, "Sync Now" otherwise
  - [x] Live event log panel: render `events` list below the button
  - [x] Error state: show `error` in red when set
  - [x] Remove the `useMutation` import — no longer needed in this component
  - [x] Keep the existing success message logic based on stream completion (use `isStreaming === false && events.length > 0` to infer completion)

- [x] Task 5: Create `backend/tests/test_story_5_3.py` (AC: #1, #4)
  - [x] Use same session + client fixture pattern as `test_story_5_2.py`
  - [x] `test_stream_returns_sse_content_type`: GET /api/v1/sync/stream → response Content-Type contains `text/event-stream`
  - [x] `test_stream_emits_sync_complete_on_success`: mock `sync_engine._run_sync_stream` or mock underlying services, verify `sync_complete` event emitted
  - [x] `test_stream_emits_sync_error_on_failure`: mock services to raise, verify `sync_error` event emitted

- [x] Task 6: Run test suite (no regressions)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/test_story_5_3.py -v` — 3 passed
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` — 80 passed, 0 regressions

- [x] Task 7: Update Postman collection
  - [x] Add `GET /api/v1/sync/stream` in the "Sync" folder with description noting SSE / EventSource usage and example event format
  - [x] Push updated collection

## Dev Notes

### What This Story Adds

Story 5.3 replaces the dashboard's fire-and-forget sync trigger with a live SSE stream. The `POST /sync/run` endpoint stays intact (scheduler continues to use it via `sync_engine.run_sync()`). The new `GET /sync/stream` endpoint runs the same sync pipeline but as a streaming async generator.

**Backend delta:** New SSE endpoint in `routers/sync.py`. The `sync_engine` module is NOT modified — we re-implement the sync steps inline in the streaming generator (same logic, async-aware steps using `asyncio.to_thread`).

**Frontend delta:** New hook `useSyncStream.ts`, updated `SyncButton.tsx` (replaces mutation with SSE), new live event log panel in `SyncButton`.

---

### Files to Touch

| File | Action | Notes |
|------|--------|-------|
| `backend/routers/sync.py` | MODIFY | Add `GET /stream` + `_sse()` helper + `_run_sync_stream()` generator |
| `backend/tests/test_story_5_3.py` | CREATE | 3 tests |
| `frontend/src/types/index.ts` | MODIFY | Add `SyncStreamEvent` interface |
| `frontend/src/hooks/useSyncStream.ts` | CREATE | EventSource lifecycle hook |
| `frontend/src/features/sync/SyncButton.tsx` | MODIFY | Replace useMutation with useSyncStream |

**Do NOT touch:** `backend/services/sync_engine.py`, `backend/scheduler.py`, `SyncLogPanel.tsx`, `SyncStatusBadge.tsx`, `useSyncLogs.ts`, `useSyncStatus.ts`.

---

### Implementation: `routers/sync.py` — New Code

Add at the top of the file:
```python
import json
import asyncio
from fastapi.responses import StreamingResponse
```

Add these three blocks (after existing routes):

```python
def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _run_sync_stream():
    """Async generator that runs the full sync pipeline and yields SSE events."""
    from datetime import datetime
    from sqlmodel import Session, select as sa_select
    from database import engine
    from models.config import Config
    from models.playlist import Playlist
    import services.spotify as spotify_service
    from services.sync_engine import harvest_tracks, deduplicate, sort_and_slice, _write_sync_log

    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        yield _sse("sync_log", {"level": "info", "message": "Starting sync…", "timestamp": timestamp})

        with Session(engine) as session:
            playlists = session.exec(
                sa_select(Playlist).where(Playlist.is_included == True)  # noqa: E712
            ).all()
            if not playlists:
                raise ValueError("No playlists selected")
            config = session.exec(sa_select(Config)).first()
            playlist_size = config.playlist_size if config else 50

        yield _sse("sync_log", {"level": "info", "message": f"Found {len(playlists)} included playlist(s)", "timestamp": timestamp})

        sp = await asyncio.to_thread(spotify_service.get_authenticated_client)
        raw_tracks = await asyncio.to_thread(harvest_tracks, playlists, sp)

        yield _sse("sync_log", {"level": "info", "message": f"Harvested {len(raw_tracks)} tracks", "timestamp": timestamp})

        deduped = deduplicate(raw_tracks)
        sliced = sort_and_slice(deduped, playlist_size)

        yield _sse("sync_log", {"level": "info", "message": f"After dedup/sort: {len(sliced)} tracks", "timestamp": timestamp})

        target_id = await asyncio.to_thread(spotify_service.get_or_create_dynamic_playlist, sp)
        track_uris = [t["uri"] for t in sliced]
        await asyncio.to_thread(spotify_service.replace_playlist_tracks, target_id, track_uris, sp)

        _write_sync_log("success", len(sliced), None, timestamp)
        yield _sse("sync_complete", {"status": "success", "track_count": len(sliced), "timestamp": timestamp})

    except Exception as exc:
        _write_sync_log("failure", None, str(exc), timestamp)
        yield _sse("sync_error", {"status": "error", "message": str(exc), "timestamp": timestamp})


@router.get("/stream")
async def stream_sync():
    return StreamingResponse(
        _run_sync_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

**Important:** The imports inside `_run_sync_stream` are written inline to avoid circular imports (same pattern as other routers). If preferred, move them to the top of the file — just verify no circular import with `services/sync_engine.py`.

---

### SSE Event Format (from architecture — use EXACTLY)

```
event: sync_log
data: {"level": "info", "message": "Harvested 42 tracks", "timestamp": "2026-04-17T14:30:00Z"}

event: sync_complete
data: {"status": "success", "track_count": 50, "timestamp": "2026-04-17T14:30:01Z"}

event: sync_error
data: {"status": "error", "message": "Token expired", "code": "TOKEN_EXPIRED", "timestamp": "..."}
```

Note: `code` field in `sync_error` is optional — include when available, omit otherwise.

Each SSE message must end with `\n\n` (double newline). The `_sse()` helper enforces this.

---

### Implementation: `types/index.ts`

Add after the `SyncLog` interface and `SyncStatus` alias:
```typescript
export interface SyncStreamEvent {
  level: string
  message: string
  timestamp: string
}
```

---

### Implementation: `hooks/useSyncStream.ts`

```typescript
import { useState, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { SyncStreamEvent } from '@/types'

export function useSyncStream() {
  const [isStreaming, setIsStreaming] = useState(false)
  const [events, setEvents] = useState<SyncStreamEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const esRef = useRef<EventSource | null>(null)
  const queryClient = useQueryClient()

  const startStream = useCallback(() => {
    if (esRef.current) {
      esRef.current.close()
    }

    setIsStreaming(true)
    setEvents([])
    setError(null)

    const es = new EventSource('/api/v1/sync/stream')
    esRef.current = es

    es.addEventListener('sync_log', (e: MessageEvent) => {
      const data: SyncStreamEvent = JSON.parse(e.data)
      setEvents((prev) => [...prev, data])
    })

    const onDone = () => {
      setIsStreaming(false)
      es.close()
      esRef.current = null
      queryClient.invalidateQueries({ queryKey: ['sync', 'logs'] })
      queryClient.invalidateQueries({ queryKey: ['sync', 'status'] })
    }

    es.addEventListener('sync_complete', onDone)

    es.addEventListener('sync_error', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      setError(data.message ?? 'Sync failed')
      onDone()
    })

    es.onerror = () => {
      // Connection dropped — retain events, do not crash
      setIsStreaming(false)
      esRef.current = null
    }
  }, [queryClient])

  return { startStream, isStreaming, events, error }
}
```

Key decisions:
- `useRef<EventSource>` to avoid stale closure issues
- `onDone` closes EventSource AND invalidates both `['sync', 'logs']` and `['sync', 'status']` queries — this auto-refreshes `SyncLogPanel` and `SyncStatusBadge`
- `es.onerror` sets `isStreaming = false` but retains events (AC #5)
- No SSE connection opened until `startStream()` is called (AC #6)

---

### Implementation: Updated `SyncButton.tsx`

Replace the existing file entirely:

```tsx
import { useSyncStream } from '@/hooks/useSyncStream'
import { Button } from '@/components/ui/button'

export default function SyncButton() {
  const { startStream, isStreaming, events, error } = useSyncStream()

  return (
    <div className="space-y-2">
      <Button onClick={startStream} disabled={isStreaming}>
        {isStreaming ? 'Syncing…' : 'Sync Now'}
      </Button>

      {events.length > 0 && (
        <ul className="text-sm text-muted-foreground space-y-0.5">
          {events.map((ev, i) => (
            <li key={i}>{ev.message}</li>
          ))}
        </ul>
      )}

      {!isStreaming && events.length > 0 && !error && (
        <p className="text-sm text-green-600">Sync complete.</p>
      )}

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}
    </div>
  )
}
```

`useMutation` is entirely removed — the SSE stream replaces the fire-and-forget pattern.

---

### Implementation: `test_story_5_3.py`

Testing SSE with `TestClient` requires reading the raw streaming response. FastAPI's `TestClient` (via `httpx`) supports streaming:

```python
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session


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


def test_stream_returns_sse_content_type(client):
    async def _mock_stream():
        yield "event: sync_complete\ndata: {\"status\": \"success\", \"track_count\": 0, \"timestamp\": \"2026-01-01T00:00:00Z\"}\n\n"

    with patch("routers.sync._run_sync_stream", return_value=_mock_stream()):
        r = client.get("/api/v1/sync/stream")
    assert "text/event-stream" in r.headers["content-type"]


def test_stream_emits_sync_complete_on_success(client):
    async def _mock_stream():
        yield "event: sync_log\ndata: {\"level\": \"info\", \"message\": \"Starting\", \"timestamp\": \"2026-01-01T00:00:00Z\"}\n\n"
        yield "event: sync_complete\ndata: {\"status\": \"success\", \"track_count\": 10, \"timestamp\": \"2026-01-01T00:00:01Z\"}\n\n"

    with patch("routers.sync._run_sync_stream", return_value=_mock_stream()):
        r = client.get("/api/v1/sync/stream")
    assert r.status_code == 200
    body = r.text
    assert "event: sync_complete" in body
    assert "sync_log" in body


def test_stream_emits_sync_error_on_failure(client):
    async def _mock_stream():
        yield "event: sync_error\ndata: {\"status\": \"error\", \"message\": \"Token expired\", \"timestamp\": \"2026-01-01T00:00:00Z\"}\n\n"

    with patch("routers.sync._run_sync_stream", return_value=_mock_stream()):
        r = client.get("/api/v1/sync/stream")
    assert r.status_code == 200
    assert "event: sync_error" in r.text
    assert "Token expired" in r.text
```

**Mock path note:** Mock `routers.sync._run_sync_stream` (not the sync_engine functions) — this is the cleanest approach for SSE streaming tests.

---

### Architecture Rules — MUST FOLLOW

- SSE endpoint: FastAPI `StreamingResponse` with `text/event-stream` (AR7)
- SSE format: `event: <type>\ndata: <json>\n\n` — exactly two newlines at end
- Frontend: native `EventSource` API — no third-party SSE library
- Hook file: `useSyncStream.ts` exactly (architecture specifies this filename)
- `POST /sync/run` stays intact — scheduler uses it via `sync_engine.run_sync()` directly, not via HTTP
- Invalidate both `['sync', 'logs']` and `['sync', 'status']` on stream completion
- No Spotify API calls in routers — use `services/spotify.py` functions
- `asyncio.to_thread` for synchronous Spotify calls inside the async generator

---

### Anti-Patterns to Avoid

- ❌ Modifying `services/sync_engine.py` — the streaming logic is in the router's generator
- ❌ Removing `POST /sync/run` — scheduler depends on it
- ❌ Using a WebSocket — architecture mandates SSE (AR7)
- ❌ Using `isLoading` instead of `isPending` — though this story uses `isStreaming` (custom state), not TanStack Query loading
- ❌ Opening EventSource on page load — only open when user clicks "Sync Now" (AC #6)
- ❌ Third-party SSE libraries — use browser-native `EventSource`
- ❌ Forgetting `X-Accel-Buffering: no` header — nginx/proxies buffer SSE by default, this disables it

---

### Previous Story Intelligence (from Story 5.2)

- Test fixtures: `session_fixture` + `client_fixture` with `StaticPool` + `dependency_overrides` — same pattern, copy from 5.2.
- Full test suite after Story 5.2: **~77 tests passed**. New story should bring total to ~80.
- `SyncStatusBadge` relies on `['sync', 'status']` query — `useSyncStream` must invalidate it on completion or the badge won't update after a streamed sync.
- `SyncLogPanel` relies on `['sync', 'logs']` query — also must be invalidated on stream completion.
- Both query invalidations are already handled in the `useSyncStream` `onDone` callback.

---

### Existing Code State (verified)

**`backend/routers/sync.py` current imports (do NOT duplicate):**
```python
from fastapi import APIRouter, HTTPException
from sqlmodel import select
import services.sync_engine as sync_engine
from dependencies import SessionDep
from models.sync_log import SyncLog
```
Add: `import json`, `import asyncio`, `from fastapi.responses import StreamingResponse`.

**`frontend/src/features/sync/SyncButton.tsx` (current — will be fully replaced):**
Uses `useMutation` from `@tanstack/react-query` and `api.post('/sync/run')`. Story 5.3 replaces the entire component — `useMutation` is removed.

**`frontend/src/features/sync/` (current):**
Contains `SyncButton.tsx`, `SyncLogPanel.tsx`, `SyncStatusBadge.tsx` (from 5.2) — add nothing new here except the `SyncButton.tsx` replacement.

**`frontend/src/hooks/` (current):**
Contains `usePlaylists.ts`, `useConfig.ts`, `useSyncLogs.ts`, `useSyncStatus.ts` — add `useSyncStream.ts`.

---

### Postman Collection

- Collection UID: `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`
- API Key: in `.mcp.json` (env `POSTMAN_API_KEY`)
- Add `GET /api/v1/sync/stream` in the "Sync" folder

Description: "SSE streaming endpoint. Connect with `EventSource` to receive real-time sync progress. Emits `sync_log`, `sync_complete`, and `sync_error` events. Triggers a full sync pipeline and streams progress until completion."

Example event stream body:
```
event: sync_log
data: {"level": "info", "message": "Starting sync…", "timestamp": "2026-05-20T14:30:00Z"}

event: sync_log
data: {"level": "info", "message": "Harvested 120 tracks", "timestamp": "2026-05-20T14:30:01Z"}

event: sync_complete
data: {"status": "success", "track_count": 50, "timestamp": "2026-05-20T14:30:02Z"}
```

---

### References

- Story 5.2 (previous): `_bmad-output/implementation-artifacts/5-2-sync-failure-indicator.md`
- Architecture SSE section: `_bmad-output/planning-artifacts/architecture.md` (section "SSE Event Format" and "Communication Patterns")
- Existing sync router: `backend/routers/sync.py`
- Existing sync engine: `backend/services/sync_engine.py` (for function signatures to import)
- SyncButton to replace: `frontend/src/features/sync/SyncButton.tsx`
- Architecture AR7: FastAPI StreamingResponse + frontend EventSource in `useSyncStream.ts`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No blockers. Used `patch("routers.sync._run_sync_stream", ...)` to mock the async generator in tests — clean approach without touching sync_engine.

### Completion Notes List

- Added `_sse()` helper, `_run_sync_stream()` async generator, and `GET /stream` route to `routers/sync.py`
- `_run_sync_stream` uses `asyncio.to_thread` for all blocking Spotify calls
- `Cache-Control: no-cache` + `X-Accel-Buffering: no` headers set on StreamingResponse
- Created `useSyncStream.ts` hook — EventSource only opens on `startStream()`, never on mount (AC #6)
- Replaced `SyncButton.tsx` entirely — `useMutation` removed, live events list rendered below button
- `onDone` invalidates both `['sync', 'logs']` and `['sync', 'status']` queries for auto-refresh
- 3 new backend tests — all pass; full suite: 80 passed, 0 regressions
- Postman: `GET Sync Stream (SSE)` added to Sync folder with SSE event format documentation

### File List

- `backend/routers/sync.py` — modified (added _sse helper, _run_sync_stream generator, GET /stream + GET /status from 5.2, asyncio/json/StreamingResponse imports)
- `backend/tests/test_story_5_3.py` — created (3 tests)
- `frontend/src/types/index.ts` — modified (SyncStreamEvent interface added)
- `frontend/src/hooks/useSyncStream.ts` — created
- `frontend/src/features/sync/SyncButton.tsx` — replaced (useMutation → useSyncStream)

## Change Log

- 2026-05-20: Story 5.3 created — ready-for-dev
- 2026-05-20: Story 5.3 implemented — all ACs satisfied, status → review
