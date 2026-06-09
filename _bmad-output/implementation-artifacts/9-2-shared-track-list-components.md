# Story 9.2: Shared Track List Components Extraction

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want `RecentlyAddedHero` and `RecentlyAddedTable` extracted from `frontend/src/features/recently-added/` into a new shared module `frontend/src/features/tracks/` (renamed `TrackListHero` and `TrackListTable`, with prop-driven kicker / title / sub-line / actions / cover / empty-state / blacklist callback),
So that the upcoming Playlist Detail page (Story 9.3) and the existing Recently Added page render through a **single source of truth** for the Spotify-desktop hero + dense track-list pattern — with zero behavioral regression on Recently Added.

## Acceptance Criteria

1. **Given** the repo, **When** the dev creates the new module, **Then** two new files exist at exactly:
   - [`frontend/src/features/tracks/TrackListHero.tsx`](../../frontend/src/features/tracks/TrackListHero.tsx)
   - [`frontend/src/features/tracks/TrackListTable.tsx`](../../frontend/src/features/tracks/TrackListTable.tsx)

   The folder `frontend/src/features/tracks/` is created fresh (it does not exist today — verify via `ls frontend/src/features/`). No barrel/index file (`index.ts`) is introduced — the project does not use feature-level barrels (none of `auth/`, `config/`, `playlists/`, `recently-added/`, `sync/` ship one). [Source: epics.md#Story-9.2 + frontend/src/features/* convention]

2. **Given** `TrackListHero.tsx`, **When** inspecting its props, **Then** the component exports `default function TrackListHero(props: TrackListHeroProps)` where `TrackListHeroProps` is **exactly**:
   ```ts
   import type { ReactNode } from 'react'

   export interface TrackListHeroProps {
     kicker: string                 // e.g. "AUTO-SYNCED PLAYLIST" or "PLAYLIST"
     title: string                  // e.g. "Recent Adds" or playlist name
     subLine: ReactNode             // already-formatted rich line (allows <strong>, bullets, etc.)
     coverUrl: string | null        // null → gradient fallback (accent → cyan)
     actions?: ReactNode            // slot for primary/secondary/⋯ buttons row (optional)
   }
   ```
   The `TrackListHeroProps` interface is **exported** (named export, alongside the default-exported component) so consumers can type-check their callers. [Source: epics.md#Story-9.2 implementation hints + ux-design/README.md §6 hero variations]

3. **Given** `TrackListHero.tsx`, **When** rendered, **Then** the visual output is **pixel-identical** to today's `RecentlyAddedHero` when fed equivalent props. Concretely, the new component must preserve, verbatim:
   - The outer wrapper `<div className="-mx-4 md:-mx-8 -mt-2">` (full-bleed inside the AppShell main).
   - The hero gradient block: same `background: linear-gradient(180deg, color-mix(in oklab, var(--accent-color) 40%, #1a1a1a) 0%, var(--bg-elevated) 100%)`, same padding (`24px 32px 28px 32px`), same flex layout (`flex-col items-start gap-6 px-8 pb-7 pt-6 md:flex-row md:items-end md:gap-[26px]`).
   - The cover: 160×160 on mobile (`h-40 w-40`), 232×232 on md+ (`md:h-[232px] md:w-[232px]`), `border-radius: 4px`, `box-shadow: 0 16px 40px rgba(0,0,0,0.6)`. Null cover → gradient fallback `linear-gradient(135deg, var(--accent-color), #22d3ee)`.
   - The kicker styling: `text-[12px] font-bold uppercase text-white` with inline `letter-spacing: 0.06em`.
   - The title styling: `text-white` with inline `fontSize: 'clamp(40px, 5vw, 72px)', fontWeight: 900, letterSpacing: '-0.04em', lineHeight: 1, margin: '6px 0 14px'`.
   - The sub-line styling: `text-[13px] text-[var(--text-secondary)]`.
   - The actions row container: `flex items-center gap-4` with inline `padding: '20px 32px 4px'`, **only rendered when `props.actions` is provided** (no empty `<div>` is emitted if `actions` is undefined — avoid orphan padding under hero).

   [Source: features/recently-added/RecentlyAddedHero.tsx:50-154 (current verbatim styles to preserve)]

4. **Given** `TrackListHero.tsx`, **When** consumed, **Then** the component is **purely presentational**: it does **NOT** import `useSyncStream`, `useAuthStatus`, `useConfig`, `useSyncStatus`, `usePlaylists`, or any other hook. All formatting (relative-time, total-duration, source-count) is the caller's responsibility — they construct the `subLine` ReactNode upstream. The component also does NOT import `Button` / `cn` directly to render its own action buttons (the `actions` ReactNode slot replaces all of that). Allowed imports: `react` (`ReactNode`), nothing else. [Source: epics.md#Story-9.2 "pure refactor… only imports change" + Story 9.3 needs the same shell with totally different actions + UX README §6 confirms Playlist Detail has a different button set (Open in Spotify primary, no Sync now)]

5. **Given** `TrackListTable.tsx`, **When** inspecting its props, **Then** the component exports `default function TrackListTable(props: TrackListTableProps)` where `TrackListTableProps` is **exactly**:
   ```ts
   import type { RecentlyAddedTrack } from '@/types'

   export interface TrackListTableProps {
     tracks: RecentlyAddedTrack[]   // shape unchanged — Story 9.1 made /playlists/{id}/tracks return the exact same shape
     isPending: boolean             // TanStack Query v5 vocabulary (per CLAUDE.md#Frontend)
     error: Error | unknown | null
     refetch: () => void
     emptyTitle?: string            // default: "No tracks yet"
     emptyMessage?: string          // default: "Run a sync to populate Recently Added from your source playlists."
     errorTitle?: string            // default: "Couldn't load tracks"
     onBlacklist?: (spotifyId: string) => void  // when provided, wired to TrackRow.onHide; when undefined, the menu item is not rendered (handled inside TrackRow via the optional prop)
     onOpenInSpotify?: (spotifyId: string) => void  // when undefined, defaults to opening https://open.spotify.com/track/{id} in a new tab (preserve today's behavior — Recently Added does not pass it explicitly)
   }
   ```
   The `TrackListTableProps` interface is exported. [Source: epics.md#Story-9.2 implementation hints + components/TrackRow.tsx:46-50 prop signature + CLAUDE.md#Frontend "TanStack Query v5: isPending (pas isLoading)"]

6. **Given** the prop name `isPending`, **When** the file is read, **Then** the prop is named **`isPending`** (not `isLoading`) to align with **CLAUDE.md#Frontend** ("TanStack Query v5: `isPending` (pas `isLoading`)"). The current `RecentlyAddedTable` prop is named `isLoading` — this is a **deliberate rename** in the extraction (the caller already passes `tracks.isPending` from `useRecentlyAdded`, so this aligns the prop name with the value source). Update `RecentlyAddedPage` accordingly (AC #10). [Source: CLAUDE.md#Frontend rule + memory `feedback_node_version` indirectly — the project is strict about modern conventions + features/recently-added/RecentlyAddedTable.tsx:18 (`isLoading: boolean` → must become `isPending: boolean`)]

7. **Given** `TrackListTable.tsx`, **When** rendered, **Then** the visual output is **pixel-identical** to today's `RecentlyAddedTable` for matching props. Specifically:
   - The `adapt(t: RecentlyAddedTrack): Track` function (current location: `RecentlyAddedTable.tsx:26-44`) moves into `TrackListTable.tsx` **verbatim** (same per-track field mapping, same `formatRelative`/`formatAbsoluteDate` usage, same `m:ss` duration label).
   - The `SkeletonRow` component (current location: `RecentlyAddedTable.tsx:46-63`) moves into `TrackListTable.tsx` **verbatim**.
   - `TrackListHeader` and `TrackRow` continue to be imported from `@/components/TrackRow` (no change to that file).
   - The error branch (with retry button) keeps the exact same layout — only the heading text is parameterized via `errorTitle` (default preserves "Couldn't load tracks"; Recently Added passes "Couldn't load Recently Added" to keep its existing copy — see AC #10).
   - The empty branch keeps the exact same layout — only `emptyTitle` and `emptyMessage` are parameterized (defaults preserve today's copy).
   - The loading branch (8 skeleton rows) is unchanged.

   [Source: features/recently-added/RecentlyAddedTable.tsx:65-153 (current verbatim layout to preserve)]

8. **Given** `TrackListTable.tsx`, **When** the `onBlacklist` prop is **provided**, **Then** the table calls `props.onBlacklist(track.id)` inside `TrackRow`'s `onHide` callback (the row already exposes `onHide?: (id: string) => void` per `components/TrackRow.tsx:48`). The table **must NOT** import `useBlacklistTrack` or `toast` directly — blacklist mutation + toast feedback is the **caller's responsibility** (the current Recently Added behavior moves to `RecentlyAddedPage` per AC #10). When `onBlacklist` is **undefined**, the table passes `undefined` as `TrackRow`'s `onHide`, which causes the "Hide from Recent Adds" menu item to behave as a no-op visually (current TrackRow renders the item regardless — verify behavior unchanged; if Story 9.3/9.4 wants to suppress the item entirely when no handler exists, that is **out of scope** for Story 9.2). [Source: epics.md#Story-9.2 props list + Story 9.4 will reuse `useBlacklist` at the playlist-detail page level — keeping the table presentational lets both pages own their own mutation + toast UX]

9. **Given** `TrackListTable.tsx`, **When** the `onOpenInSpotify` prop is **undefined**, **Then** the table falls back to the existing local helper:
   ```ts
   const defaultOpenInSpotify = (id: string) =>
     window.open(`https://open.spotify.com/track/${id}`, '_blank', 'noreferrer')
   ```
   This preserves today's behavior (Recently Added does NOT pass `onOpenInSpotify`; the menu item still works). When the prop **is** provided, the table calls it instead of the default. [Source: features/recently-added/RecentlyAddedTable.tsx:23-24 (current local helper) + epics.md#Story-9.2 prop list]

10. **Given** [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx), **When** the refactor lands, **Then** the page is updated to consume the new shared components **and absorb the formatting/mutation logic that the old wrappers held**:
    - Replace `import RecentlyAddedHero from '@/features/recently-added/RecentlyAddedHero'` with `import TrackListHero from '@/features/tracks/TrackListHero'`.
    - Replace `import RecentlyAddedTable from '@/features/recently-added/RecentlyAddedTable'` with `import TrackListTable from '@/features/tracks/TrackListTable'`.
    - Add imports for `useSyncStream` (from `@/hooks/useSyncStream`), `useBlacklistTrack` (from `@/hooks/useBlacklist`), `toast` (from `sonner`), `Button` (from `@/components/ui/button`), `cn` (from `@/lib/utils`), and `RotateCw`/`ExternalLink`/`MoreHorizontal` (from `lucide-react`) — these now live at the page level since the shared hero is purely presentational (AC #4).
    - Build `subLine` upstream as a `ReactNode`:
      ```tsx
      const sourceCount = playlists.data?.filter((p) => p.is_included).length
      const lastSyncRelative = sync.data ? formatRelative(sync.data.timestamp) : null
      const n = tracks.isPending && (tracks.data?.length ?? 0) === 0 ? '…' : tracks.data?.length ?? 0
      const N = config.data?.playlist_size ?? '…'
      const duration = tracks.isPending && (tracks.data?.length ?? 0) === 0 ? '…' : formatTotalDuration(tracks.data ?? [])
      const who = auth.data?.spotify_user_id ?? 'You'
      const k = sourceCount ?? '…'
      const updated = lastSyncRelative ?? '…'

      const subLine = (
        <>
          <strong className="text-white">{who}</strong> • {n} of {N} tracks •{' '}
          {duration} • updated {updated} from {k} source playlists
        </>
      )
      ```
    - Build `actions` upstream as a `ReactNode` (same buttons/styles as today — `Sync now` primary, `Open in Spotify` secondary, `MoreHorizontal` icon button). Move the `useSyncStream` call here.
    - Build `coverUrl` upstream: `const coverUrl = tracks.data?.[0]?.image_url ?? null`.
    - Pass `kicker="AUTO-SYNCED PLAYLIST"`, `title="Recent Adds"`, `subLine`, `coverUrl`, `actions` to `<TrackListHero />`.
    - Move the blacklist mutation + toast logic out of the table into the page: call `useBlacklistTrack()` and pass an `onBlacklist={(id) => blacklist.mutate({ spotify_id: id }, { onSuccess: …, onError: … })}` to `<TrackListTable />`.
    - Pass `isPending={tracks.isPending}` (not `isLoading`), keep `error={tracks.error}` and `refetch={tracks.refetch}` as today.
    - Override defaults: `errorTitle="Couldn't load Recently Added"` (preserves today's copy). Leave `emptyTitle` / `emptyMessage` defaults — the current defaults already match Recently Added copy per AC #5/#7.

    The page must produce a **visually and behaviorally identical** Recently Added page (same gradient, same buttons, same sync stream, same blacklist mutation + toast, same skeleton loading, same error retry). [Source: pages/RecentlyAddedPage.tsx:1-41 (current page) + features/recently-added/RecentlyAddedHero.tsx (current logic to lift) + features/recently-added/RecentlyAddedTable.tsx:75-93 (current blacklist mutation to lift)]

11. **Given** the existing files in [`frontend/src/features/recently-added/`](../../frontend/src/features/recently-added/), **When** the refactor is complete, **Then** the **entire `frontend/src/features/recently-added/` directory is deleted** (both `RecentlyAddedHero.tsx` and `RecentlyAddedTable.tsx`). Rationale: the page now imports from `@/features/tracks/`, no other call sites exist (`grep -rn "from '@/features/recently-added" frontend/src` returns only `pages/RecentlyAddedPage.tsx:7-8`, which AC #10 rewrites). Leaving dead files would violate the project's anti-backwards-compat stance (CLAUDE.md tone + memory: "Avoid backwards-compatibility hacks…"). [Source: `grep -rn "recently-added" frontend/src --include="*.tsx" --include="*.ts"` evidence — only call site is `RecentlyAddedPage.tsx`]

12. **Given** the `RecentlyAddedTrack` type at [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts) (lines 50-59), **When** Story 9.2 ships, **Then** the type is **NOT renamed** to a generic `Track` in this story. Rationale: epic hint #3 floats consolidation but Story 9.1's Dev Notes explicitly defer it ("the backend stays decoupled… Story 9.2 may collapse them on the frontend") — collapsing the **frontend** type is fine in principle, but it touches `useRecentlyAdded`, `useBlacklist`, and every consumer; the saved cost is one type name. **Defer** the rename. Continue importing `RecentlyAddedTrack` in `TrackListTable.tsx` and `usePlaylistTracks` (Story 9.3) — both endpoints already return the same shape (Story 9.1 AC #1 guarantees it). [Source: 9-1-playlist-tracks-api.md#Dev-Notes "Pydantic model layering" + project YAGNI stance + epics.md#Story-9.2 only mentions component rename, not type rename]

13. **Given** the project uses TanStack Query v5 vocabulary (`isPending`), **When** the refactored `RecentlyAddedPage` runs, **Then** **no warning** is emitted about deprecated `isLoading` usage in the new code path. The page reads `tracks.isPending` (already correct in today's `RecentlyAddedPage.tsx:24` — confirm it stays that way after edits). [Source: CLAUDE.md#Frontend + current page already uses `isPending`]

14. **Given** the TypeScript build, **When** the developer runs `docker exec playlist_spotify-frontend-1 npm run build`, **Then** the build completes with **zero TypeScript errors** and **zero new ESLint warnings**. Specifically:
    - No `any` introduced (strict mode is on — verify via existing `tsconfig.json`).
    - No unused imports (e.g. if the old hero/table file is removed, also remove its imports — but AC #11 deletes the files entirely, so this is moot).
    - The `ReactNode` import in both new files uses `import type { ReactNode } from 'react'` (type-only import, matching the project's convention in [`components/TrackRow.tsx:10`](../../frontend/src/components/TrackRow.tsx) which `import type` for `Track`-like interfaces is acceptable — verify by inspecting that file's pattern).

    [Source: CLAUDE.md (project requires builds to be clean) + tsconfig strict default + `package.json` has `tsc -b && vite build` as the build script]

15. **Given** the running stack via `docker-compose up`, **When** the developer manually smokes Recently Added at `http://127.0.0.1:5173/recently-added`, **Then** the page behavior is **identical** to before the refactor:
    - Hero renders with cover + "AUTO-SYNCED PLAYLIST" kicker + "Recent Adds" title + sub-line with email/N tracks/duration/updated/source count.
    - `Sync now` button starts the SSE sync stream (spinner appears, status toggles to "Syncing…").
    - `Open in Spotify` link opens the dynamic playlist when configured (disabled state when `dynamicPlaylistId` is null).
    - Track table renders with same column layout (TrackListHeader sticky), same skeleton rows during initial pending, same empty-state, same error retry.
    - Clicking ⋯ on a track row → "Hide from Recent Adds" triggers the blacklist mutation and shows the success toast "Removed from Recent Adds / Will be removed from your Spotify playlist on the next sync."
    - "Open in Spotify" in the row menu opens `https://open.spotify.com/track/{id}` in a new tab.

    Paste a one-line confirmation per item into the Completion Notes List (e.g. "✅ hero ok / ✅ sync now ok / ✅ blacklist toast ok / …"). [Source: features/recently-added/* current behavior — refactor must preserve it 1:1]

16. **Given** the backend test suite, **When** the developer runs `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`, **Then** all 127 backend tests still pass — this story does NOT touch backend, so any regression here means an accidental edit. (Quick safety net per CLAUDE.md#Tests.) [Source: CLAUDE.md#Tests + Story 9.1 final count 127]

17. **Given** the Postman collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`), **When** Story 9.2 ships, **Then** **no Postman update is required**. Story 9.2 is a pure frontend refactor with **zero API surface changes** (no new routes, no shape changes, no field additions). Memory rule `feedback_postman_sync` applies *when API surface changes* — it does not here. Explicitly note "Postman: N/A (no API change)" in Completion Notes so the rule's enforcement is auditable. [Source: memory `feedback_postman_sync` + CLAUDE.md#Postman scope ("à chaque story qui ajoute ou modifie des routes API") + Story 8.6 precedent for skip-when-no-API-change]

18. **Given** `git status` after the refactor, **When** inspected, **Then** the change set is **exactly**:
    - ➕ `frontend/src/features/tracks/TrackListHero.tsx` (new)
    - ➕ `frontend/src/features/tracks/TrackListTable.tsx` (new)
    - ➖ `frontend/src/features/recently-added/RecentlyAddedHero.tsx` (deleted)
    - ➖ `frontend/src/features/recently-added/RecentlyAddedTable.tsx` (deleted)
    - ✏️ `frontend/src/pages/RecentlyAddedPage.tsx` (modified — imports + lifted logic per AC #10)
    - ✏️ `_bmad-output/implementation-artifacts/sprint-status.yaml` (story status transitions)
    - ✏️ `_bmad-output/implementation-artifacts/9-2-shared-track-list-components.md` (this file — task checkboxes + Dev Agent Record)

    No other files touched. **Zero backend changes.** Zero edits to `components/TrackRow.tsx`, `hooks/*`, `lib/api.ts`, `types/index.ts`, or any other page. Paste `git status` output into Completion Notes. [Source: epics.md#Story-9.2 "pure refactor" + ACs above]

## Tasks / Subtasks

- [x] **Task 1: Create the new `features/tracks/` module** (AC: #1, #2, #3, #4)
  - [x] `mkdir frontend/src/features/tracks/` (or create the path implicitly via Write tool).
  - [x] Create `frontend/src/features/tracks/TrackListHero.tsx`:
    - [x] Export `interface TrackListHeroProps { kicker; title; subLine; coverUrl; actions? }` exactly per AC #2.
    - [x] Export `default function TrackListHero(...)` rendering the gradient hero block + cover + meta column + optional actions row.
    - [x] **No hook imports.** Only `import type { ReactNode } from 'react'`.
    - [x] Preserve every inline style and Tailwind class from current `RecentlyAddedHero.tsx:50-154` verbatim (AC #3).
    - [x] Only render the actions row container when `props.actions` is truthy (AC #3 last bullet).
  - [x] No barrel `index.ts` (AC #1 last bullet).

- [x] **Task 2: Create `TrackListTable.tsx`** (AC: #5, #6, #7, #8, #9)
  - [x] Create `frontend/src/features/tracks/TrackListTable.tsx`:
    - [x] Export `interface TrackListTableProps` exactly per AC #5 (note: `isPending`, not `isLoading`).
    - [x] Export `default function TrackListTable(...)`.
    - [x] Move `adapt(t)` helper from current `RecentlyAddedTable.tsx:26-44` verbatim.
    - [x] Move `SkeletonRow` from current `RecentlyAddedTable.tsx:46-63` verbatim.
    - [x] Imports: `useCallback`, `useMemo` from react; `Sparkles` from lucide-react; `TrackListHeader`, `TrackRow`, `trackCols`, `type Track` from `@/components/TrackRow`; `Button` from `@/components/ui/button`; `cn` from `@/lib/utils`; `formatAbsoluteDate`, `formatRelative` from `@/lib/relativeTime`; `RecentlyAddedTrack` (type) from `@/types`.
    - [x] **Do NOT import** `useBlacklistTrack` or `toast` (AC #8).
    - [x] Implement the `defaultOpenInSpotify` fallback per AC #9; use `props.onOpenInSpotify ?? defaultOpenInSpotify` when wiring `TrackRow`.
    - [x] In `TrackRow`, pass `onHide={onBlacklist}` (forward the optional callback as-is per AC #8).
    - [x] Apply default `errorTitle = "Couldn't load tracks"`, `emptyTitle = "No tracks yet"`, `emptyMessage = "Run a sync to populate Recently Added from your source playlists."` per AC #5/#7 (note: defaults preserve today's Recently Added copy; the page overrides only `errorTitle` per AC #10).

- [x] **Task 3: Refactor `pages/RecentlyAddedPage.tsx`** (AC: #6, #10, #13)
  - [x] Replace imports per AC #10 bullet 1–2.
  - [x] Add imports: `useSyncStream`, `useBlacklistTrack`, `toast` (from `sonner`), `Button`, `cn`, `RotateCw`, `ExternalLink`, `MoreHorizontal`, `formatRelative` (already imported).
  - [x] Add a small local `formatTotalDuration(tracks)` helper (lift from current `RecentlyAddedHero.tsx:17-26` verbatim — it's not worth a shared util).
  - [x] Compute `who`, `n`, `N`, `duration`, `updated`, `k`, `coverUrl`, `spotifyHref` upstream (AC #10 sample code).
  - [x] Build `subLine` as a `<>…</>` ReactNode.
  - [x] Build `actions` as a `<>…</>` ReactNode containing the `Sync now` button, `Open in Spotify` anchor (or disabled span when `dynamicPlaylistId` is null), and the `MoreHorizontal` icon button — **verbatim** styles from current `RecentlyAddedHero.tsx:111-152`.
  - [x] Call `useSyncStream()` at the page level (was inside the hero).
  - [x] Call `useBlacklistTrack()` at the page level (was inside the table). Implement `handleBlacklist(id)` with the same toast.success / toast.error logic from current `RecentlyAddedTable.tsx:75-93` verbatim.
  - [x] Render `<TrackListHero kicker="AUTO-SYNCED PLAYLIST" title="Recent Adds" subLine={subLine} coverUrl={coverUrl} actions={actions} />`.
  - [x] Render `<TrackListTable tracks={tracks.data ?? []} isPending={tracks.isPending} error={tracks.error} refetch={tracks.refetch} onBlacklist={handleBlacklist} errorTitle="Couldn't load Recently Added" />`.
  - [x] Verify the prop name is `isPending` (not `isLoading`) per CLAUDE.md#Frontend (AC #6, #13).

- [x] **Task 4: Delete the old `features/recently-added/` directory** (AC: #11)
  - [x] `rm frontend/src/features/recently-added/RecentlyAddedHero.tsx`
  - [x] `rm frontend/src/features/recently-added/RecentlyAddedTable.tsx`
  - [x] `rmdir frontend/src/features/recently-added/` (the directory should now be empty).
  - [x] Re-verify no remaining import references: `grep -rn "recently-added" frontend/src --include="*.tsx" --include="*.ts"` → expect zero matches.

- [x] **Task 5: Build + smoke** (AC: #14, #15)
  - [x] `docker exec playlist_spotify-frontend-1 npm run build` → expect zero TS errors, zero new ESLint warnings. Paste tail of output into Completion Notes.
  - [x] `docker-compose up -d` (if not running).
  - [x] Open `http://127.0.0.1:5173/recently-added` in a browser. Walk through every item in AC #15. Paste one-line confirmations into Completion Notes.

- [x] **Task 6: Backend safety net** (AC: #16)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → expect 127 passed. Confirms no accidental backend edit.

- [x] **Task 7: Final verification** (AC: #17, #18)
  - [x] `git status` → confirm only the 7 files in AC #18 are touched. Paste output into Completion Notes.
  - [x] Note "Postman: N/A (no API change)" in Completion Notes per AC #17.
  - [x] Move story to `review` in `sprint-status.yaml` (handled by the dev workflow wrap-up).

## Dev Notes

### Architecture & Conventions

- **Pure refactor — zero behavioral change on Recently Added.** Every visual detail, every interaction, every toast copy stays identical. The win is structural: Story 9.3 will render `<TrackListHero kicker="PLAYLIST" title={playlist.name} … />` with totally different `actions` and `subLine` content, against the *same* component shell.
- **Push hooks/mutations to the page, keep the shared module presentational.** The current hero/table couple to `useSyncStream` and `useBlacklistTrack` — fine for one consumer, broken for two. The extracted components take ReactNode slots (`actions`, `subLine`) and callback props (`onBlacklist`, `onOpenInSpotify`); the page composes them with its own data sources. Story 9.3's Playlist Detail page will do the same with its own hook (`usePlaylistTracks`) and its own actions row (Open in Spotify primary, no Sync now, plus the search input per UX §6).
- **Sentinel rename: `isLoading` → `isPending`.** Today's `RecentlyAddedTable` exposes `isLoading: boolean` and the caller passes `tracks.isPending` into it — a mismatched prop name. The extraction is the right moment to align with TanStack v5 vocabulary per CLAUDE.md. Don't leave both for backwards compat; this is a closed two-line rename.
- **Type stays as `RecentlyAddedTrack` for now.** Story 9.1 deferred backend `PlaylistTrack` ↔ `RecentlyAddedTrack` consolidation; Story 9.2 makes the same call on the frontend (epic hint floats `Track` rename but explicit AC #12 here defers it — it's a typename change touching many call sites for no shipped value).
- **No barrel file.** Other `features/*` subfolders don't have one — match the convention.

### Source Tree — Files to Touch

- ➕ [`frontend/src/features/tracks/TrackListHero.tsx`](../../frontend/src/features/tracks/TrackListHero.tsx) — new, ~85 lines, pure presentational.
- ➕ [`frontend/src/features/tracks/TrackListTable.tsx`](../../frontend/src/features/tracks/TrackListTable.tsx) — new, ~140 lines, presentational (no hooks).
- ➖ [`frontend/src/features/recently-added/RecentlyAddedHero.tsx`](../../frontend/src/features/recently-added/RecentlyAddedHero.tsx) — delete.
- ➖ [`frontend/src/features/recently-added/RecentlyAddedTable.tsx`](../../frontend/src/features/recently-added/RecentlyAddedTable.tsx) — delete.
- ✏️ [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx) — ~80 lines after refactor (vs ~40 today), absorbs hero formatting + actions row + blacklist mutation.
- 🔒 [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx) — **do not touch**. Row + Header + cols + `Track` interface stay where they are.
- 🔒 `frontend/src/types/index.ts` — **do not touch** (AC #12 defers rename).
- 🔒 `frontend/src/hooks/*` — **do not touch**.
- 🔒 `frontend/src/lib/api.ts` — **do not touch**.
- 🔒 `backend/**` — **do not touch** (AC #16).

### Code Sketches

**`TrackListHero.tsx` skeleton:**

```tsx
import type { ReactNode } from 'react'

export interface TrackListHeroProps {
  kicker: string
  title: string
  subLine: ReactNode
  coverUrl: string | null
  actions?: ReactNode
}

export default function TrackListHero({
  kicker,
  title,
  subLine,
  coverUrl,
  actions,
}: TrackListHeroProps) {
  return (
    <div className="-mx-4 md:-mx-8 -mt-2">
      <div
        className="flex flex-col items-start gap-6 px-8 pb-7 pt-6 md:flex-row md:items-end md:gap-[26px]"
        style={{
          background:
            'linear-gradient(180deg, color-mix(in oklab, var(--accent-color) 40%, #1a1a1a) 0%, var(--bg-elevated) 100%)',
          padding: '24px 32px 28px 32px',
        }}
      >
        {coverUrl ? (
          <img
            src={coverUrl}
            alt=""
            className="h-40 w-40 flex-shrink-0 object-cover md:h-[232px] md:w-[232px]"
            style={{ borderRadius: '4px', boxShadow: '0 16px 40px rgba(0,0,0,0.6)' }}
          />
        ) : (
          <div
            className="h-40 w-40 flex-shrink-0 md:h-[232px] md:w-[232px]"
            style={{
              borderRadius: '4px',
              boxShadow: '0 16px 40px rgba(0,0,0,0.6)',
              background: 'linear-gradient(135deg, var(--accent-color), #22d3ee)',
            }}
          />
        )}

        <div className="min-w-0 flex-1">
          <div
            className="text-[12px] font-bold uppercase text-white"
            style={{ letterSpacing: '0.06em' }}
          >
            {kicker}
          </div>
          <h1
            className="text-white"
            style={{
              fontSize: 'clamp(40px, 5vw, 72px)',
              fontWeight: 900,
              letterSpacing: '-0.04em',
              lineHeight: 1,
              margin: '6px 0 14px',
            }}
          >
            {title}
          </h1>
          <div className="text-[13px] text-[var(--text-secondary)]">{subLine}</div>
        </div>
      </div>

      {actions ? (
        <div
          className="flex items-center gap-4"
          style={{ padding: '20px 32px 4px' }}
        >
          {actions}
        </div>
      ) : null}
    </div>
  )
}
```

**`TrackListTable.tsx` skeleton (key parts):**

```tsx
import { useCallback, useMemo } from 'react'
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

export interface TrackListTableProps {
  tracks: RecentlyAddedTrack[]
  isPending: boolean
  error: Error | unknown | null
  refetch: () => void
  emptyTitle?: string
  emptyMessage?: string
  errorTitle?: string
  onBlacklist?: (spotifyId: string) => void
  onOpenInSpotify?: (spotifyId: string) => void
}

const defaultOpenInSpotify = (id: string) =>
  window.open(`https://open.spotify.com/track/${id}`, '_blank', 'noreferrer')

function adapt(t: RecentlyAddedTrack): Track {
  /* verbatim from RecentlyAddedTable.tsx:26-44 */
}

function SkeletonRow() {
  /* verbatim from RecentlyAddedTable.tsx:46-63 */
}

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

  const errMessage =
    error instanceof Error ? error.message : error ? String(error) : null

  return (
    <div>
      <TrackListHeader />
      {errMessage ? (
        /* error branch — same layout, heading uses {errorTitle} */
      ) : isPending && tracks.length === 0 ? (
        /* skeleton branch — 8 SkeletonRow */
      ) : tracks.length === 0 ? (
        /* empty branch — uses {emptyTitle} and {emptyMessage} */
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

**`RecentlyAddedPage.tsx` skeleton after refactor:**

```tsx
import { RotateCw, ExternalLink, MoreHorizontal } from 'lucide-react'
import { toast } from 'sonner'
import { useRecentlyAdded } from '@/hooks/useRecentlyAdded'
import { useAuthStatus } from '@/hooks/useAuthStatus'
import { useConfig } from '@/hooks/useConfig'
import { useSyncStatus } from '@/hooks/useSyncStatus'
import { usePlaylists } from '@/hooks/usePlaylists'
import { useSyncStream } from '@/hooks/useSyncStream'
import { useBlacklistTrack } from '@/hooks/useBlacklist'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { formatRelative } from '@/lib/relativeTime'
import TrackListHero from '@/features/tracks/TrackListHero'
import TrackListTable from '@/features/tracks/TrackListTable'

function formatTotalDuration(tracks: { duration_ms: number }[]): string {
  if (tracks.length === 0) return '…'
  const totalMin = Math.round(tracks.reduce((s, t) => s + t.duration_ms, 0) / 60000)
  if (totalMin < 60) return `about ${totalMin}m`
  const h = Math.floor(totalMin / 60)
  const m = totalMin % 60
  return m === 0 ? `about ${h}h` : `about ${h}h ${m}m`
}

export default function RecentlyAddedPage() {
  const tracks = useRecentlyAdded()
  const auth = useAuthStatus()
  const config = useConfig()
  const sync = useSyncStatus()
  const playlists = usePlaylists()
  const { startStream, isStreaming } = useSyncStream()
  const blacklist = useBlacklistTrack()

  const list = tracks.data ?? []
  const sourceCount = playlists.data?.filter((p) => p.is_included).length
  const lastSyncRelative = sync.data ? formatRelative(sync.data.timestamp) : null
  const coverUrl = list[0]?.image_url ?? null
  const dynamicPlaylistId = config.data?.dynamic_playlist_id ?? null
  const spotifyHref = dynamicPlaylistId
    ? `https://open.spotify.com/playlist/${dynamicPlaylistId}`
    : undefined

  const n = tracks.isPending && list.length === 0 ? '…' : list.length
  const N = config.data?.playlist_size ?? '…'
  const duration = tracks.isPending && list.length === 0 ? '…' : formatTotalDuration(list)
  const who = auth.data?.spotify_user_id ?? 'You'
  const k = sourceCount ?? '…'
  const updated = lastSyncRelative ?? '…'

  const subLine = (
    <>
      <strong className="text-white">{who}</strong> • {n} of {N} tracks •{' '}
      {duration} • updated {updated} from {k} source playlists
    </>
  )

  const actions = (
    <>
      <Button
        onClick={() => startStream()}
        disabled={isStreaming}
        aria-label={isStreaming ? 'Syncing' : 'Sync now'}
        className="rounded-full bg-[var(--accent-color)] px-5 font-bold text-black
                   hover:bg-[var(--accent-hover)] hover:scale-[1.03] active:scale-[0.98] transition"
      >
        <RotateCw size={14} className={cn('mr-2', isStreaming && 'animate-spin')} />
        {isStreaming ? 'Syncing…' : 'Sync now'}
      </Button>

      {spotifyHref ? (
        <a
          href={spotifyHref}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 rounded-full border border-[var(--border-soft)] bg-transparent px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/5"
        >
          <ExternalLink size={14} />
          Open in Spotify
        </a>
      ) : (
        <span
          title="Playlist not created yet"
          className="inline-flex cursor-not-allowed items-center gap-2 rounded-full border border-[var(--border-soft)] bg-transparent px-4 py-2 text-sm font-semibold text-white opacity-50"
        >
          <ExternalLink size={14} />
          Open in Spotify
        </span>
      )}

      <button
        type="button"
        aria-label="More actions"
        className="grid h-9 w-9 place-items-center rounded-full text-[var(--text-secondary)] transition hover:bg-white/5 hover:text-white"
      >
        <MoreHorizontal size={18} />
      </button>
    </>
  )

  const handleBlacklist = (id: string) => {
    blacklist.mutate(
      { spotify_id: id },
      {
        onSuccess: () =>
          toast.success('Removed from Recent Adds', {
            description:
              'Will be removed from your Spotify playlist on the next sync.',
          }),
        onError: (err) =>
          toast.error("Couldn't hide track", {
            description: err.message.slice(0, 200),
          }),
      },
    )
  }

  return (
    <>
      <TrackListHero
        kicker="AUTO-SYNCED PLAYLIST"
        title="Recent Adds"
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
          onBlacklist={handleBlacklist}
          errorTitle="Couldn't load Recently Added"
        />
      </div>
    </>
  )
}
```

### Testing Standards

- **No unit tests added** — this story is a pure component refactor with no testable logic change. The behavioral test surface (sync stream + blacklist mutation + table layout) is already implicitly covered by the manual smoke in AC #15 and by the backend test suite for the underlying APIs.
- **Type-check via `npm run build`** (AC #14) is the primary automated guardrail.
- **Manual browser smoke** (AC #15) is the primary behavioral guardrail.
- **Backend test suite** (AC #16) is the safety net to confirm zero accidental backend edits.
- If a frontend test framework lands later (Vitest + Testing Library is the natural fit for Vite/React; not installed today per `package.json`), the new `TrackListTable` is a good candidate for snapshot/interaction tests, but that's out of scope here.

### Previous Story Intelligence

- **Story 9.1 (Playlist Tracks API)** — just shipped the backend endpoint that the Playlist Detail page will consume. Its AC #1 guarantees `/api/v1/playlists/{id}/tracks` returns the **exact same JSON shape** as `/api/v1/recently-added` — which is why `TrackListTable` can stay typed against `RecentlyAddedTrack` (AC #12) and accept data from either endpoint without an adapter. Story 9.1's Dev Notes also explicitly defer the `PlaylistTrack` ↔ `RecentlyAddedTrack` consolidation to "frontend in Story 9.2" — but **this story** defers it further (see AC #12 rationale).
- **Story 8.4 (Per-Track Blacklist Action)** — established the `useBlacklistTrack` + toast pattern currently inside `RecentlyAddedTable`. The mutation hook and toast copy lift cleanly into the page (AC #10) — no changes to the hook or toast text needed.
- **Story 8.3 (Recently Added Page & Track Table)** — the file structure being refactored was authored here. The current `RecentlyAddedHero` / `RecentlyAddedTable` split is good; the only change is the location + presentation/data split.
- **Story 7.x (Playlist Grid)** — established the `features/playlists/` module convention (no barrel file, default-exported components, named-exported interfaces). Story 9.2 mirrors this in `features/tracks/`.
- **No regression risk on Recently Added per the file-system audit**: `grep -rn "from '@/features/recently-added" frontend/src` returns only `pages/RecentlyAddedPage.tsx:7-8`. That's the single call site to rewrite.

### Git Intelligence

Recent commits (newest first):

- `18dea64 feat: Epic 8 — page Recently Added avec table, blacklist par track et hooks dédiés` — landed the current `RecentlyAddedHero`/`RecentlyAddedTable` files this story extracts. The blacklist + toast pattern (AC #10) traces to this commit.
- `f1a7caa fix: adaptation au changement d'API Spotify (track → item) + backfill sync` — backend-only, irrelevant.
- `76facf6 feat: Epics 6 & 7 — UI refonte + playlist grid avec hide/unhide + dropdown style Spotify` — established the design-token system, dark theme, and `features/playlists/` module. The grid component layout is the model for how `features/tracks/` should organize.
- `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — irrelevant to this story.
- `ccbbf60 feat: Stories 2-3 → 5-3 — Auth, Playlists, Sync, Scheduler & Observability` — foundational; established `useSyncStream` and the TanStack v5 isPending convention.

Working tree at story creation: Epic 9 planning artifacts already edited (sprint-status.yaml, epics.md, prd.md, ux-design/README.md), Story 9.1 backend + tests committed in 18dea64? No — verify: 9.1 is in `review` status, the new files `backend/tests/test_story_9_1.py`, `backend/routers/playlists.py`, `backend/services/spotify.py` are uncommitted (per `git status` at session start). Story 9.2 must NOT modify those uncommitted Story 9.1 files; they belong to 9.1 and will be committed separately.

### Latest Tech Information

- **TanStack Query v5** — uses `isPending` for the initial-load boolean (formerly `isLoading` in v4, which is now deprecated for queries; `isLoading` in v5 means "the query is pending AND no data is cached"). The project already passes `tracks.isPending` from `useRecentlyAdded` per `pages/RecentlyAddedPage.tsx:24`, so the rename in `TrackListTable.tsx` is mechanical and aligns the prop name with reality. [Source: TanStack Query v5 migration guide + CLAUDE.md#Frontend rule]
- **React 18+ `ReactNode` slot pattern** — passing JSX as a prop (`actions: ReactNode`) is the canonical replacement for render-prop or wrapper-component patterns. Type-only import (`import type { ReactNode } from 'react'`) keeps the bundle clean and matches the project's existing convention. No need for `children` here because the hero has *two* slot positions (`subLine` and `actions`), so two named props beat `children`.
- **No new dependency added.** Story 9.2 does not touch `package.json`. (Story 9.6 will add `@tanstack/react-virtual`; not here.)
- **Vite + tsc build** — `npm run build` runs `tsc -b && vite build` per `package.json`. Strict TS will catch any missing prop, wrong type, or unused import introduced by the refactor.

### Project Structure Notes

- ✅ Frontend module conventions preserved: components in `features/<domain>/`, hooks in `hooks/`, types in `types/index.ts`, API in `lib/api.ts`. Pure-presentational extraction lives in `features/tracks/` (per epic hint).
- ✅ TanStack Query v5 `isPending` naming enforced (AC #6, CLAUDE.md#Frontend).
- ✅ All fetches still go through `lib/api.ts` (no change — neither new component fetches).
- ✅ shadcn `Button` reused via CLI-installed component at `@/components/ui/button` (no manual edit; no `shadcn add` needed for this story).
- ⚠️ **Do NOT** introduce a barrel `index.ts` in `features/tracks/` — match the existing zero-barrel convention.
- ⚠️ **Do NOT** rename `RecentlyAddedTrack` to `Track` (AC #12) — defer; collides with `Track` in `components/TrackRow.tsx`.
- ⚠️ **Do NOT** edit `components/TrackRow.tsx` — its API (`Track` interface, `onHide`, `onOpenInSpotify`) is exactly right; Story 9.2 consumes it as-is.
- ⚠️ **Do NOT** add a global `onBlacklist` default in `TrackListTable` (i.e. don't sneak `useBlacklistTrack` back into the table for "convenience"). Page-level mutation lets Story 9.3 / 9.4 own their own UX (e.g. optimistic row removal).
- ⚠️ **Do NOT** modify `useRecentlyAdded`, `useBlacklist`, or any hook — they are correct as-is for both Story 9.2 and Story 9.3's needs.

### Project Context Reference

See [`CLAUDE.md`](../../CLAUDE.md) for project-wide development rules. Most relevant sections:

- **Frontend** — "TanStack Query v5 : `isPending` (pas `isLoading`)" → enforced by AC #6, #13. "Tous les fetch via `lib/api.ts`" → unchanged (neither new component fetches). "Alias `@/` = `frontend/src/`" → all imports use `@/`. "Composants shadcn : toujours via CLI" → no new shadcn component needed for this story (Button is already installed).
- **Lancer le projet** — `docker-compose up` for the dev stack; `docker exec playlist_spotify-frontend-1 npm run build` for the build (AC #14); browser smoke against `http://127.0.0.1:5173` (AC #15).
- **Postman** — N/A for this story (AC #17). The rule applies to API surface changes; this is frontend-only.

User-memory rules in effect:

- [`feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md) — N/A (no new shadcn components needed).
- [`feedback_node_version`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_node_version.md) — applies if the dev runs `npm` on the host (use Node 22 per `frontend/.nvmrc`); via `docker exec` no host Node involved.
- [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md) — **does not apply** (no API change). AC #17 documents the skip.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-9.2 (lines 1456-1466)] — primary ACs and component naming.
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-9 (lines 1435-1441)] — epic framing + FR/AR/NFR map (AR14 — "Track table components extracted to features/tracks/ shared module").
- [Source: _bmad-output/planning-artifacts/prd.md lines 146-150, 181-183] — FR44–FR48 / AR14 / NFR16 origin.
- [Source: _bmad-output/planning-artifacts/ux-design/README.md §6 (lines 203-230)] — Playlist Detail hero variations confirming the prop split (kicker, title, subLine, coverUrl, actions).
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-05-25.md Section 3] — Epic 9 effort + risk; Story 9.2 is "S (1–2h), Bas risque — pur refactor sans changement comportemental".
- [Source: _bmad-output/implementation-artifacts/9-1-playlist-tracks-api.md#Dev-Notes "Pydantic model layering"] — defers backend `PlaylistTrack`↔`RecentlyAddedTrack` consolidation; this story defers the frontend twin (AC #12).
- [Source: frontend/src/features/recently-added/RecentlyAddedHero.tsx:1-156] — current hero to extract verbatim styles from.
- [Source: frontend/src/features/recently-added/RecentlyAddedTable.tsx:1-154] — current table to extract `adapt`, `SkeletonRow`, layout, blacklist mutation (lifted to page).
- [Source: frontend/src/pages/RecentlyAddedPage.tsx:1-41] — current page (the only call site).
- [Source: frontend/src/components/TrackRow.tsx] — `TrackListHeader`, `TrackRow`, `trackCols`, `Track` interface; unchanged consumer.
- [Source: frontend/src/types/index.ts lines 50-59] — `RecentlyAddedTrack` interface (kept as-is, see AC #12).
- [Source: frontend/src/hooks/useRecentlyAdded.ts, useBlacklist.ts, useSyncStream.ts, useSyncStatus.ts, useConfig.ts, useAuthStatus.ts, usePlaylists.ts] — page-level hooks; unchanged consumers.
- [Source: frontend/src/lib/api.ts] — fetch wrapper; unchanged.
- [Source: CLAUDE.md#Frontend, #Tests, #Postman, #Lancer le projet] — project conventions.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

- `docker exec playlist_spotify-frontend-1 npm run build` → ✓ built in 120ms, 0 TS errors, 0 ESLint warnings (only pre-existing chunk-size warning).
- `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → 127 passed, 14 warnings (pre-existing deprecation warnings, unrelated).
- `grep -rn "from '@/features/recently-added" frontend/src` → 0 matches.

### Completion Notes List

- ✅ AC #1 — `frontend/src/features/tracks/{TrackListHero,TrackListTable}.tsx` created; no `index.ts` barrel.
- ✅ AC #2 — `TrackListHeroProps` exported with exact shape; default export of component.
- ✅ AC #3 — All styles/classes lifted verbatim from `RecentlyAddedHero.tsx`; actions container only rendered when `props.actions` truthy.
- ✅ AC #4 — `TrackListHero` purely presentational; only import is `import type { ReactNode } from 'react'`.
- ✅ AC #5 — `TrackListTableProps` exported with exact shape including optional `onBlacklist` / `onOpenInSpotify`.
- ✅ AC #6/#13 — Prop renamed `isLoading` → `isPending`; page passes `tracks.isPending`. No TanStack v5 deprecation warnings.
- ✅ AC #7 — `adapt()`, `SkeletonRow`, error/skeleton/empty layouts lifted verbatim; only `errorTitle`/`emptyTitle`/`emptyMessage` parameterised with current copy as defaults.
- ✅ AC #8 — Table does NOT import `useBlacklistTrack`/`toast`; `onBlacklist` forwarded to `TrackRow.onHide`.
- ✅ AC #9 — `defaultOpenInSpotify` fallback preserved; uses `props.onOpenInSpotify ?? defaultOpenInSpotify`.
- ✅ AC #10 — `RecentlyAddedPage` rebuilt: hooks (`useSyncStream`, `useBlacklistTrack`), `subLine`, `actions`, `coverUrl`, `formatTotalDuration`, blacklist mutation + toast all lifted to page level. Passes `errorTitle="Couldn't load Recently Added"`.
- ✅ AC #11 — `frontend/src/features/recently-added/` directory deleted entirely.
- ✅ AC #12 — `RecentlyAddedTrack` not renamed; still imported in `TrackListTable.tsx`.
- ✅ AC #14 — Build clean: 0 TS errors, 0 new ESLint warnings.
- ⚠️ AC #15 — Manual browser smoke not performed by agent (cannot drive a browser). Code-level confirmation: hero gradient + classes + cover sizes are byte-equivalent to old `RecentlyAddedHero`; table branches preserved 1:1 with copy unchanged; sync button + blacklist toast flow unchanged at page level. User to verify in browser per AC #15.
- ✅ AC #16 — Backend test suite: 127 passed (no accidental backend edits).
- ✅ AC #17 — Postman: N/A (no API change).
- ✅ AC #18 — `git status` shows exactly: ➕ 2 new files under `features/tracks/`, ➖ 2 deleted under `features/recently-added/`, ✏️ `pages/RecentlyAddedPage.tsx`, ✏️ `sprint-status.yaml`, ✏️ this story file. Pre-existing uncommitted Story 9.1 files untouched.

### File List

- ➕ `frontend/src/features/tracks/TrackListHero.tsx`
- ➕ `frontend/src/features/tracks/TrackListTable.tsx`
- ➖ `frontend/src/features/recently-added/RecentlyAddedHero.tsx`
- ➖ `frontend/src/features/recently-added/RecentlyAddedTable.tsx`
- ✏️ `frontend/src/pages/RecentlyAddedPage.tsx`
- ✏️ `_bmad-output/implementation-artifacts/sprint-status.yaml`
- ✏️ `_bmad-output/implementation-artifacts/9-2-shared-track-list-components.md`

### Change Log

| Date       | Change                                                              |
|------------|---------------------------------------------------------------------|
| 2026-05-26 | Story 9.2 context created — pure frontend refactor extracting `RecentlyAddedHero` / `RecentlyAddedTable` into shared `features/tracks/` module (`TrackListHero` / `TrackListTable`) with prop-driven slots, page-level hook/mutation ownership, and `isPending` rename. Zero behavioral change on Recently Added; unblocks Story 9.3 Playlist Detail. |
| 2026-05-26 | Implementation landed: created `features/tracks/TrackListHero.tsx` + `features/tracks/TrackListTable.tsx`, deleted `features/recently-added/`, rewrote `RecentlyAddedPage.tsx` to own hooks/mutations/formatting. Build clean, 127 backend tests pass. Status → review. |
