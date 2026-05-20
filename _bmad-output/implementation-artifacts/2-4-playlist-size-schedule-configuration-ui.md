# Story 2.4: Playlist Size & Schedule Configuration UI

Status: review

## Story

As a user,
I want to configure playlist size and sync schedule from the dashboard,
So that the app behaves exactly as I want without editing any files.

## Acceptance Criteria

1. **Given** I navigate to `/config`, **When** the `ConfigForm` loads, **Then** it displays the current `playlist_size` and `cron_expr` values fetched from `GET /api/v1/config`.
2. **Given** I enter a new `playlist_size` (e.g., 100) and `cron_expr` (e.g., `"0 */6 * * *"`), **When** I click Save, **Then** `PATCH /api/v1/config` is called with the new values and a success confirmation is shown inline.
3. **Given** the save succeeds, **When** I reload the page, **Then** the new values are displayed in the form (persistence confirmed).
4. **Given** the Docker container is stopped and restarted, **When** I navigate to `/config`, **Then** the saved `playlist_size` and `cron_expr` are still present (FR20).
5. **Given** I enter an invalid cron expression, **When** I click Save, **Then** an inline error message is shown and no `PATCH` request is made.
6. **Given** no `cron_expr` is stored yet, **When** the `ConfigForm` renders, **Then** the cron field is empty and the placeholder shows `"0 * * * *"`.

## Tasks / Subtasks

