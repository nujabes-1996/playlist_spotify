# Story 3.1: Playlist List & Toggle UI

Status: review

## Story

As a user,
I want to see all my Spotify playlists and choose which ones to include in the sync,
So that I control exactly which music sources feed my dynamic playlist.

## Acceptance Criteria

1. **Given** the user is authenticated, **When** `GET /api/v1/playlists` is called, **Then** the response returns all user-created Spotify playlists as an array `[{spotify_id, name, is_included}]`.
2. **Given** `GET /api/v1/playlists` is called, **When** the playlists are fetched from the Spotify API, **Then** they are stored/updated in the `playlist` table in SQLite and the response is served from the DB.
3. **Given** the dashboard loads and the user is authenticated, **When** the playlist list renders, **Then** `PlaylistList` displays each playlist with its name and a toggle (`PlaylistToggle`) showing its current `is_included` state.
4. **Given** I toggle a playlist on or off, **When** `PATCH /api/v1/playlists/{spotify_id}` is called with `{"is_included": true/false}`, **Then** the `is_included` value is updated in SQLite and the toggle reflects the new state immediately.
5. **Given** the playlist list is loading, **When** the TanStack Query fetch is in progress, **Then** a skeleton or loading indicator is shown (not a blank section).
6. **Given** the playlist list refresh from Spotify API, **When** the fetch completes, **Then** it takes under 2 seconds (NFR2).

## Tasks / Subtasks

