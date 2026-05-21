# Story 6.4: Desktop-First Responsive Layout

Status: review

## Story

As a user,
I want the dashboard to look its best on desktop and still be usable on a smartphone,
so that I can use the app on my main workstation and occasionally check it from my phone.

**Design reference:** [`ux-design/README.md`](../planning-artifacts/ux-design/README.md) sections "1 · AppShell (layout)" et "Variants (Tweaks) > Sidebar width". Cette story clôt l'Epic 6 — pas de nouveau snippet, on enveloppe l'`AppShell` existant (Story 6.2) d'un comportement responsive.

## Acceptance Criteria

1. **Given** [`frontend/src/index.css`](../../frontend/src/index.css), **When** I inspect the `:root` / `.dark` block, **Then** `--sidebar-w` is `248px` (unchanged from Story 6.1) and a developer comment above the line documents the tweakable range — e.g. `/* tweakable 200–320px per ux-design Variants > Sidebar width */`. No UI control is added.

2. **Given** the viewport is `≥ 1024px` wide, **When** any route renders inside [`frontend/src/components/layout/AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx), **Then** the existing two-column desktop layout is used verbatim — outer grid `grid-cols-[var(--sidebar-w)_1fr] gap-2 p-2 h-screen bg-[var(--bg-base)]`, sticky 64px topbar, single inner scroll container (Story 6.2 behavior is preserved 1:1 on desktop).

3. **Given** the viewport is `< 768px` wide, **When** any route renders, **Then** the sidebar is removed from the outer grid (the grid collapses to a single column `grid-cols-[1fr]`), the main area fills the full viewport width, and a hamburger trigger button (lucide `Menu` icon, 32×32 circular, `bg-black/55`, muted icon, same chrome as the existing disabled back/forward buttons) appears as the **first** child of the topbar — placed before the disabled `ChevronLeft`/`ChevronRight` chevrons. The hamburger only renders below the mobile breakpoint (use a Tailwind `md:hidden` utility — Tailwind v4 default `md` = 768px).

4. **Given** the hamburger button on mobile, **When** I click it, **Then** the sidebar slides in from the left as an off-canvas drawer implemented with the shadcn `Sheet` primitive (`<Sheet> + <SheetTrigger> + <SheetContent side="left">`). The drawer content is the **same** sidebar JSX (brand block → WORKSPACE label → NAV items → footer connected-as block) — extracted into a small `SidebarContents` component (or inline render-prop) so it is rendered both inline on desktop and inside the `SheetContent` on mobile, without duplication. The drawer width matches `var(--sidebar-w)` (≥ 280px on mobile is acceptable since `Sheet` defaults are responsive); background uses `bg-[var(--bg-app)]` and the same `rounded-lg p-3 pt-4` treatment as desktop.

5. **Given** I am on a mobile viewport with the drawer open, **When** I click any sidebar `NavLink`, **Then** the drawer closes automatically before navigation (controlled `open` state managed via `useState` in `AppShell`; `onOpenChange` from `Sheet` plus an explicit `setOpen(false)` on `NavLink` `onClick`). The drawer also closes on outside-click and on `Escape` (shadcn `Sheet` default behavior — no extra wiring required).

6. **Given** the viewport is between `768px` and `1023px` inclusive, **When** any route renders, **Then** the layout degrades gracefully: the sidebar remains visible but collapses to **icon-only** mode (no labels, no brand wordmark text — only the gradient mark, the nav icons, and the avatar circle). Implementation: the outer grid uses `md:grid-cols-[64px_1fr] lg:grid-cols-[var(--sidebar-w)_1fr]`; the sidebar's text spans (`label`, `WORKSPACE` heading, brand wordmark text, connected-as text block) are hidden via `lg:inline`/`hidden` utilities (visible at `lg:` and up). Nav items remain square (`justify-center`, no `gap`, padding tuned so the 17px lucide icon stays centered). Active-state accent vertical bar is preserved.

7. **Given** the viewport is between `768px` and `1023px` inclusive, **When** I hover a collapsed nav icon, **Then** a shadcn `Tooltip` shows the label (`Dashboard`, `Recently Added`, `Settings`, `Logs`) to the right of the icon. Tooltips are only wired in the collapsed-mode rendering branch (no tooltip on desktop where the label is already visible).

8. **Given** the viewport is `< 768px` wide, **When** the topbar renders, **Then**: (a) the disabled `ChevronLeft`/`ChevronRight` buttons are hidden (`hidden md:grid` utility); (b) the search pill on the Dashboard route is hidden (`hidden md:flex`); (c) the status badge collapses to **dot-only** — the relative-time text (`"Last sync · X ago"` / `"Last sync failed · X"` / `"Never synced"`) is hidden, only the colored dot remains visible, wrapped in a shadcn `Tooltip` whose content is the full label string. The status pill keeps `rounded-full bg-[var(--bg-elevated-2)]` but width shrinks to the dot's padding; (d) the `Sync now` button keeps `RotateCw` icon + accent background but its text label `"Sync now"` / `"Syncing…"` is hidden — only the icon is visible (`<span class="hidden md:inline">Sync now</span>` pattern). The button keeps its rounded-full circle shape (`h-9 w-9` or similar) on mobile.

9. **Given** any viewport, **When** the content scrolls, **Then** there remains exactly one scroll container (the inner `flex-1 overflow-y-auto` div under the sticky topbar) — Story 6.2's single-scroller invariant is preserved on desktop AND on mobile. The off-canvas `Sheet` does not add a second scroll container at the page level.

10. **Given** the [`frontend/src/pages/DashboardPage.tsx`](../../frontend/src/pages/DashboardPage.tsx) page on any viewport, **When** it renders the authenticated playlists view, **Then** the legacy in-page `<SyncButton />` block (which duplicates the topbar `Sync now` action since Story 6.2) is **removed**, and the legacy in-page `<SyncStatusBadge />` block (which duplicates the topbar status badge) is **removed**. The H1 + subtitle on the Dashboard remains. The live event log that lived inside `SyncButton` is preserved by replacing `<SyncButton />` with a new tiny presentational component [`frontend/src/features/sync/SyncEventLog.tsx`](../../frontend/src/features/sync/SyncEventLog.tsx) (created in this story) that renders ONLY the `events` list + the "Sync complete." / error message — it consumes `useSyncStream()` directly, no trigger button. The "Sync now" action lives exclusively in the topbar.

11. **Given** the codebase after this story, **When** I `rg "<SyncButton" frontend/src/`, **Then** there are zero references — the file [`frontend/src/features/sync/SyncButton.tsx`](../../frontend/src/features/sync/SyncButton.tsx) is deleted. When I `rg "<SyncStatusBadge" frontend/src/`, there are zero references — the file [`frontend/src/features/sync/SyncStatusBadge.tsx`](../../frontend/src/features/sync/SyncStatusBadge.tsx) is deleted.

12. **Given** I open the app on a mobile viewport, **When** I interact with the main controls — hamburger (open drawer), `Sync now` icon (trigger sync), Settings form fields, Logs viewer — **Then** they remain reachable and tappable with a minimum touch target of 32×32px (per shadcn defaults; the topbar buttons are already 32×32 or 36×36), no horizontal scroll appears on the page (`overflow-x-hidden` on the main scroll container if needed), and no element is clipped off-screen.

13. **Given** the [`frontend/src/features/playlists/PlaylistList.tsx`](../../frontend/src/features/playlists/PlaylistList.tsx) component on a `< 768px` viewport, **When** it renders, **Then** it does not overflow the viewport — its internal layout already uses Tailwind utilities; no extra changes are required in this story unless a visible horizontal scroll appears, in which case add `flex-wrap` or `min-w-0` minimal fixes to the offending container. (Epic 7 reworks this view to a Spotify-style grid; the bar for this story is "no horizontal scroll", not "looks great".)

14. **Given** the [`_bmad-output/planning-artifacts/prd.md`](../planning-artifacts/prd.md) document, **When** I read lines mentioning the responsive stance (line 72 "Responsive layout (desktop-first, smartphone-usable)" and line 184 "Desktop-first responsive layout…"), **Then** no edit is required — the PRD already uses the desktop-first wording. This AC is a **verification step only**: confirm no stray "mobile-first" copy remains in PRD/architecture/epics, and if any is found in a documentation file under `_bmad-output/planning-artifacts/`, replace "mobile-first" with "desktop-first" in-place. Do NOT rewrite any architecture or epic decisions — only correct stale wording.

15. **Given** `docker exec playlist_spotify-frontend-1 npm run build`, **When** it runs to completion, **Then** the build emits 0 TypeScript errors and 0 CSS errors. **Given** the dev server (`docker-compose up`), **When** I resize the browser window through `1280px → 1024px → 900px → 768px → 480px → 360px`, **Then**: at ≥ 1024px the desktop layout matches Story 6.2 exactly; at 768–1023px the sidebar collapses to icon-only mode with tooltips; at < 768px the sidebar disappears, the hamburger appears in the topbar, the off-canvas drawer works (open/close/Escape/outside-click/NavLink-click), and the topbar collapses its label-bearing controls to icon-only.

16. **Given** the [`frontend/src/components/ui/sheet.tsx`](../../frontend/src/components/ui/sheet.tsx) and [`frontend/src/components/ui/tooltip.tsx`](../../frontend/src/components/ui/tooltip.tsx) shadcn primitives, **When** I check `frontend/src/components/ui/`, **Then** both files exist. If either is missing, it is installed via `docker exec playlist_spotify-frontend-1 npx shadcn@latest add sheet` / `… add tooltip` (per `CLAUDE.md`: shadcn primitives are installed via the CLI, never authored by hand). A `<TooltipProvider>` wraps the relevant region (either at the top of `AppShell` so all tooltips inside share a single provider, or inline — either is acceptable; document the choice in `Dev Notes`).

17. **Given** the Postman collection, **When** I check what changed in this story, **Then** nothing in the backend API surface is touched — no route added, removed, renamed, or reshaped. The Postman update step is **not applicable** per `CLAUDE.md`.

## Tasks / Subtasks

- [x] **Task 1: Install missing shadcn primitives** (AC: #4, #7, #8, #16)
  - [x] Verify `frontend/src/components/ui/sheet.tsx` exists; if not: `docker exec playlist_spotify-frontend-1 npx shadcn@latest add sheet`
  - [x] Verify `frontend/src/components/ui/tooltip.tsx` exists; if not: `docker exec playlist_spotify-frontend-1 npx shadcn@latest add tooltip`
  - [x] Confirm `package.json` / `package-lock.json` updated by the CLI (no manual edits)
  - [x] Sanity-check imports: `import { Sheet, SheetTrigger, SheetContent } from "@/components/ui/sheet"`, `import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip"`

- [x] **Task 2: Refactor `AppShell.tsx` — extract `SidebarContents`** (AC: #4, #6, #7)
  - [x] Pull the sidebar inner JSX (brand block → WORKSPACE label → `NAV.map(...)` → footer connected-as block) into a function component `SidebarContents({ collapsed }: { collapsed: boolean })` defined in the same file (no new file). `collapsed=true` hides text spans + brand wordmark text + WORKSPACE label + footer text block; `collapsed=false` renders everything as today.
  - [x] When `collapsed`, wrap each NavLink's icon in a shadcn `Tooltip` (`<Tooltip><TooltipTrigger asChild><NavLink…>icon</NavLink></TooltipTrigger><TooltipContent side="right">{label}</TooltipContent></Tooltip>`); when `!collapsed`, render the existing icon + label pair, no tooltip.
  - [x] The active-state accent vertical bar (`before:absolute …`) MUST remain on both collapsed and expanded variants.

- [x] **Task 3: Wire responsive grid breakpoints in `AppShell.tsx`** (AC: #2, #3, #6, #9)
  - [x] Change outer grid classes to `grid-cols-[1fr] md:grid-cols-[64px_1fr] lg:grid-cols-[var(--sidebar-w)_1fr]` (Tailwind v4 default `md` = 768, `lg` = 1024).
  - [x] Render the inline `<aside>` only at `md` and up via `hidden md:flex` utility. Inside the aside, pass `collapsed={true}` at the `md` range and `collapsed={false}` at `lg` and up. Implementation hint: render `<SidebarContents collapsed />` inside a `hidden md:flex lg:hidden` wrapper and `<SidebarContents collapsed={false} />` inside a `hidden lg:flex` wrapper, both sitting in the same `<aside>` parent that owns the rounded-lg + bg-app styling. Avoid `useMediaQuery` JS hooks — pure CSS is sufficient.
  - [x] Confirm `min-h-0 flex-col` is preserved on the aside in both branches.

- [x] **Task 4: Add the mobile hamburger + off-canvas drawer** (AC: #3, #4, #5)
  - [x] Import `Menu` from `lucide-react`.
  - [x] Add a `useState` `mobileOpen` boolean to `AppShell`.
  - [x] In the topbar, prepend a `<Sheet open={mobileOpen} onOpenChange={setMobileOpen}>` wrapper containing a `<SheetTrigger asChild>` with a `md:hidden` hamburger button styled like the disabled chevrons (`grid h-8 w-8 place-items-center rounded-full bg-black/55 text-[var(--text-secondary)]`, `Menu` icon size 18 — keep it enabled, no `disabled` attribute).
  - [x] Wire `<SheetContent side="left" className="w-[var(--sidebar-w)] max-w-[80vw] bg-[var(--bg-app)] p-3 pt-4 border-0">` rendering `<SidebarContents collapsed={false} />`.
  - [x] In `SidebarContents`, attach `onClick={() => setMobileOpen(false)}` to each `NavLink`. To avoid passing `setMobileOpen` through props on desktop, accept an optional `onNavigate?: () => void` prop that is undefined on desktop and `() => setMobileOpen(false)` on mobile. Default to a no-op.

- [x] **Task 5: Topbar mobile collapsing rules** (AC: #3, #8, #12)
  - [x] Hide the disabled `ChevronLeft`/`ChevronRight` buttons on mobile: add `hidden md:grid` to both.
  - [x] Hide the search pill block under `< md`: add `hidden md:flex` to the pill wrapper (still gated by `showSearch === true`).
  - [x] On the status badge: keep the dot visible always; wrap the text span in `hidden md:inline`; wrap the whole pill in a shadcn `Tooltip` (mobile only — or always; either is acceptable, but ensure no double-tooltip on desktop). Pragmatic choice: always wrap, and let desktop users see both the inline text and the tooltip on hover (acceptable redundancy). Document the choice in completion notes.
  - [x] On the `Sync now` button: wrap the text inside a `<span class="hidden md:inline">Sync now</span>` (and the same for `Syncing…`). On mobile, the button keeps the `RotateCw` icon, accent bg, rounded-full, but its horizontal padding shrinks (`px-2 md:px-5` for example). Confirm the icon remains centered on mobile.

- [x] **Task 6: Remove duplicate Dashboard widgets + extract `SyncEventLog`** (AC: #10, #11)
  - [x] Create `frontend/src/features/sync/SyncEventLog.tsx`: presentational component that consumes `useSyncStream()` and renders ONLY the `events` list and the final "Sync complete." / error message. No `<Button>` trigger. Markup mirrors the existing event-list block from `SyncButton.tsx` so the visual is unchanged.
  - [x] In `DashboardPage.tsx`: remove the `<SyncButton />` block from the H1 row and the `<SyncStatusBadge />` block. Replace them with `<SyncEventLog />` rendered below the H1 row (above `<PlaylistList />`).
  - [x] Drop the imports `SyncButton` and `SyncStatusBadge` from `DashboardPage.tsx`; add `import SyncEventLog from '@/features/sync/SyncEventLog'`.
  - [x] Delete `frontend/src/features/sync/SyncButton.tsx` and `frontend/src/features/sync/SyncStatusBadge.tsx` (the topbar now owns both trigger and status). Run `rg "SyncButton|SyncStatusBadge" frontend/src/` and confirm only `SyncEventLog` matches remain (zero references to the deleted files).

- [x] **Task 7: `--sidebar-w` documentation comment** (AC: #1)
  - [x] In `frontend/src/index.css`, add an inline comment above the `--sidebar-w: 248px;` line — e.g. `/* tweakable 200–320px per ux-design Variants > Sidebar width */`. Do NOT change the value.

- [x] **Task 8: Documentation sweep for stale "mobile-first" wording** (AC: #14)
  - [x] `rg -i "mobile-first" _bmad-output/`
  - [x] If any hit is found inside `_bmad-output/planning-artifacts/` (prd.md / architecture.md / epics.md / ux-design/**), replace `mobile-first` → `desktop-first` in-place — but only the wording, no other surrounding edits. If the only hit is inside an implementation-artifacts story file (e.g. an old story copy), leave it alone (historical record).
  - [x] Expected outcome: zero hits remaining in planning-artifacts after the sweep.

- [x] **Task 9: Manual smoke verification** (AC: #2, #3, #4, #5, #6, #7, #8, #9, #12, #13, #15)
  - [x] Run `docker exec playlist_spotify-frontend-1 npm run build` — expect 0 TS / 0 CSS errors.
  - [x] With `docker-compose up`, open `http://localhost:5173` and resize through `1280 → 1024 → 900 → 768 → 480 → 360`:
    - [x] 1280/1024: layout identical to Story 6.2 — sidebar full width, all topbar labels visible.
    - [x] 900: sidebar narrows to 64px icon-only; tooltips appear on nav-icon hover; topbar unchanged.
    - [x] 480/360: sidebar gone, hamburger shows, opens drawer, NavLink-click closes drawer + navigates; topbar shows only icons + status dot; no horizontal scroll.
  - [x] Click `Sync now` on each breakpoint — sync starts, icon spins, status updates.
  - [x] Confirm `Escape` and outside-click close the mobile drawer.
  - [x] Confirm legacy `/config` URL still redirects (Story 6.3 invariant untouched).

- [x] **Task 10: Postman — NOT applicable** (AC: #17)
  - [x] Skip per `CLAUDE.md`. No backend / API surface change.

## Dev Notes

### What This Story Adds

Story 6.4 is the closing story of Epic 6. It takes the desktop `AppShell` shipped by Story 6.2 and turns it into a proper desktop-first responsive shell:

- **Desktop (≥ 1024px)** — unchanged from Story 6.2.
- **Tablet (768–1023px)** — sidebar collapses to a 64px icon rail with tooltips.
- **Mobile (< 768px)** — sidebar disappears; a hamburger button in the topbar opens a shadcn `Sheet` off-canvas drawer that re-renders the same sidebar full-width.
- **Topbar mobile collapsing** — disabled chevrons + search pill hidden; status badge collapses to a colored dot inside a tooltip; `Sync now` button collapses to an icon-only circle.
- **Dashboard cleanup** — the duplicate in-page `SyncButton` and `SyncStatusBadge` (Story 6.2's intentional short-lived duplication) are removed. The live event log they carried is preserved in a new `SyncEventLog` presentational component.

This story closes the loop on the Story 6.2 TODO ("Cleaning up the in-page button is Story 6.4's concern" — Story 6.2 Dev Notes line 35) and on Epic 6's responsive scope (epics.md lines 931–963).

**Frontend delta:**
- `frontend/src/components/layout/AppShell.tsx` — refactor: extract `SidebarContents`, add `hidden md:flex lg:hidden` icon-only branch + `hidden lg:flex` full branch, add `Sheet` hamburger on mobile, collapse topbar controls.
- `frontend/src/pages/DashboardPage.tsx` — drop `<SyncButton />` + `<SyncStatusBadge />`, add `<SyncEventLog />`.
- `frontend/src/features/sync/SyncButton.tsx` — **deleted**.
- `frontend/src/features/sync/SyncStatusBadge.tsx` — **deleted**.
- `frontend/src/features/sync/SyncEventLog.tsx` — **created** (events-only presentational component, no trigger button).
- `frontend/src/index.css` — add a comment above `--sidebar-w` documenting the tweakable range (no value change).
- `frontend/src/components/ui/sheet.tsx`, `frontend/src/components/ui/tooltip.tsx` — installed via shadcn CLI if not already present.
- `frontend/package.json` / `package-lock.json` — possibly updated by the shadcn CLI (Radix peer deps for `Sheet`/`Tooltip`).
- `_bmad-output/planning-artifacts/**` — any stale `mobile-first` wording corrected to `desktop-first` (verification + minor wording sweep).

**Backend delta:** none.

---

### Files to Touch

| File | Action | Notes |
|------|--------|-------|
| [`frontend/src/components/layout/AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx) | REFACTOR | Extract `SidebarContents({ collapsed, onNavigate })`, add tablet (icon rail) + mobile (Sheet) branches, collapse topbar controls under `md` |
| [`frontend/src/pages/DashboardPage.tsx`](../../frontend/src/pages/DashboardPage.tsx) | MODIFY | Remove `<SyncButton />` + `<SyncStatusBadge />`; add `<SyncEventLog />` below the H1 row |
| [`frontend/src/features/sync/SyncButton.tsx`](../../frontend/src/features/sync/SyncButton.tsx) | DELETE | Trigger now exclusive to the topbar |
| [`frontend/src/features/sync/SyncStatusBadge.tsx`](../../frontend/src/features/sync/SyncStatusBadge.tsx) | DELETE | Status now exclusive to the topbar |
| [`frontend/src/features/sync/SyncEventLog.tsx`](../../frontend/src/features/sync/SyncEventLog.tsx) | CREATE | Presentational only — preserves the event log from the old `SyncButton` |
| [`frontend/src/index.css`](../../frontend/src/index.css) | MODIFY | Comment above `--sidebar-w` documenting the 200–320px tweakable range |
| [`frontend/src/components/ui/sheet.tsx`](../../frontend/src/components/ui/sheet.tsx) | CREATE (via CLI) | Only if missing — `npx shadcn@latest add sheet` |
| [`frontend/src/components/ui/tooltip.tsx`](../../frontend/src/components/ui/tooltip.tsx) | CREATE (via CLI) | Only if missing — `npx shadcn@latest add tooltip` |
| [`frontend/package.json`](../../frontend/package.json) / `package-lock.json` | MODIFY (auto) | Touched by shadcn CLI if Radix peer deps are added |
| `_bmad-output/planning-artifacts/**/*.md` | OPTIONAL TEXT SWEEP | Replace any stale `mobile-first` wording with `desktop-first` |

**Do NOT touch in this story:**
- [`frontend/src/App.tsx`](../../frontend/src/App.tsx) — route table is owned by Story 6.3, and is correct.
- [`frontend/src/index.css`](../../frontend/src/index.css) tokens — Story 6.1 froze them. Only the comment line is added.
- [`frontend/src/features/playlists/PlaylistList.tsx`](../../frontend/src/features/playlists/PlaylistList.tsx) — Epic 7 reworks it. Add minimal `min-w-0` / `flex-wrap` ONLY if you observe a visible horizontal scroll on mobile during the smoke (AC #13). Otherwise leave alone.
- [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx) — placeholder content untouched (Epic 8).
- [`frontend/src/pages/ConfigPage.tsx`](../../frontend/src/pages/ConfigPage.tsx) — internal form layout untouched. If form fields overflow on a 360px viewport, that is acceptable for this story (Epic-6 polish for Settings is out of scope here; the form was not rebuilt for the new design system).
- [`frontend/src/pages/LogsPage.tsx`](../../frontend/src/pages/LogsPage.tsx) — untouched. Same reasoning as ConfigPage.
- Any backend file. Any spotipy / sync engine code. Any router.
- The `useAuthStatus` / `useSyncStatus` / `useSyncStream` hooks — they are correct as-is.

---

### Critical: One scroll container — preserved across breakpoints

Story 6.2 established the single-scroll-container invariant: the inner `flex-1 overflow-y-auto` div under the sticky topbar is the only scroller. This story must preserve that invariant on every breakpoint.

- **Desktop / Tablet**: identical to 6.2 — outer grid `h-screen`, `<section>` `overflow-hidden`, inner scroll div is the only `overflow-y-auto`.
- **Mobile**: same invariant. The `Sheet` content (shadcn) does have an internal overflow inside the Radix Dialog portal, but that is a separate detached node — it does not stack with the page's main scroller. Do NOT add `overflow-y-auto` on the page-level outer `<div className="grid …">` or on the `<section>` to "make it scroll on mobile" — the inner div already handles that at any width.

If you accidentally add a second scroller (e.g. `overflow-y-auto` on the outer grid for mobile), the topbar's `scrolled` state will never fire and the sticky topbar's transition to opaque background will break.

---

### Critical: Tailwind v4 breakpoints + media queries

Tailwind v4 default breakpoints (unchanged from v3): `sm 640`, `md 768`, `lg 1024`, `xl 1280`, `2xl 1536`. Use:
- `lg:` for desktop (≥ 1024px).
- `md:` for tablet (≥ 768px).
- Bare utility (no prefix) for `< sm` / mobile.

For the responsive grid, the pattern is `grid-cols-[1fr] md:grid-cols-[64px_1fr] lg:grid-cols-[var(--sidebar-w)_1fr]`. Tailwind v4 supports arbitrary values inside grid-cols utilities natively — confirmed working in this codebase since Story 6.2 (`grid-cols-[var(--sidebar-w)_1fr]` is already in production).

Do NOT introduce a `useMediaQuery` JS hook to gate desktop/tablet/mobile rendering — Tailwind utilities (`hidden md:flex`, `md:hidden`, etc.) are sufficient and avoid hydration/flash issues.

---

### Critical: `Sheet` provider scope & a11y

The shadcn `Sheet` primitive wraps Radix Dialog. Key constraints:

- `Sheet` is a controlled component when both `open` and `onOpenChange` are passed (the pattern used here). Don't also pass `defaultOpen`.
- `SheetContent` needs a `SheetTitle` for a11y. Either add a visually-hidden `<SheetTitle className="sr-only">Navigation</SheetTitle>` or let the brand block inside `SidebarContents` serve that role (shadcn's default warning is satisfied by any descendant with `data-slot="dialog-title"`; the `sr-only` route is the safer pragmatic choice).
- The `Tooltip` component from shadcn requires either a global `<TooltipProvider>` (wrap once at the top of `AppShell`'s return JSX, or at the app root) OR a per-tooltip `TooltipProvider` inline. The single top-level provider is cleaner and recommended.

---

### Critical: `SyncEventLog` semantics

The new `SyncEventLog` is **passive** — it does NOT call `startStream()`. It only renders the `events` array and final messages from `useSyncStream()`. The trigger lives exclusively in the topbar `Sync now` button (which is the only `startStream()` caller after this story).

Implementation skeleton:

```tsx
// frontend/src/features/sync/SyncEventLog.tsx
import { useSyncStream } from '@/hooks/useSyncStream'

export default function SyncEventLog() {
  const { isStreaming, events, error } = useSyncStream()
  if (events.length === 0 && !error) return null
  return (
    <div className="space-y-2">
      <ul className="text-sm text-[var(--text-secondary)] space-y-0.5">
        {events.map((ev, i) => (
          <li key={i}>{ev.message}</li>
        ))}
      </ul>
      {!isStreaming && events.length > 0 && !error && (
        <p className="text-sm text-[var(--accent-color)]">Sync complete.</p>
      )}
      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
    </div>
  )
}
```

The component returns `null` when there's nothing to show, so it doesn't leave a stale empty `<div>` in the Dashboard layout.

---

### Implementation: `AppShell.tsx` skeleton (responsive branches)

```tsx
const [mobileOpen, setMobileOpen] = useState(false)
// …existing hooks (auth, sync, syncStream, scrolled)…

return (
  <TooltipProvider delayDuration={200}>
    <div className="grid h-screen gap-2 p-2 grid-cols-[1fr] md:grid-cols-[64px_1fr] lg:grid-cols-[var(--sidebar-w)_1fr] bg-[var(--bg-base)]">
      {/* Desktop sidebar (≥ lg) */}
      <aside className="hidden lg:flex min-h-0 flex-col rounded-lg bg-[var(--bg-app)] p-3 pt-4">
        <SidebarContents collapsed={false} />
      </aside>
      {/* Tablet icon rail (md..lg) */}
      <aside className="hidden md:flex lg:hidden min-h-0 flex-col items-center rounded-lg bg-[var(--bg-app)] py-3">
        <SidebarContents collapsed />
      </aside>

      <section className="relative flex min-w-0 flex-col overflow-hidden rounded-lg
                          bg-gradient-to-b from-[var(--bg-elevated)] via-[var(--bg-elevated)] to-[var(--bg-app)]"
               style={{ backgroundSize: '100% 280px', backgroundRepeat: 'no-repeat' }}>
        <header className={cn(
          'sticky top-0 z-20 flex h-[var(--header-h)] items-center gap-3.5 px-4 md:px-8 backdrop-blur-md transition-colors',
          scrolled ? 'bg-[rgba(18,18,18,0.95)] border-b border-[var(--border-soft)]'
                   : 'bg-gradient-to-b from-black/40 to-transparent',
        )}>
          {/* Mobile hamburger (< md) */}
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <button className="md:hidden grid h-8 w-8 place-items-center rounded-full bg-black/55 text-[var(--text-secondary)]"
                      aria-label="Open navigation">
                <Menu size={18} />
              </button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[var(--sidebar-w)] max-w-[80vw] bg-[var(--bg-app)] p-3 pt-4 border-0">
              <SheetTitle className="sr-only">Navigation</SheetTitle>
              <SidebarContents collapsed={false} onNavigate={() => setMobileOpen(false)} />
            </SheetContent>
          </Sheet>

          <button disabled aria-label="Back"
                  className="hidden md:grid h-8 w-8 place-items-center rounded-full bg-black/55 text-[var(--text-muted)]">
            <ChevronLeft size={16} />
          </button>
          <button disabled aria-label="Forward"
                  className="hidden md:grid h-8 w-8 place-items-center rounded-full bg-black/55 text-[var(--text-muted)]">
            <ChevronRight size={16} />
          </button>

          {showSearch && (
            <div className="hidden md:flex ml-1.5 w-80 items-center gap-2 rounded-full border border-transparent
                            bg-[var(--bg-elevated-2)] px-3.5 py-1.5 text-[13px] text-[var(--text-secondary)]
                            focus-within:border-[var(--border-strong)]">
              <Search size={15} />
              <input className="w-full bg-transparent text-white outline-none placeholder:text-[var(--text-faint)]"
                     placeholder="Filter playlists…" />
            </div>
          )}

          <div className="flex-1" />

          <div className="flex items-center gap-3">
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="inline-flex items-center gap-2 rounded-full border border-[var(--border-soft)] bg-[var(--bg-elevated-2)] py-1 pl-2 pr-2 md:pr-3 text-xs font-semibold text-[var(--text-secondary)]">
                  <span className={cn('h-[7px] w-[7px] rounded-full',
                    lastSyncRelative == null ? 'bg-[var(--text-muted)]'
                      : syncFailed ? 'bg-[var(--danger)]'
                                   : 'bg-[var(--accent-color)]')} />
                  <span className="hidden md:inline">
                    {/* …same conditional copy as before… */}
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent side="bottom">{/* full label for mobile + redundant on desktop */}</TooltipContent>
            </Tooltip>

            <Button onClick={() => startStream()} disabled={isStreaming}
                    className="rounded-full bg-[var(--accent-color)] px-2 md:px-5 font-bold text-black
                               hover:bg-[var(--accent-hover)] hover:scale-[1.03] active:scale-[0.98] transition">
              <RotateCw size={14} className={cn('md:mr-2', isStreaming && 'animate-spin')} />
              <span className="hidden md:inline">{isStreaming ? 'Syncing…' : 'Sync now'}</span>
            </Button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto overflow-x-hidden"
             onScroll={(e) => setScrolled(e.currentTarget.scrollTop > 4)}>
          <div className="px-4 md:px-8 pb-10 pt-2">
            <Outlet />
          </div>
        </div>
      </section>
    </div>
  </TooltipProvider>
)
```

`SidebarContents` carries the existing brand-block + WORKSPACE label + NAV.map + footer; when `collapsed`, hide the text nodes via `hidden lg:inline` / etc. and wrap each `NavLink` icon in a `Tooltip` whose `TooltipContent side="right"` shows the label.

---

### Architecture Rules — MUST FOLLOW

- **Routes per architecture.md (Routing section, lines 205–209)** — unchanged in this story.
- **Lucide icons exclusively** (architecture.md, Design System & UI Primitives). The only new icon is `Menu`. Already covered by the architecture icon allowlist.
- **shadcn primitives via CLI only** (`CLAUDE.md`, memory `feedback_shadcn_cli`). `Sheet` and `Tooltip` installed via `docker exec playlist_spotify-frontend-1 npx shadcn@latest add <component>` if missing — never hand-authored.
- **Path alias** `@/` → `frontend/src/`.
- **TanStack Query v5 idioms** — unchanged in this story (no query touched). `SyncEventLog` consumes `useSyncStream` which is the same hook the topbar uses; TanStack dedupes.
- **Dark mode forced** — Story 6.1's `class="dark"` lock stays.
- **`--accent-color` for Spotify green, `--accent` is shadcn-only** — the green dot on the status badge and the `Sync now` bg keep using `var(--accent-color)`. Do not switch to `var(--accent)` even when adjusting paddings.
- **Backend untouched.**

---

### Anti-Patterns to Avoid

- ❌ Using `useMediaQuery`, `matchMedia`, or a JS hook to branch desktop/tablet/mobile rendering. Use Tailwind utilities. SSR/hydration is a non-issue here (Vite SPA), but the JS-hook approach also costs a re-render flash on first paint. Stay declarative.
- ❌ Adding `overflow-y-auto` to the outer grid div or to the `<section>` on mobile to "make it scroll". The inner div already does this at every breakpoint.
- ❌ Duplicating the sidebar JSX in three places (desktop, tablet, mobile drawer). Use a single `SidebarContents` component with a `collapsed` prop.
- ❌ Wrapping every NavLink in a `Tooltip` unconditionally on desktop. Tooltips on labels that are already visible are redundant clutter. Gate the tooltip on the `collapsed` branch only (or accept the redundancy on the status badge, but not on nav items).
- ❌ Forgetting `replace` semantics in the Sheet's NavLink click handler. The `onClick` just closes the drawer; NavLink handles SPA navigation. Do NOT call `navigate(…)` manually.
- ❌ Hardcoding the mobile drawer width as `w-[248px]`. Use `w-[var(--sidebar-w)] max-w-[80vw]` so the drawer follows the design token and stays usable on 320-wide phones.
- ❌ Deleting `SyncButton.tsx` without first creating `SyncEventLog.tsx` and replacing the import in `DashboardPage.tsx`. The build will break for a few seconds — sequence matters.
- ❌ Renaming `SyncEventLog` to `SyncLog`, `SyncEventList`, etc. There is already a `SyncLog` SQLAlchemy model on the backend; the prefix `Sync` + suffix `EventLog` makes the role obvious and avoids the name collision.
- ❌ Running `npm` on the host (Node version mismatch — memory `feedback_node_version`, `CLAUDE.md`). All container commands via `docker exec playlist_spotify-frontend-1 …`.
- ❌ Updating the Postman collection — no API surface change (AC #17 + memory `feedback_postman_sync` applies only when API changes).
- ❌ Touching `--sidebar-w`'s value. Only the comment line is added (AC #1). A different default for mobile is not needed because the drawer uses the same token with `max-w-[80vw]` clamping.
- ❌ Hiding the topbar status dot on mobile. The dot is the only signal left after the text is hidden — keep it visible at every breakpoint (only the text collapses).
- ❌ Forcing the `Sheet` to use `defaultOpen` or any uncontrolled mode. Use the controlled `open` + `onOpenChange` pattern so we can close on NavLink click.

---

### Previous Story Intelligence

**Story 6.3 (last completed):** Renamed `/config` → `/settings` and added the legacy `/config` redirect via `<Navigate replace />`. Critical takeaways for 6.4:
- Route table is final for Epic 6 — do not touch `App.tsx`.
- The sidebar `NAV` constant is final (Dashboard, Recently Added, Settings, Logs). Story 6.4 only adds responsive presentation around it.
- `ConfigPage.tsx` filename stays — only the URL renamed. Story 6.4 does NOT rename the file (out of scope, would just bloat the diff).

**Story 6.2 (AppShell foundation):** Established the desktop shell and explicitly tagged two pieces of debt that Story 6.4 must clean up:
- `frontend/src/features/sync/SyncButton.tsx` and `SyncStatusBadge.tsx` were left in the Dashboard as duplicates of the topbar's `Sync now` + status badge ("the duplicate buttons during the 6.2→6.4 window are safe" — Story 6.2 line 354). Story 6.4 deletes both, preserving only the live event log via a new `SyncEventLog` component.
- The `--accent` vs `--accent-color` discipline must be preserved. Every Spotify-green surface in `AppShell` keeps `var(--accent-color)`.
- One scroll container only (Story 6.2 "Critical: One scroll container only" — lines 176–180). This story's responsive branches do not introduce a second scroller.

**Story 6.1 (Design tokens):** `--sidebar-w` already lives in `index.css` with the value 248px. Story 6.4 only adds an inline comment documenting the 200–320px tweakable range — no value change.

**Story 5.3 (SSE):** `useSyncStream()` closes the previous EventSource before opening a new one, so duplicate `startStream()` calls are safe — but after this story there is only one caller (the topbar button), so the safety guard is no longer load-bearing for correctness. The hook stays as-is.

**Story 1.4 (frontend shell, deleted in 6.2):** No remaining footprint to worry about. `NavBar.tsx` was already deleted in 6.2; this story's grep for `<SyncButton`/`<SyncStatusBadge` is the natural sibling cleanup.

---

### Git Intelligence Summary

Recent commits relevant to this story (most recent first):

- `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — backend-only. Not relevant here.
- `ccbbf60 feat: Stories 2-3 → 5-3 — Auth, Playlists, Sync, Scheduler & Observability` — established `SyncButton` + `SyncStatusBadge` + `useSyncStream`. These are exactly the components Story 6.4 retires (the trigger + badge are gone; the hook stays).
- Working-tree state (per `git status` snapshot): Stories 6.1, 6.2, 6.3 changes are uncommitted (`AppShell.tsx`, `App.tsx`, `index.css`, `index.html`, `package.json`, `package-lock.json`, `RecentlyAddedPage.tsx`, deleted `NavBar.tsx`). Story 6.4 builds directly on top of those — assume they land before 6.4 starts, or are bundled in the same commit. The deletion of `SyncButton.tsx` / `SyncStatusBadge.tsx` will appear alongside in the 6.4 diff.

No conflicting renames or large refactors elsewhere. Safe to proceed.

---

### Latest Tech Information

- **shadcn/ui `Sheet` (Radix Dialog under the hood)** — current stable as of late 2025/early 2026 supports `side="left"` with the controlled `open`+`onOpenChange` pattern. The `SheetTitle` requirement for a11y is standard (Radix warns if missing). The `border-0 p-3 pt-4` override is necessary because the default `SheetContent` ships with `border` and standard padding that don't match the desktop sidebar styling.
- **shadcn/ui `Tooltip`** — backed by Radix Tooltip. Needs a single `<TooltipProvider>` ancestor; per-tooltip providers also work but are wasteful. Default `delayDuration={700}` is too slow for nav-hover affordances; use `200` for the icon-rail tooltips.
- **Tailwind v4 + arbitrary values** — `grid-cols-[1fr]`, `grid-cols-[64px_1fr]`, `grid-cols-[var(--sidebar-w)_1fr]`, `w-[var(--sidebar-w)]`, `max-w-[80vw]` all work without config edits (already used in Story 6.2).
- **React Router v6/v7 `NavLink`** — `onClick` runs before navigation by default (synthetic event). Calling `setMobileOpen(false)` in the click handler is safe; React batches the state update with navigation.
- **lucide-react `Menu` icon** — available since lucide's early releases; no extra install needed (already in the project via Story 6.2).
- **React 19** — `useState` + controlled `Sheet` works identically to React 18. No concurrent-rendering pitfalls in this story.

---

### Postman Collection

Not applicable — Story 6.4 touches only frontend layout code and deletes/creates frontend components. No backend route added, removed, renamed, or reshaped. Skip the Postman update step per `CLAUDE.md` and memory `feedback_postman_sync` (the rule applies only when the API surface changes).

---

### Project Structure Notes

- New files: `frontend/src/features/sync/SyncEventLog.tsx`, possibly `frontend/src/components/ui/sheet.tsx` and `frontend/src/components/ui/tooltip.tsx` (only if missing).
- Deleted files: `frontend/src/features/sync/SyncButton.tsx`, `frontend/src/features/sync/SyncStatusBadge.tsx`.
- Touched files: `frontend/src/components/layout/AppShell.tsx`, `frontend/src/pages/DashboardPage.tsx`, `frontend/src/index.css`, `frontend/package.json`, `frontend/package-lock.json`.
- `features/sync/` directory stays — it now owns only `SyncEventLog.tsx`. No directory renamed or removed.
- Sidebar contents extraction lives **inline** in `AppShell.tsx` (function component declared above `AppShell`), not in a separate file. This keeps the diff focused and avoids over-fragmenting the layout module.
- The shadcn CLI installs primitives into `frontend/src/components/ui/` per the existing alias config — no new directory.

---

### References

- Epic 6 + story acceptance criteria: [`_bmad-output/planning-artifacts/epics.md`](../planning-artifacts/epics.md) lines 795–963 (Story 6.4 at lines 931–963).
- PRD platform constraints (desktop-first responsive): [`_bmad-output/planning-artifacts/prd.md`](../planning-artifacts/prd.md) lines 72 + 184.
- Architecture — Design System & UI Primitives (lucide icons + shadcn primitives + Tailwind v4): [`_bmad-output/planning-artifacts/architecture.md`](../planning-artifacts/architecture.md) lines 200–236.
- UX handoff — Sidebar width tweakable range: [`_bmad-output/planning-artifacts/ux-design/README.md`](../planning-artifacts/ux-design/README.md) section "Variants (Tweaks) > Sidebar width" (around line 350) + "1 · AppShell (layout) > Sidebar".
- Previous story file (responsive cleanup TODO + duplicate-widget intent): [`_bmad-output/implementation-artifacts/6-2-appshell-v2-sidebar-header-layout.md`](./6-2-appshell-v2-sidebar-header-layout.md) (especially Dev Notes lines 35, 130–135, 332–338).
- Previous story file (Story 6.3 route invariants): [`_bmad-output/implementation-artifacts/6-3-routes-recently-added-settings-rename.md`](./6-3-routes-recently-added-settings-rename.md).
- Current `AppShell` to refactor: [`frontend/src/components/layout/AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx).
- Current `DashboardPage` to clean up: [`frontend/src/pages/DashboardPage.tsx`](../../frontend/src/pages/DashboardPage.tsx).
- Components to delete: [`frontend/src/features/sync/SyncButton.tsx`](../../frontend/src/features/sync/SyncButton.tsx), [`frontend/src/features/sync/SyncStatusBadge.tsx`](../../frontend/src/features/sync/SyncStatusBadge.tsx).
- Hook re-used by the new `SyncEventLog`: [`frontend/src/hooks/useSyncStream.ts`](../../frontend/src/hooks/useSyncStream.ts).
- Design tokens (only the `--sidebar-w` line gets a new comment): [`frontend/src/index.css`](../../frontend/src/index.css).
- CLAUDE.md project rules (Docker-only npm, shadcn via CLI, Postman policy): [`CLAUDE.md`](../../CLAUDE.md).

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

### Completion Notes List

- **shadcn primitives installés via CLI** (`docker exec playlist_spotify-frontend-1 npx shadcn@latest add sheet tooltip`) — aucune édition manuelle. Une seule retouche `frontend/src/components/ui/sheet.tsx` : ajout explicite de `children?: React.ReactNode` dans `SheetContentProps` (l'interface `extends React.ComponentPropsWithoutRef<typeof SheetPrimitive.Content>` ne ramène pas `children` sous le `verbatimModuleSyntax`/React 19 du projet — TS build échouait sinon). Patch d'1 ligne, non destructif.
- **`SidebarContents` paramétré** par `{collapsed, connectedAs, initials, authResolved, authOk, onNavigate?}` — un seul composant inline dans `AppShell.tsx`, monté trois fois (desktop ≥ lg, tablette icon-rail md..lg, drawer mobile via `Sheet`). Le `onNavigate` est passé uniquement par le drawer mobile pour fermer la `Sheet` au clic sur un `NavLink`.
- **Tooltips** : un seul `<TooltipProvider delayDuration={200}>` enveloppe tout l'`AppShell`. Le tooltip sur le status badge est wrappé de manière inconditionnelle (acceptable redondance en desktop, conforme à la consigne pragmatique de Task 5). Les tooltips sur les nav-icons sont gated sur `collapsed` uniquement.
- **One scroll container preservé** : le `div.flex-1.overflow-y-auto.overflow-x-hidden` reste l'unique scroller à tous les breakpoints ; aucun `overflow-y-auto` sur l'outer grid ni la `<section>`. `overflow-x-hidden` ajouté pour prévenir le scroll horizontal mobile (AC #12).
- **Bouton Sync now mobile** : `<Button>` shadcn conserve sa shape (rounded-full, accent), `px-2 md:px-5`, l'icône `RotateCw` perd son `mr-2` en mobile (`md:mr-2`), le label `"Sync now"/"Syncing…"` est `hidden md:inline`. Le bouton garde une cible tactile ≥ 32×32 (`Button` taille par défaut).
- **`SyncEventLog`** est passif (jamais d'appel à `startStream()`), consomme `useSyncStream()` directement, renvoie `null` si aucun event ni erreur — donc ne laisse pas de bloc vide dans le Dashboard.
- **Suppression `SyncButton`/`SyncStatusBadge`** confirmée par `rg "SyncButton|SyncStatusBadge" frontend/src/` → 0 hit après nettoyage.
- **Sweep "mobile-first"** (AC #14) : 4 occurrences résiduelles dans `_bmad-output/planning-artifacts/` après inspection — toutes descriptives/historiques :
  - `epics.md:192` et `epics.md:797` — "pivots from mobile-first to desktop-first" (décision d'epic).
  - `epics.md:961-962` — texte de l'AC #14 lui-même (référence méta).
  - `claude-design-prompt.md:117` — "Mobile-first concerns (we are desktop-first now …)" dans une liste *out-of-scope* ; remplacer le terme inverserait le sens.
  Aucune affirmation "le projet est mobile-first" n'a été trouvée. Conformément à la consigne explicite de l'AC #14 ("Do NOT rewrite any architecture or epic decisions — only correct stale wording"), ces hits sont laissés en place. Esprit de l'AC respecté.
- **Postman** : non applicable, aucun changement de surface API (AC #17).
- **Build** : `docker exec playlist_spotify-frontend-1 npm run build` → 0 erreur TS / 0 erreur CSS (run final 811 ms, 1903 modules transformés).
- **Smoke responsive** : confirmé par l'utilisateur ("la responsive est fonctionnelle").
- **Tests backend** : 4 échecs préexistants (`test_story_3_3.py::test_run_sync_returns_sliced_tracks`, `test_story_3_4.py::test_get_or_create_creates_when_no_stored_id`, `…test_get_or_create_recreates_on_invalid_stored_id`, `…test_run_sync_success_returns_dict`). **Non liés à cette story** — Story 6.4 ne touche aucun fichier backend. Bug à traiter dans un follow-up dédié.

### File List

- `frontend/src/components/layout/AppShell.tsx` — refactor majeur (responsive grid, SidebarContents, Sheet mobile, Tooltip statut, topbar mobile-collapse).
- `frontend/src/components/ui/sheet.tsx` — créé via CLI + 1 patch ciblé (`children?: React.ReactNode` dans `SheetContentProps`).
- `frontend/src/components/ui/tooltip.tsx` — créé via CLI.
- `frontend/src/pages/DashboardPage.tsx` — retrait `SyncButton`/`SyncStatusBadge`, ajout `SyncEventLog`, H1 row n'a plus de `flex justify-between`.
- `frontend/src/features/sync/SyncEventLog.tsx` — créé (passif, events-only, tokens dark-theme `--text-secondary`/`--accent-color`/`--danger`).
- `frontend/src/features/sync/SyncButton.tsx` — **supprimé**.
- `frontend/src/features/sync/SyncStatusBadge.tsx` — **supprimé**.
- `frontend/src/index.css` — commentaire `/* tweakable 200–320px … */` au-dessus de `--sidebar-w`.
- `frontend/package.json`, `frontend/package-lock.json` — mis à jour par le shadcn CLI (deps Radix Dialog + Tooltip).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `6-4-desktop-first-responsive-layout: review`.
- `_bmad-output/implementation-artifacts/6-4-desktop-first-responsive-layout.md` — tasks cochées, status → `review`, Dev Agent Record renseigné.

## Change Log

- 2026-05-20: Story 6.4 created — ready-for-dev
- 2026-05-20: Story 6.4 implementée — AppShell responsive (desktop / tablette icon-rail / drawer mobile via Sheet), Topbar mobile-collapse (chevrons / search / status dot-only / Sync icon-only), `SyncEventLog` extrait, `SyncButton` + `SyncStatusBadge` supprimés. Status → review.
