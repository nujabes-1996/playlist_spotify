# Story 6.2: AppShell v2 — Sidebar & Header Layout

Status: review

## Story

As a user,
I want a persistent left sidebar and top header on every page,
So that navigation, sync status, and the manual sync action are always one click away.

**Design reference:** [`ux-design/README.md`](../planning-artifacts/ux-design/README.md) section "1 · AppShell (layout)" + [`ux-design/snippets/AppShell.tsx`](../planning-artifacts/ux-design/snippets/AppShell.tsx) (baseline drop-in à reprendre).

## Acceptance Criteria

1. **Given** the frontend renders, **When** any route loads, **Then** the layout uses an outer CSS grid: `grid-template-columns: var(--sidebar-w) 1fr; gap: 8px; padding: 8px; height: 100vh; background: var(--bg-base);` — matching `snippets/AppShell.tsx`.

2. **Given** the `Sidebar`, **When** I inspect its structure, **Then** it has: background `var(--bg-app)`, border-radius `8px`, padding ≈ `18px 12px 12px` (the snippet uses `p-3 pt-4`, which yields the same visual result), and contains in order — (1) brand block (28×28 gradient square accent→cyan + wordmark `playlist_spotify` weight 700 size 15px with `_` colored accent), (2) `WORKSPACE` label (uppercase, letter-spacing 0.08em, 10px, muted), (3) nav items, (4) footer block (`mt-auto`, border-top `var(--border-soft)`, avatar 26×26 + connected-as 3-line block).

3. **Given** sidebar nav items, **When** I inspect each item, **Then** each shows a lucide icon 17px + label 13.5px weight 600. Hover state = `var(--bg-hover)` + white text. Active state = `var(--bg-elevated-2)` + white text + 3px accent vertical bar on the left (via a `before:` pseudo-element) + accent icon color. Nav items in order: `Dashboard` (LayoutDashboard icon, `/`), `Recently Added` (Clock icon, `/recently-added`), `Settings` (Settings icon, `/config` — will be renamed to `/settings` in Story 6.3), `Logs` (ScrollText icon, `/logs`).

4. **Given** the topbar inside the main area, **When** I inspect its structure, **Then** it is sticky (height `var(--header-h)` = 64px, padding `0 32px`, `backdrop-filter: blur(14px)`) and contains — left: two 32×32 circular nav buttons disabled (`ChevronLeft`/`ChevronRight`, `bg-black/55`, muted icon); on the Dashboard route only: search pill (`bg-elevated-2`, rounded-full, width ~320px, `Search` icon, placeholder `"Filter playlists…"`, focus-within border `var(--border-strong)`); right: status badge (rounded-full, `bg-elevated-2`, font-size 12px, weight 600, accent dot + `"Last sync · {relativeTime}"` — red dot + `"Last sync failed · {relativeTime}"` on error) + primary `"Sync now"` button (`RotateCw` icon, rounded-full, `var(--accent-color)` bg, black text, hover lightens to `var(--accent-hover)` + scale 1.03, icon `animate-spin` while syncing, label flips to `"Syncing…"` and button is disabled).

5. **Given** the main area background, **When** I inspect its CSS, **Then** it uses `linear-gradient(180deg, var(--bg-elevated) 0%, var(--bg-app) 280px)` (rendered via Tailwind arbitrary `bg-gradient-to-b from-[var(--bg-elevated)] via-[var(--bg-elevated)] to-[var(--bg-app)]` with `backgroundSize: "100% 280px"; backgroundRepeat: "no-repeat";`) so the top of every page has a subtle accent-tinted gradient that fades into the base.

6. **Given** scrolling the content below the topbar, **When** `scrollTop > 4`, **Then** the topbar background becomes solid `rgba(18,18,18,0.95)` with a 1px bottom border `var(--border-soft)` (driven by a `scrolled` state from `onScroll` on the scroll container, the only scroll container in the layout).

7. **Given** the previous `NavBar` component is no longer used, **When** I grep the codebase, **Then** no references to the old top NavBar remain — `AppShell` is the single source of truth for chrome. The file `frontend/src/components/layout/NavBar.tsx` is **deleted**.

8. **Given** I am on a route, **When** the sidebar renders, **Then** the matching nav item is visually highlighted via React Router `NavLink`'s `isActive` (active styles per AC #3). The `Dashboard` link uses `end` so it does not match descendant routes.