- [x] Task 1: Add playlist-fetching functions to `backend/services/spotify.py` (AC: #1, #2, #6)
  - [x] Add `get_authenticated_client()` function returning a `Spotify` instance from cached token (mirrors `get_auth_status()` pattern)
  - [x] Add `get_user_playlists()` function: fetches all user-created playlists via `sp.current_user_playlists()` (paginated, 50/page), filters to `owner.id == sp.me()["id"]`, returns list of `{spotify_id, name}`

- [x] Task 2: Create `backend/routers/playlists.py` (AC: #1, #2, #4)
  - [x] Add `PlaylistRead` Pydantic model: `spotify_id: str`, `name: str`, `is_included: bool`
  - [x] Add `PlaylistPatch` Pydantic model: `is_included: bool`
  - [x] `GET /playlists` endpoint: call `spotify_service.get_user_playlists()`, upsert into `playlist` table (add new rows, update `name` on existing, delete rows whose `spotify_id` no longer appears), return all rows as `list[PlaylistRead]`
  - [x] `PATCH /playlists/{spotify_id}` endpoint: load playlist by `spotify_id`, raise 404 if not found, update `is_included`, commit, return `PlaylistRead`

- [x] Task 3: Register playlists router in `backend/main.py` (AC: #1)
  - [x] Import `router as playlists_router` from `routers.playlists`
  - [x] Add `app.include_router(playlists_router, prefix="/api/v1")`

- [x] Task 4: Add `Playlist` type and update `lib/api.ts` in the frontend (AC: #3, #4)
  - [x] Add `Playlist` interface to `frontend/src/types/index.ts`: `{ spotify_id: string; name: string; is_included: boolean }`
  - [x] Add `delete` method to `frontend/src/lib/api.ts` if needed (not required for this story — `patch` already exists)

- [x] Task 5: Create `frontend/src/hooks/usePlaylists.ts` (AC: #3, #4, #5)
  - [x] `usePlaylists()` hook: `useQuery({ queryKey: ['playlists'], queryFn: () => api.get<Playlist[]>('/playlists') })`
  - [x] `useTogglePlaylist()` hook: `useMutation` calling `api.patch<Playlist>(\`/playlists/${spotifyId}\`, { is_included })`, invalidating `['playlists']` on success

- [x] Task 6: Create `frontend/src/features/playlists/PlaylistToggle.tsx` (AC: #4)
  - [x] Props: `spotify_id: string`, `name: string`, `is_included: boolean`
  - [x] Renders a toggle/switch (use a `<button>` with visual on/off state or shadcn `Switch` if available — see note below)
  - [x] On click: call `togglePlaylist.mutate({ spotifyId, is_included: !is_included })`
  - [x] Disable toggle while mutation is pending to prevent double-toggle

- [x] Task 7: Create `frontend/src/features/playlists/PlaylistList.tsx` (AC: #3, #5)
  - [x] Call `usePlaylists()` — handle `isPending` with skeleton rows (3–5 placeholder divs), `isError` with error message
  - [x] Map over playlists array, render a `PlaylistToggle` per entry
  - [x] Empty state when no playlists returned: "No playlists found. Make sure your Spotify account has playlists."

- [x] Task 8: Update `frontend/src/pages/DashboardPage.tsx` (AC: #3)
  - [x] Import and render `<PlaylistList />` in the authenticated branch (replace the placeholder `<h1>Dashboard</h1>`)

- [x] Task 9: Write backend tests in `backend/tests/test_story_3_1.py` (AC: #1, #2, #4)
  - [x] `GET /api/v1/playlists` returns empty list when no playlists in DB and Spotify returns none (mock Spotify service)
  - [x] `GET /api/v1/playlists` upserts playlists from Spotify into DB and returns them
  - [x] `GET /api/v1/playlists` removes playlist from DB if no longer returned by Spotify
  - [x] `PATCH /api/v1/playlists/{spotify_id}` updates `is_included` to true
  - [x] `PATCH /api/v1/playlists/{spotify_id}` updates `is_included` to false
  - [x] `PATCH /api/v1/playlists/nonexistent` returns 404

- [x] Task 10: Verify all ACs
  - [x] Dashboard shows playlist list when authenticated
  - [x] Toggling a playlist updates its state immediately and persists
  - [x] Loading skeleton visible during fetch
  - [x] TypeScript build passes: `docker-compose exec frontend npm run build`

## Dev Notes

### Codebase State Entering This Story

| File | State | Action |
|------|-------|--------|
| `backend/routers/playlists.py` | ❌ Missing | CREATE |
| `backend/routers/auth.py` | ✅ Exists | UNCHANGED |
| `backend/routers/config.py` | ✅ Exists | UNCHANGED |
| `backend/main.py` | ✅ Exists | ADD playlists router registration |
| `backend/services/spotify.py` | ✅ Exists (partial) | ADD `get_authenticated_client()` + `get_user_playlists()` |
| `backend/models/playlist.py` | ✅ Exists | UNCHANGED — model is already correct |
| `backend/tests/test_story_3_1.py` | ❌ Missing | CREATE |
| `frontend/src/types/index.ts` | ✅ Exists | ADD `Playlist` interface |
| `frontend/src/hooks/usePlaylists.ts` | ❌ Missing | CREATE |
| `frontend/src/features/playlists/PlaylistToggle.tsx` | ❌ Missing | CREATE |
| `frontend/src/features/playlists/PlaylistList.tsx` | ❌ Missing | CREATE |
| `frontend/src/pages/DashboardPage.tsx` | ✅ Exists (placeholder) | REPLACE authenticated branch with `<PlaylistList />` |
| `frontend/src/lib/api.ts` | ✅ Exists | UNCHANGED — `patch` method already supports path params |

---

### Backend: `services/spotify.py` — New Functions to Add

Add these two functions at the end of the file (below `get_auth_status`):

```python
def get_authenticated_client() -> Spotify:
    """Return an authenticated Spotify client, refreshing the token if needed."""
    sp_oauth = _get_spotify_oauth()
    token_info = sp_oauth.get_cached_token()
    if token_info is None:
        raise ValueError("Not authenticated — run OAuth2 flow first")
    token_info = sp_oauth.validate_token(token_info)
    if token_info is None:
        raise ValueError("Token expired and could not be refreshed")
    return Spotify(auth=token_info["access_token"])


def get_user_playlists() -> list[dict]:
    """Fetch all user-owned playlists from Spotify. Returns [{spotify_id, name}]."""
    sp = get_authenticated_client()
    user_id = sp.me()["id"]
    results = []
    offset = 0
    limit = 50
    while True:
        page = sp.current_user_playlists(limit=limit, offset=offset)
        for item in page["items"]:
            if item["owner"]["id"] == user_id:
                results.append({"spotify_id": item["id"], "name": item["name"]})
        if page["next"] is None:
            break
        offset += limit
    return results
```

**Why `validate_token` before using:** spotipy's `validate_token` auto-refreshes an expired access token using the stored refresh token via `SQLiteCacheHandler`. This is the same pattern used in `get_auth_status()` and keeps token refresh transparent (FR3).

---

### Backend: `routers/playlists.py` — Full Implementation

Create this file at `backend/routers/playlists.py`:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from dependencies import SessionDep
from models.playlist import Playlist
from services import spotify as spotify_service

router = APIRouter(tags=["playlists"])


class PlaylistRead(BaseModel):
    spotify_id: str
    name: str
    is_included: bool


class PlaylistPatch(BaseModel):
    is_included: bool


@router.get("/playlists", response_model=list[PlaylistRead])
def get_playlists(session: SessionDep) -> list[PlaylistRead]:
    try:
        spotify_playlists = spotify_service.get_user_playlists()
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    spotify_ids = {p["spotify_id"] for p in spotify_playlists}

    # Upsert: add new, update name of existing
    for p in spotify_playlists:
        existing = session.exec(
            select(Playlist).where(Playlist.spotify_id == p["spotify_id"])
        ).first()
        if existing:
            existing.name = p["name"]
        else:
            session.add(Playlist(spotify_id=p["spotify_id"], name=p["name"]))

    # Delete playlists no longer in Spotify
    db_playlists = session.exec(select(Playlist)).all()
    for db_p in db_playlists:
        if db_p.spotify_id not in spotify_ids:
            session.delete(db_p)

    session.commit()

    rows = session.exec(select(Playlist)).all()
    return [PlaylistRead(spotify_id=r.spotify_id, name=r.name, is_included=r.is_included) for r in rows]


@router.patch("/playlists/{spotify_id}", response_model=PlaylistRead)
def toggle_playlist(spotify_id: str, payload: PlaylistPatch, session: SessionDep) -> PlaylistRead:
    playlist = session.exec(
        select(Playlist).where(Playlist.spotify_id == spotify_id)
    ).first()
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    playlist.is_included = payload.is_included
    session.commit()
    session.refresh(playlist)
    return PlaylistRead(spotify_id=playlist.spotify_id, name=playlist.name, is_included=playlist.is_included)
```

---

### Backend: `main.py` — Register Playlists Router

Add two lines to `main.py` (mirror the existing auth and config pattern):

```python
from routers.playlists import router as playlists_router
# ... (in the body, after existing include_router calls)
app.include_router(playlists_router, prefix="/api/v1")
```

Full updated imports block in `main.py`:
```python
from routers.auth import router as auth_router
from routers.config import router as config_router
from routers.playlists import router as playlists_router
```

And in the app setup block:
```python
app.include_router(config_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(playlists_router, prefix="/api/v1")
```

---

### Frontend: `types/index.ts` — Add Playlist Interface

Add below `AuthStatus` (do NOT modify existing interfaces):

```typescript
export interface Playlist {
  spotify_id: string
  name: string
  is_included: boolean
}
```

---

### Frontend: `hooks/usePlaylists.ts` — New File

Create `frontend/src/hooks/usePlaylists.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Playlist } from '@/types'

export function usePlaylists() {
  return useQuery({
    queryKey: ['playlists'],
    queryFn: () => api.get<Playlist[]>('/playlists'),
  })
}

export function useTogglePlaylist() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ spotifyId, is_included }: { spotifyId: string; is_included: boolean }) =>
      api.patch<Playlist>(`/playlists/${spotifyId}`, { is_included }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playlists'] })
    },
  })
}
```

---

### Frontend: `features/playlists/PlaylistToggle.tsx` — New File

Create `frontend/src/features/playlists/PlaylistToggle.tsx`:

```tsx
import { useTogglePlaylist } from '@/hooks/usePlaylists'

interface Props {
  spotify_id: string
  name: string
  is_included: boolean
}

export default function PlaylistToggle({ spotify_id, name, is_included }: Props) {
  const toggle = useTogglePlaylist()
  const isPending = toggle.isPending && toggle.variables?.spotifyId === spotify_id

  return (
    <div className="flex items-center justify-between py-2 px-3 rounded hover:bg-muted/50">
      <span className="text-sm">{name}</span>
      <button
        onClick={() => toggle.mutate({ spotifyId: spotify_id, is_included: !is_included })}
        disabled={isPending}
        aria-pressed={is_included}
        aria-label={`${is_included ? 'Exclude' : 'Include'} ${name}`}
        className={`relative w-10 h-6 rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
          is_included ? 'bg-primary' : 'bg-input'
        } disabled:opacity-50`}
      >
        <span
          className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-background shadow transition-transform ${
            is_included ? 'translate-x-4' : 'translate-x-0'
          }`}
        />
      </button>
    </div>
  )
}
```

**Why check `toggle.variables?.spotifyId === spotify_id`:** multiple toggles can be rendered at once; only disable the one whose mutation is in flight, not all of them.

---

### Frontend: `features/playlists/PlaylistList.tsx` — New File

Create `frontend/src/features/playlists/PlaylistList.tsx`:

```tsx
import { usePlaylists } from '@/hooks/usePlaylists'
import PlaylistToggle from './PlaylistToggle'

function SkeletonRow() {
  return (
    <div className="flex items-center justify-between py-2 px-3">
      <div className="h-4 w-48 rounded bg-muted animate-pulse" />
      <div className="h-6 w-10 rounded-full bg-muted animate-pulse" />
    </div>
  )
}

export default function PlaylistList() {
  const { data: playlists, isPending, isError } = usePlaylists()

  if (isPending) {
    return (
      <div className="divide-y">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonRow key={i} />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <p className="text-sm text-red-600 p-3">
        Failed to load playlists. Make sure you are connected to Spotify.
      </p>
    )
  }

  if (playlists.length === 0) {
    return (
      <p className="text-sm text-muted-foreground p-3">
        No playlists found. Make sure your Spotify account has playlists.
      </p>
    )
  }

  return (
    <div className="divide-y border rounded-lg overflow-hidden">
      {playlists.map((p) => (
        <PlaylistToggle key={p.spotify_id} {...p} />
      ))}
    </div>
  )
}
```

---

### Frontend: `pages/DashboardPage.tsx` — Update Authenticated Branch

Replace the placeholder in the authenticated branch only (do NOT change setup/auth/reauth logic):

```tsx
// Before (last line of the authenticated branch):
return <h1 className="text-2xl font-bold">Dashboard</h1>

// After:
import PlaylistList from '@/features/playlists/PlaylistList'
// ...
return (
  <div className="p-6 space-y-4">
    <h1 className="text-2xl font-bold">Dashboard</h1>
    <PlaylistList />
  </div>
)
```

---

### Backend Tests: `test_story_3_1.py`

```python
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from models.playlist import Playlist


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


MOCK_PLAYLISTS = [
    {"spotify_id": "abc", "name": "My Mix"},
    {"spotify_id": "def", "name": "Chill Vibes"},
]


def test_get_playlists_returns_upserted_list(client):
    with patch("routers.playlists.spotify_service.get_user_playlists", return_value=MOCK_PLAYLISTS):
        r = client.get("/api/v1/playlists")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["spotify_id"] == "abc"
    assert data[0]["is_included"] is False


def test_get_playlists_updates_name(client, session):
    session.add(Playlist(spotify_id="abc", name="Old Name"))
    session.commit()
    with patch("routers.playlists.spotify_service.get_user_playlists", return_value=MOCK_PLAYLISTS):
        r = client.get("/api/v1/playlists")
    assert r.status_code == 200
    updated = next(p for p in r.json() if p["spotify_id"] == "abc")
    assert updated["name"] == "My Mix"


def test_get_playlists_removes_deleted(client, session):
    session.add(Playlist(spotify_id="gone", name="Old Playlist"))
    session.commit()
    with patch("routers.playlists.spotify_service.get_user_playlists", return_value=MOCK_PLAYLISTS):
        r = client.get("/api/v1/playlists")
    assert r.status_code == 200
    ids = [p["spotify_id"] for p in r.json()]
    assert "gone" not in ids


def test_patch_sets_included_true(client, session):
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=False))
    session.commit()
    r = client.patch("/api/v1/playlists/abc", json={"is_included": True})
    assert r.status_code == 200
    assert r.json()["is_included"] is True


def test_patch_sets_included_false(client, session):
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=True))
    session.commit()
    r = client.patch("/api/v1/playlists/abc", json={"is_included": False})
    assert r.status_code == 200
    assert r.json()["is_included"] is False


def test_patch_nonexistent_returns_404(client):
    r = client.patch("/api/v1/playlists/nonexistent", json={"is_included": True})
    assert r.status_code == 404
```

---

### Architecture Constraints — MUST FOLLOW

- **Business logic in services/** — `get_user_playlists()` lives in `services/spotify.py`, not in the router
- **Never raw spotipy in routers** — always via `services/spotify.py`
- **No camelCase in JSON** — all fields are snake_case: `spotify_id`, `is_included`
- **No wrapper** — `GET /api/v1/playlists` returns a plain array `[...]`, not `{"data": [...]}`
- **TanStack Query key** — `['playlists']` (matches architecture doc)
- **`isPending` not `isLoading`** — TanStack Query v5 API
- **`useEffect` dependency** — not needed here; data flows directly from `usePlaylists()`

---

### Anti-Patterns to Avoid

- ❌ Returning `id` (DB primary key) in `PlaylistRead` — `spotify_id` is the identifier used both in the path param and in the frontend
- ❌ Calling `sp.current_user_playlists()` in the router — must be in `services/spotify.py`
- ❌ Using `useLoading` or `isLoading` in TanStack Query v5 — use `isPending`
- ❌ Manual loading state (`useState(true)`) — use TanStack Query's `isPending`
- ❌ Shadcn Switch component without checking it's installed — use a plain `<button>` styled as a toggle (avoids a CLI install step); shadcn Switch can be added in a later story
- ❌ `onSuccess`/`onError` on `useQuery` in v5 — these callbacks are only on `useMutation`
- ❌ Forgetting to register the playlists router in `main.py` — the endpoint will 404 silently

---

### Learnings from Epic 2 Stories

- **Pydantic v2** — `model_fields_set` for PATCH semantics; `BaseModel` (not `SQLModel`) for request/response schemas in routers
- **TanStack Query v5** — `isPending` (not `isLoading`); mutation callbacks (`onSuccess`) can go in `useMutation` definition or in the `mutate()` call options
- **TypeScript strict mode** — `noUnusedLocals: true` is on; remove any unused imports before calling complete
- **`@` alias** — resolves to `frontend/src/`; use `@/features/playlists/PlaylistList`
- **pytest `pythonpath = ["."]`** already set in `backend/pyproject.toml` — tests run from `backend/` directory
- **Test fixture pattern** — `session_fixture` + `client_fixture` with `app.dependency_overrides` is the established pattern (see `test_story_2_4.py`)
- **Mocking services** — use `unittest.mock.patch("routers.playlists.spotify_service.get_user_playlists", ...)` to mock at the import site in the router module

---

### Scope Boundary — What STOPS Here

- ❌ `is_included` persistence across restarts → Story 3.2 (it's implicit here since SQLite persists, but the explicit "restart test" is Story 3.2's acceptance criteria)
- ❌ Playlist library refresh on Spotify library changes → Story 3.2
- ❌ Track harvest / sync engine → Stories 3.3–3.5
- ❌ Manual sync trigger (`POST /api/v1/sync/run`) → Story 3.5
- ✅ This story covers: fetch-upsert-display-toggle flow only

---

### Verification Checklist

```bash
# 1. GET playlists (requires authenticated Spotify session)
curl http://localhost:8000/api/v1/playlists
# Expected: [{spotify_id: "...", name: "...", is_included: false}, ...]

# 2. Toggle a playlist
curl -X PATCH http://localhost:8000/api/v1/playlists/<spotify_id> \
  -H 'Content-Type: application/json' \
  -d '{"is_included": true}'
# Expected: {spotify_id: "...", name: "...", is_included: true}

# 3. Verify persistence
curl http://localhost:8000/api/v1/playlists
# Expected: same playlist shows is_included: true

# 4. Non-existent patch
curl -X PATCH http://localhost:8000/api/v1/playlists/bad_id \
  -H 'Content-Type: application/json' \
  -d '{"is_included": true}'
# Expected: 404

# 5. Frontend build
docker-compose exec frontend npm run build
# Expected: 0 errors, 0 warnings about unused vars

# 6. Visual check: http://localhost:5173
# Expected: authenticated user sees playlist list with toggles
# Expected: toggling updates state immediately without page reload
# Expected: skeleton shown during initial load
```

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `get_authenticated_client()` and `get_user_playlists()` to `backend/services/spotify.py`. Client reuses `_get_spotify_oauth()` + `validate_token()` pattern from `get_auth_status()` for transparent token refresh (FR3). Pagination via `current_user_playlists(limit=50, offset=...)` until `page["next"] is None`, filtered to user-owned playlists only.
- Created `backend/routers/playlists.py` with `GET /playlists` (fetch Spotify → upsert DB → delete removed → return all) and `PATCH /playlists/{spotify_id}` (load by spotify_id → 404 if not found → update is_included → commit). Business logic stays in service; router only handles HTTP.
- Registered `playlists_router` in `main.py`.
- Added `Playlist` interface to `frontend/src/types/index.ts`.
- Created `frontend/src/hooks/usePlaylists.ts` with `usePlaylists()` (query key `['playlists']`) and `useTogglePlaylist()` mutation that invalidates `['playlists']` on success.
- Created `PlaylistToggle.tsx`: pure CSS toggle button (no shadcn Switch needed), disables only the specific toggled row during mutation (`toggle.variables?.spotifyId === spotify_id`).
- Created `PlaylistList.tsx`: skeleton loading (4 animated rows), error state, empty state, and playlist list with border+divide layout.
- Updated `DashboardPage.tsx`: replaced `<h1>Dashboard</h1>` placeholder with `<PlaylistList />` in the authenticated branch.
- All 7 new backend tests pass. Full suite: 32/32 passed (0 regressions). TypeScript build: 0 errors.

### File List

- `backend/services/spotify.py` — UPDATED (added `get_authenticated_client()` + `get_user_playlists()`)
- `backend/routers/playlists.py` — NEW (`PlaylistRead`, `PlaylistPatch`, `GET /playlists`, `PATCH /playlists/{spotify_id}`)
- `backend/main.py` — UPDATED (imported and registered `playlists_router`)
- `backend/tests/test_story_3_1.py` — NEW (7 tests: upsert, name update, delete removed, preserve is_included, patch true/false, 404)
- `frontend/src/types/index.ts` — UPDATED (`Playlist` interface added)
- `frontend/src/hooks/usePlaylists.ts` — NEW (`usePlaylists`, `useTogglePlaylist`)
- `frontend/src/features/playlists/PlaylistToggle.tsx` — NEW
- `frontend/src/features/playlists/PlaylistList.tsx` — NEW
- `frontend/src/pages/DashboardPage.tsx` — UPDATED (renders `<PlaylistList />` when authenticated)

### Change Log

- 2026-05-19: Story 3.1 implemented — GET/PATCH playlists endpoints, upsert/delete DB sync from Spotify, PlaylistList + PlaylistToggle UI with skeleton loading, 7 backend tests added, 32/32 suite green, TS build clean.