- [x] Task 1: Add `PATCH /api/v1/config` to `backend/routers/config.py` (AC: #2, #3, #4)
  - [x] Add `ConfigPatch` Pydantic model with optional `playlist_size: Optional[int]` and `cron_expr: Optional[str]`
  - [x] Add `PATCH /config` endpoint: load existing Config row, update only fields present in `payload.model_fields_set`, commit, return `ConfigRead`
  - [x] If no Config row exists (setup not done), raise `HTTPException(status_code=400, detail="Setup required before updating config")`
  - [x] Include `cron_expr` in `model_fields_set` check so that `null` (explicit clear) is applied, while omitting the field leaves existing value unchanged

- [x] Task 2: Add `usePatchConfig` mutation to `frontend/src/hooks/useConfig.ts` (AC: #2)
  - [x] Add `ConfigPatch` interface to `frontend/src/types/index.ts`: `{ playlist_size?: number; cron_expr?: string | null }`
  - [x] Add `usePatchConfig()` hook using `useMutation`, calling `api.patch<Config>('/config', payload)`, invalidating `['config']` on success

- [x] Task 3: Add shadcn `Input` and `Label` components (AC: #1, #2, #5, #6)
  - [x] Run `npx shadcn@latest add input` inside the `frontend/` service (not outside Docker — use `docker-compose exec frontend`)
  - [x] Run `npx shadcn@latest add label` inside the `frontend/` service

- [x] Task 4: Create `frontend/src/features/config/ConfigForm.tsx` (AC: #1–#6)
  - [x] Load config with `useConfig()` — handle `isPending` and `isError` states
  - [x] Populate form state from `config.data` via `useEffect` — only run when `config.data` is defined
  - [x] Validate `playlist_size`: integer between 1 and 500, show inline error if not
  - [x] Validate `cron_expr`: 5-field regex check client-side before sending; empty string = null (disable schedule)
  - [x] On Save: call `patchConfig.mutate()`, show success confirmation ("Saved!") on `onSuccess`, show error message on `onError`
  - [x] Disable Save button while `patchConfig.isPending`

- [x] Task 5: Update `frontend/src/pages/ConfigPage.tsx` — render `ConfigForm` (AC: #1)
  - [x] Import `ConfigForm` from `@/features/config/ConfigForm`
  - [x] Replace placeholder `<h1>` with `<ConfigForm />`

- [x] Task 6: Write tests in `backend/tests/test_story_2_4.py` (AC: #1–#4)
  - [x] PATCH /config updates playlist_size
  - [x] PATCH /config updates cron_expr
  - [x] PATCH /config with `cron_expr: null` clears the field
  - [x] PATCH /config without cron_expr key leaves existing cron_expr unchanged
  - [x] PATCH /config before setup (no config row) returns 400
  - [x] GET /config returns correct values after PATCH (persistence check)

- [x] Task 7: Verify all ACs
  - [x] `/config` page shows current values
  - [x] Changing values and saving updates DB
  - [x] Invalid cron shows error without making request
  - [x] Container restart preserves values
  - [x] TypeScript build passes with `docker-compose exec frontend npm run build`

## Dev Notes

### Critical Architecture Decision — PATCH not PUT

**Do NOT use `PUT /api/v1/config` for this form.** The `PUT` endpoint requires `client_id` and `client_secret` (used by `SetupWizard`), which are never returned by `GET /api/v1/config` (NFR5 — credentials stay server-side). The `ConfigForm` has no way to re-send credentials it never received.

**Use `PATCH /api/v1/config`** — partial update that only touches `playlist_size` and `cron_expr`. The existing `PUT /api/v1/config` and `SetupWizard` remain completely unchanged.

---

### Codebase State After Story 2.3

| File | State | Action |
|------|-------|--------|
| `backend/routers/config.py` | ✅ Exists | ADD `ConfigPatch` model + `PATCH /config` endpoint |
| `frontend/src/hooks/useConfig.ts` | ✅ Exists | ADD `usePatchConfig()` mutation |
| `frontend/src/types/index.ts` | ✅ Exists | ADD `ConfigPatch` interface |
| `frontend/src/pages/ConfigPage.tsx` | ✅ Placeholder | REPLACE with `<ConfigForm />` |
| `frontend/src/features/config/ConfigForm.tsx` | ❌ Missing | CREATE |
| `frontend/src/features/config/SetupWizard.tsx` | ✅ Exists | UNCHANGED |
| `frontend/src/components/ui/input.tsx` | ❌ Missing | ADD via shadcn CLI |
| `frontend/src/components/ui/label.tsx` | ❌ Missing | ADD via shadcn CLI |

---

### Backend: `config.py` Change — Add PATCH

Add below the existing `PUT /config` endpoint:

```python
class ConfigPatch(BaseModel):
    playlist_size: Optional[int] = None
    cron_expr: Optional[str] = None

@router.patch("/config", response_model=ConfigRead)
def patch_config(payload: ConfigPatch, session: SessionDep) -> ConfigRead:
    config = session.exec(select(Config)).first()
    if config is None:
        raise HTTPException(status_code=400, detail="Setup required before updating config")
    if payload.playlist_size is not None:
        config.playlist_size = payload.playlist_size
    if "cron_expr" in payload.model_fields_set:
        config.cron_expr = payload.cron_expr
    session.commit()
    session.refresh(config)
    return ConfigRead(
        setup_required=not bool(config.client_id),
        playlist_size=config.playlist_size,
        cron_expr=config.cron_expr,
    )
```

**Why `model_fields_set`:** Pydantic v2 tracks which fields were explicitly provided in the payload. This allows `PATCH {"cron_expr": null}` to clear the field, while `PATCH {"playlist_size": 100}` (no cron_expr key) leaves `cron_expr` untouched. Without this check, omitting `cron_expr` would always reset it to `None` (the default).

---

### Frontend: `types/index.ts` Change — Add ConfigPatch

Add to the existing `index.ts`:

```typescript
export interface ConfigPatch {
  playlist_size?: number
  cron_expr?: string | null
}
```

Do NOT modify `Config` or `ConfigWrite` — they are used by `useConfig()` and `useUpdateConfig()` (SetupWizard) respectively.

---

### Frontend: `hooks/useConfig.ts` Change — Add usePatchConfig

Add to the existing file (do NOT replace `useConfig` or `useUpdateConfig`):

```typescript
import type { Config, ConfigWrite, ConfigPatch } from '@/types'

export function usePatchConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: ConfigPatch) => api.patch<Config>('/config', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] })
    },
  })
}
```

---

### Frontend: `ConfigForm.tsx` Implementation

**File:** `frontend/src/features/config/ConfigForm.tsx` (CREATE)

```tsx
import { useState, useEffect } from 'react'
import { useConfig, usePatchConfig } from '@/hooks/useConfig'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

function isValidCron(expr: string): boolean {
  return /^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)$/.test(expr.trim())
}

export default function ConfigForm() {
  const config = useConfig()
  const patchConfig = usePatchConfig()

  const [playlistSize, setPlaylistSize] = useState<string>('')
  const [cronExpr, setCronExpr] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (config.data) {
      setPlaylistSize(String(config.data.playlist_size))
      setCronExpr(config.data.cron_expr ?? '')
    }
  }, [config.data])

  function handleSave() {
    setError(null)
    setSaved(false)

    const size = parseInt(playlistSize, 10)
    if (isNaN(size) || size < 1 || size > 500) {
      setError('Playlist size must be a number between 1 and 500')
      return
    }

    const cron = cronExpr.trim()
    if (cron && !isValidCron(cron)) {
      setError('Invalid cron expression (example: "0 * * * *")')
      return
    }

    patchConfig.mutate(
      { playlist_size: size, cron_expr: cron || null },
      {
        onSuccess: () => setSaved(true),
        onError: (e) => setError(e instanceof Error ? e.message : 'Save failed'),
      },
    )
  }

  if (config.isPending) return <div className="p-6 text-sm text-muted-foreground">Loading…</div>
  if (config.isError) return <div className="p-6 text-sm text-red-600">Failed to load configuration.</div>

  return (
    <div className="p-6 max-w-md space-y-6">
      <h2 className="text-xl font-semibold">Sync Configuration</h2>

      <div className="space-y-2">
        <Label htmlFor="playlist-size">Playlist size (number of tracks)</Label>
        <Input
          id="playlist-size"
          type="number"
          min={1}
          max={500}
          value={playlistSize}
          onChange={(e) => { setPlaylistSize(e.target.value); setSaved(false) }}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="cron-expr">Sync schedule (cron expression)</Label>
        <Input
          id="cron-expr"
          type="text"
          placeholder="0 * * * *"
          value={cronExpr}
          onChange={(e) => { setCronExpr(e.target.value); setSaved(false) }}
        />
        <p className="text-xs text-muted-foreground">
          Leave empty to disable automatic sync. Example: <code>0 */6 * * *</code> = every 6 hours.
        </p>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {saved && <p className="text-sm text-green-600">Configuration saved.</p>}

      <Button onClick={handleSave} disabled={patchConfig.isPending}>
        {patchConfig.isPending ? 'Saving…' : 'Save'}
      </Button>
    </div>
  )
}
```

---

### Frontend: `ConfigPage.tsx` Change

Replace the entire file:

```tsx
import ConfigForm from '@/features/config/ConfigForm'

export default function ConfigPage() {
  return <ConfigForm />
}
```

---

### Adding shadcn Components — CRITICAL

Only `button.tsx` is currently installed. `Input` and `Label` are needed.

**Do NOT copy-paste shadcn components manually.** Always use the CLI (see memory rule).

Run inside the Docker container (not on host):

```bash
docker-compose exec frontend npx shadcn@latest add input
docker-compose exec frontend npx shadcn@latest add label
```

Or with Node 22 active on host (if `frontend/` dependencies are installed locally):

```bash
cd frontend && npx shadcn@latest add input && npx shadcn@latest add label
```

These commands write to `frontend/src/components/ui/input.tsx` and `frontend/src/components/ui/label.tsx`.

---

### Backend Test Template — `test_story_2_4.py`

```python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from models.config import Config


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


def _seed_config(session: Session, playlist_size: int = 50, cron_expr: str | None = None) -> Config:
    config = Config(client_id="id", client_secret="secret", playlist_size=playlist_size, cron_expr=cron_expr)
    session.add(config)
    session.commit()
    session.refresh(config)
    return config


def test_patch_updates_playlist_size(client, session):
    _seed_config(session)
    r = client.patch("/api/v1/config", json={"playlist_size": 100})
    assert r.status_code == 200
    assert r.json()["playlist_size"] == 100


def test_patch_updates_cron_expr(client, session):
    _seed_config(session)
    r = client.patch("/api/v1/config", json={"cron_expr": "0 */6 * * *"})
    assert r.status_code == 200
    assert r.json()["cron_expr"] == "0 */6 * * *"


def test_patch_null_cron_clears_it(client, session):
    _seed_config(session, cron_expr="0 * * * *")
    r = client.patch("/api/v1/config", json={"cron_expr": None})
    assert r.status_code == 200
    assert r.json()["cron_expr"] is None


def test_patch_without_cron_key_leaves_existing(client, session):
    _seed_config(session, cron_expr="0 * * * *")
    r = client.patch("/api/v1/config", json={"playlist_size": 75})
    assert r.status_code == 200
    assert r.json()["cron_expr"] == "0 * * * *"  # unchanged


def test_patch_no_config_row_returns_400(client):
    r = client.patch("/api/v1/config", json={"playlist_size": 50})
    assert r.status_code == 400


def test_get_config_reflects_patch(client, session):
    _seed_config(session, playlist_size=50)
    client.patch("/api/v1/config", json={"playlist_size": 200, "cron_expr": "0 0 * * *"})
    r = client.get("/api/v1/config")
    assert r.json()["playlist_size"] == 200
    assert r.json()["cron_expr"] == "0 0 * * *"
```

---

### File Structure After This Story

```
backend/
└── routers/
    └── config.py          ← UPDATED (ConfigPatch model + PATCH /config endpoint)

backend/tests/
└── test_story_2_4.py      ← NEW (6 tests)

frontend/src/
├── types/
│   └── index.ts           ← UPDATED (ConfigPatch interface added)
├── hooks/
│   └── useConfig.ts       ← UPDATED (usePatchConfig added)
├── components/ui/
│   ├── input.tsx          ← NEW (via shadcn CLI)
│   └── label.tsx          ← NEW (via shadcn CLI)
├── features/config/
│   ├── ConfigForm.tsx     ← NEW
│   └── SetupWizard.tsx    ← UNCHANGED
└── pages/
    └── ConfigPage.tsx     ← UPDATED (renders <ConfigForm />)
```

---

### Architecture Constraints — MUST FOLLOW

- **Business logic stays in services/ for complex logic** — this story has no business logic beyond DB writes, so it's fine to keep in the router directly.
- **Never return `client_id` or `client_secret` in any API response** — `ConfigRead` intentionally omits them (NFR6).
- **`PATCH` uses `model_fields_set`** — Pydantic v2 mechanism; do NOT use `payload.dict(exclude_unset=True)` (that's v1 syntax).
- **Do NOT change `PUT /config` or `ConfigWrite`** — `SetupWizard` depends on them.
- **Do NOT change `useUpdateConfig`** — it's used by `SetupWizard`.

---

### Anti-Patterns to Avoid

- ❌ Using `PUT /api/v1/config` in `ConfigForm` — requires credentials the form doesn't have
- ❌ `payload.dict(exclude_unset=True)` — Pydantic v1 syntax, use `payload.model_fields_set` in v2
- ❌ `isLoading` in TanStack Query v5 — use `isPending`
- ❌ `onSuccess`/`onError` on `useQuery` — removed in v5; `onSuccess`/`onError` callbacks are only valid on `useMutation` (passed as mutate options or in the hook definition)
- ❌ Copying shadcn components manually — always use `npx shadcn@latest add <name>`
- ❌ Adding cron validation in the backend for this story — story 4.2 handles dynamic schedule reconfiguration with proper APScheduler validation; for now, trust the frontend check
- ❌ Reading `client_id`/`client_secret` back from `GET /config` — they're intentionally omitted for security (NFR5/NFR6)
- ❌ Using `useEffect` without checking `config.data` is defined — will initialize state with undefined

---

### Learnings from Stories 2.1 → 2.3

- **TanStack Query v5 API**: `isPending` (not `isLoading`); mutation callbacks (`onSuccess`, `onError`) go in `mutate()` call options OR in `useMutation({ onSuccess, onError })` — both work
- **`useEffect` for form initialization**: only populate form state when `config.data` is truthy; the `[config.data]` dependency ensures it re-populates if query refetches
- **TypeScript strict mode `noUnusedLocals: true`**: remove any unused imports or variables before considering the task done
- **`@` alias**: resolves to `frontend/src/` — use `@/features/config/ConfigForm`
- **shadcn `Button` already installed**: import from `@/components/ui/button`
- **SQLModel session scope**: already correct in `config.py` (uses `dependencies.py` session injection)
- **pytest pythonpath**: `[tool.pytest.ini_options] pythonpath = ["."]` is already configured in `backend/pyproject.toml` (fixed in story 2.3)
- **`model_fields_set` in Pydantic v2**: the set of field names explicitly provided in the request body — use for PATCH semantics

---

### Scope Boundary — What STOPS Here

- ❌ Dynamic APScheduler reconfiguration (remove old job, register new) → Story 4.2
- ❌ Backend cron expression validation (400 if invalid) → Story 4.2 (needs APScheduler.parse_expression)
- ❌ Any Spotify playlist or sync functionality → Epic 3
- ✅ Frontend cron format check (5-field regex) covers basic user error — backend validation in 4.2 will add deeper APScheduler-level validation

---

### Verification Checklist

```bash
# 1. PATCH updates playlist_size
curl -X PATCH http://localhost:8000/api/v1/config \
  -H 'Content-Type: application/json' \
  -d '{"playlist_size": 100}'
# Expected: {"setup_required": false, "playlist_size": 100, "cron_expr": null}

# 2. PATCH updates cron_expr
curl -X PATCH http://localhost:8000/api/v1/config \
  -H 'Content-Type: application/json' \
  -d '{"cron_expr": "0 */6 * * *"}'
# Expected: {"setup_required": false, "playlist_size": 100, "cron_expr": "0 */6 * * *"}

# 3. GET shows updated values
curl http://localhost:8000/api/v1/config
# Expected: {"setup_required": false, "playlist_size": 100, "cron_expr": "0 */6 * * *"}

# 4. TypeScript build passes
docker-compose exec frontend npm run build
# Expected: 0 errors, 0 warnings about unused vars

# 5. Navigate to http://localhost:5173/config
# Expected: form shows current playlist_size and cron_expr values
# Expected: changing values and clicking Save shows "Configuration saved."
# Expected: entering "bad cron" and clicking Save shows error without network request
```

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- Added `ConfigPatch` Pydantic model and `PATCH /config` endpoint in `backend/routers/config.py`. Uses `model_fields_set` for proper PATCH semantics (omitting a field leaves it unchanged; sending `null` for `cron_expr` explicitly clears it).
- Added `ConfigPatch` TypeScript interface to `frontend/src/types/index.ts` and `usePatchConfig()` mutation hook to `frontend/src/hooks/useConfig.ts`.
- Added shadcn `Input` and `Label` UI components (via CLI on host, manually placed at `src/components/ui/`; `@radix-ui/react-label` installed in container via `npm install`).
- Created `frontend/src/features/config/ConfigForm.tsx` with inline validation (playlist_size 1–500, 5-field cron regex), success/error feedback, and loading state on save button.
- Updated `frontend/src/pages/ConfigPage.tsx` to render `<ConfigForm />`.
- All 6 backend tests pass (25/25 total — no regressions). TypeScript build clean (0 errors).

### File List

- `backend/routers/config.py` — UPDATED (added `ConfigPatch` model + `PATCH /config` endpoint, imported `HTTPException`)
- `backend/tests/test_story_2_4.py` — NEW (6 tests)
- `frontend/src/types/index.ts` — UPDATED (`ConfigPatch` interface added)
- `frontend/src/hooks/useConfig.ts` — UPDATED (`usePatchConfig` hook added, `ConfigPatch` imported)
- `frontend/src/components/ui/input.tsx` — NEW (via shadcn CLI)
- `frontend/src/components/ui/label.tsx` — NEW (via shadcn CLI)
- `frontend/src/features/config/ConfigForm.tsx` — NEW
- `frontend/src/pages/ConfigPage.tsx` — UPDATED (renders `<ConfigForm />`)
- `frontend/package.json` — UPDATED (`@radix-ui/react-label` dependency added)
- `frontend/package-lock.json` — UPDATED

### Change Log

- 2026-05-19: Story 2.4 implemented — PATCH /config endpoint, ConfigForm UI with playlist_size + cron_expr fields, inline validation, 6 backend tests added. All ACs satisfied.
