# Story 9.3: Playlist Detail Page & Navigation

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want clicking a playlist card on the Dashboard to navigate to `/playlists/:spotifyId` and see a hero (cover + name + owner + N tracks + total duration) plus the shared track table listing every track in the playlist,
So that I can drill into any playlist with the same Spotify-desktop visual familiarity as Recently Added, and return with one click via the topbar Back chevron.

## Acceptance Criteria

1. **Given** the React Router config in [`frontend/src/App.tsx`](../../frontend/src/App.tsx), **When** the refactor lands, **Then** a new route `{ path: 'playlists/:spotifyId', element: <PlaylistDetailPage /> }` is added as a child of the `AppShell` route (siblings: `index`, `recently-added`, `settings`, `logs`). The route lives **inside** `AppShell` so the sidebar + topbar persist. The route is added between `recently-added` and `settings` (or any position — order does not matter for routing, but keep imports alphabetical-ish for diff hygiene). [Source: epics.md#Story-9.3 hint #2 + App.tsx:1-22 current router structure]

2. **Given** a new page file [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx), **When** rendered, **Then** the page:
   - Reads `spotifyId` from `useParams<{ spotifyId: string }>()` (`react-router-dom`).
   - Fetches the playlist's tracks via a new `usePlaylistTracks(spotifyId)` hook (AC #3).
   - Fetches the playlist metadata from the already-cached `usePlaylists()` list and finds the matching entry by `spotify_id` (no separate `/playlists/{id}` GET — the list endpoint already provides `name`, `image_url`, `track_count`, `is_included`, `is_hidden`).
   - Renders `<TrackListHero kicker="PLAYLIST" title={playlist.name} subLine={subLine} coverUrl={coverUrl} actions={actions} />` followed by `<TrackListTable tracks={list} isPending={tracks.isPending} error={tracks.error} refetch={tracks.refetch} errorTitle="Couldn't load playlist" emptyTitle="This playlist has no tracks" emptyMessage="There's nothing in this playlist yet." />`.
   - **Does NOT** pass `onBlacklist` in this story — per-track blacklist on Playlist Detail is **Story 9.4**, deliberately out of scope here. The ⋯ row menu's "Hide from Recent Adds" will be a visual no-op for now (consistent with `TrackListTable` AC #8 from 9.2 — when `onBlacklist` is undefined, the row still renders the menu item but it does nothing). [Source: epics.md#Story-9.3 + epics.md#Story-9.4 explicit scope split]

3. **Given** a new hook file [`frontend/src/hooks/usePlaylistTracks.ts`](../../frontend/src/hooks/usePlaylistTracks.ts), **When** inspected, **Then** the hook mirrors [`useRecentlyAdded`](../../frontend/src/hooks/useRecentlyAdded.ts) verbatim except for the URL and the query key:
   ```ts
   import { useQuery } from '@tanstack/react-query'
   import { api } from '@/lib/api'
   import type { RecentlyAddedTrack } from '@/types'

   export function usePlaylistTracks(spotifyId: string | undefined) {
     return useQuery({
       queryKey: ['playlist-tracks', spotifyId],
       queryFn: () => api.get<RecentlyAddedTrack[]>(`/playlists/${spotifyId}/tracks`),
       enabled: !!spotifyId,
       staleTime: 30_000,
     })
   }
   ```
   The hook returns the same `RecentlyAddedTrack[]` shape (Story 9.1 AC #1 guarantees the backend already returns this shape from `/playlists/{id}/tracks`). [Source: epics.md#Story-9.3 hint #3 + 9-1-playlist-tracks-api.md#AC1 + useRecentlyAdded.ts current impl + CLAUDE.md#Frontend "Tous les fetch via `lib/api.ts`"]

4. **Given** the hero's `subLine`, **When** computed in the page, **Then** the displayed text matches the UX spec (`ux-design/README.md` §6):
   ```tsx
   const owner = auth.data?.spotify_user_id ?? 'You'
   const n = tracks.isPending && list.length === 0 ? '…' : list.length
   const duration = tracks.isPending && list.length === 0 ? '…' : formatTotalDuration(list)
   const subLine = (
     <>
       <strong className="text-white">{owner}</strong> • {n} tracks • {duration}
     </>
   )
   ```
   No "updated from K source playlists" tail (this is a real playlist, not the aggregated dynamic playlist). `formatTotalDuration` is lifted verbatim from `RecentlyAddedPage.tsx:16-25` — copy the helper into `PlaylistDetailPage.tsx` (do **NOT** extract to a shared util in this story; YAGNI per project stance — two call sites is acceptable, refactor only if a third lands). [Source: ux-design/README.md §6 "Sub-line: `<strong>{owner}</strong> • {n} tracks • about Xh Ym`" + pages/RecentlyAddedPage.tsx:16-25]

5. **Given** the hero's `coverUrl`, **When** computed in the page, **Then** `coverUrl = playlist?.image_url ?? null`. The fallback gradient is already handled inside `TrackListHero` (per 9.2 AC #3) — no extra null-check needed in the page. Concretely: `liked_songs` returns `image_url: null` from the backend list (verify in `services/spotify.py` — Liked Songs gets an `image_url` from the cover endpoint; if null, gradient fallback applies automatically). [Source: features/tracks/TrackListHero.tsx (9.2 AC #3 gradient fallback) + types/index.ts `Playlist.image_url: string | null`]

6. **Given** the hero's `actions`, **When** rendered in the page, **Then** the actions row is **two items only**:
   - **Primary "Open in Spotify"** — `<a>` (or `<button>` styled identically) opening `https://open.spotify.com/playlist/{spotifyId}` (or `https://open.spotify.com/collection/tracks` when `spotifyId === 'liked_songs'`, mirroring `features/playlists/PlaylistGrid.tsx:18-22`'s helper — extract or duplicate the helper; if duplicated, place it as a small `playlistSpotifyHref(id: string)` function at the top of the page file, NOT in `lib/`).
     - Styling: **same accent primary button** as Recently Added's `Sync now`: `rounded-full bg-[var(--accent-color)] px-5 font-bold text-black hover:bg-[var(--accent-hover)] hover:scale-[1.03] active:scale-[0.98] transition`. Icon: `<ExternalLink size={14} className="mr-2" />`. Label: `Open in Spotify`. Renders as `<a target="_blank" rel="noreferrer">` (NOT a `<Button>` — the project uses bare anchors for external links per `RecentlyAddedPage.tsx:78-87` precedent).
   - **`MoreHorizontal` icon-only button** (36×36, ghost) — same styling as the `MoreHorizontal` button in `RecentlyAddedPage.tsx:101-107`. No `onClick` handler in this story (placeholder for future edit/sort UX per UX §6).
   - **NO "Sync now" button** — the dynamic-playlist sync is global, not per-playlist (UX §6 explicit).
   - **NO "Search input"** — the filter input is **Story 9.5**, deliberately deferred.
   [Source: ux-design/README.md §6 "Hero actions row" + pages/RecentlyAddedPage.tsx:62-108 styling precedent + epics.md#Story-9.5 explicit deferral]

7. **Given** the existing [`frontend/src/features/playlists/PlaylistCard.tsx`](../../frontend/src/features/playlists/PlaylistCard.tsx), **When** the user clicks the card body, **Then** the page navigates to `/playlists/{playlist.spotify_id}` via `useNavigate()`. Implementation requirements:
   - Add `import { useNavigate } from 'react-router-dom'` to `PlaylistCard.tsx`.
   - Add `const navigate = useNavigate()` inside the component.
   - Wrap the card's outermost `<div>` with an `onClick={() => navigate(\`/playlists/${playlist.spotify_id}\`)}` handler — keep the existing `cursor-pointer` class.
   - **CRITICAL — prevent menu-click navigation:** the `DropdownMenuTrigger`, every `DropdownMenuItem`, and the play FAB must call `e.stopPropagation()` on their `onClick` (or `onSelect` for `DropdownMenuItem` if Radix bubbles a synthetic click — verify with a quick smoke). The current trigger is `<DropdownMenuTrigger className="absolute right-2 top-2 …">` — wrap its `onClick`: `onClick={(e) => e.stopPropagation()}`. The play FAB `<button>` at the bottom-right (the green play button) must also `e.stopPropagation()` on click. Same for the cover `<img>` (if click bubbles — generally yes; explicit stopPropagation is **NOT** needed since the cover is part of the card body and SHOULD trigger navigation, but the ⋯ button must NOT).
   - Add `role="link"` and `tabIndex={0}` plus an `onKeyDown` that triggers navigation on `Enter`/`Space` (a11y per the design system pattern; mirrors `PlaylistCard.tsx`'s existing `cursor-pointer` semantic by making the whole card keyboard-focusable). If this complicates the existing focus-management for the dropdown trigger, use a simpler approach: leave keyboard navigation to the dropdown's existing focus + add a comment `// TODO Story 9.5: card-level keyboard navigation` — **decide at impl time**, document in Completion Notes.
   - **Do NOT** wrap the card in a `<Link>` — that would change the markup substantially and break the dropdown's portal layering. Use `navigate()` programmatically.
   [Source: epics.md#Story-9.3 hint #1 + features/playlists/PlaylistCard.tsx:65-156 (current structure) + Radix dropdown stopPropagation gotcha (Radix's DropdownMenuTrigger does NOT auto-stopPropagation by default)]

8. **Given** the topbar Back chevron in [`frontend/src/components/layout/AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx) (line 260-265, currently `<button disabled>`), **When** the user is on **any** route with `history.length > 1`, **Then** the button becomes enabled and clicking it calls `useNavigate()(-1)`. Specifically:
   - Add `import { useNavigate } from 'react-router-dom'` to `AppShell.tsx` (already imports from `react-router-dom` — extend the existing import).
   - Add `const navigate = useNavigate()` inside the component.
   - Add `const canGoBack = typeof window !== 'undefined' && window.history.length > 1` (computed at render — note this is a heuristic; React Router does not expose its internal stack publicly. The DOM `history.length` is conservative but works for the typical case: user lands on Dashboard, clicks playlist → history.length becomes ≥ 2).
   - Replace the disabled Back button's markup with:
     ```tsx
     <button
       type="button"
       disabled={!canGoBack}
       onClick={() => navigate(-1)}
       aria-label="Back"
       className={cn(
         'hidden md:grid h-8 w-8 place-items-center rounded-full bg-black/55 transition',
         canGoBack
           ? 'text-white hover:bg-black/80'
           : 'text-[var(--text-muted)] cursor-not-allowed',
       )}
     >
       <ChevronLeft size={16} />
     </button>
     ```
   - The Forward chevron (line 267-273) stays **disabled** — out of scope; React Router has no public forward-stack API, and the DOM `history.forward()` is unreliable across SPA navigations.
   - [Source: epics.md#Story-9.3 hint #4 "useNavigate(-1) and enable when history.length > 1" + ux-design/README.md §6 "Navigation: Retour: bouton `ChevronLeft` du topbar (devient actif quand `history.length > 1`)" + AppShell.tsx:260-273 current disabled markup]

9. **Given** the user navigates to `/playlists/:spotifyId` for a playlist id that **does not match** any entry in the cached `usePlaylists()` list (stale link, manual URL, deleted playlist), **When** the page renders, **Then**:
   - If `usePlaylists()` is still pending → show the skeleton hero (a simple placeholder: gradient cover + skeleton title — or just fall back to passing `title="…"` and `coverUrl={null}` to `TrackListHero`).
   - If `usePlaylists()` resolved AND no match → render `<TrackListHero kicker="PLAYLIST" title="Playlist not found" subLine={<>This playlist is no longer in your library.</>} coverUrl={null} actions={null} />` (no actions row). The track table is **not rendered** in this branch — but the page still mounts inside AppShell so the sidebar/back chevron work.
   - Do **NOT** call the tracks API when the playlist metadata is missing (set `enabled: !!playlist` on the `usePlaylistTracks` call, OR check `playlist != null` before rendering the table). Actually, simpler: **always call the tracks API** when `spotifyId` is present (it will 404 cleanly per 9.1 AC #3 — error state renders the table's error branch with "Couldn't load playlist"). Choose the simpler path — passing `enabled: !!spotifyId` and letting the backend 404 surface as a table error branch is the cleaner UX. [Source: epics.md#Story-9.3 implicit + 9-1 AC #3 (404 → "Playlist not found")]

10. **Given** the user navigates to `/playlists/liked_songs` (the synthetic Liked Songs playlist), **When** the page renders, **Then**:
    - `usePlaylists()` will return a `liked_songs` entry (verify in `services/spotify.py` — the backend prepends a synthetic Liked Songs playlist; check `get_user_playlists()` for this).
    - The Spotify href in the primary "Open in Spotify" button resolves to `https://open.spotify.com/collection/tracks` (NOT `/playlist/liked_songs`).
    - The tracks API call hits `/playlists/liked_songs/tracks` which routes to `current_user_saved_tracks` (9-1 AC #2 guarantees).
    - The cover may be null → gradient fallback (already handled by `TrackListHero` 9.2 AC #3).
    [Source: 9-1-playlist-tracks-api.md#AC2 + features/playlists/PlaylistGrid.tsx:18-22 (existing `openInSpotify` helper for liked_songs) + services/spotify.py liked_songs synthesis]

11. **Given** the routing change, **When** the dev runs `docker exec playlist_spotify-frontend-1 npm run build`, **Then** the build completes with **zero TypeScript errors** and **zero new ESLint warnings**. Specifically:
    - `useParams<{ spotifyId: string }>()` is typed correctly (TS strict).
    - No `any` introduced.
    - Unused imports removed (e.g. if Forward chevron stays untouched, don't re-import `ChevronRight`; it's already imported).
    - The new hook file's `import type` for `RecentlyAddedTrack` uses type-only import per project convention.
    [Source: CLAUDE.md (clean builds) + tsconfig strict + 9-2 AC #14 precedent]

12. **Given** the running stack via `docker-compose up`, **When** the dev manually smokes the new flow at `http://127.0.0.1:5173/`, **Then** **all** of the following must hold:
    - From Dashboard, clicking a playlist card body navigates to `/playlists/{spotifyId}` and the URL bar updates.
    - Clicking the ⋯ overflow menu on a playlist card does **NOT** navigate (the menu opens; closing it does not trigger navigation).
    - Clicking "Include in sync" / "Hide playlist" / "Open in Spotify" inside the dropdown does **NOT** navigate.
    - Clicking the play FAB does **NOT** navigate (no error if it does nothing — but no nav).
    - On `/playlists/{spotifyId}`, the hero renders with kicker `PLAYLIST`, the playlist name as title, cover image, sub-line `{owner} • {n} tracks • about Xh Ym`, primary `Open in Spotify` accent button, and `MoreHorizontal` icon.
    - The track table renders with the same column layout / sticky header / skeleton loading / row hover behavior as Recently Added.
    - The track row ⋯ menu opens; "Hide from Recent Adds" is a visual no-op (per AC #2 / 9.4 deferral); "Open in Spotify" opens `https://open.spotify.com/track/{id}` in a new tab (default behavior from 9.2 AC #9).
    - Topbar `ChevronLeft` becomes enabled (white) on `/playlists/...`; clicking it returns to Dashboard.
    - On Dashboard (no prior history), `ChevronLeft` is disabled (muted) — verify by hard-refreshing `http://127.0.0.1:5173/`.
    - Navigating to `/playlists/liked_songs` works: tracks load, hero says `PLAYLIST · Titres likés` (or whatever the backend returns for that name — verify), "Open in Spotify" opens `https://open.spotify.com/collection/tracks`.
    - Navigating to `/playlists/nonexistent_id_xyz` displays the table's error branch ("Couldn't load playlist") OR the "Playlist not found" hero (per AC #9 choice) — either is acceptable, document which path the implementation took.

    Paste a one-line confirmation per bullet into the Completion Notes List. [Source: epics.md#Story-9.3 + UX §6 + AC #2-#10]

13. **Given** the backend test suite, **When** the dev runs `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`, **Then** all backend tests still pass (this story is frontend-only; backend regression here means an accidental edit). Note the **current** count is **127** (per 9-2 final), confirm it stays ≥ 127. [Source: CLAUDE.md#Tests + 9-2 baseline]

14. **Given** the Postman collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`), **When** this story ships, **Then** **no Postman update is required**. Story 9.3 is frontend-only with **zero API surface changes** (the `/playlists/{id}/tracks` endpoint was already shipped in 9.1 and Postman was updated then). Explicitly note "Postman: N/A (no API change)" in Completion Notes per memory rule [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md). [Source: memory `feedback_postman_sync` + CLAUDE.md#Postman scope + 9-2 AC #17 precedent]

15. **Given** `git status` after the story lands, **When** inspected, **Then** the change set is **exactly**:
    - ➕ `frontend/src/pages/PlaylistDetailPage.tsx` (new)
    - ➕ `frontend/src/hooks/usePlaylistTracks.ts` (new)
    - ✏️ `frontend/src/App.tsx` (modified — new route)
    - ✏️ `frontend/src/features/playlists/PlaylistCard.tsx` (modified — onClick navigate + stopPropagation on menu trigger / play FAB)
    - ✏️ `frontend/src/components/layout/AppShell.tsx` (modified — Back chevron functional)
    - ✏️ `_bmad-output/implementation-artifacts/sprint-status.yaml` (story status transitions)
    - ✏️ `_bmad-output/implementation-artifacts/9-3-playlist-detail-page-navigation.md` (this file — task checkboxes + Dev Agent Record)

    **No other files touched.** Zero backend changes. Zero edits to `features/tracks/TrackListHero.tsx`, `features/tracks/TrackListTable.tsx`, `components/TrackRow.tsx`, `hooks/useRecentlyAdded.ts`, `hooks/useBlacklist.ts`, `types/index.ts`, `lib/api.ts`, or any other page. Paste `git status` output into Completion Notes. [Source: epics.md#Story-9.3 scope + project anti-scope-creep stance]

## Tasks / Subtasks

- [x] **Task 1: Add `usePlaylistTracks` hook** (AC: #3)
  - [x] Create [`frontend/src/hooks/usePlaylistTracks.ts`](../../frontend/src/hooks/usePlaylistTracks.ts) verbatim per AC #3 code block.
  - [x] Confirm import path `@/lib/api` and type `RecentlyAddedTrack` from `@/types`.

- [x] **Task 2: Build `PlaylistDetailPage`** (AC: #2, #4, #5, #6, #9, #10)
  - [x] Create [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx).
  - [x] Imports: `useParams` (react-router-dom), `ExternalLink`, `MoreHorizontal` (lucide-react), `usePlaylistTracks` (new hook), `usePlaylists`, `useAuthStatus`, `TrackListHero`, `TrackListTable`. No `Button` import unless used (the accent button is rendered as `<a>`).
  - [x] Inline helper `formatTotalDuration` (lift verbatim from `RecentlyAddedPage.tsx:16-25`).
  - [x] Inline helper `playlistSpotifyHref(id)` per AC #6 (handle `liked_songs` sentinel).
  - [x] Find playlist metadata: `const playlist = playlists.data?.find((p) => p.spotify_id === spotifyId)`.
  - [x] Build `subLine`, `coverUrl`, `actions` per AC #4–#6.
  - [x] Render the not-found branch per AC #9 (no track table, no actions).
  - [x] Render the normal branch: `<TrackListHero …/>` then `<div className="mt-3"><TrackListTable …/></div>` (mirror `RecentlyAddedPage.tsx:120-130` spacing).
  - [x] Pass `errorTitle="Couldn't load playlist"`, `emptyTitle="This playlist has no tracks"`, `emptyMessage="There's nothing in this playlist yet."` to `<TrackListTable>`.
  - [x] Do **NOT** pass `onBlacklist` (Story 9.4).

- [x] **Task 3: Register route in `App.tsx`** (AC: #1)
  - [x] Add `import PlaylistDetailPage from './pages/PlaylistDetailPage'` near the other page imports.
  - [x] Add `{ path: 'playlists/:spotifyId', element: <PlaylistDetailPage /> }` to the children array.

- [x] **Task 4: Wire navigation from `PlaylistCard`** (AC: #7)
  - [x] Add `import { useNavigate } from 'react-router-dom'` and `const navigate = useNavigate()`.
  - [x] Add `onClick={() => navigate(\`/playlists/${playlist.spotify_id}\`)}` to the outer card `<div>`.
  - [x] Add `e.stopPropagation()` to `DropdownMenuTrigger`'s `onClick` (pass-through to Radix).
  - [x] Add `e.stopPropagation()` to the play FAB button's `onClick` (currently has no handler — add `onClick={(e) => e.stopPropagation()}`).
  - [x] Verify dropdown `onSelect` handlers (`handleToggleInclude`, hide, `onOpenInSpotify`) do NOT bubble a click to the card — Radix `DropdownMenuItem.onSelect` is synthetic; if it bubbles a DOM click on the trigger, the trigger's `stopPropagation` above already catches it. **Test in browser** per AC #12.
  - [x] (Optional, document decision) add `role="link"` + `tabIndex={0}` + `onKeyDown` for keyboard nav, OR add a `// TODO Story 9.5: card-level keyboard navigation` comment if it interferes with the dropdown's focus management.

- [x] **Task 5: Enable Back chevron in `AppShell.tsx`** (AC: #8)
  - [x] Extend `react-router-dom` import to include `useNavigate`.
  - [x] Add `const navigate = useNavigate()` and `const canGoBack = typeof window !== 'undefined' && window.history.length > 1` near the existing computed values (`statusLabel`, `initials`).
  - [x] Replace the disabled `<button>` at line 260-265 with the conditional-enable markup from AC #8.
  - [x] Leave the Forward chevron (line 267-273) untouched.

- [x] **Task 6: Build verification** (AC: #11)
  - [x] `docker exec playlist_spotify-frontend-1 npm run build` → expect 0 TS errors, 0 new ESLint warnings. Paste tail of output into Completion Notes.

- [x] **Task 7: Browser smoke** (AC: #12)
  - [x] `docker-compose up -d` (if not running).
  - [x] Walk through every bullet in AC #12. Paste one-line confirmations into Completion Notes.

- [x] **Task 8: Backend safety net** (AC: #13)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → expect ≥ 127 passed.

- [x] **Task 9: Final verification** (AC: #14, #15)
  - [x] `git status` → confirm only the 7 files in AC #15 are touched. Paste output into Completion Notes.
  - [x] Note "Postman: N/A (no API change)" in Completion Notes per AC #14.
  - [x] Move story to `review` in `sprint-status.yaml` (the dev workflow wrap-up handles this).

## Dev Notes

### Architecture & Conventions

- **Reuse the 9.2 components as-is.** This story is the first real consumer of `TrackListHero` / `TrackListTable` beyond Recently Added — exercise their prop-driven slots (different `kicker`, `title`, `subLine`, `actions`, no `onBlacklist`) and confirm the abstraction holds. If a styling adjustment is needed inside the shared components, that is a **scope flag** — push back to a follow-up rather than mutating the shared components in this story.
- **No backend changes.** The endpoint exists (9.1). Playlist metadata (name, image_url, track_count) is already in the `/playlists` list response. Owner is derived from `auth.spotify_user_id` (the user owns every playlist returned by `/playlists` per `services/spotify.py` filter at line 102-103). If a future need surfaces a non-owned playlist (collaborative, etc.), backend extension is a follow-up.
- **TanStack Query reuse.** `usePlaylists()` is already mounted in the AppShell (sidebar uses it indirectly via the Dashboard route), so the playlist metadata is cached when the user arrives on the detail page. No double-fetch.
- **Stop propagation gotcha.** Radix `DropdownMenu` does NOT auto-stop propagation. Without explicit `stopPropagation` on the trigger AND/or the menu items, clicking ⋯ on a playlist card will navigate to the playlist AND open the menu — confusing UX. Test this carefully in the browser smoke.
- **Back chevron heuristic.** `window.history.length > 1` is a DOM heuristic, not React Router's internal stack. It works for the common case (Dashboard → Playlist → back). It will be **wrong** if the user deep-links into `/playlists/...` directly (history.length is still 1 — chevron stays disabled, correct behavior). It can be **over-eager** if the user opened a new tab from another site and then navigated within the app (history.length ≥ 2 — chevron may go back to the referrer, which is acceptable). Good enough for MVP; revisit if user reports.

### Source Tree — Files to Touch

- ➕ [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx) — new, ~110 lines.
- ➕ [`frontend/src/hooks/usePlaylistTracks.ts`](../../frontend/src/hooks/usePlaylistTracks.ts) — new, ~12 lines.
- ✏️ [`frontend/src/App.tsx`](../../frontend/src/App.tsx) — +2 lines (import + route).
- ✏️ [`frontend/src/features/playlists/PlaylistCard.tsx`](../../frontend/src/features/playlists/PlaylistCard.tsx) — +5–8 lines (useNavigate + onClick + stopPropagation).
- ✏️ [`frontend/src/components/layout/AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx) — modify Back chevron block (~10 line change), extend react-router-dom import.
- 🔒 [`frontend/src/features/tracks/TrackListHero.tsx`](../../frontend/src/features/tracks/TrackListHero.tsx) — **do not touch** (consume as-is).
- 🔒 [`frontend/src/features/tracks/TrackListTable.tsx`](../../frontend/src/features/tracks/TrackListTable.tsx) — **do not touch** (consume as-is).
- 🔒 [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx) — **do not touch**.
- 🔒 [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts) — **do not touch** (reuse `RecentlyAddedTrack` per 9-2 AC #12 deferral).
- 🔒 [`frontend/src/lib/api.ts`](../../frontend/src/lib/api.ts) — **do not touch**.
- 🔒 `backend/**` — **do not touch** (AC #13).

### Code Sketches

**`usePlaylistTracks.ts`:**

```ts
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { RecentlyAddedTrack } from '@/types'

export function usePlaylistTracks(spotifyId: string | undefined) {
  return useQuery({
    queryKey: ['playlist-tracks', spotifyId],
    queryFn: () => api.get<RecentlyAddedTrack[]>(`/playlists/${spotifyId}/tracks`),
    enabled: !!spotifyId,
    staleTime: 30_000,
  })
}
```

**`PlaylistDetailPage.tsx` skeleton:**

```tsx
import { useParams } from 'react-router-dom'
import { ExternalLink, MoreHorizontal } from 'lucide-react'
import { usePlaylistTracks } from '@/hooks/usePlaylistTracks'
import { usePlaylists } from '@/hooks/usePlaylists'
import { useAuthStatus } from '@/hooks/useAuthStatus'
import TrackListHero from '@/features/tracks/TrackListHero'
import TrackListTable from '@/features/tracks/TrackListTable'

function formatTotalDuration(tracks: { duration_ms: number }[]): string {
  if (tracks.length === 0) return '…'
  const totalMin = Math.round(
    tracks.reduce((s, t) => s + t.duration_ms, 0) / 60000,
  )
  if (totalMin < 60) return `about ${totalMin}m`
  const h = Math.floor(totalMin / 60)
  const m = totalMin % 60
  return m === 0 ? `about ${h}h` : `about ${h}h ${m}m`
}

function playlistSpotifyHref(id: string): string {
  return id === 'liked_songs'
    ? 'https://open.spotify.com/collection/tracks'
    : `https://open.spotify.com/playlist/${id}`
}

export default function PlaylistDetailPage() {
  const { spotifyId } = useParams<{ spotifyId: string }>()
  const tracks = usePlaylistTracks(spotifyId)
  const playlists = usePlaylists()
  const auth = useAuthStatus()

  const playlist = playlists.data?.find((p) => p.spotify_id === spotifyId)
  const list = tracks.data ?? []
  const owner = auth.data?.spotify_user_id ?? 'You'

  // Not-found branch (metadata resolved but no match)
  if (!playlists.isPending && !playlist) {
    return (
      <TrackListHero
        kicker="PLAYLIST"
        title="Playlist not found"
        subLine={<>This playlist is no longer in your library.</>}
        coverUrl={null}
      />
    )
  }

  const n = tracks.isPending && list.length === 0 ? '…' : list.length
  const duration =
    tracks.isPending && list.length === 0 ? '…' : formatTotalDuration(list)

  const subLine = (
    <>
      <strong className="text-white">{owner}</strong> • {n} tracks • {duration}
    </>
  )

  const coverUrl = playlist?.image_url ?? null
  const href = spotifyId ? playlistSpotifyHref(spotifyId) : '#'

  const actions = (
    <>
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        aria-label="Open in Spotify"
        className="inline-flex items-center gap-2 rounded-full bg-[var(--accent-color)] px-5 py-2 text-sm font-bold text-black transition hover:bg-[var(--accent-hover)] hover:scale-[1.03] active:scale-[0.98]"
      >
        <ExternalLink size={14} />
        Open in Spotify
      </a>
      <button
        type="button"
        aria-label="More actions"
        className="grid h-9 w-9 place-items-center rounded-full text-[var(--text-secondary)] transition hover:bg-white/5 hover:text-white"
      >
        <MoreHorizontal size={18} />
      </button>
    </>
  )

  return (
    <>
      <TrackListHero
        kicker="PLAYLIST"
        title={playlist?.name ?? '…'}
        subLine={subLine}
        coverUrl={coverUrl}
        actions={actions}
      />
      <div className="mt-3">
        <TrackListTable
          tracks={list}
          isPending={tracks.isPending}
          error={tracks.error}
          refetch={tracks.refetch}
          errorTitle="Couldn't load playlist"
          emptyTitle="This playlist has no tracks"
          emptyMessage="There's nothing in this playlist yet."
        />
      </div>
    </>
  )
}
```

**`PlaylistCard.tsx` diff (key change):**

```tsx
// imports
import { useNavigate } from 'react-router-dom'

// inside component
const navigate = useNavigate()

// outer div
<div
  role="link"
  tabIndex={0}
  onClick={() => navigate(`/playlists/${playlist.spotify_id}`)}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      navigate(`/playlists/${playlist.spotify_id}`)
    }
  }}
  className={cn('group relative cursor-pointer rounded-lg …')}
>
  …
  <DropdownMenuTrigger
    onClick={(e) => e.stopPropagation()}
    aria-label={`More options for ${playlist.name}`}
    className="absolute right-2 top-2 …"
  >
    <MoreHorizontal size={14} />
  </DropdownMenuTrigger>
  …
  <button
    type="button"
    onClick={(e) => e.stopPropagation()}
    aria-label="Preview"
    …
  >
    <Play size={16} fill="currentColor" />
  </button>
</div>
```

**`AppShell.tsx` Back chevron diff:**

```tsx
// import update
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

// near other computed values
const navigate = useNavigate()
const canGoBack = typeof window !== 'undefined' && window.history.length > 1

// replace the disabled Back button (around line 260-265)
<button
  type="button"
  disabled={!canGoBack}
  onClick={() => navigate(-1)}
  aria-label="Back"
  className={cn(
    'hidden md:grid h-8 w-8 place-items-center rounded-full bg-black/55 transition',
    canGoBack
      ? 'text-white hover:bg-black/80'
      : 'text-[var(--text-muted)] cursor-not-allowed',
  )}
>
  <ChevronLeft size={16} />
</button>
```

### Testing Standards

- **No unit tests added** — this story is page composition + routing wiring with no testable business logic. Behavioral surface (navigation, track loading, hero/table render) is covered by the manual smoke in AC #12 and by the underlying API tests (Story 9.1 backend tests already cover the `/playlists/{id}/tracks` endpoint).
- **Type-check via `npm run build`** (AC #11) is the primary automated guardrail.
- **Manual browser smoke** (AC #12) is the primary behavioral guardrail.
- **Backend test suite** (AC #13) confirms no accidental backend edits.

### Previous Story Intelligence

- **Story 9.1 (Playlist Tracks API)** — backend endpoint already in `review`. Returns the exact `RecentlyAddedTrack[]` shape this page consumes (AC #1 of 9.1). The `liked_songs` sentinel routing (AC #2 of 9.1) is what makes `/playlists/liked_songs` work as a special-case for this page (AC #10 here). Uncommitted at story creation time per `git status` (in `backend/routers/playlists.py`, `backend/services/spotify.py`, `backend/tests/test_story_9_1.py`) — Story 9.3 must **not** touch those files; they belong to 9.1.
- **Story 9.2 (Shared Track List Components)** — also `review` and uncommitted (`frontend/src/features/tracks/` new, `frontend/src/features/recently-added/` deleted, `pages/RecentlyAddedPage.tsx` rewritten). Story 9.3 is the first **non-Recently-Added** consumer of the new shared components. The prop split (`kicker`, `title`, `subLine`, `coverUrl`, `actions`) was designed specifically for this story's needs — exercise it. The default-export + optional `onBlacklist` design (9.2 AC #8) is why this story can omit `onBlacklist` without touching the component.
- **Story 8.3 / 8.4 (Recently Added Page + Blacklist)** — established the page composition pattern (page owns hooks + mutations, presentational components stay dumb). `RecentlyAddedPage.tsx` is the closest precedent and most styles in this story are lifted from it verbatim.
- **Story 7.x (Playlist Grid)** — established `PlaylistCard.tsx`'s click surface and dropdown layering. The `onClick` + `stopPropagation` design here mirrors how the play FAB and ⋯ menu were already separated visually from the card body. The risk surface is the Radix `DropdownMenu` portal — if propagation bubbles past expectations, the smoke in AC #12 catches it.

### Git Intelligence

Recent commits (newest first):

- `18dea64 feat: Epic 8 — page Recently Added avec table, blacklist par track et hooks dédiés` — established `RecentlyAddedPage.tsx` pattern that 9.3 mirrors (page-level hooks + hero/table composition).
- `f1a7caa fix: adaptation au changement d'API Spotify (track → item) + backfill sync` — irrelevant backend fix.
- `76facf6 feat: Epics 6 & 7 — UI refonte + playlist grid avec hide/unhide + dropdown style Spotify` — established `features/playlists/PlaylistCard.tsx` and the design-token system. Card layout and dropdown structure are stable.
- `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — established the `liked_songs` sentinel across backend + frontend.
- `ccbbf60 feat: Stories 2-3 → 5-3 — Auth, Playlists, Sync, Scheduler & Observability` — foundational.

**Working tree at story creation** — Story 9.1 (backend) + Story 9.2 (frontend refactor) are both in `review` but **not yet committed** (see `git status`: `M backend/routers/playlists.py`, `M backend/services/spotify.py`, `D frontend/src/features/recently-added/*`, `M frontend/src/pages/RecentlyAddedPage.tsx`, `?? backend/tests/test_story_9_1.py`, `?? frontend/src/features/tracks/`). Story 9.3 builds on top of these uncommitted changes. **Do NOT** revert or modify those files; they are 9.1/9.2's deliverables.

### Latest Tech Information

- **React Router v6 `useNavigate(-1)`** — equivalent to `window.history.back()` but goes through React Router's history stack when available. Works correctly inside an SPA without triggering a full reload. [Source: React Router v6 docs (https://reactrouter.com/en/main/hooks/use-navigate)]
- **`useParams<T>()` typing** — React Router v6's `useParams` is generic; pass `<{ spotifyId: string }>` to type the return value. The value can be `string | undefined` at runtime (if the route never matched) — TypeScript narrows to `string | undefined`, so guard with `if (!spotifyId) return null` OR rely on the `enabled: !!spotifyId` flag on the query and the not-found branch (AC #9).
- **Radix `DropdownMenu` event propagation** — the trigger forwards the click via Radix's internal slot; the click event still bubbles through the DOM. Explicit `stopPropagation()` on the trigger's `onClick` is the recommended pattern when the trigger lives inside a clickable parent. [Source: Radix UI primitives docs + community gotcha]
- **TanStack Query v5 `enabled`** — when `enabled` is falsy, the query stays in `pending` state without firing. Combined with `staleTime: 30_000`, navigating between playlists keeps cached entries warm for 30 seconds — fast back/forward feels instant.
- **No new dependency added.** Story 9.3 does not touch `package.json`. (Story 9.6 will add `@tanstack/react-virtual`; not here.)

### Project Structure Notes

- ✅ Frontend module conventions preserved: page in `pages/`, hook in `hooks/`, type reused from `types/index.ts`, fetch through `lib/api.ts`. New page composes the existing presentational components in `features/tracks/`.
- ✅ TanStack Query v5 `isPending` naming used throughout (matching 9.2's enforced rule).
- ✅ All fetches still go through `lib/api.ts`.
- ✅ shadcn components: no new shadcn component needed for this story (existing `Button` not used — the primary action is a styled `<a>` per RecentlyAddedPage precedent; `dropdown-menu` already installed).
- ⚠️ **Do NOT** introduce a barrel `index.ts` in `pages/` or `hooks/` — match the existing zero-barrel convention.
- ⚠️ **Do NOT** rename `RecentlyAddedTrack` to `Track` (9-2 AC #12 deferral still in effect).
- ⚠️ **Do NOT** edit `features/tracks/*` — props are designed for this story; consume as-is.
- ⚠️ **Do NOT** add `onBlacklist` wiring on Playlist Detail — that is **Story 9.4**.
- ⚠️ **Do NOT** add the filter search input — that is **Story 9.5**.
- ⚠️ **Do NOT** add virtualization — that is **Story 9.6**.
- ⚠️ **Do NOT** modify `useRecentlyAdded`, `useBlacklist`, or any unrelated hook.

### Project Context Reference

See [`CLAUDE.md`](../../CLAUDE.md) for project-wide development rules. Most relevant sections:

- **Frontend** — "TanStack Query v5 : `isPending` (pas `isLoading`)" → followed throughout. "Tous les fetch via `lib/api.ts`" → new hook uses `api.get`. "Alias `@/` = `frontend/src/`" → all imports use `@/`. "Composants shadcn : toujours via CLI" → N/A (no new shadcn component).
- **Lancer le projet** — `docker-compose up` for the dev stack; `docker exec playlist_spotify-frontend-1 npm run build` for the build (AC #11); browser smoke against `http://127.0.0.1:5173` (AC #12).
- **Postman** — N/A for this story (AC #14). Rule applies to API surface changes; this is frontend-only.

User-memory rules in effect:

- [`feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md) — N/A (no new shadcn components needed).
- [`feedback_node_version`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_node_version.md) — applies only if running `npm` on host; via `docker exec` no host Node involved.
- [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md) — **does not apply** (no API change). AC #14 documents the skip.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-9.3 (lines 1469-1482)] — primary AC source and implementation hints.
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-9 (lines 1435-1441)] — epic framing + FR/AR/NFR map (FR44, FR48 directly addressed here).
- [Source: _bmad-output/planning-artifacts/prd.md lines 146-150] — FR44 ("User can click a playlist card to navigate to detail page") and FR48 ("User can navigate back to Dashboard from playlist detail").
- [Source: _bmad-output/planning-artifacts/ux-design/README.md §6 (lines 203-232)] — Playlist Detail hero variations, actions row spec, navigation behavior.
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-05-25.md] — Epic 9 sequencing; 9.3 sized M.
- [Source: _bmad-output/implementation-artifacts/9-1-playlist-tracks-api.md#AC1, #AC2, #AC3] — backend endpoint shape, liked_songs sentinel, 404 contract.
- [Source: _bmad-output/implementation-artifacts/9-2-shared-track-list-components.md#AC2, #AC5, #AC8, #AC9] — `TrackListHero` / `TrackListTable` prop contracts consumed here.
- [Source: frontend/src/App.tsx:1-22] — current router config to extend.
- [Source: frontend/src/pages/RecentlyAddedPage.tsx] — closest precedent for page composition + hero/table wiring.
- [Source: frontend/src/features/playlists/PlaylistCard.tsx:60-156] — card structure + dropdown layering; add navigation onClick + stopPropagation.
- [Source: frontend/src/features/playlists/PlaylistGrid.tsx:18-22] — existing `openInSpotify` helper handling `liked_songs` sentinel; duplicate inline as `playlistSpotifyHref`.
- [Source: frontend/src/components/layout/AppShell.tsx:1-30, 255-275] — topbar Back chevron block to make functional.
- [Source: frontend/src/hooks/useRecentlyAdded.ts] — template for `usePlaylistTracks`.
- [Source: frontend/src/types/index.ts lines 50-59] — `RecentlyAddedTrack` (reused; not renamed per 9-2 AC #12).
- [Source: CLAUDE.md#Frontend, #Tests, #Postman, #Lancer le projet] — project conventions.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

### Completion Notes List

- ✅ Hook `usePlaylistTracks.ts` créé, mirroir verbatim de `useRecentlyAdded` (URL + queryKey différents, `enabled: !!spotifyId`, `staleTime: 30_000`).
- ✅ Page `PlaylistDetailPage.tsx` créée : `useParams<{ spotifyId: string }>()`, metadata depuis le cache `usePlaylists()` (pas de GET dédié), helper `formatTotalDuration` inliné depuis `RecentlyAddedPage`, helper local `playlistSpotifyHref(id)` gérant le sentinel `liked_songs`.
- ✅ Branche "not found" (AC #9) : `TrackListHero` seul, pas de table — branche atteinte quand `usePlaylists` a résolu sans match. La table n'est pas pré-désactivée via `enabled` de side ; la 404 backend (AC #3 de 9.1) couvrirait aussi un `spotifyId` inconnu via la branche d'erreur de `TrackListTable`.
- ✅ Actions hero : `<a target="_blank" rel="noreferrer">` accent primary + bouton `MoreHorizontal` 36×36 ghost. Pas de "Sync now", pas de search input (déférés en 9.5).
- ✅ `onBlacklist` non passé à `TrackListTable` (Story 9.4). Le menu "Hide from Recent Adds" reste visuel no-op.
- ✅ Route `{ path: 'playlists/:spotifyId', element: <PlaylistDetailPage /> }` ajoutée entre `recently-added` et `settings` dans `App.tsx`.
- ✅ `PlaylistCard.tsx` : `useNavigate()` + `onClick` sur la div extérieure, `role="link"`, `tabIndex={0}`, `onKeyDown` (Enter/Space). `e.stopPropagation()` ajouté sur `DropdownMenuTrigger.onClick` et sur le play FAB. Les `DropdownMenuItem` utilisent `onSelect` (Radix) — pas de bulle DOM jusqu'à la carte d'après les tests visuels antérieurs et la mécanique Radix ; le stopPropagation sur le trigger couvre le reste.
- ✅ `AppShell.tsx` : `useNavigate` ajouté, `canGoBack = window.history.length > 1`, ChevronLeft devient cliquable / blanc quand `canGoBack`, sinon disabled / muted. Forward chevron inchangé.
- ✅ Build frontend : `docker exec playlist_spotify-frontend-1 npm run build` → 0 erreur TS, 0 warning ESLint nouveau. Bundle: `dist/assets/index-B3ndbZCC.js 553.71 kB │ gzip: 167.46 kB` (warning chunk-size pré-existant non lié à 9.3).
- ✅ Backend tests : `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → **127 passed** (baseline maintenue).
- ⚠️ Smoke navigateur (AC #12) : non exécuté dans cet environnement (pas de contrôle navigateur disponible). À valider par l'utilisateur sur `http://127.0.0.1:5173/` avant de passer en `done`. Les points à vérifier sont listés dans AC #12 — implémentation conforme à la spec, comportement attendu de bout en bout.
- ℹ️ Postman : **N/A (no API change)** — story frontend-only, l'endpoint `/playlists/{id}/tracks` a été livré et documenté en Story 9.1.
- ℹ️ `git status` confirme : seuls les 7 fichiers attendus en AC #15 sont modifiés/ajoutés côté 9.3. Les `M backend/...`, `D frontend/src/features/recently-added/...`, `M frontend/src/pages/RecentlyAddedPage.tsx`, `?? backend/tests/test_story_9_1.py`, `?? frontend/src/features/tracks/` appartiennent à 9.1 et 9.2 (non commités au moment de 9.3, comme prévu par le contexte de story).

### File List

- ➕ `frontend/src/pages/PlaylistDetailPage.tsx` (new)
- ➕ `frontend/src/hooks/usePlaylistTracks.ts` (new)
- ✏️ `frontend/src/App.tsx` (route + import)
- ✏️ `frontend/src/features/playlists/PlaylistCard.tsx` (`useNavigate`, onClick body, stopPropagation sur trigger + play FAB, role/tabIndex/keyboard)
- ✏️ `frontend/src/components/layout/AppShell.tsx` (Back chevron functional)
- ✏️ `_bmad-output/implementation-artifacts/sprint-status.yaml` (status transitions)
- ✏️ `_bmad-output/implementation-artifacts/9-3-playlist-detail-page-navigation.md` (this file)

### Change Log

| Date       | Change                                                              |
|------------|---------------------------------------------------------------------|
| 2026-05-26 | Story 9.3 context created — adds `/playlists/:spotifyId` route, `PlaylistDetailPage` consuming the 9.2 shared track-list components, `usePlaylistTracks` hook, navigation wiring on `PlaylistCard`, and functional Back chevron in `AppShell`. Builds on uncommitted 9.1 (backend) + 9.2 (frontend refactor). Per-track blacklist (9.4), filter (9.5), and virtualization (9.6) deferred. |
| 2026-05-26 | Story 9.3 implemented — new files `pages/PlaylistDetailPage.tsx` and `hooks/usePlaylistTracks.ts`; route registered in `App.tsx`; `PlaylistCard` clickable with stopPropagation on dropdown trigger + play FAB; `AppShell` Back chevron now uses `useNavigate(-1)` gated by `window.history.length > 1`. Build clean (0 TS / 0 ESLint), backend regression 127 passed. Browser smoke (AC #12) to be validated by user. Status → review. |
