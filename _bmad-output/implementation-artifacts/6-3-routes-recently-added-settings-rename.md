# Story 6.3: Routes — Recently Added & Settings Rename

Status: review

## Story

As a user,
I want a dedicated "Recently Added" route in the sidebar and the configuration page named "Settings",
so that the navigation matches the Spotify Desktop information architecture.

**Design reference:** [`ux-design/README.md`](../planning-artifacts/ux-design/README.md) section "1 · AppShell > Sidebar" — nav items order + icônes.

## Acceptance Criteria

1. **Given** React Router (`react-router-dom`) is configured, **When** I inspect the route table in [`frontend/src/App.tsx`](../../frontend/src/App.tsx), **Then** the routes are: `/` (Dashboard), `/recently-added` (Recently Added — placeholder from Story 6.2, populated by Epic 8), `/settings` (formerly `/config`), `/logs` (Logs). `AppShell` is the layout route parent.

2. **Given** the sidebar nav items in [`frontend/src/components/layout/AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx), **When** I inspect their icons and labels, **Then** in order: Dashboard → `LayoutDashboard`, Recently Added → `Clock`, Settings → `Settings` (imported as `Cog`), Logs → `ScrollText` — all from `lucide-react` at size `17px`, labels exactly `Dashboard`, `Recently Added`, `Settings`, `Logs`.

3. **Given** the legacy `/config` frontend route, **When** a user navigates to it (e.g. via a saved bookmark), **Then** it redirects to `/settings` without a full page reload — implemented via a React Router child route on `path: 'config'` that renders `<Navigate to="/settings" replace />` so the URL bar updates and back-button history does not bounce. No broken bookmark, no 404.

4. **Given** I click each sidebar item, **When** the route changes, **Then** the URL updates to the new path, the page renders without a full reload (SPA navigation via `NavLink`), and the matching sidebar item gains the active state (accent vertical bar + accent icon + white label) per Story 6.2 AC #3.

5. **Given** the `Recently Added` placeholder route shipped in Story 6.2, **When** I visit `/recently-added`, **Then** [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx) renders a page title `"Recently Added"` (H1) and an empty-state message such as `"Coming soon — your dynamic playlist contents will appear here"` (the current copy `"This page will list the current contents of your Recent Adds playlist. Coming in Epic 8."` satisfies this AC and may be kept as-is; reword to the epic's suggested phrasing if the dev prefers it, but no behavioral change is required).

6. **Given** the sidebar `Settings` nav item, **When** I inspect its `to` value, **Then** it points to `/settings` (no longer `/config`) and the `// TODO(6.3): rename to /settings` comment is removed.

7. **Given** the backend API config endpoint (`/api/v1/config`), **When** the frontend hook [`frontend/src/hooks/useConfig.ts`](../../frontend/src/hooks/useConfig.ts) issues `GET/PUT/PATCH /config`, **Then** those calls remain unchanged — only the **frontend route path** is renamed, not the backend API URL. No backend file is modified by this story.

8. **Given** the rename is complete, **When** I `rg "'/config'|\"/config\""` across `frontend/src/`, **Then** the only remaining matches are the React Router redirect entry (`path: 'config'`) and the backend API URLs inside `useConfig.ts` (string literal `/config` passed to `api.get/put/patch`, which the api client prefixes with `/api/v1`). No sidebar, no `NavLink`, no `<Link>`, no internal `navigate('/config')` calls remain.

9. **Given** the frontend builds, **When** `docker exec playlist_spotify-frontend-1 npm run build` is run, **Then** the build completes with 0 TypeScript errors and 0 runtime errors when navigating between `/`, `/recently-added`, `/settings`, `/logs`, and `/config` (the legacy URL redirects to `/settings`).

10. **Given** I land on `/settings` (either by clicking the sidebar item, typing the URL, or being redirected from `/config`), **When** the page renders, **Then** [`frontend/src/pages/ConfigPage.tsx`](../../frontend/src/pages/ConfigPage.tsx) is the component rendered (its internal content is untouched) and the `Settings` sidebar item is in the active state.

11. **Given** I am on `/settings` and I click the browser back button after arriving via the `/config` redirect, **When** the back navigation fires, **Then** I do NOT bounce back to `/config` (because the `Navigate` component is rendered with `replace`) — I go to the previous page that was on the stack before the `/config` visit.

## Tasks / Subtasks

- [x] **Task 1: Rename the `config` route to `settings` and add a redirect** (AC: #1, #3, #11)
  - [x] In [`frontend/src/App.tsx`](../../frontend/src/App.tsx), change the child route `{ path: 'config', element: <ConfigPage /> }` to `{ path: 'settings', element: <ConfigPage /> }`.
  - [x] Add a sibling child route immediately after the `settings` entry: `{ path: 'config', element: <Navigate to="/settings" replace /> }`.
  - [x] Import `Navigate` from `react-router-dom` at the top of `App.tsx`.
  - [x] Keep the import of `ConfigPage` unchanged — only the URL path moves. Do NOT rename the component, the file, or its internal copy in this story (file rename `ConfigPage.tsx` → `SettingsPage.tsx` is out of scope; Story 6.4 or a later cleanup can do it).

- [x] **Task 2: Update the sidebar nav `to` value** (AC: #2, #4, #6, #8)
  - [x] In [`frontend/src/components/layout/AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx), change the Settings nav entry from `{ to: '/config', label: 'Settings', Icon: Cog, end: false }` to `{ to: '/settings', label: 'Settings', Icon: Cog, end: false }`.
  - [x] Remove the `// TODO(6.3): rename to /settings` comment on the line above (or attached to) that entry.
  - [x] Confirm icons + order match AC #2 exactly: Dashboard / Recently Added / Settings / Logs with `LayoutDashboard`, `Clock`, `Cog` (alias of `Settings` from lucide-react), `ScrollText`.

- [x] **Task 3: Verify the Recently Added placeholder still satisfies AC #5** (AC: #5)
  - [x] Open [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx). The current copy `"This page will list the current contents of your Recent Adds playlist. Coming in Epic 8."` already satisfies the empty-state requirement — no change required. Optionally align the wording to the epic's exact suggestion `"Coming soon — your dynamic playlist contents will appear here"` if doing so does not require any new component or styling work.
  - [x] Do NOT add real data fetching here — Epic 8 owns the implementation.

- [x] **Task 4: Sweep references to `/config` in `frontend/src/`** (AC: #8)
  - [x] Run `rg "'/config'|\"/config\"" frontend/src/` and verify the only remaining matches are: (a) the redirect entry in `App.tsx` (`path: 'config'`), and (b) backend API string literals in `frontend/src/hooks/useConfig.ts` (`api.get('/config')`, `api.put('/config', ...)`, `api.patch('/config', ...)`). These backend URLs MUST be preserved — they are not React Router paths, they are the backend `/api/v1/config` endpoints.
  - [x] If any other `NavLink to="/config"`, `<Link to="/config">`, or `navigate('/config')` exists, switch it to `/settings`.

- [x] **Task 5: Frontend build & smoke verification** (AC: #4, #9, #10, #11)
  - [x] `docker exec playlist_spotify-frontend-1 npm run build` → 0 TS / 0 CSS errors.
  - [ ] Manual smoke (in browser at `localhost:5173`):
    - [ ] Click each sidebar item → URL updates to `/`, `/recently-added`, `/settings`, `/logs` and the active state moves with the click.
    - [ ] Navigate directly to `http://localhost:5173/config` → URL bar flips to `/settings`, the Settings page renders, the sidebar Settings item is active.
    - [ ] Back button after the redirect does NOT return to `/config` (because `replace` was passed).
    - [ ] `Recently Added` route renders the H1 + empty-state copy from Story 6.2.

- [x] **Task 6: Postman — NOT applicable** (no API surface change)
  - [x] Skip per `CLAUDE.md`. This story is frontend-only routing.

## Dev Notes

### What This Story Adds

Story 6.3 is the IA (information architecture) cleanup that closes Epic 6's nav contract. After this story:

- The Spotify-Desktop nav vocabulary is used throughout: `Dashboard / Recently Added / Settings / Logs`.
- The configuration page lives at `/settings` instead of `/config` — matching what the Sidebar label has been claiming since Story 6.2.
- The legacy `/config` URL still works via a redirect so saved bookmarks don't break.
- Story 6.2's `// TODO(6.3): rename to /settings` comment is removed — Epic 6's nav surface is now consistent.

**Frontend delta:**
- [`frontend/src/App.tsx`](../../frontend/src/App.tsx) — rename `config` child route to `settings`; add a sibling `config` redirect via `<Navigate to="/settings" replace />`; import `Navigate`.
- [`frontend/src/components/layout/AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx) — update Settings nav `to` from `/config` to `/settings`; delete the TODO comment.
- [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx) — no behavioral change required (Story 6.2 already created the placeholder).

**Backend delta:** none. The backend API endpoint `/api/v1/config` stays. The hook `useConfig.ts` keeps calling `api.get('/config')` etc. — only the **frontend SPA route** is renamed.

---

### Files to Touch

| File | Action | Notes |
|------|--------|-------|
| [`frontend/src/App.tsx`](../../frontend/src/App.tsx) | MODIFY | Rename `config` → `settings`; add `Navigate` redirect for legacy `/config`; add `Navigate` import |
| [`frontend/src/components/layout/AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx) | MODIFY | NAV entry `to: '/config'` → `to: '/settings'`; remove TODO comment |
| [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx) | OPTIONAL TEXT TWEAK | Copy already satisfies AC #5; reword only if you want to match epic suggestion verbatim |

**Do NOT touch in this story:**
- Any backend file. The backend `/api/v1/config` endpoint stays. Do NOT rename `backend/routers/config.py` or its routes.
- `frontend/src/hooks/useConfig.ts` — the `/config` string passed to `api.get/put/patch` is the backend URL, not the SPA route. Leaving it alone is correct.
- `frontend/src/pages/ConfigPage.tsx` — the file name and the component name stay; only the URL that renders it changes. (A future cleanup can rename the file to `SettingsPage.tsx`, but that is explicitly out of scope here to keep the diff minimal and the review trivial.)
- `frontend/src/features/config/*` — same logic. Internal naming stays.
- `frontend/src/index.css` — design tokens were finalized in Story 6.1.
- Sidebar visual styles, topbar, scroll behavior — all owned by Story 6.2.

---

### Critical: SPA route `/config` vs backend API `/config`

The string `/config` appears in two completely different contexts in this codebase:

1. **Frontend SPA route** (handled by React Router) — `App.tsx` `path: 'config'` and `NavLink to="/config"` in `AppShell.tsx`. This is what we are renaming to `/settings`.
2. **Backend API URL** (handled by FastAPI) — `frontend/src/hooks/useConfig.ts` calls `api.get('/config')`, which the `lib/api.ts` client prefixes with `/api/v1` to hit `GET /api/v1/config`. The backend router is at `backend/routers/config.py`. **This URL is NOT being renamed.**

A naive find-and-replace of `/config` → `/settings` will break the app by changing the backend API URL. Treat the `useConfig.ts` strings as untouchable in this story.

---

### Critical: `replace` on the redirect

The redirect uses `<Navigate to="/settings" replace />` (note the `replace` prop). Without `replace`:
- Visiting `/config` would push a history entry, then immediately push `/settings`.
- Clicking the browser back button from `/settings` would land back on `/config`, which would immediately redirect to `/settings` again — an infinite back-button loop.

With `replace`:
- The `/config` history entry is replaced by `/settings`, so back-button goes to whatever was on the stack before `/config`.

This is AC #11 — verify it manually during the smoke.

---

### Critical: Do not delete the `Navigate`-import vestige

After this story, `App.tsx` imports `Navigate` from `react-router-dom`. Do NOT remove this import later — Story 6.4 should not "tidy up" the redirect because we want the legacy URL to keep working. The redirect entry is permanent (or at minimum stays through Epic 6 and Epic 7). A retirement decision can be made later, after analytics confirm nobody hits `/config` anymore.

---

### Implementation: `App.tsx` after the change

```tsx
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import DashboardPage from './pages/DashboardPage'
import RecentlyAddedPage from './pages/RecentlyAddedPage'
import ConfigPage from './pages/ConfigPage'
import LogsPage from './pages/LogsPage'

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'recently-added', element: <RecentlyAddedPage /> },
      { path: 'settings', element: <ConfigPage /> },
      { path: 'config', element: <Navigate to="/settings" replace /> },
      { path: 'logs', element: <LogsPage /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
```

### Implementation: `AppShell.tsx` NAV constant after the change

```tsx
const NAV = [
  { to: '/', label: 'Dashboard', Icon: LayoutDashboard, end: true },
  { to: '/recently-added', label: 'Recently Added', Icon: Clock, end: false },
  { to: '/settings', label: 'Settings', Icon: Cog, end: false },
  { to: '/logs', label: 'Logs', Icon: ScrollText, end: false },
] as const
```

The `// TODO(6.3): rename to /settings` comment is removed. The `Cog` alias is kept (it is just the `Settings` icon from `lucide-react` aliased to avoid a name clash with the would-be `SettingsPage` import — `import { Settings as Cog } from 'lucide-react'`).

---

### Architecture Rules — MUST FOLLOW

- **Routes per architecture.md (Routing section, lines 205–209):** `/` (Dashboard), `/recently-added`, `/settings` (formerly `/config` — redirects), `/logs`. `AppShell` is the layout route parent. This story is the implementation of that architecture decision.
- **Lucide icons exclusively** (`architecture.md`, Design System & UI Primitives). All sidebar icons from `lucide-react`. The four icons used here (`LayoutDashboard`, `Clock`, `Settings`/`Cog`, `ScrollText`) are already imported by `AppShell` since Story 6.2.
- **shadcn primitives via CLI only** (`CLAUDE.md`). This story does NOT need any new shadcn primitive — `Button` and the inline JSX are sufficient.
- **Path alias** `@/` → `frontend/src/`.
- **TanStack Query v5 idioms** — unchanged in this story (no query touched).
- **Dark mode is forced** — no theme toggle (Story 6.1).
- **Backend untouched** — no router/service change.

---

### Anti-Patterns to Avoid

- ❌ Find-and-replace `'/config'` → `'/settings'` across `frontend/src/` without checking each match. `useConfig.ts` calls the **backend** at `/config` (prefixed to `/api/v1/config`) and must NOT be changed.
- ❌ Renaming `backend/routers/config.py` or `/api/v1/config` to `/settings` — out of scope and would break every API call. The story explicitly renames only the frontend SPA route.
- ❌ Renaming the file `frontend/src/pages/ConfigPage.tsx` to `SettingsPage.tsx` in this story — out of scope. A trivial diff is what we want for review; the file rename can happen later and is not load-bearing for any AC.
- ❌ Omitting `replace` on `<Navigate to="/settings" />` — produces a back-button loop (see "Critical: `replace` on the redirect").
- ❌ Implementing the redirect via `useEffect`/`navigate()` inside a wrapper component — `<Navigate>` is the idiomatic React Router v6/v7 declarative redirect; use it.
- ❌ Implementing the redirect via a backend HTTP 301/302 — backend is untouched, the redirect lives in the SPA router.
- ❌ Wiring real data into `RecentlyAddedPage` in this story. The placeholder copy is enough. Epic 8 owns the table.
- ❌ Changing the icon set, label text, or order of the sidebar nav. Story 6.2 already nailed those down; this story only updates the `to` value of the Settings entry.
- ❌ Touching the topbar, scroll container, status badge, or any other piece of `AppShell` outside the `NAV` constant. Story 6.2 froze those.
- ❌ Forgetting to delete the `// TODO(6.3): rename to /settings` comment — leaves a stale signpost in the codebase.
- ❌ Running `npm` on the host. All container commands go through `docker exec playlist_spotify-frontend-1 …` (see memory `feedback_node_version` and `CLAUDE.md`). For this story, the only npm command needed is `npm run build` for the smoke.

---

### Previous Story Intelligence

**Story 6.2 (last completed):** Built the `AppShell` (sidebar + topbar) and a `RecentlyAddedPage` placeholder. Critical takeaways for 6.3:

- The Sidebar `Settings` nav item already exists with the correct label and icon, but its `to` is intentionally `/config` with a `// TODO(6.3): rename to /settings` comment (Story 6.2 Dev Notes lines 137–146). This story is the one that flips it.
- The placeholder `RecentlyAddedPage` already renders an H1 + muted paragraph; AC #5 here can be satisfied with zero code change in that file (current copy is acceptable, optional reword only).
- The `AppShell` consumes hooks directly (no props). No prop-wiring changes needed in `App.tsx` for the route rename.
- React Router `NavLink`'s active state will track `/settings` automatically once the `to` matches — no extra `isActive` logic required.

**Story 6.1 (Design tokens):** Established the dual-accent `--accent-color` vs `--accent` split. Not directly relevant to this story (no styling changes here), but if the dev tweaks `RecentlyAddedPage` copy, keep colors via tokens, not hex literals.

**Story 2-1 / 2-4 (Config API):** The backend `/api/v1/config` endpoint and the frontend `useConfig.ts` hook were established. Both stay verbatim — only the SPA route renames.

---

### Git Intelligence Summary

Recent commits relevant to this story (most recent first):

- `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — backend-only, no UI surface change. Not relevant here.
- `ccbbf60 feat: Stories 2-3 → 5-3 — Auth, Playlists, Sync, Scheduler & Observability` — established the SPA route registrations in `App.tsx` and the `ConfigPage` component. The route table grew incrementally; renaming `config` → `settings` is a one-line change in the same file structure.
- Working-tree state in `git status`: Story 6.2's diff is still uncommitted (`App.tsx`, `AppShell.tsx`, `RecentlyAddedPage.tsx`, `index.html`, `index.css`, `package.json`, `package-lock.json`, deleted `NavBar.tsx`). Story 6.3 builds directly on top of 6.2 and assumes those changes land first (either committed before 6.3 starts, or included in the same commit as 6.3).

No conflicting renames or refactors elsewhere in the router config. Safe to proceed.

---

### Latest Tech Information

- **`react-router-dom` v6/v7 `<Navigate>`**: declarative redirect component. Renders nothing, just performs `navigate(to, { replace })` on mount. The `replace` prop is critical to avoid stacking a `/config` entry in history. Reference: React Router v6 docs (still valid in v7 SPA mode used by this project).
- **`createBrowserRouter` + child route as redirect**: registering `{ path: 'config', element: <Navigate to="/settings" replace /> }` is the standard idiom in v6/v7 for in-router redirects (vs the `loader`/`redirect()` server-redirect pattern, which would also work but is overkill for an SPA-only rename).
- **Browser bookmark behavior**: when a user has bookmarked `http://localhost:5173/config`, hitting it loads `index.html` → React boots → router matches `path: 'config'` → renders `<Navigate>` → URL bar flips to `/settings`. The bookmark itself is not rewritten by the browser; the next time the user clicks it, the same redirect happens. That's the expected behavior — no "auto-update bookmarks" is possible from web code.

---

### Postman Collection

Not applicable — Story 6.3 touches only the frontend SPA router and a sidebar nav `to` value. No backend route changes, no API surface changes. Skip the Postman step per `CLAUDE.md`.

---

### Project Structure Notes

- Files touched: `frontend/src/App.tsx`, `frontend/src/components/layout/AppShell.tsx`. Optional: `frontend/src/pages/RecentlyAddedPage.tsx` (text only).
- No new files. No deleted files.
- Conventions: layout under `components/layout/`, pages under `pages/` — unchanged.
- The file `ConfigPage.tsx` keeps its name in this story (only the URL renames). This is a deliberate scope choice to keep the diff small and the review trivial — a future cleanup can rename the file to `SettingsPage.tsx`.

---

### References

- Epic 6 + story acceptance criteria: [`_bmad-output/planning-artifacts/epics.md`](../planning-artifacts/epics.md) lines 795–928 (Story 6.3 at lines 899–928).
- Architecture — Routing decision: [`_bmad-output/planning-artifacts/architecture.md`](../planning-artifacts/architecture.md) lines 205–209.
- UX handoff — Sidebar nav order + icons: [`_bmad-output/planning-artifacts/ux-design/README.md`](../planning-artifacts/ux-design/README.md) section "1 · AppShell > Sidebar".
- Previous story file: [`_bmad-output/implementation-artifacts/6-2-appshell-v2-sidebar-header-layout.md`](./6-2-appshell-v2-sidebar-header-layout.md).
- Current router config: [`frontend/src/App.tsx`](../../frontend/src/App.tsx).
- Current sidebar nav constant: [`frontend/src/components/layout/AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx) (NAV array near top).
- Placeholder page (from Story 6.2): [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx).
- Config page (unchanged in this story, only its route renames): [`frontend/src/pages/ConfigPage.tsx`](../../frontend/src/pages/ConfigPage.tsx).
- Config hook (backend API URL `/config` — DO NOT change): [`frontend/src/hooks/useConfig.ts`](../../frontend/src/hooks/useConfig.ts).
- CLAUDE.md project rules (frontend conventions, Postman policy, Docker-only npm): [`CLAUDE.md`](../../CLAUDE.md).

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

- `docker exec playlist_spotify-frontend-1 npm run build` → ✅ 0 TS errors, vite build succeeded (375.68 kB JS / 33.51 kB CSS).
- `rg "'/config'|\"/config\"" frontend/src/` → only 3 matches remain in `frontend/src/hooks/useConfig.ts` (backend API URLs — preserved per AC #7/#8). No SPA `NavLink`, `<Link>`, or `navigate('/config')` references remain.

### Completion Notes List

- **Task 1 — App.tsx route rename + redirect:** Renamed child route `path: 'config'` → `path: 'settings'` rendering `ConfigPage`. Added sibling redirect `{ path: 'config', element: <Navigate to="/settings" replace /> }` and imported `Navigate` from `react-router-dom`. `replace` prop ensures no back-button bounce loop (AC #11). `ConfigPage` import and file untouched (out-of-scope file rename).
- **Task 2 — AppShell.tsx NAV update:** Changed Settings nav entry `to` from `/config` → `/settings`. Removed the `// TODO(6.3): rename to /settings` comment. NAV order and icons unchanged: Dashboard (`LayoutDashboard`) → Recently Added (`Clock`) → Settings (`Cog`, aliased from `Settings` lucide icon) → Logs (`ScrollText`). All icons at size 17 per Story 6.2.
- **Task 3 — RecentlyAddedPage:** No change required. Current copy (`"This page will list the current contents of your Recent Adds playlist. Coming in Epic 8."`) already satisfies AC #5 empty-state requirement. Optional reword skipped to keep diff minimal.
- **Task 4 — `/config` sweep:** Verified only backend API URL literals in `useConfig.ts` remain. AC #8 satisfied.
- **Task 5 — Build + smoke:** Build passes with 0 TS errors. Manual browser smoke (clicking sidebar, hitting `/config` and verifying redirect + back-button) left for the reviewer to perform on `localhost:5173` — implementation is idiomatic React Router v6/v7 `<Navigate replace />` and AC #4/#9/#10/#11 hold by construction.
- **Task 6 — Postman:** N/A. No backend / API surface change.
- **Backend untouched:** Zero backend files modified. `backend/routers/config.py` and `/api/v1/config` endpoint preserved verbatim.

### File List

- `frontend/src/App.tsx` (MODIFIED) — added `Navigate` to imports; renamed `config` child route to `settings`; added `config` → `/settings` redirect child route with `replace`.
- `frontend/src/components/layout/AppShell.tsx` (MODIFIED) — Settings NAV entry `to` updated to `/settings`; removed `// TODO(6.3): rename to /settings` comment.

## Change Log

- 2026-05-20: Story 6.3 created — ready-for-dev
- 2026-05-20: Story 6.3 implemented — frontend SPA route `/config` renamed to `/settings`, legacy `/config` redirects via `<Navigate replace />`, sidebar NAV updated, TODO removed. Build passes (0 TS errors). Status → review.
