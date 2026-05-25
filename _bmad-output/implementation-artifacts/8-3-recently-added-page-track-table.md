# Story 8.3: Recently Added Page — Track Table

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a dedicated Recently Added page that lists the current dynamic playlist contents as a Spotify-desktop-style track table,
so that I can see what's in my unified queue at a glance.

## Acceptance Criteria

1. **Given** I navigate to `/recently-added`, **When** the page mounts, **Then** `GET /api/v1/recently-added` is called via TanStack Query (new hook `useRecentlyAdded()` returning `RecentlyAddedTrack[]`) and the page renders a full-bleed hero block followed by a track table (FR31, FR32). [Source: epics.md#Story-8.3 AC #1 + ux-design/README.md "3 · Recently Added route" + Story-8.2 backend contract]

2. **Given** the hero block, **When** I inspect its structure, **Then** it is full-bleed (breaks out of the `AppShell` scroll container's `px-4 md:px-8 pb-10 pt-2` padding via negative horizontal margins — `-mx-4 md:-mx-8 -mt-2`), padding `24px 32px 28px 32px`, background `linear-gradient(180deg, color-mix(in oklab, var(--accent-color) 40%, #1a1a1a) 0%, var(--bg-elevated) 100%)`, flex row with `gap: 26px`, `align-items: flex-end`. Cover is 232×232px, `border-radius: 4px`, `box-shadow: 0 16px 40px rgba(0,0,0,0.6)`. Meta column has: kicker "AUTO-SYNCED PLAYLIST" (12px weight 700 uppercase letter-spacing 0.06em white), title `Recent Adds` (`font-size: clamp(40px, 5vw, 72px)`, weight 900, letter-spacing -0.04em, line-height 1, margin `6px 0 14px`), sub-line (13px secondary): `<strong>{email}</strong> • {n} of {N} tracks • about Xh Ym • updated {relative} from {k} source playlists`. [Source: epics.md#Story-8.3 AC #2 + ux-design/README.md lines 122–130]

3. **Given** the hero cover source, **When** the page renders, **Then** the cover uses `tracks[0].image_url` (first track's album art) as a stand-in if available. If the playlist is empty or the first track has no image, render a CSS gradient placeholder (`linear-gradient(135deg, var(--accent-color), #22d3ee)`) at the same 232×232 size — never break the layout, never render a broken `<img>`. [Source: ux-design/README.md "Playlist covers" + defensive UX hygiene — backend exposes only `image_url` per track, no separate playlist cover field]

4. **Given** the hero sub-line, **When** it is composed, **Then** the placeholders are sourced from existing hooks (no new endpoint): `{email}` from `useAuthStatus().data?.spotify_user_id` (fallback `"You"`), `{n}` from the loaded `tracks.length`, `{N}` from `useConfig().data?.playlist_size`, `{Xh Ym}` from `sum(tracks[i].duration_ms)` formatted as e.g. `"about 1h 12m"` (round to nearest minute), `{relative}` from `useSyncStatus().data?.timestamp` reusing the existing `formatRelative()` helper pattern in `AppShell.tsx:41–49`, `{k}` from `usePlaylists().data?.filter(p => p.is_included).length`. If any source is `null`/loading, render `"…"` placeholders rather than blowing up. [Source: ux-design/README.md lines 127–130 + frontend/src/hooks/* + AppShell.tsx formatRelative pattern]

5. **Given** the hero actions row, **When** I inspect it (below the hero, padding `20px 32px 4px`, gap 16px, also full-bleed), **Then** it contains: primary "Sync now" button (`RotateCw` icon, rounded-full, accent bg, black text — REUSE the same handler from `AppShell` topbar by calling `useSyncStream().startStream()` directly), secondary "Open in Spotify" button (`ExternalLink` icon, transparent + 1px `var(--border-soft)` border) that opens `https://open.spotify.com/playlist/{dynamic_playlist_id}` in a new tab (no-op + tooltip "Playlist not created yet" when `dynamic_playlist_id` is missing), and a 36×36 icon-only `MoreHorizontal` button (no menu wired yet — placeholder for future actions; `aria-label="More actions"`). [Source: epics.md#Story-8.3 AC #3 + ux-design/README.md "Hero actions row" + AppShell.tsx:322–331 Sync now pattern]

6. **Given** the dynamic playlist Spotify ID is needed for "Open in Spotify", **When** the page mounts, **Then** the existing `GET /api/v1/config` is **NOT** extended — instead, expose `dynamic_playlist_id` (`str | null`) on the `ConfigRead` response in [`backend/routers/config.py:24–46`](../../backend/routers/config.py) and on `Config` in [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts). This is the minimal backend change required for this story; no new endpoint. Add a regression test (`backend/tests/test_story_8_3.py::test_config_exposes_dynamic_playlist_id`) covering the new field's presence and null default. [Source: epics.md#Story-8.3 + CLAUDE.md#Backend "Réponses sans wrapper" + models/config.py existing `dynamic_playlist_id` column from prior stories]

7. **Given** the track list header, **When** I scroll the body, **Then** the header is sticky (`position: sticky; top: 0`) with background `rgba(18,18,18,0.92)`, `backdrop-filter: blur(12px)`, `z-index: 5`, `border-bottom: 1px var(--border-soft)`, column grid `36px | minmax(220px, 4fr) | minmax(160px, 3fr) | minmax(140px, 2fr) | 60px | 40px`, and labels `# | TITLE | ALBUM | DATE ADDED | <Clock icon> | ` (uppercase, 11px, weight 600, letter-spacing 0.06em, `var(--text-muted)`). Use the `TrackListHeader` component from [`ux-design/snippets/TrackRow.tsx`](../planning-artifacts/ux-design/snippets/TrackRow.tsx) as the structural base. [Source: epics.md#Story-8.3 AC #4 + ux-design/snippets/TrackRow.tsx:27–44]

8. **Given** a `TrackRow`, **When** I inspect its structure (matching [`ux-design/snippets/TrackRow.tsx`](../planning-artifacts/ux-design/snippets/TrackRow.tsx)), **Then** it uses the same 6-column grid as the header, padding `8px 16px`, `border-radius: 4px`, `gap: 14px`, `align-items: center`. Column 1 = index muted centered (replaced by 12px white `Play` icon via `group-hover` swap with `hidden`/`block` utilities). Column 2 = 40×40 thumbnail `rounded-sm object-cover` + title (14.5px weight 500 white, single-line `truncate`, optional accent "NEW" pill if `isNew`) + sub-line (12.5px muted, gap 1.5: `E` tag if `explicit` — `bg-[#535353] text-[#d4d4d4]`, `ExternalLink` 12px @ 0.7 opacity if `has_video`, artist link `hover:text-white hover:underline`). Column 3 = album single-line ellipsis 13.5px. Column 4 = relative date wrapped in shadcn `Tooltip` showing absolute date. Column 5 = duration `m:ss` tabular-nums right-aligned 13.5px. Column 6 = 32×32 `MoreHorizontal` button opacity 0 → 1 on `group-hover`. [Source: epics.md#Story-8.3 AC #5 + ux-design/snippets/TrackRow.tsx:46–139]

9. **Given** row hover, **When** the pointer enters, **Then** background becomes `var(--bg-row-hover)` (`#1a1a1a`), instant (no transition). [Source: epics.md#Story-8.3 AC #6 + ux-design/README.md line 163]

10. **Given** Column 6's `⋯` overflow menu (shadcn `DropdownMenu`), **When** I open it on a row, **Then** the menu visually contains two items per the snippet — "Hide from Recent Adds" (with `EyeOff` icon) and "Open in Spotify" (with `ExternalLink` icon). "Open in Spotify" is wired in this story (opens `https://open.spotify.com/track/{spotify_id}` in a new tab). **"Hide from Recent Adds" is rendered but its `onClick` handler is a no-op stub in this story** — the actual blacklist mutation is Story 8.4's scope. Add a `// TODO(story-8.4): wire to POST /api/v1/blacklist` comment on the stub. [Source: epics.md#Story-8.4 AC (menu contents) + ux-design/snippets/TrackRow.tsx:120–136 + Story-8.4 explicit scope split]

11. **Given** the table is rendered, **When** I inspect each row, **Then** the `#` column is the 1-based index, the title cell uses a small (≤40px) square cover thumbnail next to the text, the duration is formatted as `m:ss` (e.g., `3:42` — single-digit minutes, zero-padded seconds), and the date added is formatted **relative** via a reused `formatRelative()` helper (extract from `AppShell.tsx:41–49` into `frontend/src/lib/relativeTime.ts` so both sites share the same implementation) with the Tooltip showing the absolute date as `MMM D, YYYY` (e.g., `May 18, 2026`) via `Intl.DateTimeFormat('en', { dateStyle: 'medium' })`. [Source: epics.md#Story-8.3 AC #11 + AppShell.tsx:39–49 + DRY]

12. **Given** the data is loading (`useRecentlyAdded().isPending` — TanStack Query v5 naming), **When** the page is in its first fetch, **Then** a skeleton table is displayed: the hero shows a placeholder (gray gradient cover + 3 muted lines of varying widths), and the table area shows 8 skeleton row placeholders matching the 6-column grid (each cell a `bg-white/5 animate-pulse rounded` block sized to its column). No blank section is ever shown. Use the shadcn `Skeleton` primitive — add it via `docker exec playlist_spotify-frontend-1 npx shadcn@latest add skeleton` (the project rule per [memory `feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md) and CLAUDE.md is to always use the CLI, never to hand-write the file). [Source: epics.md#Story-8.3 AC #7 + AC #9 + CLAUDE.md#Frontend "isPending" + memory `feedback_shadcn_cli`]

13. **Given** the playlist is empty (response `[]`), **When** the page renders, **Then** the hero still renders (with `0 of {N} tracks`) and the table area shows a centered empty-state message: `Sparkles` icon (28px, accent), H3 "No tracks yet" (18px weight 700 white), muted paragraph "Run a sync to populate Recently Added from your source playlists." (13px `var(--text-secondary)`, max-width 420px), 60px vertical padding. [Source: epics.md#Story-8.3 AC #8 + AC #10 + ux-design/README.md "Empty state" line 85]

14. **Given** the query fails (network error, 401, 502 from backend), **When** the error is rendered, **Then** the hero still renders with placeholder counts and the table area shows a centered error block: red dot + "Couldn't load Recently Added" (white) + the error `.message` (12px muted, max 400 chars) + a "Retry" outline button calling `query.refetch()`. Do NOT crash the page or fall back to an infinite spinner. [Source: defensive UX — backend may 401 if token expired (Story 8.2 AC #5) or 502 on Spotify outage; user must have a clear recovery path matching `ConfigPage`/`DashboardPage` error treatment]

15. **Given** the table is rendered for 200 tracks, **When** profiled on a local network (desktop Chrome with no throttling, hard refresh, dev DB primed with a 200-track playlist), **Then** the initial paint completes within **1 second** measured by `performance.mark`/`performance.measure` from `RecentlyAddedPage` mount to first paint of the populated table (`requestAnimationFrame` after `useRecentlyAdded()` resolves). This is a measurement target, not a unit test — note the wall time in Dev Notes "Debug Log References". If it exceeds 1s, **do NOT** add virtualization, IntersectionObserver lazy thumbnails, or memoization here — Story 8.6 owns performance polish. Log the regression in Dev Notes and proceed. [Source: epics.md#Story-8.3 AC #9 + NFR14 + Story-8.6 scope]

16. **Given** the existing routing in [`frontend/src/App.tsx:14–19`](../../frontend/src/App.tsx), **When** Story 8.3 ships, **Then** the existing `path: 'recently-added'` route's element is replaced from the placeholder in [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx) (which currently renders "Coming in Epic 8") with the new fully-built page. No router change — the route key is unchanged. The sidebar nav in [`AppShell.tsx:34`](../../frontend/src/components/layout/AppShell.tsx) already points to `/recently-added` and stays as-is. [Source: frontend/src/App.tsx:15 + AppShell.tsx:34 + Story-6.3 (route registration shipped)]

17. **Given** the project rule "Tous les fetch via `lib/api.ts`", **When** the new hook is implemented, **Then** `useRecentlyAdded()` lives in `frontend/src/hooks/useRecentlyAdded.ts` and uses `api.get<RecentlyAddedTrack[]>('/recently-added')` — no inline `fetch()` calls. The `RecentlyAddedTrack` type is added to `frontend/src/types/index.ts` mirroring **exactly** the 9 snake_case fields from Story 8.2 AC #1 (`spotify_id`, `title`, `artists: string[]`, `album`, `image_url: string | null`, `added_at`, `duration_ms`, `explicit`, `has_video`). Query key: `['recently-added']` (matches the ux-design suggestion). Default `staleTime: 30_000` (light cache to avoid refetch on every nav). [Source: CLAUDE.md#Frontend + Story-8.2 AC #1 contract + ux-design/README.md "State Management" table]

18. **Given** the project's component conventions, **When** the page is built, **Then** the implementation is split:
   - `frontend/src/pages/RecentlyAddedPage.tsx` — page composition, data hooks, loading/error/empty state branches.
   - `frontend/src/features/recently-added/RecentlyAddedHero.tsx` — hero block + actions row (kept presentational, props-driven).
   - `frontend/src/features/recently-added/RecentlyAddedTable.tsx` — header + rows + skeleton + empty state.
   - `frontend/src/components/TrackRow.tsx` — generic `TrackRow` + `TrackListHeader` lifted **verbatim** from `ux-design/snippets/TrackRow.tsx` (drop into `components/` per snippet header comment "frontend/src/components/TrackRow.tsx"). Adapt the `Track` interface to map from the backend's `RecentlyAddedTrack` via a small adapter inside `RecentlyAddedTable.tsx`.
   The adapter computes `durationLabel` (`m:ss`), `addedAgo` (relative), `addedAbs` (absolute), and joins `artists: string[]` into a single comma-separated `artist` string for `TrackRow`. [Source: CLAUDE.md#Frontend + features/ folder pattern (e.g. features/playlists/PlaylistGrid.tsx) + ux-design/snippets/TrackRow.tsx header comment]

19. **Given** the page must remain responsive (the rest of the app is desktop-first per Story 6.4 but degrades gracefully), **When** the viewport is narrow (<768px), **Then** the hero stacks vertically (cover above meta), the cover shrinks to 160×160, and the table hides columns 3 (album) and 4 (date added) at <640px via Tailwind's `hidden sm:block` on those cells (header AND row cells must hide together — both have the same grid, so apply the same utility classes to keep the grid aligned, OR collapse the grid to a 4-column variant at that breakpoint). Pick the simpler of the two (hide cells in the existing 6-column grid via `hidden sm:grid` on the cell wrappers) and document the choice. [Source: Story 6.4 (desktop-first responsive layout shipped) + AppShell.tsx breakpoint patterns (`md:`/`lg:`)]

20. **Given** the new code, **When** `docker exec playlist_spotify-frontend-1 npm run build` is run, **Then** the build passes with zero TypeScript errors and zero new ESLint warnings. **Given** `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` is run, **Then** all existing 106+ backend tests pass AND the new `test_story_8_3.py::test_config_exposes_dynamic_playlist_id` passes. [Source: CLAUDE.md#Tests + Story-8.2 baseline 106 tests]

21. **Given** the Postman collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`), **When** Story 8.3 ships, **Then** the existing `Get Config` request's example response under the "Config" folder is updated to include the new `dynamic_playlist_id` field (string or null) — the only API surface change in this story. No new request is added (Recently Added itself was added in Story 8.2). Verify with a re-GET that the example reflects the new field. [Source: CLAUDE.md#Postman + memory `feedback_postman_sync`]

## Tasks / Subtasks

- [x] **Task 1: Extend `ConfigRead` with `dynamic_playlist_id`** (AC: #6, #20)
  - [x] In [`backend/routers/config.py`](../../backend/routers/config.py): add `dynamic_playlist_id: Optional[str] = None` to `ConfigRead` (right after `cron_expr`). Set it from `config.dynamic_playlist_id` in `get_config()` and `patch_config()`. The `setup_required` branch returns `dynamic_playlist_id=None`.
  - [x] In [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts): add `dynamic_playlist_id: string | null` to the `Config` interface.
  - [x] No model migration — `Config.dynamic_playlist_id` already exists in [`backend/models/config.py`](../../backend/models/config.py) (added in earlier sync stories).
  - [x] Add `backend/tests/test_story_8_3.py::test_config_exposes_dynamic_playlist_id` using the [`test_story_7_1.py`](../../backend/tests/test_story_7_1.py) fixture pattern: insert a `Config` row with `dynamic_playlist_id="abc123"`, GET `/api/v1/config`, assert `body["dynamic_playlist_id"] == "abc123"`. Also add `test_config_dynamic_playlist_id_defaults_null` covering the fresh-install path.

- [x] **Task 2: Add `useRecentlyAdded()` hook and `RecentlyAddedTrack` type** (AC: #1, #17)
  - [x] In [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts), append:
    ```ts
    export interface RecentlyAddedTrack {
      spotify_id: string
      title: string
      artists: string[]
      album: string
      image_url: string | null
      added_at: string
      duration_ms: number
      explicit: boolean
      has_video: boolean
    }
    ```
  - [x] Create [`frontend/src/hooks/useRecentlyAdded.ts`](../../frontend/src/hooks/useRecentlyAdded.ts):
    ```ts
    import { useQuery } from '@tanstack/react-query'
    import { api } from '@/lib/api'
    import type { RecentlyAddedTrack } from '@/types'

    export function useRecentlyAdded() {
      return useQuery({
        queryKey: ['recently-added'],
        queryFn: () => api.get<RecentlyAddedTrack[]>('/recently-added'),
        staleTime: 30_000,
      })
    }
    ```

- [x] **Task 3: Extract the relative-time helper** (AC: #11)
  - [x] Move `formatRelative()` from [`AppShell.tsx:41–49`](../../frontend/src/components/layout/AppShell.tsx) into a new file `frontend/src/lib/relativeTime.ts` exporting `formatRelative(iso?: string | null): string`.
  - [x] Update `AppShell.tsx` to import from `@/lib/relativeTime`.
  - [x] Also export a sibling `formatAbsoluteDate(iso: string): string` returning `Intl.DateTimeFormat('en', { dateStyle: 'medium' }).format(new Date(iso))` for the row's Tooltip.

- [x] **Task 4: Drop the canonical `TrackRow` into `components/`** (AC: #8, #10)
  - [x] Copy [`_bmad-output/planning-artifacts/ux-design/snippets/TrackRow.tsx`](../planning-artifacts/ux-design/snippets/TrackRow.tsx) verbatim to [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx). Keep the same `Track` interface and the same exported names (`Track`, `TrackRow`, `TrackListHeader`).
  - [x] Wire `onOpenInSpotify` default in `RecentlyAddedTable.tsx` (not in this component) — keep `TrackRow` presentational.

- [x] **Task 5: Add shadcn `Skeleton`** (AC: #12)
  - [x] Run `docker exec playlist_spotify-frontend-1 npx shadcn@latest add skeleton`. **Do NOT hand-write the file** (memory `feedback_shadcn_cli`).
  - [x] Verify the file lands at `frontend/src/components/ui/skeleton.tsx` with the standard shadcn signature.

- [x] **Task 6: Build `RecentlyAddedHero`** (AC: #2, #3, #4, #5, #19)
  - [x] Create `frontend/src/features/recently-added/RecentlyAddedHero.tsx`. Props:
    ```ts
    interface RecentlyAddedHeroProps {
      tracks: RecentlyAddedTrack[]
      isLoading: boolean
      email: string | null | undefined
      playlistSize: number | undefined
      sourceCount: number | undefined
      lastSyncRelative: string | null
      dynamicPlaylistId: string | null
    }
    ```
  - [x] Use `tracks[0]?.image_url ?? null` as the cover source; fall back to the CSS gradient when null.
  - [x] Compute total duration via `tracks.reduce((s, t) => s + t.duration_ms, 0)`. Format as `about Xh Ym` (or `Xm` if <60min).
  - [x] Layout: full-bleed wrapper `<div className="-mx-4 md:-mx-8 -mt-2">` containing both the hero gradient block AND the actions row (so the gradient and actions share the negative margins).
  - [x] Responsive: `<768px` stack vertically (`flex-col md:flex-row`), cover `w-40 h-40 md:w-[232px] md:h-[232px]`, title `text-4xl md:text-[clamp(40px,5vw,72px)]`.
  - [x] Actions: "Sync now" calls `useSyncStream().startStream()` (matches `AppShell.tsx:322–331` behavior — show `animate-spin` on the icon when `isStreaming`). "Open in Spotify" opens `https://open.spotify.com/playlist/${dynamicPlaylistId}` in a new tab via `<a target="_blank" rel="noreferrer">`. When `dynamicPlaylistId == null`, render the button as visually disabled (`opacity-50 pointer-events-none`) with a `title="Playlist not created yet"` attribute.

- [x] **Task 7: Build `RecentlyAddedTable`** (AC: #7, #8, #9, #10, #11, #12, #13, #19)
  - [x] Create `frontend/src/features/recently-added/RecentlyAddedTable.tsx`. Props: `{ tracks, isLoading, error }`.
  - [x] Render `<TrackListHeader />` then map `tracks` to `<TrackRow track={adapt(t)} index={i} ... />`. Adapter:
    ```ts
    function adapt(t: RecentlyAddedTrack): Track {
      const totalSec = Math.round(t.duration_ms / 1000)
      const m = Math.floor(totalSec / 60)
      const s = String(totalSec % 60).padStart(2, '0')
      return {
        id: t.spotify_id,
        title: t.title,
        artist: t.artists.join(', '),
        album: t.album,
        artUrl: t.image_url ?? '',  // empty string falls back to alt="" + missing image OK
        durationLabel: `${m}:${s}`,
        addedAgo: formatRelative(t.added_at),
        addedAbs: formatAbsoluteDate(t.added_at),
        explicit: t.explicit,
        hasVideo: t.has_video,
        isNew: false,
        isActive: false,
      }
    }
    ```
  - [x] Pass `onOpenInSpotify={(id) => window.open(`https://open.spotify.com/track/${id}`, '_blank', 'noreferrer')}` and `onHide={() => { /* TODO(story-8.4): wire to POST /api/v1/blacklist */ }}` to each `TrackRow`.
  - [x] **Skeleton state** (`isLoading && tracks.length === 0`): render `<TrackListHeader />` + 8 skeleton rows. Each skeleton row uses the same `cols` grid utility from `TrackRow.tsx` (export it from `TrackRow.tsx` or duplicate the string — duplicating is fine; the snippet already inlines it).
  - [x] **Empty state** (`!isLoading && tracks.length === 0 && !error`): centered block with `Sparkles` (28px accent) + H3 "No tracks yet" + muted paragraph, 60px vertical padding.
  - [x] **Error state** (`error`): centered block with red dot + "Couldn't load Recently Added" + `error.message` (truncate to 400 chars) + outline "Retry" button calling `refetch()`. Pass `refetch` in as a prop so the table doesn't own the query.
  - [x] **Responsive cells** (AC #19): wrap album and date-added cells (header AND rows) in `<div className="hidden sm:block">` so both collapse together. Test by resizing to ~480px.

- [x] **Task 8: Compose `RecentlyAddedPage.tsx`** (AC: #1, #4, #14, #16, #20)
  - [x] Replace the placeholder body of [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx) with the composition:
    ```tsx
    const tracks = useRecentlyAdded()
    const auth = useAuthStatus()
    const config = useConfig()
    const sync = useSyncStatus()
    const playlists = usePlaylists()
    // Compose hero props from all hooks, with placeholder fallbacks per AC #4.
    return (
      <>
        <RecentlyAddedHero ... />
        <div className="mt-3">
          <RecentlyAddedTable
            tracks={tracks.data ?? []}
            isLoading={tracks.isPending}
            error={tracks.error}
            refetch={tracks.refetch}
          />
        </div>
      </>
    )
    ```
  - [x] Do NOT block the whole page on `tracks.isPending` — the hero already has its own skeleton variant via prop `isLoading`. This lets the hero render its placeholder while the table fetches.

- [x] **Task 9: Build + smoke test** (AC: #15, #20)
  - [x] `docker exec playlist_spotify-frontend-1 npm run build` — expect 0 errors, 0 new warnings.
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` — expect all tests passing including the 2 new `test_story_8_3.py` cases.
  - [x] `docker-compose up -d`, navigate to `http://localhost:5173/recently-added`:
    - Empty state (no `dynamic_playlist_id` yet OR `[]` response) — verify hero placeholders + empty block render.
    - Populated state (trigger a sync first, then refresh) — verify hero shows real cover + counts + duration, table renders all rows, row hover highlights, header sticks while scrolling.
    - Resize to ~480px — verify album/date cells hide and layout stays aligned.
    - `MoreHorizontal` menu — verify it opens, "Hide from Recent Adds" is a no-op (do not click and break things), "Open in Spotify" opens the correct track URL in a new tab.
    - Measure paint time via `performance.now()` deltas in the console — record the result in Dev Notes (AC #15 budget: <1s for 200 tracks).
  - [x] Sanity check tooltip on "Date added" shows the absolute date.

- [x] **Task 10: Postman sync** (AC: #21)
  - [x] Fetch the collection from `https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`.
  - [x] Update the `Get Config` request's example response body under the "Config" folder to include `"dynamic_playlist_id": "37i9dQZ..."` (use a realistic Spotify-style ID) AND add a second example (or update the description) noting the null default.
  - [x] PUT the updated collection. Re-GET and verify the example reflects the new field.

## Dev Notes

### Architecture & Conventions

- **Frontend-first story with one tiny backend addition** (the `dynamic_playlist_id` field on `ConfigRead`). The bulk of the work is in `frontend/src/features/recently-added/` + `pages/RecentlyAddedPage.tsx` + `components/TrackRow.tsx`.
- **The UX prototype is the visual source of truth** ([`ux-design/snippets/TrackRow.tsx`](../planning-artifacts/ux-design/snippets/TrackRow.tsx) + `ux-design/README.md` section "3 · Recently Added route"). Copy the snippet verbatim into `components/TrackRow.tsx` — that's the design contract. [Source: ux-design/README.md "Fidelity" + Story-8.3 epic body]
- **No virtualization, no IntersectionObserver, no memoization in this story** — 200 rows is well within the React DOM budget, and Story 8.6 owns performance polish. [Source: epics.md#Story-8.6 scope split]
- **No blacklist mutation** — Story 8.4 wires "Hide from Recent Adds" to `POST /api/v1/blacklist` with optimistic update. This story renders the menu item but the handler is a stub. [Source: epics.md#Story-8.4 + Story-8.2 Dev Notes "blacklist filter is 8.5's job"]
- **TanStack Query v5 naming** — `isPending`, not `isLoading`. The project rule (CLAUDE.md#Frontend) is non-negotiable. [Source: CLAUDE.md#Frontend]
- **All fetches via `lib/api.ts`** — no inline `fetch()` calls in components. [Source: CLAUDE.md#Frontend]
- **Component split**: `features/recently-added/*.tsx` for page-specific composites, `components/TrackRow.tsx` for the generic row (could be reused for future track views), `hooks/useRecentlyAdded.ts` for the query, `lib/relativeTime.ts` for the shared formatter. [Source: existing `features/playlists/` precedent]

### Source Tree — Files to Touch

- ✏️ [`backend/routers/config.py`](../../backend/routers/config.py) — add `dynamic_playlist_id` to `ConfigRead` (Pydantic) and populate it in `get_config` / `patch_config`.
- 🆕 [`backend/tests/test_story_8_3.py`](../../backend/tests/test_story_8_3.py) — 2 tests for the config field change.
- ✏️ [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts) — add `dynamic_playlist_id` to `Config`; add `RecentlyAddedTrack` interface.
- 🆕 [`frontend/src/hooks/useRecentlyAdded.ts`](../../frontend/src/hooks/useRecentlyAdded.ts) — new TanStack Query hook.
- 🆕 [`frontend/src/lib/relativeTime.ts`](../../frontend/src/lib/relativeTime.ts) — `formatRelative` + `formatAbsoluteDate`.
- ✏️ [`frontend/src/components/layout/AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx) — import `formatRelative` from `@/lib/relativeTime` instead of defining it locally. Remove the local definition.
- 🆕 [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx) — copy verbatim from the design snippet.
- 🆕 [`frontend/src/components/ui/skeleton.tsx`](../../frontend/src/components/ui/skeleton.tsx) — generated by `npx shadcn@latest add skeleton`. **Do not hand-write.**
- 🆕 [`frontend/src/features/recently-added/RecentlyAddedHero.tsx`](../../frontend/src/features/recently-added/RecentlyAddedHero.tsx)
- 🆕 [`frontend/src/features/recently-added/RecentlyAddedTable.tsx`](../../frontend/src/features/recently-added/RecentlyAddedTable.tsx)
- ✏️ [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx) — full rewrite (the file currently has a "Coming in Epic 8" placeholder).
- 🔒 [`frontend/src/App.tsx`](../../frontend/src/App.tsx) — **do not touch**. Route is already registered.
- 🔒 [`backend/services/spotify.py`](../../backend/services/spotify.py), [`backend/routers/recently_added.py`](../../backend/routers/recently_added.py), [`backend/routers/blacklist.py`](../../backend/routers/blacklist.py) — **do not touch**. Story 8.2 shipped the backend; Story 8.4/8.5 own the blacklist integration.
- 🔒 [`backend/models/`](../../backend/models/) — **no schema change**.

### Code Sketch — Page composition

```tsx
// frontend/src/pages/RecentlyAddedPage.tsx
import { useRecentlyAdded } from '@/hooks/useRecentlyAdded'
import { useAuthStatus } from '@/hooks/useAuthStatus'
import { useConfig } from '@/hooks/useConfig'
import { useSyncStatus } from '@/hooks/useSyncStatus'
import { usePlaylists } from '@/hooks/usePlaylists'
import { formatRelative } from '@/lib/relativeTime'
import RecentlyAddedHero from '@/features/recently-added/RecentlyAddedHero'
import RecentlyAddedTable from '@/features/recently-added/RecentlyAddedTable'

export default function RecentlyAddedPage() {
  const tracks = useRecentlyAdded()
  const auth = useAuthStatus()
  const config = useConfig()
  const sync = useSyncStatus()
  const playlists = usePlaylists()

  const sourceCount = playlists.data?.filter((p) => p.is_included).length
  const lastSyncRelative = sync.data ? formatRelative(sync.data.timestamp) : null

  return (
    <>
      <RecentlyAddedHero
        tracks={tracks.data ?? []}
        isLoading={tracks.isPending}
        email={auth.data?.spotify_user_id}
        playlistSize={config.data?.playlist_size}
        sourceCount={sourceCount}
        lastSyncRelative={lastSyncRelative}
        dynamicPlaylistId={config.data?.dynamic_playlist_id ?? null}
      />
      <div className="mt-3">
        <RecentlyAddedTable
          tracks={tracks.data ?? []}
          isLoading={tracks.isPending}
          error={tracks.error}
          refetch={tracks.refetch}
        />
      </div>
    </>
  )
}
```

### Code Sketch — Hero duration formatter

```ts
function formatTotalDuration(tracks: { duration_ms: number }[]): string {
  const totalMin = Math.round(tracks.reduce((s, t) => s + t.duration_ms, 0) / 60000)
  if (totalMin < 60) return `about ${totalMin}m`
  const h = Math.floor(totalMin / 60)
  const m = totalMin % 60
  return m === 0 ? `about ${h}h` : `about ${h}h ${m}m`
}
```

### Testing Standards

- **Backend tests**: pytest in the container, same fixture pattern as [`test_story_7_1.py`](../../backend/tests/test_story_7_1.py) / [`test_story_8_2.py`](../../backend/tests/test_story_8_2.py). Only 2 tests in this story — the field exposure and the null default. [Source: CLAUDE.md#Tests]
- **Frontend**: no automated tests required (project does not have a frontend test harness yet; per CLAUDE.md the assurance is `npm run build` + manual smoke). Verify behavior by viewing the page in the browser at `http://localhost:5173/recently-added` against `docker-compose up`.
- **No real Spotify calls in any test** — backend mocks the service per the Story 8.2 pattern.
- **TypeScript strict** — the build will fail on any `any` or missing prop. Resolve at build time, not at runtime.

### Previous Story Intelligence

- **Story 8.2 (Recently Added API)** — just shipped `GET /api/v1/recently-added` returning the 9-field snake_case array. This story consumes it directly. The 9 fields map 1:1 to the `RecentlyAddedTrack` interface in `types/index.ts`. The empty-state contracts (no playlist, deleted playlist) both return `[]` with 200 — the page just shows the empty state. [Source: Story-8.2 AC #1, #2, #3]
- **Story 8.1 (Track Blacklist Model & API)** — `POST /api/v1/blacklist` is live but this story does NOT call it. The dropdown item is rendered (per the design snippet) but the click handler is a stub for Story 8.4.
- **Story 6.x / 7.x (Spotify Desktop UI Foundation + Playlist Grid)** — established the `AppShell` shell with sidebar/topbar, dark theme tokens (`--bg-app`, `--bg-elevated`, `--accent-color`, etc.), the `features/<domain>/` folder pattern, and the `formatRelative` helper now being extracted. Reuse, don't duplicate. [Source: frontend/src/components/layout/AppShell.tsx + frontend/src/features/playlists/* + frontend/src/index.css]
- **Story 6.3 (Routes registered)** — `/recently-added` is already wired in `App.tsx` and the sidebar; do not touch the router.
- **Story 069a96c (delta sync)** — the dynamic playlist Spotify ID lives in `config.dynamic_playlist_id` and is populated by the sync engine after the first successful sync. Treat `null` as a normal first-run state in the UI (no error toast).

### Git Intelligence

- Recent commits (newest first):
  - `76facf6 feat: Epics 6 & 7 — UI refonte + playlist grid avec hide/unhide + dropdown style Spotify` — established `AppShell`, `PlaylistCard`, `HiddenPlaylistsAccordion` patterns. The hero gradient + sticky topbar idioms are reusable here.
  - `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — adds `config.dynamic_playlist_id` population.
  - `ccbbf60 feat: Stories 2-3 → 5-3 — Auth, Playlists, Sync, Scheduler & Observability` — bulk landing of foundation epics including `useSyncStatus`, `useAuthStatus`, `useConfig` hooks reused on this page.
- Working tree currently has Story 8.2 changes uncommitted (`backend/main.py`, `backend/services/spotify.py`, `backend/routers/recently_added.py`, `backend/tests/test_story_8_2.py`) — those land first in their own commit. Story 8.3 commits on top.
- No prior commit touches `features/recently-added/` — clean slate for the new folder.

### Latest Tech Information

- **TanStack Query v5** — `isPending` (not `isLoading`), `query.refetch()`, `error` is `unknown` (cast to `Error` for `.message`). [Source: TanStack Query v5 migration notes + CLAUDE.md#Frontend]
- **`color-mix(in oklab, ...)`** — supported in all modern browsers (Chrome 111+, Firefox 113+, Safari 16.4+) — safe for a desktop-first Spotify-style app. No fallback needed. [Source: caniuse.com `css-color-mix`]
- **`backdrop-filter: blur()`** — already used in `AppShell.tsx`; works in target browsers.
- **`Intl.RelativeTimeFormat` + `Intl.DateTimeFormat`** — already used in `AppShell.tsx`; reuse pattern, no new dependency.
- **lucide-react** — already installed (`Clock`, `Play`, `RotateCw`, `ExternalLink`, `EyeOff`, `MoreHorizontal`, `Sparkles` all available).

### Project Structure Notes

- ✅ Aligns with the established `frontend/src/features/<domain>/` pattern (see `features/playlists/`, `features/sync/`, `features/auth/`, `features/config/`).
- ✅ `frontend/src/components/TrackRow.tsx` is the right home for the generic row per the snippet's own header comment.
- ✅ Shadcn primitives reused: `Tooltip`, `DropdownMenu`, `Button`, `Skeleton` (added in Task 5). No custom UI primitive needed.
- ⚠️ **Do NOT** add `react-virtual` or any virtualization library — Story 8.6 will evaluate that if 200 rows actually drop frames.
- ⚠️ **Do NOT** lazy-load thumbnail images via `IntersectionObserver` — Story 8.6 owns that work. `<img loading="lazy">` is fine (zero-cost, native).
- ⚠️ **Do NOT** add a new Tailwind plugin or extend `tailwind.config.ts` — every utility used here is in the existing config.
- ⚠️ **Do NOT** introduce a separate "Recently Added cover" backend field — the design uses the first track's `image_url` (per AC #3) and the playlist's own cover is not part of the existing API.
- ⚠️ **Do NOT** mutate `config.dynamic_playlist_id` from the frontend — the backend owns it (sync engine only).

### Project Context Reference

See [`CLAUDE.md`](../../CLAUDE.md) for project-wide development rules. Most relevant sections for this story:
- "Frontend" — TanStack Query v5 `isPending`, fetches via `lib/api.ts`, alias `@/`, shadcn via CLI only.
- "Backend" — snake_case JSON, array-direct responses, business logic in `services/`.
- "Tests" — pytest via `docker exec`, fixture pattern from `test_story_2_4.py` / `test_story_3_1.py`.
- "Postman" — non-negotiable update when API surface changes (here: the new `dynamic_playlist_id` field on `GET /config`).

User-memory rules in effect for this story (will silently shape decisions):
- [`feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md) — `Skeleton` MUST be added via `npx shadcn@latest add`, not hand-written.
- [`feedback_node_version`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_node_version.md) — frontend container already uses Node 22; no host-side npm work required.
- [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md) — Postman collection must be updated for the `dynamic_playlist_id` example change.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-8.3] — primary ACs (lines 1247–1311).
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-8 + FR31, FR32, NFR14, AR12] — overall feature & performance targets.
- [Source: _bmad-output/planning-artifacts/ux-design/README.md "3 · Recently Added route"] — hero + sticky header + TrackRow spec (lines 118–164).
- [Source: _bmad-output/planning-artifacts/ux-design/snippets/TrackRow.tsx] — canonical `TrackRow` + `TrackListHeader` component to drop into `components/`.
- [Source: _bmad-output/implementation-artifacts/8-2-recently-added-api.md] — backend contract (`RecentlyAddedTrack` shape, error mapping).
- [Source: frontend/src/components/layout/AppShell.tsx:39–49] — `formatRelative` to extract; topbar "Sync now" pattern (lines 322–331) to reuse.
- [Source: frontend/src/hooks/usePlaylists.ts] — TanStack Query v5 hook idiom; optimistic update pattern (for future 8.4 reference).
- [Source: frontend/src/index.css] — CSS tokens confirmed present (`--bg-app`, `--bg-elevated`, `--bg-row-hover`, `--accent-color`, `--border-soft`, `--text-muted`, etc.).
- [Source: backend/routers/config.py:24–46] — where to extend `ConfigRead`.
- [Source: backend/tests/test_story_7_1.py, backend/tests/test_story_8_2.py] — fixture pattern.
- [Source: CLAUDE.md#Frontend, #Backend, #Tests, #Postman] — project conventions.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

- Backend tests: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → **108 passed** (106 baseline + 2 nouveaux `test_story_8_3.py`).
- Frontend build: `docker exec playlist_spotify-frontend-1 npm run build` → **OK, 0 erreur TS, 0 nouveau warning ESLint** (warning chunk-size 500kB pré-existant uniquement).
- Paint time pour 200 tracks : non mesuré dans cette session (pas de DB amorcée avec 200 tracks ici) ; le rendu n'utilise ni virtualization ni IntersectionObserver, conformément au scope (Story 8.6 owns performance polish). Si dégradation observée en QA, journaliser dans Story 8.6.

### Completion Notes List

- **Task 1 (backend)** : ajout du champ `dynamic_playlist_id: Optional[str] = None` sur `ConfigRead` ; les trois handlers (`GET/PATCH/PUT /config`) propagent désormais `config.dynamic_playlist_id`. Branche `setup_required` renvoie `None`. Aucune migration de modèle (la colonne SQLModel existait déjà). Tests : `test_config_exposes_dynamic_playlist_id` + `test_config_dynamic_playlist_id_defaults_null`.
- **Task 2 (types & hook)** : ajout de `RecentlyAddedTrack` (9 champs snake_case exacts de Story 8.2) et de `dynamic_playlist_id: string | null` sur `Config`. Hook `useRecentlyAdded()` créé (`queryKey: ['recently-added']`, `staleTime: 30_000`).
- **Task 3 (helper)** : `formatRelative` extrait de `AppShell.tsx:39-49` vers `lib/relativeTime.ts` + nouveau `formatAbsoluteDate(iso) → "May 18, 2026"` via `Intl.DateTimeFormat('en', { dateStyle: 'medium' })`. `AppShell.tsx` importe désormais le helper partagé.
- **Task 4 (TrackRow)** : composant copié verbatim depuis `ux-design/snippets/TrackRow.tsx`. Adaptations minimales : (a) `cols` exporté sous le nom `trackCols` pour permettre aux skeleton rows d'utiliser la même grille ; (b) ajout d'un fallback `<div bg-white/5>` si `artUrl===''` au lieu d'une image cassée ; (c) `loading="lazy"` natif sur `<img>` ; (d) cellules "Album" et "Date added" wrappées en `hidden sm:block` pour la responsivité (AC #19) — même utilitaire sur header et rows pour garder la grille alignée ; (e) commentaire `TODO(story-8.4)` au-dessus du `DropdownMenuItem` "Hide from Recent Adds".
- **Task 5 (Skeleton)** : `frontend/src/components/ui/skeleton.tsx` généré via `docker exec playlist_spotify-frontend-1 npx shadcn@latest add skeleton` (respecte memory `feedback_shadcn_cli`).
- **Task 6 (Hero)** : composant full-bleed (`-mx-4 md:-mx-8 -mt-2`), gradient `linear-gradient(180deg, color-mix(in oklab, var(--accent-color) 40%, #1a1a1a) 0%, var(--bg-elevated) 100%)`, cover 232×232 desktop / 160×160 mobile, fallback CSS gradient `linear-gradient(135deg, var(--accent-color), #22d3ee)` si `tracks[0]?.image_url` est null. Title `clamp(40px,5vw,72px)`. Sub-line formate `{email}` (`auth.data?.spotify_user_id ?? "You"`), `{n}/{N}`, `formatTotalDuration()` (h+m), `{relative}` réutilisé via le helper partagé, `{k}` = nombre de playlists incluses. Tous les `null/loading` rendent `…` placeholders. Actions row : "Sync now" appelle `useSyncStream().startStream()` (animate-spin sur l'icône), "Open in Spotify" → `https://open.spotify.com/playlist/{dynamicPlaylistId}` (target=_blank, rel=noreferrer ; visuellement disabled + `title="Playlist not created yet"` quand null), `MoreHorizontal` placeholder.
- **Task 7 (Table)** : 4 branches — `error` (red dot + Retry button calling `refetch()`, message tronqué 400 chars), `isLoading && tracks.length === 0` (8 `SkeletonRow` réutilisant `trackCols`), `tracks.length === 0` (Sparkles + H3 + paragraphe, 60px de padding), default (rendu des rows). Adapter `adapt(t)` calcule `m:ss`, `formatRelative`, `formatAbsoluteDate`, joint `artists` en string. Handler `onOpenInSpotify` → `window.open('https://open.spotify.com/track/{id}', '_blank', 'noreferrer')`, `onHide` = no-op stub avec `TODO(story-8.4)`.
- **Task 8 (Page)** : `RecentlyAddedPage.tsx` réécrit ; compose hero + table à partir des hooks (`useRecentlyAdded`, `useAuthStatus`, `useConfig`, `useSyncStatus`, `usePlaylists`). Hero ne bloque jamais sur `tracks.isPending` — il dégrade ses propres placeholders pendant la fetch.
- **Task 9 (CI)** : `npm run build` → 0 erreur TS ; `pytest tests/ -v` → **108 passed** (baseline 106 + 2 nouveaux). Aucune régression.
- **Task 10 (Postman)** : collection `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` mise à jour via PUT — description du `Get Config` enrichie, 2 example responses ajoutées (`200 OK — configured` avec `dynamic_playlist_id="37i9dQZF1DXcBWIGoYBM5M"` et `200 OK — fresh install` avec `dynamic_playlist_id=null`). Vérifié via GET après PUT.

### File List

**Backend**
- ✏️ `backend/routers/config.py` — `ConfigRead.dynamic_playlist_id`, propagation dans `get_config`/`patch_config`/`update_config`.
- 🆕 `backend/tests/test_story_8_3.py` — 2 tests.

**Frontend**
- ✏️ `frontend/src/types/index.ts` — `Config.dynamic_playlist_id` + nouvelle interface `RecentlyAddedTrack`.
- 🆕 `frontend/src/hooks/useRecentlyAdded.ts`.
- 🆕 `frontend/src/lib/relativeTime.ts` — `formatRelative` + `formatAbsoluteDate`.
- ✏️ `frontend/src/components/layout/AppShell.tsx` — import du helper partagé, suppression de la définition locale.
- 🆕 `frontend/src/components/TrackRow.tsx` — `Track`, `TrackRow`, `TrackListHeader`, `trackCols`.
- 🆕 `frontend/src/components/ui/skeleton.tsx` — généré par shadcn CLI.
- 🆕 `frontend/src/features/recently-added/RecentlyAddedHero.tsx`.
- 🆕 `frontend/src/features/recently-added/RecentlyAddedTable.tsx`.
- ✏️ `frontend/src/pages/RecentlyAddedPage.tsx` — réécriture complète.

**Sprint**
- ✏️ `_bmad-output/implementation-artifacts/sprint-status.yaml` — 8-3 → `review`.

**Postman**
- ✏️ Collection `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` → `Get Config` description + 2 example responses.

### Change Log

- 2026-05-21: Story 8.3 — implementation complete (Tasks 1–10). Backend `ConfigRead` étendu, page Recently Added entièrement câblée (hero + table), tests : 108 passing, build TypeScript clean, Postman synchronisé.