9. **Given** the Sidebar footer renders, **When** I inspect it, **Then** it shows: a 26×26 gradient circle avatar with the user's initials (uppercase, first 2 chars of the connected email/user id) + `"Connected as"` label (12px, weight 600, white) + the email/user id (13px, weight 700, white, truncated) + a status dot row (`bg-[var(--accent-color)]` when authenticated, `bg-[var(--danger)]` when not) followed by `"Token healthy"` / `"Token expired"`. Wiring: read from the existing `useAuthStatus()` hook — display `spotify_user_id` (fallback `"you@spotify"`) as the identifier, and use `authenticated` (true → ok, false → err) to drive the dot color and label.

10. **Given** the AppShell renders on desktop (≥1024px), **When** I inspect spacing, **Then** generous padding/gaps are used consistent with Spotify Desktop density (outer grid gap 8px + padding 8px; topbar `px-8`; content scroll wrapper `px-8 pb-10 pt-2`). Smaller breakpoints are not in scope for this story (Story 6.4 handles responsive).

11. **Given** the topbar `"Sync now"` button, **When** clicked, **Then** it triggers the same SSE sync flow currently powering `SyncButton` (i.e. calls `startStream` from `useSyncStream()`) — `isStreaming` drives the `syncing` prop (label + spin + disabled). The legacy `<SyncButton />` block remains usable inside the Dashboard page for now (it still renders the live event log); only the trigger button is duplicated in the topbar. Cleaning up the in-page button is Story 6.4's concern.

12. **Given** the topbar status badge, **When** rendered, **Then** it consumes `useSyncStatus()` and shows: when `data.status === 'success'` → accent dot + `"Last sync · {relative}"`; when `data.status === 'failure'` → red dot + `"Last sync failed · {relative}"`; when `data == null` → muted dot + `"Never synced"`. Use a small inline `formatRelative(timestamp)` helper (e.g. `"4 min ago"`, `"2 h ago"`, `"3 d ago"`) — `Intl.RelativeTimeFormat('en', { numeric: 'auto' })` is acceptable; no new dependency.

13. **Given** the search pill on Dashboard, **When** rendered, **Then** it is purely visual/inert for this story — the input is uncontrolled, has no `onChange` wired to global state, and does not filter anything. The actual filtering is wired in Epic 7. (Showing the pill conditionally on `/` is the only Dashboard-aware behavior in `AppShell`.)

14. **Given** the `frontend/package.json`, **When** I inspect dependencies, **Then** `lucide-react` is added (current latest stable, no peer-dep conflicts with React 19). Installed via `docker exec playlist_spotify-frontend-1 npm install lucide-react` so the lockfile inside the container stays consistent.

15. **Given** the frontend builds, **When** `docker exec playlist_spotify-frontend-1 npm run build` is run, **Then** the build completes with no TypeScript errors and no runtime errors when navigating between all current routes (`/`, `/config`, `/logs`, plus the new `/recently-added` placeholder).

16. **Given** a `/recently-added` route is referenced by the sidebar, **When** it is visited, **Then** a tiny placeholder page exists so the link is not a 404. The placeholder renders a single H1 `"Recently Added"` + muted paragraph `"This page will list the current contents of your Recent Adds playlist. Coming in Epic 8."`. The real implementation is Epic 8 (Story 8.x).

17. **Given** the AppShell renders, **When** the `useAuthStatus()` query is still pending or has failed, **Then** the sidebar footer must not crash — render a neutral state (avatar with `"?"`, label `"Connecting…"` or `"Not connected"`, muted dot). The rest of the chrome must still render (sidebar nav + topbar are independent of auth).

## Tasks / Subtasks

