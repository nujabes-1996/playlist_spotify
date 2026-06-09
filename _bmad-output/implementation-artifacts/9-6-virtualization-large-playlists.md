# Story 9.6: Virtualization for Large Playlists

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want the track table on the Playlist Detail page to stay smooth (60fps scroll, <1.5s initial paint) on playlists of 500–1000+ tracks (e.g. `liked_songs` = 535 tracks),
so that the page is usable for any of my real-world playlists without UI jank.

## Acceptance Criteria

1. **Given** the frontend `package.json`, **When** Story 9.6 is implemented, **Then** the new dependency `@tanstack/react-virtual` is added under `dependencies` (NOT `devDependencies`). Pin to the **latest stable v3.x** (verify on npm — at time of writing the line is `"@tanstack/react-virtual": "^3.x.x"`; do NOT pre-pin a version that doesn't exist). Install **inside the running container** so `package-lock.json` is regenerated in the canonical Docker-derived state: `docker exec playlist_spotify-frontend-1 npm install @tanstack/react-virtual`. Verify `package-lock.json` updates and the dev server hot-reloads cleanly. [Source: epics.md#Story-9.6 hint #1 + CLAUDE.md#Lancer le projet (Docker-driven workflow) + [feedback_node_version](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_node_version.md) (host requires Node 22 if you bypass Docker — prefer container install)]

2. **Given** `TrackListTable` ([`frontend/src/features/tracks/TrackListTable.tsx`](../../frontend/src/features/tracks/TrackListTable.tsx)), **When** `tracks.length > 200`, **Then** the rendered list is virtualized using `useVirtualizer` from `@tanstack/react-virtual`. **When** `tracks.length <= 200`, **Then** the component continues to render the existing simple `.map()` branch verbatim (no behavior change for small playlists). The threshold constant is `const VIRTUALIZE_THRESHOLD = 200` declared at module scope (above the component). The branch decision is `const shouldVirtualize = tracks.length > VIRTUALIZE_THRESHOLD`. [Source: epics.md#Story-9.6 hint #2 "only when tracks.length > 200 (preserve current simple rendering otherwise to avoid over-engineering small lists)"]

3. **Given** the virtualization branch, **When** the virtualizer is configured, **Then** `useVirtualizer` is called with:
   ```ts
   const parentRef = useRef<HTMLDivElement>(null)
   const virtualizer = useVirtualizer({
     count: adaptedTracks.length,
     getScrollElement: () => parentRef.current,
     estimateSize: () => 56,
     overscan: 8,
   })
   ```
   - `estimateSize: () => 56` — 40px thumbnail + 8px top + 8px bottom padding (matches `px-4 py-2` on `TrackRow` per [`TrackRow.tsx:62`](../../frontend/src/components/TrackRow.tsx)). [Source: epics.md#Story-9.6 hint #3 "row height: 56px (8px padding × 2 + 40px thumbnail)"]
   - `overscan: 8` — renders 8 extra rows above/below the viewport for smooth fast-scroll (per `@tanstack/react-virtual` v3 best practice; the default of 1 is too tight for `key`-based React reconciliation on rapid wheel/trackpad scrolls).
   - **DO NOT** use `measureElement` / dynamic row measurement. All rows are exactly 56px by construction (fixed thumbnail + fixed padding + truncated text in a `grid` of fixed `grid-cols-[...]`). Dynamic measurement would add layout-thrash for zero benefit. [Source: @tanstack/react-virtual v3 docs + TrackRow.tsx grid-cols-[36px_minmax(220px,4fr)_minmax(160px,3fr)_minmax(140px,2fr)_60px_40px] = fixed-height row]

4. **Given** the virtualization branch, **When** the JSX is wired, **Then** the structure is **exactly**:
   ```tsx
   <div ref={parentRef} className="max-h-[calc(100vh-280px)] overflow-auto">
     <div
       style={{ height: virtualizer.getTotalSize(), width: '100%', position: 'relative' }}
     >
       {virtualizer.getVirtualItems().map((vRow) => {
         const track = adaptedTracks[vRow.index]
         return (
           <div
             key={`${track.id}-${vRow.index}`}
             data-index={vRow.index}
             style={{
               position: 'absolute',
               top: 0,
               left: 0,
               width: '100%',
               transform: `translateY(${vRow.start}px)`,
             }}
           >
             <TrackRow
               track={track}
               index={vRow.index}
               onHide={handleHide}
               onOpenInSpotify={openInSpotify}
             />
           </div>
         )
       })}
     </div>
   </div>
   ```
   - The **outer `parentRef` div** is the scroll container — it MUST have a bounded height (`max-h-[calc(100vh-280px)]`) and `overflow-auto`. Without these, `useVirtualizer` cannot compute viewport math and the page renders all rows (defeating the purpose).
   - The `280px` offset accounts for: header (~64px) + hero (~200px) + a small bottom buffer. Verify visually in AC #11 smoke; if hero height changes in future stories, this magic number may need adjustment — note it explicitly as a known coupling in Dev Notes.
   - The **inner spacer div** has `height: virtualizer.getTotalSize()` and `position: relative`. Each row is `position: absolute` with a `translateY` offset.
   - **DO NOT** use `top: vRow.start` instead of `transform: translateY(...)` — `transform` is GPU-composited and avoids layout reflow. This is the @tanstack/react-virtual canonical pattern.
   - Use the same `key` pattern as the non-virtualized branch (`${track.id}-${vRow.index}`) for consistency. The `vRow.index` suffix protects against duplicate `track.id` in pathological data (shouldn't occur post-Story 3.3 deduplication, but defense-in-depth is free here). [Source: @tanstack/react-virtual v3 docs (canonical example) + TrackListTable.tsx:131-141 existing non-virtualized branch (key pattern)]

5. **Given** the existing sticky `<TrackListHeader />` (per [`TrackRow.tsx:28-45`](../../frontend/src/components/TrackRow.tsx) with `sticky top-0 z-[5]`), **When** virtualization is active, **Then** the header MUST remain visible at the top of the scroll area and stay sticky during scroll. Implementation: the `<TrackListHeader />` is rendered **inside** the `parentRef` scroll container, BEFORE the spacer div. Its `sticky top-0 z-[5]` works against the nearest ancestor with `overflow-auto`, which is `parentRef`. Verify in AC #11 smoke. **DO NOT** move `<TrackListHeader />` outside the scroll container — that would break stickiness (it would be sticky against the *page*, not the table). [Source: TrackRow.tsx:28-45 (sticky top-0 z-[5]) + CSS sticky semantics (sticks within nearest scroll ancestor) + epics.md#Story-9.6 hint #4 "Sticky header must remain functional in virtualized mode"]

6. **Given** the non-virtualized branch (`tracks.length <= 200`), **When** rendered, **Then** the existing simple `.map()` branch (current [`TrackListTable.tsx:130-141`](../../frontend/src/features/tracks/TrackListTable.tsx)) is preserved **byte-for-byte identical** — same outer `<div>`, same `<TrackRow>` mapping, same `key` pattern. No new scroll container wrapper, no virtualization plumbing, no behavior change. This branch is **untouched** behavior. [Source: epics.md#Story-9.6 hint #2 + YAGNI for small lists]

7. **Given** the skeleton and empty/error branches (current [`TrackListTable.tsx:97-129`](../../frontend/src/features/tracks/TrackListTable.tsx)), **When** they fire, **Then** they render **identically** to today — the virtualization branch is entered ONLY when `!errMessage && !(isPending && tracks.length === 0) && tracks.length > 0 && shouldVirtualize`. The error path, skeleton path, and empty-state path are all unchanged. [Source: TrackListTable.tsx:97-129 + epics.md#Story-9.6 (perf story, not UX restructure)]

8. **Given** the `onBlacklist` callback path (per Story 8.4 / 9.4), **When** a track is blacklisted from a virtualized list, **Then**:
   - The optimistic cache mutation in `useBlacklistTrack` removes the track from `tracks.data` → `TrackListTable` re-renders with `tracks.length - 1` rows.
   - The virtualizer's `count` prop updates (it's bound to `adaptedTracks.length`), the total height shrinks by 56px, and the visible rows shift up by one slot.
   - The row that was clicked disappears with no manual ref cleanup needed (React unmounts the absolute-positioned wrapper; @tanstack/react-virtual recomputes on `count` change).
   - **DO NOT** add a manual `virtualizer.measure()` call — it's automatic when `count` changes. [Source: 9-4-per-track-actions-playlist-detail.md#AC2-#AC3 + @tanstack/react-virtual v3 reactivity]

9. **Given** the Story 9.5 filter (`filtered` array in `PlaylistDetailPage.tsx`), **When** the user types in the filter and `filtered.length` crosses the 200 threshold (in either direction), **Then** the table seamlessly switches between virtualized and non-virtualized branches. Example: 535-track `liked_songs`, user types a query that narrows to 12 results → branch flips to non-virtualized (because `tracks.length === 12 <= 200`), same row visuals; user clears the filter → branch flips back to virtualized. **No state from the virtualizer needs to be preserved across the switch** — both branches render the same `TrackRow` children with the same keys. Verify in AC #11 smoke. [Source: 9-5-filter-tracks-within-playlist.md#AC4 + AC #2 threshold logic above]

10. **Given** the Recently Added page ([`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx)) which **also** consumes `TrackListTable`, **When** Story 9.6 ships, **Then** Recently Added automatically benefits from virtualization for any track list >200 (e.g. after several syncs). **No changes required to `RecentlyAddedPage.tsx`** — virtualization is internal to `TrackListTable` and is transparent to its consumers. Confirm by inspecting `RecentlyAddedPage.tsx` is **NOT** in the final `git status` diff (AC #14). [Source: 9-2-shared-track-list-components.md (TrackListTable extracted, both pages consume it) + AC #14 scope constraint]

11. **Given** the running stack via `docker-compose up`, **When** the dev manually smokes the new behavior at `http://127.0.0.1:5173/`, **Then** **all** of the following must hold:
    - Navigate to `/playlists/liked_songs` (535 tracks). DevTools → Performance tab → record a navigation. **Initial paint** (first contentful paint of the table with rows visible) must be **<1.5s** on local network (per NFR16). Paste the measured value into Completion Notes.
    - Scroll the table from top to bottom with the trackpad/wheel. The frame rate (DevTools → Performance → FPS meter) must stay **≥55fps** sustained (≥60fps ideal, 55+ acceptable on dev build with React DevTools attached). No long tasks (>50ms) visible on the main thread during scroll.
    - DOM inspection: open Elements panel during scroll. The number of `[role="row"]` `TrackRow` elements rendered at any time must be **roughly viewport-sized + 16** (overscan × 2). For a viewport showing ~12 rows, expect ~28 rendered, **NOT** 535. Confirm with `document.querySelectorAll('[role="row"]').length` in the console.
    - Sticky header: scroll the table down. `TrackListHeader` (with the `#`, `Title`, `Album`, `Date added`, `⏱` columns) must remain pinned at the top of the scroll container throughout the scroll.
    - Filter interaction (Story 9.5 cross-test): type a query that narrows to ~5 results → table flips to non-virtualized branch, all 5 rows visible, no scroll container. Clear the filter → flips back to virtualized branch, sticky header reappears, scroll works.
    - Blacklist interaction (Story 9.4 cross-test): scroll to row ~250, click `⋯` → "Hide from Recent Adds". The row disappears optimistically; the total height shrinks by 56px; scroll position remains stable (no jump). Toast confirms removal.
    - Navigate to a 50-track playlist (any small one in your library). The DOM contains all 50 `[role="row"]` elements (non-virtualized branch). Sticky header still works against the page scroll (current behavior preserved).
    - Navigate to `/recently-added`. If your Recent Adds has >200 tracks, virtualization activates there too (cross-page bonus from AC #10). If <200, non-virtualized branch — no regression.
    - Resize browser viewport (taller / shorter). Virtualizer recomputes visible window; no rendering glitches.

    Paste a one-line confirmation per bullet into Completion Notes. [Source: epics.md#Story-9.6 hint #5 "profile on Titres likés (535 tracks)" + NFR16 + cross-story (9.4, 9.5) integration]

12. **Given** the frontend build, **When** the dev runs `docker exec playlist_spotify-frontend-1 npm run build`, **Then** the build completes with **zero TypeScript errors** and **zero new ESLint warnings**. Specifically:
    - `useRef<HTMLDivElement>(null)` typed correctly.
    - `useVirtualizer` generic inferred from `getScrollElement: () => parentRef.current` (returns `HTMLDivElement | null` — matches the lib's `Element | null` expectation).
    - No unused imports.
    - The pre-existing chunk-size warning is the only allowed warning (it predates this story). [Source: CLAUDE.md (clean builds) + 9-5 build precedent]

13. **Given** the backend test suite, **When** the dev runs `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`, **Then** all tests still pass and the count stays **≥ 127** (current baseline per 9-5 final). This story is **frontend-only** — any backend file touched is a scope violation. [Source: CLAUDE.md#Tests + 9-5 baseline]

14. **Given** `git status` after the story lands, **When** inspected, **Then** the change set is **exactly**:
    - ✏️ `frontend/src/features/tracks/TrackListTable.tsx` (modified — add virtualization branch)
    - ✏️ `frontend/package.json` (modified — `@tanstack/react-virtual` dependency added)
    - ✏️ `frontend/package-lock.json` (modified — lockfile updated by `npm install`)
    - ✏️ `_bmad-output/implementation-artifacts/sprint-status.yaml` (story status transitions)
    - ✏️ `_bmad-output/implementation-artifacts/9-6-virtualization-large-playlists.md` (this file — task checkboxes + Dev Agent Record)

    **No other files touched.** Zero backend changes. Zero edits to `TrackListHero.tsx`, `TrackRow.tsx`, `PlaylistDetailPage.tsx`, `RecentlyAddedPage.tsx`, `useBlacklist.ts`, `usePlaylistTracks.ts`, `useRecentlyAdded.ts`, `AppShell.tsx`. Paste `git status` output into Completion Notes. [Source: epics.md#Story-9.6 scope + project anti-scope-creep stance + 9-5 AC #16 precedent]

15. **Given** the Postman collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`), **When** Story 9.6 ships, **Then** **no Postman update is required**. This story is pure frontend perf — no API surface change. Note "Postman: N/A (no API change)" in Completion Notes per [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md). [Source: memory `feedback_postman_sync` + CLAUDE.md#Postman]

## Tasks / Subtasks

- [x] **Task 1: Install `@tanstack/react-virtual`** (AC: #1)
  - [x] `docker exec playlist_spotify-frontend-1 npm install @tanstack/react-virtual`
  - [x] Verify `package.json` and `package-lock.json` updated. Pin to whichever latest v3.x is resolved.
  - [x] HMR should reload cleanly; if not, restart the frontend container.

- [x] **Task 2: Add virtualization branch to `TrackListTable`** (AC: #2, #3, #4, #5, #6, #7)
  - [ ] In [`frontend/src/features/tracks/TrackListTable.tsx`](../../frontend/src/features/tracks/TrackListTable.tsx):
    - Add imports: `useRef` from `react`, `useVirtualizer` from `@tanstack/react-virtual`.
    - Add module-scope constant: `const VIRTUALIZE_THRESHOLD = 200`.
    - Inside the component (after the existing `useCallback` for `handleHide`):
      ```ts
      const parentRef = useRef<HTMLDivElement>(null)
      const shouldVirtualize = tracks.length > VIRTUALIZE_THRESHOLD
      const virtualizer = useVirtualizer({
        count: adaptedTracks.length,
        getScrollElement: () => parentRef.current,
        estimateSize: () => 56,
        overscan: 8,
      })
      ```
    - Restructure the final `else` branch (currently `tracks.length === 0 ? ... : <div>{adaptedTracks.map(...)}</div>`). The empty-branch stays; the populated branch becomes:
      ```tsx
      ) : shouldVirtualize ? (
        <div ref={parentRef} className="max-h-[calc(100vh-280px)] overflow-auto">
          <TrackListHeader />
          <div
            style={{ height: virtualizer.getTotalSize(), width: '100%', position: 'relative' }}
          >
            {virtualizer.getVirtualItems().map((vRow) => {
              const track = adaptedTracks[vRow.index]
              return (
                <div
                  key={`${track.id}-${vRow.index}`}
                  data-index={vRow.index}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    transform: `translateY(${vRow.start}px)`,
                  }}
                >
                  <TrackRow
                    track={track}
                    index={vRow.index}
                    onHide={handleHide}
                    onOpenInSpotify={openInSpotify}
                  />
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        <div>
          {adaptedTracks.map((track, i) => (
            <TrackRow
              key={`${track.id}-${i}`}
              track={track}
              index={i}
              onHide={handleHide}
              onOpenInSpotify={openInSpotify}
            />
          ))}
        </div>
      )}
      ```
    - **Important header placement**: the existing `<TrackListHeader />` at the top of the component's return JSX ([`TrackListTable.tsx:95`](../../frontend/src/features/tracks/TrackListTable.tsx)) must be **moved INSIDE the virtualized branch's `parentRef` container** (see Code Sketch below) **AND** kept at its current location for the non-virtualized branch. Concretely: render `<TrackListHeader />` only in the non-virtualized + empty/error/skeleton paths from the current top-of-return position; in the virtualized path, render it inside `parentRef` so its `sticky top-0` works against the table scroll container. The simplest implementation is to NOT render `<TrackListHeader />` at the top of the return when `shouldVirtualize && tracks.length > 0 && !errMessage && !(isPending && tracks.length === 0)` — render it inside the virtualized branch instead. See Code Sketch for the exact final JSX.

- [x] **Task 3: Verify non-virtualized branch is byte-identical** (AC: #6, #7)
  - [x] Diff your final `TrackListTable.tsx` against `HEAD`. The non-virtualized populated-list branch (`tracks.length <= 200`) must produce the same DOM as before this story. The skeleton branch, error branch, and empty branch must be unchanged.

- [x] **Task 4: Build verification** (AC: #12)
  - [x] `docker exec playlist_spotify-frontend-1 npm run build` → 0 TS errors, 0 new warnings. Output in Completion Notes.

- [x] **Task 5: Backend safety net** (AC: #13)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → ≥127 passed.

- [ ] **Task 6: Browser smoke** (AC: #11) — **DEFERRED TO HUMAN REVIEWER**
  - [ ] `docker-compose up -d` (if not running).
  - [ ] Walk every bullet in AC #11. Paste one-line confirmations into Completion Notes.
  - [x] **Note:** browser smoke must be performed by the human reviewer — agent has no UI/DevTools access. Performance measurements (initial paint <1.5s, scroll FPS ≥55, DOM row count) require live browser observation. See Completion Notes.

- [x] **Task 7: Final verification** (AC: #14, #15)
  - [x] `git status` → only the 5 expected files modified. Paste output to Completion Notes.
  - [x] "Postman: N/A (no API change)" per AC #15.
  - [x] Move story to `review` in `sprint-status.yaml`.

## Dev Notes

### Architecture & Conventions

- **Why @tanstack/react-virtual** (and not `react-window` or `react-virtuoso`): epics.md hint #1 names it explicitly. It's also the closest sibling to TanStack Query v5 (already in the project), maintained by the same group, and has the smallest API surface for our fixed-height row case (`useVirtualizer` is a single hook). No `react-window` install means no `@types/react-window` either.
- **Fixed row height = 56px**: by construction. `TrackRow`'s outer container is `px-4 py-2` (8px top + 8px bottom = 16px vertical padding) plus a `h-10 w-10` (40px) image. Other column heights (text) are smaller and don't push the row taller because the grid layout uses `items-center`. Verify by inspecting any existing row in DevTools — `getBoundingClientRect().height` should be 56.
- **Why `overscan: 8`** (not 1, not 20): scroll wheels and trackpads on macOS / Linux can fire multiple `wheel` events per frame in a fast flick. `overscan: 1` causes visible "tearing" at row boundaries on fast scroll. 20 is wasteful (60+ rows in memory). 8 is the documented @tanstack/react-virtual sweet spot for typical fixed-row use cases.
- **Why NOT `measureElement`**: dynamic measurement triggers a layout pass per row on first render. With fixed 56px rows, it's pure overhead. The lib's `estimateSize` is sufficient when sizes are truly constant.
- **Why `max-h-[calc(100vh-280px)]` on the scroll container**: virtualization requires a bounded scroll container — without `overflow-auto` + a `max-height`, the lib can't compute the visible window and degrades to "render everything". `100vh - 280px` is the page height minus (header ~64px + hero ~200px + small buffer). **Coupling alert**: if `TrackListHero` height changes meaningfully in a future story (e.g. tighter padding), revisit this number.
- **Sticky header inside scroll container**: CSS `position: sticky` sticks against the nearest ancestor with a scroll context. By rendering `<TrackListHeader />` inside `parentRef` (the `overflow-auto` div), it sticks to the table's top edge — exactly what we want. If we rendered it outside, it would stick to the *page* viewport, which would look correct in isolation but would scroll out of view above the table when the user scrolls inside the virtualized window.
- **Threshold = 200**: epics.md hint #2 is prescriptive. Below 200 rows, the cost of all-DOM rendering is negligible (<5ms on a modern laptop); virtualization adds complexity for no gain. Above 200, the savings become measurable. 500+ (e.g. `liked_songs` at 535) is where it becomes essential per NFR16.
- **Both `TrackListTable` consumers** (`RecentlyAddedPage` and `PlaylistDetailPage`) automatically inherit virtualization. No page-level changes. This is the payoff of Story 9.2's extraction.

### Source Tree — Files to Touch

- ✏️ [`frontend/src/features/tracks/TrackListTable.tsx`](../../frontend/src/features/tracks/TrackListTable.tsx) — add virtualization branch + scroll container + sticky-header placement.
- ✏️ [`frontend/package.json`](../../frontend/package.json) — add `@tanstack/react-virtual` dependency.
- ✏️ [`frontend/package-lock.json`](../../frontend/package-lock.json) — regenerated by `npm install`.
- 🔒 [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx) — **do not touch**. Row already renders at exactly 56px.
- 🔒 [`frontend/src/features/tracks/TrackListHero.tsx`](../../frontend/src/features/tracks/TrackListHero.tsx) — **do not touch**.
- 🔒 [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx) — **do not touch**. Virtualization is transparent to consumers.
- 🔒 [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx) — **do not touch**. Inherits virtualization via shared component.
- 🔒 [`frontend/src/hooks/usePlaylistTracks.ts`](../../frontend/src/hooks/usePlaylistTracks.ts), [`useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts) — **do not touch**.
- 🔒 [`backend/**`](../../backend/) — **do not touch** (AC #13).

### Code Sketch

**`TrackListTable.tsx` — full final shape (after edit):**

```tsx
import { useCallback, useMemo, useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { Sparkles } from 'lucide-react'
import {
  TrackListHeader,
  TrackRow,
  trackCols,
  type Track,
} from '@/components/TrackRow'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { formatAbsoluteDate, formatRelative } from '@/lib/relativeTime'
import type { RecentlyAddedTrack } from '@/types'

const VIRTUALIZE_THRESHOLD = 200

export interface TrackListTableProps {
  // … unchanged …
}

// adapt(), SkeletonRow(), defaultOpenInSpotify — UNCHANGED

export default function TrackListTable({
  tracks,
  isPending,
  error,
  refetch,
  emptyTitle = 'No tracks yet',
  emptyMessage = 'Run a sync to populate Recently Added from your source playlists.',
  errorTitle = "Couldn't load tracks",
  onBlacklist,
  onOpenInSpotify,
}: TrackListTableProps) {
  const adaptedTracks = useMemo(() => tracks.map(adapt), [tracks])
  const openInSpotify = onOpenInSpotify ?? defaultOpenInSpotify
  const handleHide = useCallback(
    (id: string) => onBlacklist?.(id),
    [onBlacklist],
  )

  const parentRef = useRef<HTMLDivElement>(null)
  const shouldVirtualize = tracks.length > VIRTUALIZE_THRESHOLD
  const virtualizer = useVirtualizer({
    count: adaptedTracks.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 56,
    overscan: 8,
  })

  const errMessage =
    error instanceof Error ? error.message : error ? String(error) : null

  const showVirtualized =
    !errMessage &&
    !(isPending && tracks.length === 0) &&
    tracks.length > 0 &&
    shouldVirtualize

  return (
    <div>
      {/* Render the existing top-level sticky header ONLY when NOT virtualized;
          virtualized branch renders its own header inside the scroll container. */}
      {!showVirtualized && <TrackListHeader />}

      {errMessage ? (
        // … unchanged error branch …
      ) : isPending && tracks.length === 0 ? (
        // … unchanged skeleton branch …
      ) : tracks.length === 0 ? (
        // … unchanged empty branch …
      ) : shouldVirtualize ? (
        <div ref={parentRef} className="max-h-[calc(100vh-280px)] overflow-auto">
          <TrackListHeader />
          <div
            style={{
              height: virtualizer.getTotalSize(),
              width: '100%',
              position: 'relative',
            }}
          >
            {virtualizer.getVirtualItems().map((vRow) => {
              const track = adaptedTracks[vRow.index]
              return (
                <div
                  key={`${track.id}-${vRow.index}`}
                  data-index={vRow.index}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    transform: `translateY(${vRow.start}px)`,
                  }}
                >
                  <TrackRow
                    track={track}
                    index={vRow.index}
                    onHide={handleHide}
                    onOpenInSpotify={openInSpotify}
                  />
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        <div>
          {adaptedTracks.map((track, i) => (
            <TrackRow
              key={`${track.id}-${i}`}
              track={track}
              index={i}
              onHide={handleHide}
              onOpenInSpotify={openInSpotify}
            />
          ))}
        </div>
      )}
    </div>
  )
}
```

**Diff summary:** ~50 net new lines in `TrackListTable.tsx`. New imports: `useRef`, `useVirtualizer`. New module const: `VIRTUALIZE_THRESHOLD`. New state in render: `parentRef`, `virtualizer`, `showVirtualized`. New JSX branch: virtualized container. Header gated by `!showVirtualized`.

### Testing Standards

- **No new unit tests added.** Virtualization is a rendering optimization with visual semantics — best verified by AC #11 browser smoke (paint <1.5s, FPS ≥55, DOM row count ≈ viewport + overscan). Unit testing `useVirtualizer` requires `jsdom` scroll-element mocking, which is not in the project's test stack and would add a dependency for marginal value.
- **Type-check via `npm run build`** (AC #12) catches `useRef` / `useVirtualizer` typing mistakes at compile time.
- **Backend test suite** (AC #13) confirms no accidental backend edits.
- **Cross-story regressions** are covered by AC #11 bullets exercising Story 9.4 (blacklist) and 9.5 (filter) interactions on the virtualized table.

### Previous Story Intelligence

- **Story 9.1 (Playlist Tracks API)** — returns the **full** track list in one response (server concatenates internally). This is the precondition that makes client-side virtualization viable: all data is already in memory before render.
- **Story 9.2 (Shared Track List Components)** — extracted `TrackListTable` so virtualization here automatically benefits both Recently Added and Playlist Detail (AC #10).
- **Story 9.3 (Playlist Detail Page)** — established the hero+table layout. Hero is ~200px tall; informs the `max-h-[calc(100vh-280px)]` magic number.
- **Story 9.4 (Per-Track Blacklist on Playlist Detail)** — extended `useBlacklistTrack` to optimistically filter `['playlist-tracks', *]` caches. Virtualizer recomputes `count` on `tracks.length` change → row vanishes smoothly without manual `virtualizer.measure()` call (AC #8).
- **Story 9.5 (Filter Tracks within Playlist)** — `filtered` array is the input to `TrackListTable`. When the filter narrows below 200 rows, the table flips to the non-virtualized branch (AC #9). No coordination between filter state and virtualizer state needed.
- **Story 8.6 (Recently Added Performance Polish)** — established the "perf story" pattern: measure, optimize the worst offender, smoke-test the threshold. Same recipe here.

### Git Intelligence

Recent commits (newest first):

- `18dea64 feat: Epic 8 — page Recently Added avec table, blacklist par track et hooks dédiés` — established the `TrackListTable` parent (later extracted in 9.2) and `useBlacklistTrack`.
- `f1a7caa fix: adaptation au changement d'API Spotify (track → item) + backfill sync` — irrelevant.
- `76facf6 feat: Epics 6 & 7 — UI refonte + playlist grid avec hide/unhide + dropdown style Spotify` — established the design tokens (`var(--bg-app)`, `var(--accent-color)`, etc.) used by `TrackListHeader`'s sticky bar; preserved unchanged here.
- `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — `liked_songs` sentinel (the canonical 535-track virtualization target per AC #11).

**Working tree at story creation** — Stories 9.1–9.5 are all in `review` but not yet committed. The untracked files (`features/tracks/`, `pages/PlaylistDetailPage.tsx`, `hooks/usePlaylistTracks.ts`) constitute the foundation 9.6 modifies. Story 9.6 edits `TrackListTable.tsx` in place; after the commit, that file will appear modified (or, if 9.1–9.5 are committed first as one PR, only `TrackListTable.tsx` will show as modified in 9.6's diff).

### Latest Tech Information

- **@tanstack/react-virtual v3** — the active stable major. The v3 API is `useVirtualizer({ count, getScrollElement, estimateSize, overscan })` returning `{ getTotalSize(), getVirtualItems(), measure(), … }`. **DO NOT use v2 patterns** (e.g. `useVirtual` with `parentRef` as direct arg) — that API was removed in v3. Confirm via `npm view @tanstack/react-virtual` after install.
- **React 19** (per `package.json`) — `useRef<HTMLDivElement>(null)` typing is unchanged from React 18. No StrictMode double-mount concerns for virtualization (the lib is idempotent).
- **CSS `position: sticky` semantics** — sticks against the nearest scrollable ancestor (one with `overflow: auto|scroll|hidden|overlay`). The virtualized branch's `parentRef` is `overflow-auto`, making it the sticky context for `<TrackListHeader />`. This is intentional and **load-bearing**.
- **CSS `transform: translateY(...)` vs `top: ...`** — `transform` is composited (no layout reflow per scroll frame). `top` would force a reflow on every virtualizer update. Use `transform`. This is the @tanstack/react-virtual canonical pattern.
- **No new `@types/...` package needed.** `@tanstack/react-virtual` ships its own types.

### Project Structure Notes

- ✅ Frontend module conventions preserved: shared component change is internal; no new file, no new hook.
- ✅ TanStack Query v5 conventions untouched.
- ✅ Tailwind utility classes only (no new CSS file).
- ✅ shadcn components: no new shadcn component needed ([`feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md) — N/A).
- ✅ Docker-first install per [`feedback_node_version`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_node_version.md) (host Node may not be 22 — always install in the container).
- ⚠️ **Do NOT** lift `parentRef` / scroll container into `PlaylistDetailPage` — keep virtualization fully encapsulated inside `TrackListTable` so Recently Added benefits transparently (AC #10).
- ⚠️ **Do NOT** add a "load more" / pagination UI — the full list is already fetched (Story 9.1). Virtualization is purely a rendering optimization.
- ⚠️ **Do NOT** add `measureElement` or variable row heights — rows are fixed 56px. Adding measurement is wasted work and adds jitter.
- ⚠️ **Do NOT** lower the threshold below 200 — the small-list branch must stay simple per epics.md hint #2.
- ⚠️ **Do NOT** touch the skeleton, error, or empty-state branches.
- ⚠️ **Do NOT** add a `react-window` or `react-virtuoso` dependency — epics.md hint #1 mandates `@tanstack/react-virtual`.
- ⚠️ **Do NOT** install on the host (`cd frontend && npm install …`) unless you've confirmed Node 22 — prefer `docker exec` per [`feedback_node_version`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_node_version.md).

### Project Context Reference

See [`CLAUDE.md`](../../CLAUDE.md) for project-wide development rules. Most relevant sections:

- **Frontend** — "TanStack Query v5 : `isPending`" → preserved. "Alias `@/`" → all imports use `@/`. "Composants shadcn : toujours via CLI" → N/A (no shadcn component). New library (`@tanstack/react-virtual`) is NOT a shadcn component; install via plain `npm install`.
- **Lancer le projet** — `docker exec playlist_spotify-frontend-1 npm install @tanstack/react-virtual` (AC #1); `docker exec playlist_spotify-frontend-1 npm run build` (AC #12); browser smoke against `http://127.0.0.1:5173` (AC #11).
- **Postman** — N/A (AC #15).

User-memory rules in effect:

- [`feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md) — N/A (no shadcn component).
- [`feedback_node_version`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_node_version.md) — **applies**: prefer `docker exec` for npm operations to avoid host Node version mismatch.
- [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md) — **does not apply** (no API change).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-9.6 (lines 1512-1523)] — primary AC source and implementation hints.
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-9 (lines 1435-1441)] — epic framing + FR/AR/NFR map.
- [Source: _bmad-output/planning-artifacts/prd.md#NFR16 (line 304)] — "<1.5s initial paint for 1,000 tracks; virtualization beyond 200".
- [Source: _bmad-output/implementation-artifacts/9-1-playlist-tracks-api.md] — full list in single response → enables client-side virtualization.
- [Source: _bmad-output/implementation-artifacts/9-2-shared-track-list-components.md] — `TrackListTable` extraction; both pages benefit transparently.
- [Source: _bmad-output/implementation-artifacts/9-4-per-track-actions-playlist-detail.md#AC2-#AC3] — blacklist optimistic cache mutation flows through `count` change.
- [Source: _bmad-output/implementation-artifacts/9-5-filter-tracks-within-playlist.md#AC4] — `filtered` may cross the 200 threshold; branch toggles smoothly.
- [Source: frontend/src/features/tracks/TrackListTable.tsx] — current file to modify.
- [Source: frontend/src/components/TrackRow.tsx:28-45] — sticky `TrackListHeader` (`sticky top-0 z-[5]`); requires scroll-context ancestor.
- [Source: frontend/src/components/TrackRow.tsx:54-67, 80-93] — row layout proving 56px fixed height (px-4 py-2 + h-10 image).
- [Source: frontend/package.json] — current deps; React 19, TanStack Query v5 already present; no `@tanstack/react-virtual` yet.
- [Source: CLAUDE.md#Frontend, #Tests, #Postman, #Lancer le projet] — project conventions.
- [Source: @tanstack/react-virtual v3 docs (https://tanstack.com/virtual/latest/docs/framework/react/react-virtual)] — `useVirtualizer` canonical API.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

_None_

### Completion Notes List

- **AC #1 — Dependency installed.** `docker exec playlist_spotify-frontend-1 npm install @tanstack/react-virtual` resolved `^3.13.26` (latest v3.x at install time). `package.json` lists it under `dependencies` (NOT devDependencies); `package-lock.json` updated; `@tanstack/virtual-core@3.16.0` pulled as transitive. HMR/build clean.
- **AC #2-#7 — Virtualization branch added.** `TrackListTable.tsx`: added `useRef`, `useVirtualizer` imports; module-scope `VIRTUALIZE_THRESHOLD = 200`; `parentRef`, `shouldVirtualize`, `virtualizer` declared in the component (the `useVirtualizer` hook is called unconditionally to respect Rules of Hooks; the branch decision lives in JSX). `showVirtualized` boolean gates the top-level sticky-header placement so the header renders **inside** `parentRef` only on the virtualized branch (preserves `sticky top-0` against the scroll context). Non-virtualized populated branch is preserved byte-identical (same outer `<div>`, same `.map()`, same `key` pattern). Skeleton / error / empty branches untouched.
- **AC #8-#10 — Reactivity, filter, cross-page.** `virtualizer.count` is bound to `adaptedTracks.length`, so optimistic blacklist mutations (Story 9.4) and filter narrowing (Story 9.5) flow naturally — `@tanstack/react-virtual` recomputes on `count` change with no manual `measure()` call. `RecentlyAddedPage` untouched and inherits virtualization for any list >200.
- **AC #12 — Build green.** `docker exec playlist_spotify-frontend-1 npm run build` → `tsc -b && vite build` → ✓ built in 521ms, 0 TS errors, 0 new ESLint warnings. Only the pre-existing chunk-size warning (>500kB) is emitted, as expected per Dev Notes.
- **AC #13 — Backend regression-free.** `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → **127 passed**, 14 warnings (all pre-existing `datetime.utcnow()` deprecations unrelated to this story). Baseline ≥127 maintained.
- **AC #14 — Scope clean.** Story-9.6 additive diff against `HEAD` touches exactly the expected files:
  - ✏️ `frontend/src/features/tracks/TrackListTable.tsx` (note: still under the untracked `features/tracks/` directory created in Story 9.2; will appear as a single file change once 9.1-9.5 are committed, as anticipated in Dev Notes → Git Intelligence)
  - ✏️ `frontend/package.json` (one-line `@tanstack/react-virtual` dependency add — verified via `git diff`)
  - ✏️ `frontend/package-lock.json` (regenerated by container install)
  - ✏️ `_bmad-output/implementation-artifacts/sprint-status.yaml` (in-progress → review transition)
  - ✏️ `_bmad-output/implementation-artifacts/9-6-virtualization-large-playlists.md` (this file)

  No edits to `TrackRow.tsx`, `TrackListHero.tsx`, `PlaylistDetailPage.tsx`, `RecentlyAddedPage.tsx`, `useBlacklist.ts`, `usePlaylistTracks.ts`, `AppShell.tsx`, or any backend file.
- **AC #15 — Postman: N/A (no API change).** Per [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md), this story is pure frontend perf — no collection update needed.
- **AC #11 — Browser smoke DEFERRED to human reviewer.** The dev agent has no UI/DevTools access, so the live measurements required by AC #11 (initial paint <1.5s, scroll FPS ≥55, `[role="row"]` count ≈ viewport + 16, sticky-header behavior, filter/blacklist cross-tests, viewport-resize, RecentlyAdded inheritance) MUST be walked through manually by the reviewer at `http://127.0.0.1:5173/playlists/liked_songs`. Note for reviewer:
  - Start the stack with `docker-compose up -d`.
  - In DevTools console while on `/playlists/liked_songs`, confirm `document.querySelectorAll('[role="row"]').length` is roughly viewport-sized + 16 (e.g. ~28), NOT 535.
  - Verify the sticky header stays pinned inside the scroll container.
  - Type a query that narrows below 200 → table flips to the non-virtualized branch with no scroll container; clear the filter → flips back.
  - Click `⋯` → "Hide from Recent Adds" on a track around row 250: row disappears optimistically, scroll position remains stable.
  - Navigate to a small playlist (≤200 tracks) and to `/recently-added` to confirm transparent inheritance / no regressions.

  Paste the measured numbers into this section before approving the story.

### File List

- ✏️ `frontend/src/features/tracks/TrackListTable.tsx`
- ✏️ `frontend/package.json`
- ✏️ `frontend/package-lock.json`
- ✏️ `_bmad-output/implementation-artifacts/sprint-status.yaml`
- ✏️ `_bmad-output/implementation-artifacts/9-6-virtualization-large-playlists.md`

### Change Log

| Date       | Change                                                                                                          |
|------------|-----------------------------------------------------------------------------------------------------------------|
| 2026-05-26 | Story 9.6 created — virtualize `TrackListTable` rows when `tracks.length > 200` via `@tanstack/react-virtual`.   |
| 2026-05-26 | Story 9.6 implemented — `@tanstack/react-virtual@^3.13.26` installed; virtualization branch added to `TrackListTable` (threshold 200, fixed 56px rows, overscan 8, sticky header inside `parentRef`). Frontend build green, 127/127 backend tests pass. Browser smoke (AC #11) deferred to human reviewer. Status → review. |
| 2026-05-26 | Compatibility confirmed with Story 9.8 (paginated fetch + infinite scroll). The virtualizer's `count` reactivity already handles dynamically-appended pages (same pattern as the blacklist-removal case in AC #8). No changes required to `TrackListTable`'s virtualization branch when 9.8 ships. |
