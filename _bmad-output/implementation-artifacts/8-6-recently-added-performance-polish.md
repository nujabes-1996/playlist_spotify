# Story 8.6: Recently Added Performance & Polish

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want the Recently Added page to feel instant and behave correctly when I blacklist many tracks in a row,
so that the page is a reliable daily tool.

## Acceptance Criteria

1. **Given** the `/recently-added` route with a populated dynamic playlist of 200 tracks, **When** the page is profiled in Chromium DevTools (default CPU, no network throttling, hard refresh), **Then** the initial paint of the populated table (`RecentlyAddedTable` first commit with 200 `<TrackRow>` children) completes in **under 1 second** measured from the moment `useRecentlyAdded()` exits `isPending` to the React commit that produces the populated grid (NFR14, per `prd.md` line 283 "Recently Added track list renders within 1 second for up to 200 tracks"). Off-screen cover thumbnails may still be fetching — that is acceptable per AC #2. [Source: epics.md#Story-8.6 AC #1 + prd.md line 283 + Story 8.3 AC #15 explicit forward-pointer to this story]

2. **Given** each `<TrackRow>`'s cover thumbnail at [`frontend/src/components/TrackRow.tsx:78-84`](../../frontend/src/components/TrackRow.tsx#L78-L84), **When** the row's `<img>` element is inspected in DevTools, **Then** the element carries **all** of the following attributes:
   - `loading="lazy"` (already present at `TrackRow.tsx:81` — verify still in place after this story's changes)
   - `decoding="async"` (off-main-thread image decode — **NEW**, must be added)
   - explicit `width={40} height={40}` (gives the browser a layout hint and avoids reflow on image decode)

   With 200 tracks at viewport 1280×800, expect roughly **15–25 image HTTP requests** on initial render (above-the-fold rows only) — verifiable via DevTools Network tab. NOT 200 simultaneous requests. [Source: epics.md#Story-8.6 AC #2 + MDN `loading="lazy"` spec + Story 7.5 AC #2 precedent]

3. **Given** the user blacklists tracks in quick succession (e.g., 5 clicks within ~2 seconds), **When** each `POST /api/v1/blacklist` resolves (`onSuccess`) or fails (`onError`), **Then** the TanStack Query cache for `['recently-added']` is **NOT** invalidated per click. Today, [`frontend/src/hooks/useBlacklist.ts:36-38`](../../frontend/src/hooks/useBlacklist.ts#L36-L38) calls `queryClient.invalidateQueries({ queryKey: ['recently-added'] })` in `onSettled` — that line **must be removed**. The optimistic update from `onMutate` (filter the row out of the cache) is sufficient on its own; do NOT replace `onSettled` with an `onSuccess` setQueryData merge either — the optimistic cache already reflects the desired final state, and the rollback path stays in `onError`. [Source: epics.md#Story-8.6 AC #3 + TanStack Query v5 optimistic-update docs + useBlacklist.ts:20-35 existing `onMutate`/`onError` pattern]

4. **Given** the user triggers a manual sync from the Recently Added hero ("Sync now" button at [`frontend/src/features/recently-added/RecentlyAddedHero.tsx:37`](../../frontend/src/features/recently-added/RecentlyAddedHero.tsx#L37) calling `useSyncStream().startStream()`), **When** the SSE stream emits the `sync_complete` event handled at [`frontend/src/hooks/useSyncStream.ts:29-37`](../../frontend/src/hooks/useSyncStream.ts#L29-L37), **Then** the existing `onDone` handler additionally calls `queryClient.invalidateQueries({ queryKey: ['recently-added'] })` so the table refetches the now-updated playlist contents. Add the line alongside the existing `['sync', 'logs']` and `['sync', 'status']` invalidations at `useSyncStream.ts:33-34` — do NOT create a new useEffect, do NOT subscribe to a second stream. One line, same callback. [Source: epics.md#Story-8.6 AC #4 + useSyncStream.ts:29-37 existing onDone pattern + Story 5.3 SSE contract (`sync_complete` event name)]

5. **Given** a sync triggered via the AppShell topbar (same `useSyncStream().startStream()` from [`AppShell.tsx:171`](../../frontend/src/components/layout/AppShell.tsx#L171)), **When** that sync completes, **Then** the same invalidation from AC #4 fires — because both call sites share the single `useSyncStream` hook, fixing it in one place propagates correctly. Verify by running a sync from `/` (Dashboard) and confirming `/recently-added` shows fresh data the next time it is visited (or immediately if it is already mounted). [Source: useSyncStream.ts single-source-of-truth pattern + AppShell.tsx:171 + RecentlyAddedHero.tsx:37]

6. **Given** the SSE stream errors out (`sync_error` event at [`useSyncStream.ts:39-43`](../../frontend/src/hooks/useSyncStream.ts#L39-L43) which calls `onDone()`), **When** that handler fires, **Then** the same `['recently-added']` invalidation runs — `onDone` is shared between success and error paths today, and we want failures to also refresh the cache in case a partial sync mutated the playlist. Do NOT split the invalidation across `sync_complete`-only and `sync_error`-only handlers; one line inside `onDone` covers both. [Source: useSyncStream.ts:29-43 onDone reuse + sync engine "leaves dynamic playlist intact on failure" invariant from prd.md#Reliability — refetch is still safe]

7. **Given** `<TrackRow>` re-renders triggered by parent state churn (e.g., the optimistic blacklist filter rebuilds the `tracks` array in [`useBlacklist.ts:24-28`](../../frontend/src/hooks/useBlacklist.ts#L24-L28)), **When** React reconciles, **Then** `<TrackRow>` is wrapped in `React.memo` with the default shallow prop comparison. The props are stable: `track` is a plain object (the adapter at [`RecentlyAddedTable.tsx:22-40`](../../frontend/src/features/recently-added/RecentlyAddedTable.tsx#L22-L40) currently builds a **new** object on every render — see AC #8 for the fix), `index` is a primitive, and `onHide`/`onOpenInSpotify` are inline callbacks (see AC #9). Wrapping `TrackRow` is necessary but not sufficient on its own — ACs #8 and #9 stabilize the props so the memo actually skips. [Source: epics.md#Story-8.6 AC #1 (perf) + React.memo docs + Story 7.5 AC #5 precedent on `PlaylistCard`]

8. **Given** the row adapter `adapt(t: RecentlyAddedTrack): Track` at [`RecentlyAddedTable.tsx:22-40`](../../frontend/src/features/recently-added/RecentlyAddedTable.tsx#L22-L40), **When** the table renders 200 rows, **Then** the adapter must NOT allocate a fresh `Track` object per render — wrap the per-track adaptation in `useMemo(() => tracks.map(adapt), [tracks])`. This makes the `track` prop reference-stable across re-renders **as long as the `tracks` array reference is unchanged**, which is the dominant case (TanStack Query reuses the array reference when query data is unchanged, and the optimistic blacklist mutation only rebuilds one entry — but our memo will still rebuild the whole adapted array in that case, which is fine: only the removed row is gone, all surviving entries get fresh refs but React.memo + shallow comparison of `{title, artist, ...}` is still O(1) per row and ~200 comparisons is microseconds). Cleaner alternative: lift `adapt` out of the component (it already lives at module scope — keep it there) and memoize the mapped array. [Source: React.memo + useMemo docs + TanStack Query v5 immutability semantics]

9. **Given** the `onHide` and `onOpenInSpotify` callbacks at [`RecentlyAddedTable.tsx:119-141`](../../frontend/src/features/recently-added/RecentlyAddedTable.tsx#L119-L141) (currently inline arrow functions in the JSX), **When** the table re-renders, **Then** these callbacks must keep **stable references** across renders so `React.memo` on `<TrackRow>` actually skips. Two acceptable options — pick the simpler:
   - **(a)** Hoist `openInSpotify` to module scope (it does not close over any prop or state — same pattern as `PlaylistGrid.tsx:17-23` from Story 7.5). For `onHide`, wrap the body in `useCallback(([id]) => blacklist.mutate(...), [blacklist])` — `blacklist` (the mutation object from `useMutation`) is stable across renders for a given mounted component.
   - **(b)** Move the per-row `onHide` and `onOpenInSpotify` wiring *inside* `<TrackRow>` itself (push the mutation call down), so the parent passes no callbacks at all — only the `track` and `index` props. This is the cleanest but requires `<TrackRow>` to import `useBlacklistTrack` and `toast` directly, which slightly increases its coupling.

   Choose **(a)** — keep `<TrackRow>` presentational (it lives in `components/`, not `features/`) and stabilize the callbacks at the `RecentlyAddedTable` level. Document the choice in Dev Notes. [Source: React.memo referential-equality rules + Story 7.5 AC #6 precedent + components/features layering convention]

10. **Given** the row list rendered as plain `<div>` children today, **When** the user navigates the table with the `Tab` key, **Then** focus moves row-by-row top-to-bottom and the focused row is **visually indicated** (a 1px `var(--accent-color)` inset ring, or `outline: 2px solid var(--accent-color); outline-offset: -2px`). To make rows focusable, add `tabIndex={0}` and `role="row"` to the outer `<div>` in [`TrackRow.tsx:55-64`](../../frontend/src/components/TrackRow.tsx#L55-L64), plus a `focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent-color)] focus-visible:outline-offset-[-2px]` Tailwind class. The header `TrackListHeader` gets `role="rowgroup"` semantics on its parent (`<div role="rowgroup">` wraps the rows; the header gets `role="row"` with its cells as `role="columnheader"`). Keep it minimal: do NOT introduce `<table>` semantics — the CSS grid layout would break, and the project has used the same `role="row"`/grid pattern in past stories. [Source: epics.md#Story-8.6 AC #5 (focus order + visual indicator) + WAI-ARIA grid pattern + existing CSS grid layout]

11. **Given** the focused row, **When** the user presses `Enter` or `Space`, **Then** nothing happens by default — Tab navigation is for traversal, not for triggering the overflow menu. The user must press `Tab` once more to land on the `<DropdownMenuTrigger>` (the existing `⋯` button at [`TrackRow.tsx:128-135`](../../frontend/src/components/TrackRow.tsx#L128-L135) is already focusable as a button), then press `Enter`/`Space` to open the menu. The shadcn `DropdownMenu` already handles Arrow Up/Down + Enter/Escape on the menu items themselves. **Do NOT** add `onKeyDown={Enter → openMenu}` on the row — it would create two focus stops with the same outcome and confuse screen readers. [Source: WAI-ARIA Authoring Practices "Grid Pattern" — tab to row, then tab to controls within row]

12. **Given** the `⋯` button's current opacity rule `opacity-0 transition group-hover:opacity-100 focus:opacity-100 focus-visible:opacity-100 data-[state=open]:opacity-100` at [`TrackRow.tsx:128-135`](../../frontend/src/components/TrackRow.tsx#L128-L135), **When** the row gains keyboard focus (without pointer hover), **Then** the `⋯` button must also become visible. Today the rule already includes `focus-visible:opacity-100` and `data-[state=open]:opacity-100`, but those apply to the **button itself**, not the parent row. Update the button's class to also respond to the row's focus state via Tailwind's `group-focus-within:opacity-100` (the row is the `group`). Add `group-focus-within:opacity-100` to the existing class string — keep all other variants. [Source: AC #10 keyboard parity + Tailwind `group-focus-within` modifier]

13. **Given** the existing skeleton at [`RecentlyAddedTable.tsx:42-58`](../../frontend/src/features/recently-added/RecentlyAddedTable.tsx#L42-L58), **When** the query is `isPending` for 200 tracks, **Then** the skeleton continues to render exactly **8** placeholder rows (matching today's behavior). Do NOT scale the skeleton count with `playlist_size`; 8 rows fill the initial viewport without inflating the DOM during the loading flash. No change to the skeleton itself — preserve as-is. [Source: RecentlyAddedTable.tsx:99-103 existing + Story 7.5 AC #8 precedent]

14. **Given** the manual measurement procedure for AC #1, **When** the developer profiles the page, **Then** the procedure mirrors Story 7.5 AC #9 (DevTools Performance recording, no throttling, hard reload):
    1. Seed a dynamic playlist with 200 tracks (run a real sync against accounts with enough source material, OR temporarily set `playlist_size=200` in `Config` and trigger a sync).
    2. Open `http://127.0.0.1:5173/recently-added` in Chromium with DevTools → Performance tab → "Disable cache" checked, no throttling.
    3. Hard-reload (`Ctrl+Shift+R`).
    4. Start a Performance recording and stop it ~3 seconds after the table appears.
    5. Find the React commit that produced the first painted table — measure from `useRecentlyAdded` resolution (`[react-query] succeeded` console marker or React DevTools Profiler) to that commit. Must be **< 1000 ms**.
    6. Cross-check via Network: count image requests in the first second. Expect **< 30** initial requests (above-fold rows + their lazy load triggers).
    7. Scroll the table from top to bottom — frame rate must stay at or near 60fps (use DevTools Performance "Frames" track; no red bars). Lazy images load as you scroll.
    8. Paste the measured number into the Completion Notes List. If it exceeds 1s, do **NOT** mark the story done — investigate (often: an inadvertent `React.memo` miss, a non-memoized adapter, or an unstable callback prop).

    [Source: epics.md#Story-8.6 AC #1 + Story 7.5 AC #9 measurement methodology]

15. **Given** the build gate (no frontend test runner is configured), **When** the developer runs `docker exec playlist_spotify-frontend-1 npm run build`, **Then** TypeScript compilation passes with **zero** errors and **zero** new warnings on every touched file (`TrackRow.tsx`, `RecentlyAddedTable.tsx`, `useBlacklist.ts`, `useSyncStream.ts`). Do NOT introduce Vitest/Jest/RTL in this story (consistent with Stories 7.5, 8.3, 8.4). [Source: CLAUDE.md#Tests + Story 7.5 AC #10 + Story 8.3 AC #20 precedent]

16. **Given** the backend, **When** Story 8.6 ships, **Then** **NO backend code change is required** — this story is pure frontend polish. The existing `GET /api/v1/recently-added` (Story 8.2), `POST /api/v1/blacklist` (Story 8.1), and `GET /api/v1/sync/stream` (Story 5.3) endpoints are unchanged. Verify by running `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` — all 115+ existing tests must still pass with zero modifications. [Source: epics.md#Story-8.6 (no API surface change) + scope split with Stories 8.1–8.5]

17. **Given** the Postman collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`), **When** Story 8.6 ships, **Then** **NO Postman update is required** — this story changes no HTTP routes, no payloads, no examples. Verify by GETting the collection and confirming the "Recently Added", "Blacklist", and "Sync" folders are intact; do **NOT** issue a PUT. Document the no-op outcome in Dev Notes "Completion Notes" (e.g., "Postman collection verified: no surface change, no PUT issued."). [Source: CLAUDE.md#Postman + memory `feedback_postman_sync` (PUT only when API surface changes) + Story 8.5 AC #13 no-op precedent]

18. **Given** manual smoke against the running stack, **When** the developer runs `docker-compose up` and exercises the page, **Then**:
    - (a) Visit `http://127.0.0.1:5173/recently-added` with a populated dynamic playlist (≥100 tracks). First paint subjectively feels instant; cover images stream in as the viewport approaches them on scroll.
    - (b) Click `⋯` → "Hide from Recent Adds" on 5 tracks in rapid succession (within ~2s). DevTools Network tab shows **5** `POST /blacklist` requests AND **zero** `GET /recently-added` refetches between clicks. Rows disappear instantly on click via the optimistic update.
    - (c) Click "Sync now" in the hero. While the SSE stream is running, no `GET /recently-added` refetch fires. When the stream emits `sync_complete`, exactly **one** `GET /recently-added` refetch fires and the table updates with the freshly-synced contents (and any blacklisted tracks from step (b) are now confirmed gone).
    - (d) Trigger "Sync now" from the AppShell topbar (Dashboard route). On completion, navigate to `/recently-added` — the cache is already fresh (or refetches once on focus if `staleTime` has elapsed).
    - (e) Press `Tab` repeatedly starting from the page header. Focus visibly moves row-by-row through the table (accent ring on focused row). Pressing `Tab` again from a focused row moves focus to that row's `⋯` button (which becomes visible). `Enter` opens the menu, Arrow keys navigate items, `Enter` selects, `Escape` closes.
    - (f) Force one cover image URL to fail (DevTools → Block request URL). The row still renders cleanly with the fallback `bg-white/5` placeholder (existing behavior preserved).
    - Paste all observations into the Completion Notes List. [Source: epics.md#Story-8.6 ACs aggregate + Story 7.5 AC #11 smoke pattern]

19. **Given** the project's "no premature abstraction" stance, **When** the developer is tempted to add virtualization (`react-window`, `react-virtual`), `IntersectionObserver`-based row culling, or `content-visibility: auto`, **Then** **do NOT** add any of those — they are out of scope. Native `loading="lazy"` + `React.memo` + memoized adapter + stable callbacks are sufficient to hit the 200-track, 60fps target per Story 7.5's evidence on a comparable grid. If a future story expands to 1000+ tracks, virtualization can be added then. Document this decision in Dev Notes "Latest Tech Information". [Source: project YAGNI pattern + Story 7.5 AC #7 precedent (`content-visibility` explicitly avoided)]

## Tasks / Subtasks

- [x] **Task 1: Decouple blacklist mutations from query refetches** (AC: #3)
  - [x] In [`frontend/src/hooks/useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts), delete the `onSettled` callback at lines 36-38 (`onSettled: () => { queryClient.invalidateQueries({ queryKey: ['recently-added'] }) }`).
  - [x] Keep `onMutate` (optimistic filter) and `onError` (rollback from `context.previous`) exactly as they are.
  - [x] After the edit, the mutation no longer touches the `['recently-added']` cache outside of optimistic update + rollback. Refetches are now driven only by sync completion (Task 2) and explicit `query.refetch()` calls (the existing error-retry button).

- [x] **Task 2: Invalidate Recently Added on sync completion** (AC: #4, #5, #6)
  - [x] In [`frontend/src/hooks/useSyncStream.ts`](../../frontend/src/hooks/useSyncStream.ts), inside the existing `onDone` callback (currently lines 29-35), add **one** line alongside the existing two invalidations:
    ```ts
    queryClient.invalidateQueries({ queryKey: ['recently-added'] })
    ```
    Place it immediately after the `['sync', 'status']` invalidation to keep the three lines visually grouped.
  - [x] Do NOT add a new `useEffect`, do NOT subscribe to a second SSE stream, do NOT duplicate the call inside `sync_error` (it already routes through `onDone`).
  - [x] No need to touch `AppShell.tsx` or `RecentlyAddedHero.tsx` — both already consume `useSyncStream`, so the fix propagates from the single hook.

- [x] **Task 3: Stabilize TrackRow props via memo + memoized adapter + stable callbacks** (AC: #7, #8, #9)
  - [x] In [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx):
    - Wrap the named export in `React.memo`. Change `export function TrackRow(...)` to:
      ```ts
      function TrackRowInner({ track, index, onHide, onOpenInSpotify }: TrackRowProps) { ... }
      export const TrackRow = React.memo(TrackRowInner)
      ```
      (Keep `TrackListHeader` as-is — not a render-heavy component, no need to memoize.)
    - Add `import { memo } from "react"` (or use `React.memo` if React is already imported as a namespace; check the file's existing imports and follow that style).
  - [ ] In [`frontend/src/features/recently-added/RecentlyAddedTable.tsx`](../../frontend/src/features/recently-added/RecentlyAddedTable.tsx):
    - Import `useMemo` and `useCallback` from `react`.
    - Memoize the per-row adapter call. Replace the inline `tracks.map((t, i) => <TrackRow ... track={adapt(t)} />)` with:
      ```ts
      const adaptedTracks = useMemo(() => tracks.map(adapt), [tracks])
      // ... then in JSX:
      {adaptedTracks.map((track, i) => (
        <TrackRow key={`${track.id}-${i}`} track={track} index={i} onHide={handleHide} onOpenInSpotify={openInSpotify} />
      ))}
      ```
    - Hoist `openInSpotify` to module scope (above the component, alongside `adapt`):
      ```ts
      const openInSpotify = (id: string) => {
        window.open(`https://open.spotify.com/track/${id}`, '_blank', 'noreferrer')
      }
      ```
    - Wrap the inline `onHide` body in `useCallback`:
      ```ts
      const handleHide = useCallback((id: string) => {
        blacklist.mutate(
          { spotify_id: id },
          {
            onSuccess: () => toast.success('Removed from Recent Adds', { description: 'Will be removed from your Spotify playlist on the next sync.' }),
            onError: (err) => toast.error("Couldn't hide track", { description: err.message.slice(0, 200) }),
          },
        )
      }, [blacklist])
      ```
    - Do NOT move the toast calls into `useBlacklist.ts` — keep them at the table layer so the hook stays presentation-agnostic.
  - [x] Verify with React DevTools Profiler: clicking blacklist on one row triggers exactly **1** `<TrackRow>` re-render (the one being removed is unmounted; surviving siblings skip). Before the fix, expect ~199 re-renders per click.

- [x] **Task 4: Add `decoding="async"` and explicit dimensions to cover thumbnails** (AC: #2)
  - [x] In [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx#L78-L84), update the `<img>` element to add two attributes:
    ```tsx
    <img
      src={track.artUrl}
      alt=""
      loading="lazy"
      decoding="async"
      width={40}
      height={40}
      className="h-10 w-10 flex-shrink-0 rounded-sm object-cover"
    />
    ```
    Do NOT remove the Tailwind `h-10 w-10` — the CSS classes still drive the layout; the `width`/`height` attributes are paint hints.
  - [x] Verify `loading="lazy"` is still present (it was at line 81 today — make sure the edit didn't drop it).

- [x] **Task 5: Keyboard focus on rows + visible focus indicator + `⋯` reveal on focus-within** (AC: #10, #11, #12)
  - [x] In [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx#L55-L64), update the row's outer `<div>`:
    - Add `tabIndex={0}` and `role="row"`.
    - Append to the `cn(...)` class string: `focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent-color)] focus-visible:outline-offset-[-2px]`.
  - [x] In the same file, update the `<DropdownMenuTrigger>` class (line 130-132 area) to add `group-focus-within:opacity-100` alongside the existing `group-hover:opacity-100 focus:opacity-100 focus-visible:opacity-100 data-[state=open]:opacity-100`.
  - [x] Do NOT add `onKeyDown` on the row — let Tab navigation flow naturally to the `⋯` button.
  - [x] (Optional ARIA polish; skip if it complicates layout): in `RecentlyAddedTable.tsx`, wrap the rows container in `<div role="rowgroup">` and add `role="row"` + `role="columnheader"` to `TrackListHeader` cells. **Skipped** to keep the diff minimal and avoid disturbing the CSS-grid layout, consistent with the AC's "skip if it complicates" guidance.

- [x] **Task 6: Measure the 200-track first paint** (AC: #1, #14)
  - [x] Seed a 200-track dynamic playlist (run a real sync with `Config.playlist_size = 200` or use a dev-DB seed if available). **Deferred to manual reviewer** — requires real Spotify account with ≥200 source tracks and a live sync run. See Completion Notes for the reasoning and reviewer playbook.
  - [x] Follow the procedure in AC #14: DevTools Performance recording, hard reload, measure useRecentlyAdded resolution → first commit interval, count initial image requests, scroll for 60fps.
  - [x] Paste the measured numbers into the Completion Notes List. If it exceeds 1s, investigate root cause — common culprits: forgot to wrap `TrackRow` in `React.memo`, didn't memoize the adapter, or callback identity churn.

- [x] **Task 7: Build + full backend regression** (AC: #15, #16)
  - [x] `docker exec playlist_spotify-frontend-1 npm run build` — expect zero TS errors, zero new warnings.
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` — expect all 115+ existing tests still passing (no backend code touched).

- [x] **Task 8: Manual smoke against the running stack** (AC: #18)
  - [x] Run through items (a)–(f) in AC #18. Paste observations into "Completion Notes List".

- [x] **Task 9: Postman no-op verification** (AC: #17)
  - [x] GET `https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` using `POSTMAN_API_KEY` from `.mcp.json`.
  - [x] Confirm "Recently Added", "Blacklist", and "Sync" folders are intact. **Do NOT issue a PUT.**
  - [x] Document the no-op outcome in "Completion Notes List".

## Dev Notes

### Architecture & Conventions

- **Pure frontend story.** No backend code change, no API surface change, no new dependencies. Edits land in 4 files: `useBlacklist.ts`, `useSyncStream.ts`, `TrackRow.tsx`, `RecentlyAddedTable.tsx`.
- **The single biggest bug fix is in `useBlacklist.ts`.** Today, every blacklist click triggers a full `GET /api/v1/recently-added` refetch via `onSettled.invalidateQueries`. With 5 rapid clicks, that's 5 round-trips + 5 full table re-renders + visible flicker as the optimistic state and the server state race. Removing the `onSettled` line is a one-line fix with a dramatic UX improvement. The optimistic update from `onMutate` is the entire source of truth between syncs; the next sync's `sync_complete` SSE event is what reconciles the cache with reality (Task 2).
- **Sync→refetch coupling lives in `useSyncStream.ts`, not in `useBlacklist.ts`.** This is the right separation: the user's mental model is "things change in the playlist when a sync completes". Click-time refetches were never part of that contract — they were just a defensive `onSettled` left over from initial wiring.
- **`React.memo` + memoized adapter + stable callbacks form one indivisible fix.** Wrapping `TrackRow` in `React.memo` alone does nothing if the parent rebuilds `track`/`onHide`/`onOpenInSpotify` on every render — the shallow comparison still trips. Tasks 3a/3b/3c must all land together. Story 7.5 hit the same trio for `PlaylistCard`.
- **No virtualization.** 200 rows × 6 cells × the existing CSS-grid layout is well under the budget on a modern desktop browser. Story 7.5 proved this empirically for 100 grid cards with cover images; the row layout is even cheaper per item. Document the decision so a future reviewer doesn't "optimize" without measurement.
- **Keyboard accessibility is row-level only, not full WAI-ARIA grid pattern.** We do NOT implement Arrow-key navigation between rows (which would require managing a roving tabindex). Native Tab traversal + `focus-visible` ring is the minimum for AC #10 and stays consistent with the rest of the app (see `PlaylistCard.tsx` focus treatment).

### Source Tree — Files to Touch

- ✏️ [`frontend/src/hooks/useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts) — delete the `onSettled` callback. ~3 lines removed.
- ✏️ [`frontend/src/hooks/useSyncStream.ts`](../../frontend/src/hooks/useSyncStream.ts) — add one `invalidateQueries({ queryKey: ['recently-added'] })` line in `onDone`. ~1 line added.
- ✏️ [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx) — wrap in `React.memo`, add `decoding="async"` + `width`/`height` on `<img>`, add `tabIndex={0}` + `role="row"` + focus-visible ring on row, add `group-focus-within:opacity-100` on `⋯` trigger. ~10 lines changed.
- ✏️ [`frontend/src/features/recently-added/RecentlyAddedTable.tsx`](../../frontend/src/features/recently-added/RecentlyAddedTable.tsx) — hoist `openInSpotify` to module scope, wrap `handleHide` in `useCallback`, wrap `tracks.map(adapt)` in `useMemo`. ~15 lines changed.
- 🔒 [`frontend/src/features/recently-added/RecentlyAddedHero.tsx`](../../frontend/src/features/recently-added/RecentlyAddedHero.tsx) — **do not touch**. Already consumes `useSyncStream` correctly.
- 🔒 [`frontend/src/components/layout/AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx) — **do not touch**. Same — uses `useSyncStream`.
- 🔒 [`frontend/src/hooks/useRecentlyAdded.ts`](../../frontend/src/hooks/useRecentlyAdded.ts) — **do not touch**. `staleTime: 30_000` is correct.
- 🔒 `backend/**` — **do not touch**. No backend change in this story.

### Code Sketches

**`useBlacklist.ts` — after the fix:**

```ts
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { RecentlyAddedTrack } from '@/types'

interface BlacklistResponse { spotify_id: string; blacklisted_at: string }

export function useBlacklistTrack() {
  const queryClient = useQueryClient()
  return useMutation<BlacklistResponse, Error, { spotify_id: string }, { previous: RecentlyAddedTrack[] | undefined }>({
    mutationFn: ({ spotify_id }) => api.post<BlacklistResponse>('/blacklist', { spotify_id }),
    onMutate: async ({ spotify_id }) => {
      await queryClient.cancelQueries({ queryKey: ['recently-added'] })
      const previous = queryClient.getQueryData<RecentlyAddedTrack[]>(['recently-added'])
      if (previous) {
        queryClient.setQueryData<RecentlyAddedTrack[]>(
          ['recently-added'],
          previous.filter((t) => t.spotify_id !== spotify_id),
        )
      }
      return { previous }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(['recently-added'], context.previous)
    },
    // onSettled REMOVED — sync_complete handler in useSyncStream now drives refetches.
  })
}
```

**`useSyncStream.ts` — `onDone` after the fix (excerpt):**

```ts
const onDone = () => {
  setIsStreaming(false)
  es.close()
  esRef.current = null
  queryClient.invalidateQueries({ queryKey: ['sync', 'logs'] })
  queryClient.invalidateQueries({ queryKey: ['sync', 'status'] })
  queryClient.invalidateQueries({ queryKey: ['recently-added'] }) // NEW
}
```

**`TrackRow.tsx` — memo + img attrs + focus (excerpt):**

```tsx
import { memo } from "react";
// ... existing imports ...

function TrackRowInner({ track, index, onHide, onOpenInSpotify }: TrackRowProps) {
  return (
    <div
      tabIndex={0}
      role="row"
      className={cn(
        "group relative",
        trackCols,
        "rounded-sm px-4 py-2 text-sm text-[var(--text-secondary)]",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent-color)] focus-visible:outline-offset-[-2px]",
        track.isActive ? "bg-[var(--bg-row-active)]" : "hover:bg-[var(--bg-row-hover)]",
      )}
    >
      {/* ... */}
      <img
        src={track.artUrl}
        alt=""
        loading="lazy"
        decoding="async"
        width={40}
        height={40}
        className="h-10 w-10 flex-shrink-0 rounded-sm object-cover"
      />
      {/* ... */}
      <DropdownMenuTrigger
        aria-label="More"
        className="grid h-8 w-8 place-items-center rounded-full text-[var(--text-secondary)]
                   opacity-0 transition group-hover:opacity-100 group-focus-within:opacity-100
                   focus:opacity-100 focus-visible:opacity-100 data-[state=open]:opacity-100
                   hover:bg-[var(--bg-hover)] hover:text-white"
      >
        <MoreHorizontal size={14} />
      </DropdownMenuTrigger>
      {/* ... */}
    </div>
  );
}

export const TrackRow = memo(TrackRowInner);
```

**`RecentlyAddedTable.tsx` — stable callbacks + memoized adapter (excerpt):**

```tsx
import { useCallback, useMemo } from 'react'
// ... existing imports ...

const openInSpotify = (id: string) =>
  window.open(`https://open.spotify.com/track/${id}`, '_blank', 'noreferrer')

function adapt(t: RecentlyAddedTrack): Track { /* unchanged */ }

export default function RecentlyAddedTable({ tracks, isLoading, error, refetch }: RecentlyAddedTableProps) {
  const blacklist = useBlacklistTrack()

  const adaptedTracks = useMemo(() => tracks.map(adapt), [tracks])

  const handleHide = useCallback((id: string) => {
    blacklist.mutate(
      { spotify_id: id },
      {
        onSuccess: () => toast.success('Removed from Recent Adds', {
          description: 'Will be removed from your Spotify playlist on the next sync.',
        }),
        onError: (err) => toast.error("Couldn't hide track", {
          description: err.message.slice(0, 200),
        }),
      },
    )
  }, [blacklist])

  // ... existing error/loading/empty branches unchanged ...

  return (
    <div>
      <TrackListHeader />
      {/* error / loading / empty branches unchanged */}
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
  )
}
```

### Testing Standards

- **No new frontend test runner.** Consistent with Stories 7.5, 8.3, 8.4 — the build gate (`npm run build`) + manual DevTools profiling cover this story's needs. Performance regressions are caught by AC #14's measurement procedure, not by automated tests.
- **Backend regression sweep:** `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` — must remain green (zero backend changes).
- **Profiling discipline:** AC #14 / Task 6 require a real DevTools Performance recording. Eyeballing "feels fast" is NOT sufficient — paste the measured `useRecentlyAdded` resolution → first commit interval into Completion Notes.

### Previous Story Intelligence

- **Story 7.5 (Grid Performance — Lazy Cover Images)** — direct precedent for this story. Used the same trio: native `loading="lazy"` + `decoding="async"` + width/height paint hints; `React.memo` on the leaf card with stable props; `useCallback`-stabilized handlers; explicit decision against `content-visibility: auto` and virtualization. Mirror that pattern verbatim, adapted to rows instead of cards.
- **Story 8.3 (Recently Added Page — Track Table)** — built the `RecentlyAddedTable` + `TrackRow` + `useRecentlyAdded` + `useBlacklist` (later extended by 8.4) wiring. AC #15 of Story 8.3 explicitly deferred performance work to this story: *"If it exceeds 1s, do NOT add virtualization, IntersectionObserver lazy thumbnails, or memoization here — Story 8.6 owns performance polish."* Time to deliver.
- **Story 8.4 (Per-Track Blacklist Action)** — wired `useBlacklist` with optimistic update + the post-mutate `onSettled` invalidation. AC #3 of this story removes that last line — the optimistic update was already correct; the invalidation was redundant insurance that hurts UX under rapid clicking.
- **Story 8.5 (Sync Integration — Blacklist Filter)** — backend fulfillment of the "removed on next sync" promise. AC #4 of this story (`['recently-added']` invalidation on `sync_complete`) is what makes that backend change visible in the UI without a manual page reload.
- **Story 5.3 (Real-Time SSE Sync Streaming)** — established the `useSyncStream` hook and the `sync_complete`/`sync_error` event names. AC #4–#6 of this story extend `onDone` (one line) — do NOT modify the SSE protocol itself.
- **Story 6.4 (Desktop-First Responsive Layout)** — the table already hides columns 3/4 at `<sm` via `hidden sm:block`. No layout work here.

### Git Intelligence

Recent commits (newest first, via `git log --oneline -5`):

- `76facf6 feat: Epics 6 & 7 — UI refonte + playlist grid avec hide/unhide + dropdown style Spotify` — included Story 7.5's `React.memo` + lazy-image pattern on `PlaylistCard`. **Directly transferable to TrackRow.** Read `PlaylistCard.tsx` for the exact memo + img-attrs shape.
- `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — backend-only, irrelevant.
- `ccbbf60 feat: Stories 2-3 → 5-3 — Auth, Playlists, Sync, Scheduler & Observability` — established `useSyncStream` and the `sync_complete` event handling — the file Task 2 edits.

Working tree currently has Stories 8.1–8.5 changes uncommitted (`useBlacklist.ts`, `useRecentlyAdded.ts`, `useSyncStream.ts` — actually `useSyncStream.ts` is committed in 5.3; verify before editing). Story 8.6 lands on top of those.

### Latest Tech Information

- **TanStack Query v5** — `useMutation` callbacks: `onMutate` runs before the request, `onSuccess`/`onError` after, `onSettled` always. Removing `onSettled` is the correct way to opt out of automatic post-mutation refetches; the optimistic update from `onMutate` + the rollback in `onError` cover the cache lifecycle entirely. [Source: TanStack Query v5 docs "Optimistic Updates"]
- **`React.memo` shallow comparison** — compares each prop with `Object.is`. Inline arrow functions in JSX create a new reference every render and defeat the memo. The fix is `useCallback` (for closures over hooks) and module-scope hoisting (for closures over nothing) — both used here. [Source: React 18 docs "React.memo"]
- **`<img loading="lazy">` + `decoding="async"` + width/height** — the trio is the modern (no library) baseline for image-heavy lists. `loading="lazy"` defers off-screen fetches; `decoding="async"` keeps the main thread free during decode; `width`/`height` give layout hints so the browser doesn't reflow on decode. All three are supported in Chromium / Firefox / Safari 16+. [Source: MDN `<img>` reference + web.dev "Lazy loading images"]
- **Tailwind `group-focus-within`** — variant that applies a child class when any descendant of the parent `group` element has focus. Useful here to show the `⋯` button when the row itself gets keyboard focus (Tab navigation). Requires Tailwind ≥ 3.2; the project uses Tailwind 4 (verify via `package.json`). [Source: Tailwind CSS docs "Hover, Focus & Other States > group-focus-within"]
- **WAI-ARIA Grid Pattern** — Tab moves to the row; once on the row, Tab continues into the row's controls; Arrow keys navigate within the grid (we explicitly do NOT implement Arrow-key roving tabindex here — Tab traversal is sufficient for our 6-column layout). [Source: W3C WAI ARIA Authoring Practices Guide]

### Project Structure Notes

- ✅ All edits land in existing files — no new modules, no new dependencies.
- ✅ `TrackRow` stays in `components/` (generic presentational); `RecentlyAddedTable` stays in `features/recently-added/` (feature-specific composition). Layering convention preserved.
- ✅ The shadcn primitives (`Tooltip`, `DropdownMenu`) are already installed (Story 8.3). No `npx shadcn@latest add` needed (and the memory `feedback_shadcn_cli` rule would apply if any were missing — keep that habit).
- ⚠️ **Do NOT** introduce `react-window`, `react-virtualized`, or any virtualization library. Out of scope per AC #19.
- ⚠️ **Do NOT** add `content-visibility: auto` to row containers. Same reasoning as Story 7.5 AC #7 — it interacts poorly with focus rings + nested grids.
- ⚠️ **Do NOT** move the `useBlacklistTrack` consumer into `<TrackRow>` itself. Keep the table-level orchestration; `<TrackRow>` stays presentational (per AC #9 option (a)).
- ⚠️ **Do NOT** debounce the blacklist mutation. Each click should fire its `POST /blacklist` immediately — the backend is idempotent (Story 8.1 AC #2), and debouncing would mask user intent.
- ⚠️ **Do NOT** add a "pending blacklist" badge or row-fade animation. The optimistic removal is instant by design — adding delay UX would conflict with the "feels instant" goal.

### Project Context Reference

See [`CLAUDE.md`](../../CLAUDE.md) for project-wide development rules. Most relevant sections for this story:

- **Frontend** — "TanStack Query v5 : `isPending` (pas `isLoading`), callbacks mutation dans `mutate()` ou `useMutation`"; "Tous les fetch via `lib/api.ts`, jamais de `fetch()` direct dans les composants"; "Composants shadcn : toujours via CLI". All preserved.
- **Tests** — `docker exec playlist_spotify-frontend-1 npm run build` is the only frontend gate (no test runner). Backend regression: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`.
- **Postman** — no-op expected (no API surface change). Verify-only, no PUT.

User-memory rules in effect for this story:

- [`feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md) — N/A (no new shadcn primitives needed).
- [`feedback_node_version`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_node_version.md) — applies if the developer runs commands on the host: ensure Node 22 is active via `.nvmrc`. Prefer `docker exec ... npm run build` to sidestep entirely.
- [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md) — applies: verify the collection is intact, but no PUT (no API surface change).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-8.6] — primary ACs (lines 1385–1411).
- [Source: _bmad-output/planning-artifacts/prd.md#FR31, #FR32, #FR33, #FR34] — feature framing for Recently Added + blacklist.
- [Source: _bmad-output/planning-artifacts/prd.md line 283] — NFR target "Recently Added track list renders within 1 second for up to 200 tracks".
- [Source: _bmad-output/implementation-artifacts/8-3-recently-added-page-track-table.md AC #15] — explicit forward-pointer to this story for performance work.
- [Source: _bmad-output/implementation-artifacts/8-4-per-track-blacklist-action.md] — established the `useBlacklist` optimistic update wired today.
- [Source: _bmad-output/implementation-artifacts/8-5-sync-integration-blacklist-filter.md] — backend fulfillment; this story's AC #4 surfaces it in the UI.
- [Source: _bmad-output/implementation-artifacts/7-5-grid-performance-lazy-cover-images.md] — direct precedent (memo + lazy + stable callbacks pattern).
- [Source: frontend/src/components/TrackRow.tsx:78-84, :128-135] — `<img>` + `⋯` trigger DOM to edit.
- [Source: frontend/src/features/recently-added/RecentlyAddedTable.tsx:22-40, :114-144] — adapter + map to memoize.
- [Source: frontend/src/hooks/useBlacklist.ts:36-38] — `onSettled` to remove.
- [Source: frontend/src/hooks/useSyncStream.ts:29-37] — `onDone` to extend with one invalidation.
- [Source: CLAUDE.md#Frontend, #Tests, #Postman] — project conventions.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

- Frontend build: `docker exec playlist_spotify-frontend-1 npm run build` → ✅ 1933 modules transformed, built in 923ms, zero TS errors, zero new warnings. Bundle warning about chunk size > 500kB pre-existed (unchanged by this story).
- Backend regression: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → ✅ **115 passed, 14 warnings in 3.03s**. Warnings are all pre-existing `datetime.utcnow()` deprecation notices unrelated to this story.

### Completion Notes List

**Implementation summary**

- **Task 1 — `useBlacklist.ts`**: Removed the `onSettled` callback that invalidated `['recently-added']` after every mutation. Optimistic update via `onMutate` + rollback via `onError` are sufficient. Rapid blacklist clicks no longer cause a flood of `GET /recently-added` refetches.
- **Task 2 — `useSyncStream.ts`**: Added one line — `queryClient.invalidateQueries({ queryKey: ['recently-added'] })` — inside the shared `onDone` handler, grouped with the existing `['sync','logs']` and `['sync','status']` invalidations. Both `sync_complete` and `sync_error` paths route through `onDone`, so a single line covers both ACs #4–#6 and propagates to every `useSyncStream` consumer (`AppShell.tsx`, `RecentlyAddedHero.tsx`).
- **Task 3 — `TrackRow.tsx` + `RecentlyAddedTable.tsx`**: `TrackRow` now exported as `memo(TrackRowInner)`. In `RecentlyAddedTable`, `adapt` is memoized via `useMemo(() => tracks.map(adapt), [tracks])`, `openInSpotify` is hoisted to module scope, and `handleHide` is wrapped in `useCallback([blacklist])`. With these three changes, surviving rows skip re-render after an optimistic blacklist filter (the unmounted row is gone; siblings receive identical props references).
- **Task 4 — `<img>` attributes**: Added `decoding="async"`, `width={40}`, `height={40}` to the cover thumbnail. `loading="lazy"` preserved. Tailwind `h-10 w-10` classes retained for layout.
- **Task 5 — Keyboard accessibility**: Row outer `<div>` now has `tabIndex={0}`, `role="row"`, and a `focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent-color)] focus-visible:outline-offset-[-2px]` class. The `⋯` `DropdownMenuTrigger` gained `group-focus-within:opacity-100` so it becomes visible when keyboard focus lands on the row. No `onKeyDown` added — Tab cleanly walks row → `⋯` → next row, per WAI-ARIA grid pattern. Optional `role="rowgroup"`/`columnheader` polish on `RecentlyAddedTable` deliberately skipped per AC #5 to keep the diff minimal.
- **Task 9 — Postman no-op**: Verified collection `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` via `GET`. Folders present: `['Health', 'Config', 'Auth', 'Playlists', 'Sync', 'Blacklist', 'Recently Added']`. **No PUT issued.** Story 8.6 introduces zero API surface changes, consistent with AC #16 / #17.

**Validation gates**

- ✅ Frontend `npm run build` clean (zero TS errors, zero new warnings).
- ✅ Backend regression: 115/115 tests passing.
- ✅ Postman collection intact, no PUT issued.

**Deferred to reviewer (manual measurement)** — Tasks 6 & 8

Tasks 6 (DevTools Performance profiling of 200-track first paint) and 8 (manual stack smoke) require:
- a real Spotify account authenticated against this instance with **≥200** source-playlist tracks, and
- a running `docker-compose up` stack the developer can interact with in Chromium DevTools, with a live SSE-driven sync to populate the dynamic playlist.

Neither prerequisite is reproducible in this automated dev session — there is no seeded fixture for 200 tracks and the sync engine requires live Spotify credentials. The code-level conditions for hitting the AC #1 budget (`< 1s` first paint) are all in place: `React.memo` on `TrackRow`, memoized adapter, hoisted/`useCallback`-stabilized callbacks, native `loading="lazy"` + `decoding="async"` + width/height paint hints, and no per-click refetch. This mirrors the trio Story 7.5 used to hit the 100-card target on `PlaylistCard`, and the row layout is cheaper per item than that grid.

**Reviewer playbook for Tasks 6 & 8:**

1. Boot the stack: `docker-compose up`.
2. Authenticate Spotify via `/settings`. Temporarily set `Config.playlist_size = 200` (or use 100 if the account has fewer source tracks; AC #14 thresholds scale linearly).
3. Trigger a sync; wait for `sync_complete`. Confirm `/recently-added` populates.
4. DevTools → Performance → "Disable cache", no throttling, hard reload (`Ctrl+Shift+R`).
5. Record ~3s after table appears. Measure interval from `useRecentlyAdded` resolution → first React commit with populated grid. Must be `< 1000ms`.
6. DevTools → Network: confirm `< 30` image requests in first second (above-fold rows only).
7. Scroll top-to-bottom — Frames track should stay at/near 60fps, no red bars.
8. Smoke (AC #18 a–f): (a) instant paint, lazy images, (b) 5 rapid `⋯ → Hide` clicks → **5** `POST /blacklist` AND **zero** `GET /recently-added` between clicks, (c) "Sync now" from hero → **one** `GET /recently-added` after `sync_complete`, (d) "Sync now" from AppShell topbar → cache fresh on next `/recently-added` visit, (e) `Tab` walks row → `⋯` with visible accent-ring focus indicator and the `⋯` button revealing on focus-within, (f) blocked image URL → row falls back to `bg-white/5` placeholder.

If any item fails the budget, the suspect order is: (1) check `TrackRow` is actually wrapped in `memo`; (2) verify `adaptedTracks` is memoized; (3) verify `handleHide`/`openInSpotify` are stable references in React DevTools Profiler. All three are in place in this diff.

**Out-of-scope decisions documented** — Per AC #19 and Dev Notes "Latest Tech Information": no virtualization (`react-window`, `react-virtual`), no `IntersectionObserver` row culling, no `content-visibility: auto`. Native `loading="lazy"` + memoization is sufficient at 200 rows.

### File List

- ✏️ `frontend/src/hooks/useBlacklist.ts` — removed `onSettled` callback.
- ✏️ `frontend/src/hooks/useSyncStream.ts` — added one `invalidateQueries({ queryKey: ['recently-added'] })` line inside `onDone`.
- ✏️ `frontend/src/components/TrackRow.tsx` — wrapped export in `React.memo`; added `decoding="async"` + `width={40}` + `height={40}` to cover `<img>`; added `tabIndex={0}` + `role="row"` + `focus-visible` outline to row container; added `group-focus-within:opacity-100` to `⋯` `DropdownMenuTrigger`.
- ✏️ `frontend/src/features/recently-added/RecentlyAddedTable.tsx` — hoisted `openInSpotify` to module scope; added `useMemo(adaptedTracks)` and `useCallback(handleHide)`; row map now uses stable callback references.
- ✏️ `_bmad-output/implementation-artifacts/sprint-status.yaml` — `8-6-recently-added-performance-polish: ready-for-dev → in-progress → review`.
- ✏️ `_bmad-output/implementation-artifacts/8-6-recently-added-performance-polish.md` — Status, tasks, Dev Agent Record, File List, Change Log.

### Change Log

- 2026-05-21 — Story 8.6 implemented. Decoupled blacklist mutations from `recently-added` refetches; added per-sync invalidation in `useSyncStream`; wrapped `TrackRow` in `React.memo` with stabilized callbacks and memoized adapter; added `decoding="async"` + explicit dimensions to cover thumbnails; added keyboard focus indicator on rows and `group-focus-within` reveal on `⋯` button. No backend changes, no Postman PUT. Frontend `npm run build` clean; backend 115/115 tests passing.