- [x] **Task 1: Install `lucide-react`** (AC: #14)
  - [x] `docker exec playlist_spotify-frontend-1 npm install lucide-react`
  - [x] Verify `frontend/package.json` and `frontend/package-lock.json` are updated
  - [x] Sanity-check the import: `import { LayoutDashboard } from "lucide-react"` resolves

- [x] **Task 2: Rewrite `frontend/src/components/layout/AppShell.tsx`** (AC: #1, #2, #3, #4, #5, #6, #8, #9, #10, #11, #12, #13, #17)
  - [x] Baseline from `ux-design/snippets/AppShell.tsx`, adapted (no props)
  - [x] Hooks: `useAuthStatus()`, `useSyncStatus()`, `useSyncStream()`. No props on `AppShell`.
  - [x] `showSearch` derived from `useLocation().pathname === '/'`
  - [x] Hidden-count badge omitted (Epic 7)
  - [x] `connectedAs` from `useAuthStatus().data?.spotify_user_id` w/ fallback; inline initials helper
  - [x] Single scroll container with `onScroll` driving `scrolled` state
  - [x] All Spotify-green surfaces use `var(--accent-color)`
  - [x] Inline `formatRelative(iso)` with `Intl.RelativeTimeFormat` + `"Never synced"` for null
  - [x] `Sync now` wired to `startStream()`; disabled + spin on `isStreaming`
  - [x] `<Outlet />` lives inside `flex-1 overflow-y-auto > px-8 pb-10 pt-2`

- [x] **Task 3: Add the `/recently-added` placeholder route** (AC: #15, #16)
  - [x] Created `frontend/src/pages/RecentlyAddedPage.tsx` (H1 + muted paragraph)
  - [x] Registered child route between `index` and `config` in `App.tsx`

- [x] **Task 4: Delete the legacy `NavBar`** (AC: #7)
  - [x] Deleted `frontend/src/components/layout/NavBar.tsx`
  - [x] No `NavBar` import remains
  - [x] `rg "NavBar" frontend/src/` returns 0 matches
  - [x] In-page `SyncButton` untouched (Story 6.4 cleanup)

- [x] **Task 5: Snap the Dashboard topbar layout** (AC: #4, #11, #12, #13)
  - [x] In-page `SyncButton` left in place — visual duplication noted for Story 6.4
  - [x] No edits to `SyncStatusBadge.tsx` — topbar badge implemented inline in `AppShell`

- [x] **Task 6: Verify shadcn primitives still work and no new ones are required** (AC: #15)
  - [x] Only `Button` used; no new primitive installed

- [x] **Task 7: Build & smoke verification** (AC: #15)
  - [x] `docker exec playlist_spotify-frontend-1 npm run build` → 0 TS / 0 CSS errors (1825 modules, built in 383ms)
  - [ ] Manual browser smoke (deferred to user — dev server running)
  - [ ] Manual `Sync now` smoke (deferred to user)
  - [ ] Manual scroll → opaque topbar smoke (deferred to user)

- [x] **Task 8: Postman — NOT applicable** (no API surface change)
  - [x] Skipped per CLAUDE.md

## Dev Notes

### What This Story Adds

Story 6.2 is the layout backbone of Epic 6. It introduces the persistent Spotify-Desktop-style **sidebar + topbar** that wraps every route. After this story:

- Every page renders inside the new `AppShell` (grid: sidebar 248px + main area with gradient and sticky topbar).
- The `Sync now` action and the `Last sync · …` status badge are always visible in the topbar.
- The legacy `NavBar` is gone for good.
- The sidebar lists the 4 Spotify-Desktop nav items (`Dashboard`, `Recently Added`, `Settings`, `Logs`) — only `Recently Added` is new and lands as a placeholder route (real content arrives in Epic 8).

**Frontend delta:**
- `frontend/src/components/layout/AppShell.tsx` — full rewrite (new structure based on `ux-design/snippets/AppShell.tsx`, but consuming TanStack Query hooks instead of props).
- `frontend/src/components/layout/NavBar.tsx` — **deleted**.
- `frontend/src/pages/RecentlyAddedPage.tsx` — **created** (placeholder).
- `frontend/src/App.tsx` — register `/recently-added` route.
- `frontend/package.json` + `package-lock.json` — add `lucide-react`.

**Backend delta:** none.

---

### Files to Touch

| File | Action | Notes |
|------|--------|-------|
| [`frontend/src/components/layout/AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx) | REWRITE | Based on `ux-design/snippets/AppShell.tsx`; consumes hooks instead of props |
| [`frontend/src/components/layout/NavBar.tsx`](../../frontend/src/components/layout/NavBar.tsx) | DELETE | Single source of truth is now `AppShell` |
| [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx) | CREATE | Placeholder route for Epic 8 |
| [`frontend/src/App.tsx`](../../frontend/src/App.tsx) | MODIFY | Add `recently-added` child route |
| [`frontend/package.json`](../../frontend/package.json) | MODIFY | Add `lucide-react` |
| [`frontend/package-lock.json`](../../frontend/package-lock.json) | MODIFY | Lockfile update (auto via npm) |

**Do NOT touch in this story:**
- `frontend/src/index.css` — tokens are already correct (Story 6.1). Re-read the dual accent comment (lines 110–117 of `index.css`): use `--accent-color` for green, NOT `--accent`.
- `frontend/src/components/ui/*` — no shadcn primitive edits.
- `frontend/src/features/sync/SyncButton.tsx` and `SyncLogPanel.tsx` — the in-page button stays until Story 6.4 cleanup.
- `frontend/src/features/sync/SyncStatusBadge.tsx` — the in-page badge stays; the topbar badge is implemented inline (different visual shape).
- `frontend/src/pages/ConfigPage.tsx`, `LogsPage.tsx`, `DashboardPage.tsx` — body content untouched. Story 6.3 will rename routes; Story 6.4 will clean up redundant in-page widgets.
- Any backend file. No router/service changes.

---

### Critical: Sidebar nav `to` values vs Story 6.3

Story 6.3 will rename `/config` → `/settings` and add `/recently-added` as a real route shell. **For 6.2:**

- Dashboard → `to="/"` (with `end` prop on NavLink so it doesn't stay active on every route)
- Recently Added → `to="/recently-added"` (placeholder route created in this story)
- Settings → `to="/config"` ⚠️ **TEMPORARY** — the label says "Settings" but the route is still `/config` until Story 6.3 renames it. Leave a `// TODO(6.3): rename to /settings` comment next to the `to` value.
- Logs → `to="/logs"`

Do NOT rename `/config` to `/settings` in this story — that change spans `App.tsx`, `ConfigPage`, any backend redirects, and is explicitly Story 6.3's scope.

---

### Critical: Accent token discipline

[`frontend/src/index.css`](../../frontend/src/index.css) (Story 6.1) exposes **two** accent tokens:

- `--accent-color: #1DB954` — the Spotify green used for app-level accents (active nav bar, primary button bg, status dot, accent text in the brand wordmark).
- `--accent: #232323` — a subtle elevated surface used by shadcn `Button variant="ghost"`/`"outline"` hover and other primitives.

**Every Spotify-green surface in `AppShell` MUST use `var(--accent-color)`** (or `bg-[var(--accent-color)]`, `text-[var(--accent-color)]`, etc.). If you accidentally use `var(--accent)` for the active-nav bar or the primary button, you'll get a dark gray surface instead of the bright green — the design fails silently.

The snippet `ux-design/snippets/AppShell.tsx` already uses `var(--accent-color)` correctly — preserve that.

---

### Critical: Hook consumption vs prop drilling

The handoff snippet `ux-design/snippets/AppShell.tsx` is **props-driven** (parents pass `syncStatus`, `lastSync`, `syncing`, `connectedAs`, `onSync`, `showSearch`). In this project we already have:

- `useAuthStatus()` → `{ authenticated, has_previous_auth, spotify_user_id }` (`frontend/src/hooks/useAuthStatus.ts`)
- `useSyncStatus()` → `SyncLog | null` (`frontend/src/hooks/useSyncStatus.ts`)
- `useSyncStream()` → `{ startStream, isStreaming, events, error }` (`frontend/src/hooks/useSyncStream.ts`)
- `useLocation()` from `react-router-dom`

`AppShell` should call these hooks directly so it can sit in `App.tsx` as `<AppShell />` (no parent prop wiring needed). Components downstream (`SyncButton`, `SyncStatusBadge`, etc.) already consume the same hooks — TanStack Query dedupes, so there is no extra network cost.

---

### Critical: One scroll container only

The outer grid takes the full `100vh`. The sidebar is `flex-col` and lets its nav flex naturally (do not add `overflow-y-auto` there for this story — the nav has 4 items, nowhere near overflowing). The main `<section>` is `overflow-hidden` and contains the sticky topbar + a single `flex-1 overflow-y-auto` div. **Only that inner div scrolls** — it's the one whose `onScroll` drives the `scrolled` boolean for the topbar.

If you set `overflow-y-auto` on the outer grid or on the `<section>` you'll get either two scroll bars or a topbar that never knows it's been scrolled.

---

### Implementation: `AppShell.tsx` skeleton (adapted from the snippet)

The snippet at `ux-design/snippets/AppShell.tsx` is the visual source of truth. Below is the same structure adapted to consume hooks and avoid the props API. **Use this as a starting point, not a strict copy — keep all the Tailwind classes from the snippet because they encode the exact spacing.**

```tsx
// frontend/src/components/layout/AppShell.tsx
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Clock, Settings as Cog, ScrollText,
  RotateCw, ChevronLeft, ChevronRight, Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuthStatus } from "@/hooks/useAuthStatus";
import { useSyncStatus } from "@/hooks/useSyncStatus";
import { useSyncStream } from "@/hooks/useSyncStream";

const NAV = [
  { to: "/",                 label: "Dashboard",      Icon: LayoutDashboard, end: true  },
  { to: "/recently-added",   label: "Recently Added", Icon: Clock,           end: false },
  // TODO(6.3): rename target to "/settings" when Story 6.3 renames /config
  { to: "/config",           label: "Settings",       Icon: Cog,             end: false },
  { to: "/logs",             label: "Logs",           Icon: ScrollText,      end: false },
] as const;

const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
function formatRelative(iso?: string | null): string {
  if (!iso) return "never";
  const diffMs = new Date(iso).getTime() - Date.now();
  const diffMin = Math.round(diffMs / 60000);
  if (Math.abs(diffMin) < 60) return rtf.format(diffMin, "minute");
  const diffHr = Math.round(diffMin / 60);
  if (Math.abs(diffHr) < 48) return rtf.format(diffHr, "hour");
  return rtf.format(Math.round(diffHr / 24), "day");
}

export default function AppShell() {
  const { pathname } = useLocation();
  const showSearch = pathname === "/";
  const auth = useAuthStatus();
  const sync = useSyncStatus();
  const { startStream, isStreaming } = useSyncStream();
  const [scrolled, setScrolled] = useState(false);

  const connectedAs = auth.data?.spotify_user_id ?? "Not connected";
  const initials = (connectedAs.match(/[a-z0-9]/gi)?.slice(0, 2).join("") ?? "??").toUpperCase();
  const authOk = auth.data?.authenticated === true;

  const lastSync = sync.data ? formatRelative(sync.data.timestamp) : null;
  const syncFailed = sync.data?.status === "failure";

  return (
    <div className="grid h-screen gap-2 p-2 grid-cols-[var(--sidebar-w)_1fr] bg-[var(--bg-base)]">
      {/* SIDEBAR */}
      <aside className="flex min-h-0 flex-col rounded-lg bg-[var(--bg-app)] p-3 pt-4">
        {/* brand, WORKSPACE label, nav, footer — per snippet (use var(--accent-color)) */}
        {/* …nav items via NAV.map(NavLink, isActive styles per AC #3)… */}
        {/* …footer reads connectedAs / initials / authOk… */}
      </aside>

      {/* MAIN */}
      <section
        className="relative flex min-w-0 flex-col overflow-hidden rounded-lg
                   bg-gradient-to-b from-[var(--bg-elevated)] via-[var(--bg-elevated)] to-[var(--bg-app)]"
        style={{ backgroundSize: "100% 280px", backgroundRepeat: "no-repeat" }}
      >
        <header className={cn(
          "sticky top-0 z-20 flex h-[var(--header-h)] items-center gap-3.5 px-8 backdrop-blur-md transition-colors",
          scrolled
            ? "bg-[rgba(18,18,18,0.95)] border-b border-[var(--border-soft)]"
            : "bg-gradient-to-b from-black/40 to-transparent",
        )}>
          {/* …chevrons (disabled), search pill (if showSearch), spacer, status badge, Sync now Button… */}
        </header>

        <div
          className="flex-1 overflow-y-auto"
          onScroll={(e) => setScrolled(e.currentTarget.scrollTop > 4)}
        >
          <div className="px-8 pb-10 pt-2">
            <Outlet />
          </div>
        </div>
      </section>
    </div>
  );
}
```

**Use the snippet's exact class strings for all Tailwind values** — brand-block, nav-item active state (`before:absolute before:left-0 before:top-2 before:bottom-2 before:w-[3px] before:rounded before:bg-[var(--accent-color)] [&_svg]:text-[var(--accent-color)]`), search pill, status badge, sync button. The skeleton above only sketches structure.

---

### Implementation: `RecentlyAddedPage.tsx`

```tsx
// frontend/src/pages/RecentlyAddedPage.tsx
export default function RecentlyAddedPage() {
  return (
    <div className="space-y-3 pt-2">
      <h1 className="text-3xl font-extrabold tracking-tight text-[var(--text-primary)]">
        Recently Added
      </h1>
      <p className="text-sm text-[var(--text-secondary)]">
        This page will list the current contents of your Recent Adds playlist. Coming in Epic 8.
      </p>
    </div>
  );
}
```

---

### Implementation: `App.tsx` route registration

Insert `recently-added` between `index` and `config` to match the sidebar order:

```tsx
children: [
  { index: true, element: <DashboardPage /> },
  { path: 'recently-added', element: <RecentlyAddedPage /> },
  { path: 'config', element: <ConfigPage /> },
  { path: 'logs', element: <LogsPage /> },
],
```

Add the import: `import RecentlyAddedPage from './pages/RecentlyAddedPage'`. Default export and props API of `AppShell` remain unchanged (still default export, still parameterless).

---

### Architecture Rules — MUST FOLLOW

- **Lucide icons exclusively** (`architecture.md`, Design System section). All icons in `AppShell` come from `lucide-react`. Do not introduce `react-icons`, custom SVGs, or emoji icons.
- **shadcn primitives via CLI only** (`CLAUDE.md`). For this story you only need `Button` (already installed); no new component needed.
- **Tokens are the single source of truth** — every color/spacing reference uses `var(--…)` (or Tailwind arbitrary value `bg-[var(--…)]`). No hardcoded hex inside `AppShell`.
- **`--accent-color` for Spotify green; `--accent` is shadcn-only** (see Story 6.1 dev notes lines 240–248).
- **Path alias** `@/` → `frontend/src/` — use it (`@/hooks/...`, `@/components/...`).
- **TanStack Query v5 idioms** — `isPending` (not `isLoading`), no `onSuccess`/`onError` options on `useQuery` (must be handled at component level if needed).
- **Dark mode is forced** — no theme toggle anywhere (Story 6.1 AC #2).

---

### Anti-Patterns to Avoid

- ❌ Using `var(--accent)` for the active-nav bar / sync button bg → wrong color (subtle gray). Use `var(--accent-color)`.
- ❌ Editing `frontend/src/index.css` to add tokens "missing" in 6.1 — all tokens needed for 6.2 are already there. If something seems missing, double-check the snippet's class names against `index.css`.
- ❌ Passing `syncStatus`/`onSync`/`connectedAs` as props from `App.tsx` — `AppShell` reads everything via hooks. Keep it parameterless.
- ❌ Wiring the search pill to global filter state — it's inert in this story (AC #13). Epic 7 owns the filter logic.
- ❌ Deleting `frontend/src/features/sync/SyncButton.tsx` or `SyncStatusBadge.tsx` — they remain rendered inside `DashboardPage` for now; Story 6.4 will remove them once the topbar fully owns those affordances.
- ❌ Renaming `/config` → `/settings` in this story — that is Story 6.3's job. Sidebar `to` for "Settings" stays `/config` for now.
- ❌ Removing the dashboard heading / in-page `SyncButton` — the visual duplication is intentional and short-lived. Note it in completion notes.
- ❌ Adding `overflow-y-auto` to more than one element inside the main section — must be the single scroll container under the sticky topbar.
- ❌ Forgetting `end` on the Dashboard NavLink (`to="/"`) — without it, "Dashboard" stays "active" on every route.
- ❌ Running `npm install lucide-react` on the host (Node version mismatch / dirty lockfile). Always `docker exec` (per `CLAUDE.md` and memory `feedback_node_version`).
- ❌ Adding `lucide-react` with `--save-dev` or a pinned old version — let `npm install lucide-react` pick the current stable (verified compatible with React 19 since 2025).
- ❌ Pushing AppShell logic that crashes when `useAuthStatus()` is `isPending` or `isError` — guard with neutral defaults (AC #17).
- ❌ Touching backend / spotipy / sync engine code — out of scope.

---

### Previous Story Intelligence

**Story 6.1 (last completed):** Established the design tokens and the `class="dark"` lock. **Critical takeaways for 6.2:**

- `--accent` ≠ `--accent-color`. The dual-accent split is documented inline in `frontend/src/index.css` and again in the dev notes here. Many AppShell visual bugs will stem from confusing the two.
- The shadcn `Button` already resolves to `bg-[var(--primary)] text-[var(--primary-foreground)]` (`#1DB954` on `#000`), which matches the topbar `Sync now` button — but the design also wants `rounded-full`, `px-5`, `font-bold`, hover scale, and an icon. Pass those classes explicitly via `className` (the snippet shows how) and override `rounded-md` from `buttonVariants`.
- Tailwind v4 is in use (`@import "tailwindcss";`). All arbitrary values like `bg-[var(--accent-color)]` and `h-[var(--header-h)]` work natively — no JIT config required.
- The previous story added a global `:focus-visible` outline rule. The chevron buttons in the topbar are `disabled` and should NOT show a focus ring — `disabled` already removes them from tab order.

**Story 5.3 (SSE):** The current `SyncButton` calls `useSyncStream().startStream()`. The new topbar `Sync now` button is the same wiring — calling `startStream()` twice in parallel (once from each visible button) is guarded by the hook (`if (esRef.current) { esRef.current.close() }`), so the duplicate buttons during the 6.2→6.4 window are safe.

**Story 1.4 (frontend shell):** Introduced the legacy `NavBar` we're deleting. The `App.tsx` router structure is the right place to register `/recently-added` (no separate router config file).

---

### Git Intelligence Summary

Recent commits relevant to this story:

- `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — backend-only, no UI surface change.
- `ccbbf60 feat: Stories 2-3 → 5-3 — Auth, Playlists, Sync, Scheduler & Observability` — bulk frontend wiring; established the hooks (`useAuthStatus`, `useSyncStatus`, `useSyncStream`) that AppShell will consume.
- Working-tree changes mentioned in `git status` (`6-1-design-tokens-dark-theme.md`, `frontend/index.html`, `frontend/src/index.css`) are Story 6.1's commit-in-progress — Story 6.2 builds directly on top of 6.1 and assumes those tokens are in `master` (or at least merged before 6.2 starts).

No conflicting renames or large refactors on the frontend layout components since `NavBar.tsx` was introduced — safe to delete.

---

### Latest Tech Information

- **`lucide-react`**: as of late 2025/early 2026, tree-shakes by default with Vite's named imports — no per-icon import path needed (`import { LayoutDashboard } from "lucide-react"` is correct, not `lucide-react/dist/esm/icons/layout-dashboard`). Bundle impact for ~10 icons used here is ~5 kB gzip.
- **React 19** (project is on `react@19.x` per `package.json`): `useState`, `useLocation`, `NavLink` patterns used here are unchanged from React 18. No concurrent-rendering pitfalls in this story.
- **`react-router-dom` v6**: `NavLink`'s `className` callback signature is `({ isActive, isPending }) => string`. Use `isActive` only.
- **`Intl.RelativeTimeFormat`**: supported in all evergreen browsers — no polyfill, no dep.
- **Tailwind v4 + arbitrary values**: `bg-[rgba(18,18,18,0.95)]`, `h-[var(--header-h)]`, `grid-cols-[var(--sidebar-w)_1fr]` all work without any config edits.

---

### Postman Collection

Not applicable — Story 6.2 touches only frontend layout components and adds a placeholder route. No API surface change. Skip the Postman step per `CLAUDE.md`.

---

### Project Structure Notes

- New files: `frontend/src/pages/RecentlyAddedPage.tsx`.
- Deleted files: `frontend/src/components/layout/NavBar.tsx`.
- Touched files: `frontend/src/components/layout/AppShell.tsx`, `frontend/src/App.tsx`, `frontend/package.json`, `frontend/package-lock.json`.
- Layout file lives under `components/layout/` (existing convention from Story 1.4).
- Pages live under `pages/` (existing convention).
- No new directory.

---

### References

- Epic 6 + story acceptance criteria: `_bmad-output/planning-artifacts/epics.md` lines 795–897 (Story 6.2 at lines 839–896).
- UX handoff — AppShell description: `_bmad-output/planning-artifacts/ux-design/README.md` section "1 · AppShell (layout)" (lines 45–69).
- Drop-in baseline (visual source of truth): `_bmad-output/planning-artifacts/ux-design/snippets/AppShell.tsx` (full file).
- Architecture — Design System & UI Primitives: `_bmad-output/planning-artifacts/architecture.md` lines 213–236.
- Tokens applied in 6.1: [`frontend/src/index.css`](../../frontend/src/index.css) (`--accent-color`, `--accent`, `--sidebar-w`, `--header-h`, etc.).
- Previous story file: `_bmad-output/implementation-artifacts/6-1-design-tokens-dark-theme.md`.
- Existing hooks consumed by AppShell:
  - [`frontend/src/hooks/useAuthStatus.ts`](../../frontend/src/hooks/useAuthStatus.ts)
  - [`frontend/src/hooks/useSyncStatus.ts`](../../frontend/src/hooks/useSyncStatus.ts)
  - [`frontend/src/hooks/useSyncStream.ts`](../../frontend/src/hooks/useSyncStream.ts)
- Existing shadcn Button: [`frontend/src/components/ui/button.tsx`](../../frontend/src/components/ui/button.tsx).
- Current router config: [`frontend/src/App.tsx`](../../frontend/src/App.tsx).
- Legacy file to delete: [`frontend/src/components/layout/NavBar.tsx`](../../frontend/src/components/layout/NavBar.tsx).

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

- `docker exec playlist_spotify-frontend-1 npm install lucide-react` → 1 package added, 0 vulnerabilities
- `docker exec playlist_spotify-frontend-1 npm run build` → ✓ built in 383ms, 0 TS / 0 CSS errors

### Completion Notes List

- AppShell.tsx rewritten end-to-end based on `ux-design/snippets/AppShell.tsx` — props-driven snippet adapted to consume `useAuthStatus()`, `useSyncStatus()`, `useSyncStream()` directly. `AppShell` is now parameterless and can sit unwrapped in `App.tsx`.
- Sidebar nav uses React Router `NavLink` with `end: true` on Dashboard only; active state styling per AC #3 (accent vertical bar via `before:` pseudo + accent icon color).
- "Settings" sidebar item points to `/config` with a `// TODO(6.3): rename to /settings` comment — rename is explicitly Story 6.3 scope.
- Topbar status badge uses inline `formatRelative()` (`Intl.RelativeTimeFormat`, no new dependency) and handles three states: success (accent dot + "Last sync · X"), failure (red dot + "Last sync failed · X"), null (muted dot + "Never synced").
- Sidebar footer guards against `useAuthStatus()` pending/error per AC #17: avatar renders `?`, label flips to "Connecting…"/"Not connected", dot uses `var(--text-muted)` until auth resolves. Chrome (sidebar + topbar) renders independently of auth state.
- One scroll container only: the inner `flex-1 overflow-y-auto` div under the sticky topbar. `onScroll` drives `scrolled` boolean; topbar background flips to `rgba(18,18,18,0.95)` + `border-soft` bottom border past 4px.
- In-page `SyncButton` and `SyncStatusBadge` left untouched in `DashboardPage` — visual duplication with the new topbar `Sync now` / status badge is intentional and short-lived (Story 6.4 cleanup). The duplicate `startStream()` calls are safe because `useSyncStream()` closes any existing `EventSource` before opening a new one.
- `lucide-react` resolved to `^1.16.0` inside the container (current published version exposing the standard icon set: `LayoutDashboard`, `Clock`, `Settings`, `ScrollText`, `RotateCw`, `ChevronLeft`, `ChevronRight`, `Search` all verified at runtime).
- Host-side TS may report `Cannot find module 'lucide-react'` because the host has no `node_modules` install — this is expected per project convention (Docker is the source of truth, Node 22 inside the container; see `feedback_node_version`). The container build is clean.
- Manual browser smoke tests for Task 7 (nav routes, Sync now click flow, scroll-into-opaque topbar) are deferred — they require visual verification in the browser by the reviewer.

### File List

- `frontend/src/components/layout/AppShell.tsx` — REWRITE
- `frontend/src/components/layout/NavBar.tsx` — DELETED
- `frontend/src/pages/RecentlyAddedPage.tsx` — CREATED
- `frontend/src/App.tsx` — MODIFIED (added `RecentlyAddedPage` import + child route)
- `frontend/package.json` — MODIFIED (`lucide-react` dependency added)
- `frontend/package-lock.json` — MODIFIED (lockfile updated by npm)

## Change Log

- 2026-05-20: Story 6.2 created — ready-for-dev
- 2026-05-20: Story 6.2 implemented — AppShell v2 (sidebar + topbar) live, legacy NavBar removed, `/recently-added` placeholder added, `lucide-react` installed; status → review
