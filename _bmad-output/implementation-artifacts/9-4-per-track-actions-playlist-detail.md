# Story 9.4: Per-Track Actions on Playlist Detail

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want the `⋯` overflow menu on each row of the Playlist Detail page to expose "Hide from Recent Adds" (blacklist by `spotify_id`) and "Open in Spotify" — same as on Recently Added,
so that I can blacklist a track from any context (playlist drill-down, not only Recently Added) with optimistic UI and a confirmation toast.

## Acceptance Criteria

1. **Given** the Playlist Detail page [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx), **When** rendered, **Then** the `<TrackListTable>` receives a non-undefined `onBlacklist` prop wired to the existing `useBlacklistTrack` mutation (no new hook). Concretely: `const blacklist = useBlacklistTrack()` at the top of the component, and the table is rendered with `onBlacklist={(id) => blacklist.mutate({ spotify_id: id }, { onSuccess: …, onError: … })}`. The "Open in Spotify" track action keeps the default behavior from [`TrackListTable.tsx:26-27`](../../frontend/src/features/tracks/TrackListTable.tsx) (opens `https://open.spotify.com/track/{id}` in a new tab) — do NOT pass `onOpenInSpotify`. [Source: epics.md#Story-9.4 hint #1 + 9-2-shared-track-list-components.md#AC8 (onBlacklist is the gate) + 9-3-playlist-detail-page-navigation.md#AC2 (onBlacklist deliberately omitted in 9.3 → enabled now)]

2. **Given** the existing [`frontend/src/hooks/useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts) currently only mutates the `['recently-added']` query cache, **When** Story 9.4 ships, **Then** `useBlacklistTrack`'s `onMutate` and `onError` are extended to **also** optimistically filter every `['playlist-tracks', <spotifyId>]` query currently in the cache (the Playlist Detail page uses this query key per [`hooks/usePlaylistTracks.ts:7`](../../frontend/src/hooks/usePlaylistTracks.ts)). Implementation pattern:
   - In `onMutate`, after the existing `['recently-added']` cancel + snapshot + filter:
     - `await queryClient.cancelQueries({ queryKey: ['playlist-tracks'] })`
     - `const previousPlaylistTracks = queryClient.getQueriesData<RecentlyAddedTrack[]>({ queryKey: ['playlist-tracks'] })` → array of `[queryKey, data]` tuples for every cached playlist.
     - For each tuple, `setQueryData(key, data.filter((t) => t.spotify_id !== spotify_id))`.
   - In `onError`, restore each `previousPlaylistTracks` tuple via `setQueryData(key, data)`.
   - The mutation's `context` shape is widened to `{ previous: RecentlyAddedTrack[] | undefined; previousPlaylistTracks: Array<[QueryKey, RecentlyAddedTrack[] | undefined]> }`.
   - Do **NOT** add `onSettled` to invalidate `['playlist-tracks']` — the row stays filtered until the next sync (mirroring `['recently-added']` post-9.x behavior; the 8.4 mutation also does not invalidate `['recently-added']` per [`useBlacklist.ts:31-35`](../../frontend/src/hooks/useBlacklist.ts), confirmed by reading the file: no `onSettled`).
   [Source: epics.md#Story-9.4 hint #1 "blacklist is by spotify_id, source-agnostic" + frontend/src/hooks/useBlacklist.ts current shape + TanStack Query v5 `getQueriesData` / `setQueryData` API + frontend/src/hooks/usePlaylistTracks.ts queryKey shape]

3. **Given** the user clicks "Hide from Recent Adds" on a track row of the Playlist Detail page, **When** the click fires, **Then**:
   - The row is removed from the current playlist's track table **immediately** (optimistic — driven by AC #2 cache update of `['playlist-tracks', spotifyId]`).
   - If the **same track** is also present in the cached `['recently-added']` list, it is removed from there too (driven by the existing AC #2 `['recently-added']` filter — this is the existing 8.4 behavior, preserved).
   - The `POST /api/v1/blacklist` request is sent with body `{"spotify_id": "<id>"}` via `api.post` (same as 8.4).
   - On success: `toast.success("Removed from Recent Adds", { description: "Will be removed from your Spotify Recent Adds playlist on the next sync." })`.
   - On error: the optimistic removal is reverted (per AC #2 `onError` restoration) and `toast.error("Couldn't hide track", { description: <truncated err.message, max 200 chars> })` fires.
   [Source: epics.md#Story-9.4 hint #2 "Optimistic UI: remove row from local table state, restore on error (same pattern as Story 8.4)" + hint #3 confirmation toast copy + 8-4-per-track-blacklist-action.md#AC4 #AC5 (toast pattern)]

4. **Given** the toast copy, **When** rendered, **Then** the description string is **exactly** `Will be removed from your Spotify Recent Adds playlist on the next sync.` — note the explicit mention of "Recent Adds playlist" (the user just blacklisted from a *different* playlist, so the copy needs to be unambiguous about *where* the effect manifests). This differs from Story 8.4's copy ("Will be removed from your Spotify playlist on the next sync.") which was contextually obvious. Update **only** the call site inside `PlaylistDetailPage.tsx`; do NOT modify the Recently Added page's toast copy (regression risk). [Source: epics.md#Story-9.4 hint #3 explicit copy + UX consistency with 8.4 site-specific phrasing]

5. **Given** the row's `⋯` menu opens, **When** the user inspects it, **Then** the menu shows **exactly** the same two items as Recently Added (rendered by [`TrackRow.tsx:144-151`](../../frontend/src/components/TrackRow.tsx)):
   - `Hide from Recent Adds` (with `EyeOff` icon — the label intentionally says "Recent Adds" even when triggered from a playlist; the action effect *is* the dynamic Recent Adds playlist suppression, not removal from the source playlist).
   - `Open in Spotify` (with `ExternalLink` icon).
   The menu structure is **not** modified in this story. **Do NOT** edit [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx). The label rephrasing ("Hide from this playlist" or similar) is **out of scope** — global behavior, global label. [Source: epics.md#Story-9.4 AC "same as Recently Added: 'Hide from Recent Adds' + 'Open in Spotify'" + TrackRow.tsx current menu items + project anti-scope-creep stance]

6. **Given** the existing [`pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx) `handleBlacklist` already wires `useBlacklistTrack` with success/error toasts (lines 103-118), **When** Story 9.4 ships, **Then** the new wiring in `PlaylistDetailPage.tsx` mirrors that pattern verbatim (same callback shape, same `err.message.slice(0, 200)` cap), with the only diff being the description string (AC #4). **Do NOT** extract a shared `handleBlacklistToast` helper in this story — two call sites with a one-string diff is acceptable. YAGNI; revisit only if a third site appears. [Source: RecentlyAddedPage.tsx:103-118 + project YAGNI stance (matches 9.3 AC #4 rationale for `formatTotalDuration` duplication)]

7. **Given** the user blacklists a track from the Playlist Detail page, **When** the row disappears, **Then** the `usePlaylists()` cache's `track_count` for that playlist is **not** decremented in this story. The hero's sub-line (`{n} tracks`) computes `n` from `list.length` (i.e. the live filtered track array, per [`PlaylistDetailPage.tsx:47`](../../frontend/src/pages/PlaylistDetailPage.tsx)), so the displayed count **does** drop by one automatically. The metadata `playlist.track_count` from `usePlaylists()` is only used by other surfaces (Dashboard card subtitle), which will reconcile on the next sync's playlist refresh. Do NOT mutate `usePlaylists()` cache here. [Source: PlaylistDetailPage.tsx:47 (sub-line derives `n` from live `list`) + epic 9.4 scope (UI action only, no metadata sync)]

8. **Given** the user opens `/playlists/liked_songs` and blacklists a track, **When** the action fires, **Then** it behaves identically to any other playlist:
   - The row is removed from `['playlist-tracks', 'liked_songs']` (the synthetic Liked Songs playlist's query — per Story 9.1's `liked_songs` sentinel handling in `services/spotify.py`).
   - The POST hits `/api/v1/blacklist` with the same `spotify_id`.
   - The toast appears.
   - The track will be filtered from the next dynamic Recent Adds harvest by Story 8.5's sync engine. The Liked Songs library itself (Spotify-side) is **not** touched — blacklist only affects the dynamic playlist. [Source: epics.md#Story-9.4 + 9-1-playlist-tracks-api.md#AC2 (liked_songs handling) + 8-5-sync-integration-blacklist-filter.md (blacklist effect scope)]

9. **Given** keyboard navigation, **When** the user tabs to a track row's `⋯` trigger (visible via `focus:opacity-100 focus-visible:opacity-100 data-[state=open]:opacity-100` already on [`TrackRow.tsx:137-140`](../../frontend/src/components/TrackRow.tsx) from Story 8.4) and presses Enter/Space to open the menu, then ArrowDown to highlight "Hide from Recent Adds" and Enter to fire, **Then** the blacklist action triggers identically to a mouse click. No changes needed — the `DropdownMenu` keyboard semantics are inherited from Radix. [Source: Story-8.4 AC #6 (already-shipped focus styling) + Radix DropdownMenu native a11y]

10. **Given** the build verification, **When** the dev runs `docker exec playlist_spotify-frontend-1 npm run build`, **Then** the build completes with **zero TypeScript errors** and **zero new ESLint warnings**. Specifically:
    - The new `context` shape in `useBlacklistTrack` is typed (no `any`).
    - `getQueriesData` returns `Array<[QueryKey, T | undefined]>` — type both the tuple array and the restore loop.
    - `QueryKey` is imported as a **type-only** import from `@tanstack/react-query` (project convention).
    - No unused imports.
    [Source: CLAUDE.md (clean builds) + tsconfig strict + 9-3 AC #11 precedent]

11. **Given** the backend test suite, **When** the dev runs `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`, **Then** all tests still pass and the count stays **≥ 127** (current baseline per 9-3 final). This story is **frontend-only** — any backend file touched is a scope violation. [Source: CLAUDE.md#Tests + 9-3 baseline]

12. **Given** the running stack via `docker-compose up`, **When** the dev manually smokes the new flow at `http://127.0.0.1:5173/`, **Then** **all** of the following must hold:
    - Navigate to `/playlists/<some-playlist-id>` (click a card on Dashboard).
    - Hover a track row → `⋯` trigger fades in.
    - Click `⋯` → menu opens, both items visible.
    - Click "Hide from Recent Adds":
      - Row disappears **instantly** (optimistic).
      - Success toast `Removed from Recent Adds` with description `Will be removed from your Spotify Recent Adds playlist on the next sync.` appears.
      - Network panel: one `POST /api/v1/blacklist` with body `{"spotify_id":"<id>"}` returning 201 (or 200 if duplicate).
    - Open Recently Added in another tab/panel before clicking → after clicking on the playlist detail, the same `spotify_id` row (if present) also disappears from Recently Added's table (cross-cache effect).
    - Click "Open in Spotify" in a row's menu → opens `https://open.spotify.com/track/{id}` in new tab.
    - Error path: `docker-compose stop backend`, click "Hide from Recent Adds" again → row vanishes then re-appears; error toast `Couldn't hide track` with network error message. Restart backend.
    - Navigate to `/playlists/liked_songs`, hide a track → identical behavior; verify the row is removed from `['playlist-tracks','liked_songs']` cache only (and `['recently-added']` if the same track was there).
    - Keyboard path: focus a row, Tab to `⋯`, Enter, ArrowDown, Enter on "Hide from Recent Adds" → row vanishes, toast appears.

    Paste a one-line confirmation per bullet into the Completion Notes List. [Source: epics.md#Story-9.4 + 8-4-per-track-blacklist-action.md#Task-5 smoke pattern]

13. **Given** the Postman collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`), **When** Story 9.4 ships, **Then** **no Postman update is required**. The `POST /api/v1/blacklist` endpoint was already documented in Story 8.1's Postman push and verified in Story 8.4. Explicitly note "Postman: N/A (no API change)" in Completion Notes per memory rule [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md). [Source: memory `feedback_postman_sync` + CLAUDE.md#Postman + Story-8.1 + Story-8.4 AC #16 precedent]

14. **Given** `git status` after the story lands, **When** inspected, **Then** the change set is **exactly**:
    - ✏️ `frontend/src/hooks/useBlacklist.ts` (modified — extend `onMutate` / `onError` to also handle `['playlist-tracks', *]` caches; widen `context` type)
    - ✏️ `frontend/src/pages/PlaylistDetailPage.tsx` (modified — `useBlacklistTrack` call + `onBlacklist` prop + toast handler)
    - ✏️ `_bmad-output/implementation-artifacts/sprint-status.yaml` (story status transitions)
    - ✏️ `_bmad-output/implementation-artifacts/9-4-per-track-actions-playlist-detail.md` (this file — task checkboxes + Dev Agent Record)

    **No other files touched.** Zero backend changes. Zero edits to `features/tracks/TrackListHero.tsx`, `features/tracks/TrackListTable.tsx`, `components/TrackRow.tsx`, `hooks/usePlaylistTracks.ts`, `hooks/usePlaylists.ts`, `hooks/useRecentlyAdded.ts`, `types/index.ts`, `lib/api.ts`, `pages/RecentlyAddedPage.tsx`, or any other page/component. Paste `git status` output into Completion Notes. [Source: epics.md#Story-9.4 scope + project anti-scope-creep stance + 9-3 AC #15 precedent]

## Tasks / Subtasks

- [x] **Task 1: Extend `useBlacklistTrack` to invalidate `['playlist-tracks', *]` caches optimistically** (AC: #2)
  - [x] In [`frontend/src/hooks/useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts):
    - Import `type { QueryKey } from '@tanstack/react-query'` (extend the existing import).
    - Widen the `context` generic of `useMutation` to:
      ```ts
      {
        previous: RecentlyAddedTrack[] | undefined
        previousPlaylistTracks: Array<[QueryKey, RecentlyAddedTrack[] | undefined]>
      }
      ```
    - In `onMutate`, after the existing `['recently-added']` block:
      ```ts
      await queryClient.cancelQueries({ queryKey: ['playlist-tracks'] })
      const previousPlaylistTracks = queryClient.getQueriesData<RecentlyAddedTrack[]>({
        queryKey: ['playlist-tracks'],
      })
      previousPlaylistTracks.forEach(([key, data]) => {
        if (data) {
          queryClient.setQueryData<RecentlyAddedTrack[]>(
            key,
            data.filter((t) => t.spotify_id !== spotify_id),
          )
        }
      })
      return { previous, previousPlaylistTracks }
      ```
    - In `onError`, after the existing `['recently-added']` restore:
      ```ts
      if (context?.previousPlaylistTracks) {
        context.previousPlaylistTracks.forEach(([key, data]) => {
          queryClient.setQueryData(key, data)
        })
      }
      ```
    - Do **NOT** add `onSettled`. Do **NOT** invalidate `['playlist-tracks']` post-success — the row stays filtered until the next sync (matching the existing `['recently-added']` post-success behavior in this hook).
  - [x] Verify the hook's exported signature stays compatible with `pages/RecentlyAddedPage.tsx`'s call site (no breaking change — the mutation function signature is unchanged; only the internal `context` is widened).

- [x] **Task 2: Wire `useBlacklistTrack` into `PlaylistDetailPage`** (AC: #1, #3, #4, #6)
  - [x] In [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx):
    - Add imports: `import { toast } from 'sonner'` and `import { useBlacklistTrack } from '@/hooks/useBlacklist'`.
    - Inside the component, add `const blacklist = useBlacklistTrack()` near the other hooks (after `useAuthStatus()`).
    - Add a `handleBlacklist` function (mirror `RecentlyAddedPage.tsx:103-118` verbatim except for the description):
      ```ts
      const handleBlacklist = (id: string) => {
        blacklist.mutate(
          { spotify_id: id },
          {
            onSuccess: () =>
              toast.success('Removed from Recent Adds', {
                description:
                  'Will be removed from your Spotify Recent Adds playlist on the next sync.',
              }),
            onError: (err) =>
              toast.error("Couldn't hide track", {
                description: err.message.slice(0, 200),
              }),
          },
        )
      }
      ```
    - Pass `onBlacklist={handleBlacklist}` to the `<TrackListTable>` in the main render branch (the one with the track table — NOT the not-found branch, which has no table). Do NOT pass `onOpenInSpotify` (preserve the default).
  - [x] The not-found branch (AC #9 of 9.3) is untouched — no `TrackListTable` is rendered there.

- [x] **Task 3: Build verification** (AC: #10)
  - [x] `docker exec playlist_spotify-frontend-1 npm run build` → expect 0 TS errors, 0 new ESLint warnings. Paste tail of output into Completion Notes.

- [x] **Task 4: Backend safety net** (AC: #11)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → expect **≥ 127 passed**.

- [x] **Task 5: Browser smoke** (AC: #12)
  - [x] `docker-compose up -d` (if not running).
  - [x] Walk through every bullet in AC #12. Paste one-line confirmations into Completion Notes.

- [x] **Task 6: Final verification** (AC: #13, #14)
  - [x] `git status` → confirm only the 4 files in AC #14 are touched. Paste output into Completion Notes.
  - [x] Note "Postman: N/A (no API change)" in Completion Notes per AC #13.
  - [x] Move story to `review` in `sprint-status.yaml` (the dev workflow wrap-up handles this).

## Dev Notes

### Architecture & Conventions

- **Hook-level cross-cache optimism.** The blacklist mutation is global by design — a `spotify_id` is unique across every track surface (Recently Added, every playlist, Liked Songs). Centralizing the cross-cache optimistic update inside `useBlacklistTrack` (rather than in each call site) means future track-list surfaces (a "Hidden Tracks" admin page, a sync-conflict viewer, etc.) get the cache hygiene for free. This story is the first cross-cache consumer; the pattern is intentionally generalized via `getQueriesData({ queryKey: ['playlist-tracks'] })` — a hierarchical match that catches every `['playlist-tracks', <id>]` regardless of `<id>`.
- **No `onSettled` invalidate.** Story 8.4's `useBlacklist.ts` deliberately omits an `onSettled` invalidate (verified by re-reading the file — it has `onMutate` + `onError` only). The rationale is "the row stays gone until the next sync naturally refetches the surface" — and the same applies to playlist tracks. Adding an invalidate would cause the just-blacklisted row to flash back in (the backend `GET /playlists/{id}/tracks` returns *all* playlist tracks regardless of blacklist state — the blacklist filter is applied by the sync engine to the *dynamic* Recent Adds playlist, not to the source playlists per Story 8.5 scope). **Do not add `onSettled`.**
- **Label vs. action semantics.** The menu label is "Hide from Recent Adds" — this is correct even when triggered from a playlist context because the blacklist affects the dynamic Recent Adds playlist, not the source playlist where the user clicked. The toast description ("Will be removed from your Spotify Recent Adds playlist on the next sync.") is what disambiguates this for the user.
- **`getQueriesData` vs. `getQueryData`.** Use `getQueriesData` (plural — partial-key match) to capture all `['playlist-tracks', *]` entries; `getQueryData` requires an exact key. TanStack Query v5 returns tuples `Array<[QueryKey, T | undefined]>`.
- **`cancelQueries` with partial key.** `queryClient.cancelQueries({ queryKey: ['playlist-tracks'] })` cancels every in-flight query whose key starts with `['playlist-tracks']` — exactly what we want before snapshotting.

### Source Tree — Files to Touch

- ✏️ [`frontend/src/hooks/useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts) — widen `context`, extend `onMutate` / `onError` (~15 lines added).
- ✏️ [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx) — add hook call + `handleBlacklist` + `onBlacklist` prop (~20 lines).
- 🔒 [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx) — **do not touch**. Menu items + focus styling already correct from 8.4.
- 🔒 [`frontend/src/features/tracks/TrackListTable.tsx`](../../frontend/src/features/tracks/TrackListTable.tsx) — **do not touch**. Already exposes `onBlacklist?` via `onHide` wiring (per 9.2 AC #8).
- 🔒 [`frontend/src/hooks/usePlaylistTracks.ts`](../../frontend/src/hooks/usePlaylistTracks.ts) — **do not touch**. Read-only consumer.
- 🔒 [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx) — **do not touch**. The hook extension is backwards-compatible (signature unchanged, context-only widening — only the hook internals care about the new tuple).
- 🔒 [`backend/**`](../../backend/) — **do not touch** (AC #11).

### Code Sketches

**`useBlacklist.ts` (full file after change):**

```ts
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { QueryKey } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { RecentlyAddedTrack } from '@/types'

interface BlacklistResponse {
  spotify_id: string
  blacklisted_at: string
}

type Ctx = {
  previous: RecentlyAddedTrack[] | undefined
  previousPlaylistTracks: Array<[QueryKey, RecentlyAddedTrack[] | undefined]>
}

export function useBlacklistTrack() {
  const queryClient = useQueryClient()
  return useMutation<BlacklistResponse, Error, { spotify_id: string }, Ctx>({
    mutationFn: ({ spotify_id }) =>
      api.post<BlacklistResponse>('/blacklist', { spotify_id }),
    onMutate: async ({ spotify_id }) => {
      // Recently Added cache (existing 8.4 behavior)
      await queryClient.cancelQueries({ queryKey: ['recently-added'] })
      const previous = queryClient.getQueryData<RecentlyAddedTrack[]>([
        'recently-added',
      ])
      if (previous) {
        queryClient.setQueryData<RecentlyAddedTrack[]>(
          ['recently-added'],
          previous.filter((t) => t.spotify_id !== spotify_id),
        )
      }

      // Playlist-tracks caches (new in 9.4 — every cached playlist)
      await queryClient.cancelQueries({ queryKey: ['playlist-tracks'] })
      const previousPlaylistTracks = queryClient.getQueriesData<
        RecentlyAddedTrack[]
      >({ queryKey: ['playlist-tracks'] })
      previousPlaylistTracks.forEach(([key, data]) => {
        if (data) {
          queryClient.setQueryData<RecentlyAddedTrack[]>(
            key,
            data.filter((t) => t.spotify_id !== spotify_id),
          )
        }
      })

      return { previous, previousPlaylistTracks }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['recently-added'], context.previous)
      }
      if (context?.previousPlaylistTracks) {
        context.previousPlaylistTracks.forEach(([key, data]) => {
          queryClient.setQueryData(key, data)
        })
      }
    },
  })
}
```

**`PlaylistDetailPage.tsx` diff (additions, in render order):**

```tsx
// imports
import { toast } from 'sonner'
import { useBlacklistTrack } from '@/hooks/useBlacklist'

// inside component, near other hook calls
const blacklist = useBlacklistTrack()

// near other helpers in the body
const handleBlacklist = (id: string) => {
  blacklist.mutate(
    { spotify_id: id },
    {
      onSuccess: () =>
        toast.success('Removed from Recent Adds', {
          description:
            'Will be removed from your Spotify Recent Adds playlist on the next sync.',
        }),
      onError: (err) =>
        toast.error("Couldn't hide track", {
          description: err.message.slice(0, 200),
        }),
    },
  )
}

// in the main JSX
<TrackListTable
  tracks={list}
  isPending={tracks.isPending}
  error={tracks.error}
  refetch={tracks.refetch}
  onBlacklist={handleBlacklist}
  errorTitle="Couldn't load playlist"
  emptyTitle="This playlist has no tracks"
  emptyMessage="There's nothing in this playlist yet."
/>
```

### Testing Standards

- **No new unit tests added** — this story is wire-up + a cache-key broadening inside an existing hook. The hook's hot path (`['recently-added']` mutation) already covered behaviorally by 8.4's smoke; the new `['playlist-tracks']` path is covered by AC #12 smoke.
- **Type-check via `npm run build`** (AC #10) is the primary automated guardrail. The context widening will surface any type slip.
- **Manual browser smoke** (AC #12) is the primary behavioral guardrail — pay special attention to the cross-cache effect (blacklist on playlist also removes from Recently Added if present) and the error rollback (both caches restore).
- **Backend test suite** (AC #11) confirms no accidental backend edits.

### Previous Story Intelligence

- **Story 8.1 (Track Blacklist Model & API)** — shipped idempotent `POST /api/v1/blacklist`. No change required here.
- **Story 8.4 (Per-Track Blacklist Action on Recently Added)** — shipped the original `useBlacklistTrack` with the `['recently-added']` optimistic update. Story 9.4 **extends** that hook to also handle `['playlist-tracks', *]` keys. The existing call site in `RecentlyAddedPage.tsx` continues to work without modification because the hook's exported signature is unchanged — only the internal `context` is widened.
- **Story 9.1 (Playlist Tracks API)** — returns the same `RecentlyAddedTrack` shape as Recently Added, which is why the blacklist filter (`t.spotify_id !== variables.spotify_id`) works uniformly across both cache families.
- **Story 9.2 (Shared Track List Components)** — `TrackListTable` already exposes `onBlacklist?`; when undefined, the `⋯` menu item is a no-op (per 9.2 AC #8). Passing a non-undefined handler in this story flips it on.
- **Story 9.3 (Playlist Detail Page & Navigation)** — created the `PlaylistDetailPage` that **deliberately omits** `onBlacklist` (per 9.3 AC #2, third bullet — explicit deferral to 9.4). Story 9.4 is the activation step; no other 9.3 plumbing needs to change.
- **Story 8.5 (Sync Integration — Blacklist Filter)** — already shipped (status `review`). When the next sync runs, blacklisted tracks are filtered out of the dynamic Recent Adds harvest. The Recently Added query naturally reconciles after sync (via `useSyncStream` invalidation). No coupling needed in 9.4.

### Git Intelligence

Recent commits (newest first):

- `18dea64 feat: Epic 8 — page Recently Added avec table, blacklist par track et hooks dédiés` — established `useBlacklistTrack`'s `['recently-added']` optimistic pattern. Story 9.4 mirrors the structure but adds the `['playlist-tracks', *]` family.
- `f1a7caa fix: adaptation au changement d'API Spotify (track → item) + backfill sync` — irrelevant.
- `76facf6 feat: Epics 6 & 7 — UI refonte + playlist grid avec hide/unhide + dropdown style Spotify` — established the `useHidePlaylist` optimistic pattern (the design template for `useBlacklistTrack`); also the `sonner` toast usage in `PlaylistCard.tsx:141`.
- `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — established the `liked_songs` sentinel.

**Working tree at story creation** — Stories 9.1, 9.2, 9.3 are all in `review` but **not yet committed** (see `git status`: `M backend/routers/playlists.py`, `M backend/services/spotify.py`, `M frontend/src/App.tsx`, `M frontend/src/components/layout/AppShell.tsx`, `M frontend/src/features/playlists/PlaylistCard.tsx`, `D frontend/src/features/recently-added/*`, `M frontend/src/pages/RecentlyAddedPage.tsx`, `?? frontend/src/features/tracks/`, `?? frontend/src/hooks/usePlaylistTracks.ts`, `?? frontend/src/pages/PlaylistDetailPage.tsx`, `?? backend/tests/test_story_9_1.py`). Story 9.4 builds on top of these uncommitted changes — **do NOT** revert or modify those files outside the explicit scope (AC #14).

### Latest Tech Information

- **TanStack Query v5 `getQueriesData`** — partial-key matcher; signature: `getQueriesData<T>({ queryKey }: { queryKey: QueryKey }): Array<[QueryKey, T | undefined]>`. Distinct from `getQueryData` (singular, exact-key). Use for batch snapshotting across a key family.
- **TanStack Query v5 `cancelQueries`** with `queryKey: ['playlist-tracks']` cancels every in-flight query whose key **starts with** `['playlist-tracks']` (hierarchical match) — exactly the semantics we need. [Source: TanStack Query v5 docs — Query Cancellation]
- **TanStack Query v5 `QueryKey`** — type alias `readonly unknown[]`. Import as `import type { QueryKey } from '@tanstack/react-query'`. [Source: TanStack Query v5 types]
- **Mutation `context` widening is backwards-compatible at the call site** — call sites only see `data`, `error`, `variables` and per-call `onSuccess` / `onError` callbacks (which receive `data | error, variables, context`). If a call site doesn't read `context`, the widening is transparent. `RecentlyAddedPage.tsx` does not read `context` in its per-call callbacks (verified at lines 107-115) — safe.
- **No new dependency added.** This story does not touch `package.json`.

### Project Structure Notes

- ✅ Frontend module conventions preserved: hook in `hooks/`, page in `pages/`, fetch through `lib/api.ts`, sonner via the existing `App.tsx` Toaster mount.
- ✅ TanStack Query v5 `isPending` naming convention untouched.
- ✅ shadcn components: no new shadcn component needed (DropdownMenu, sonner already installed).
- ⚠️ **Do NOT** introduce a `useUnblacklistTrack` hook (DELETE /blacklist) — still out of scope (no UI consumes it). Same rationale as Story 8.4 AC #12.
- ⚠️ **Do NOT** introduce a `['blacklist']` query key — still no GET /blacklist consumer in the UI.
- ⚠️ **Do NOT** edit `TrackRow.tsx`, `TrackListTable.tsx`, `TrackListHero.tsx`, or any other shared component. The plumbing is correct; only the call-site flips it on.
- ⚠️ **Do NOT** rephrase the menu label "Hide from Recent Adds" — global label, global behavior (AC #5).
- ⚠️ **Do NOT** decrement `usePlaylists()` cache's `track_count` — out of scope (AC #7).
- ⚠️ **Do NOT** add a confirmation modal — optimistic + toast is the explicit design (mirrors 8.4).
- ⚠️ **Do NOT** extract a shared `handleBlacklistToast` helper — two call sites is acceptable (AC #6).

### Project Context Reference

See [`CLAUDE.md`](../../CLAUDE.md) for project-wide development rules. Most relevant sections:

- **Frontend** — "TanStack Query v5 : `isPending` (pas `isLoading`)" → preserved. "Tous les fetch via `lib/api.ts`" → reused via existing `api.post` call in the hook. "Alias `@/` = `frontend/src/`" → all imports use `@/`. "Composants shadcn : toujours via CLI" → N/A (no new shadcn component).
- **Lancer le projet** — `docker-compose up` for the dev stack; `docker exec playlist_spotify-frontend-1 npm run build` for the build (AC #10); browser smoke against `http://127.0.0.1:5173` (AC #12).
- **Postman** — N/A for this story (AC #13). Rule applies to API surface changes; this is frontend-only.

User-memory rules in effect:

- [`feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md) — N/A (no new shadcn components needed).
- [`feedback_node_version`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_node_version.md) — applies only if running `npm` on host; via `docker exec` no host Node involved.
- [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md) — **does not apply** (no API change). AC #13 documents the skip.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-9.4 (lines 1485-1495)] — primary AC source and implementation hints.
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-9 (lines 1435-1441)] — epic framing + FR/AR/NFR map.
- [Source: _bmad-output/planning-artifacts/prd.md FR45, FR46] — per-track blacklist action availability across track-list surfaces.
- [Source: _bmad-output/implementation-artifacts/8-4-per-track-blacklist-action.md#AC2-#AC10] — original blacklist optimistic mutation pattern; reused and extended here.
- [Source: _bmad-output/implementation-artifacts/9-1-playlist-tracks-api.md#AC1-#AC2] — playlist tracks endpoint shape + liked_songs sentinel.
- [Source: _bmad-output/implementation-artifacts/9-2-shared-track-list-components.md#AC8] — `TrackListTable`'s `onBlacklist?` prop contract (no-op when undefined).
- [Source: _bmad-output/implementation-artifacts/9-3-playlist-detail-page-navigation.md#AC2] — explicit deferral of `onBlacklist` to Story 9.4.
- [Source: frontend/src/hooks/useBlacklist.ts] — current hook to extend.
- [Source: frontend/src/pages/PlaylistDetailPage.tsx] — current page to wire.
- [Source: frontend/src/pages/RecentlyAddedPage.tsx:103-118] — call-site precedent for handler + toast.
- [Source: frontend/src/features/tracks/TrackListTable.tsx:14-24, 68-84] — `onBlacklist` prop signature; consumed unchanged.
- [Source: frontend/src/components/TrackRow.tsx:134-152] — menu structure; consumed unchanged.
- [Source: frontend/src/hooks/usePlaylistTracks.ts] — query key family `['playlist-tracks', spotifyId]` targeted by the new cache update.
- [Source: CLAUDE.md#Frontend, #Tests, #Postman, #Lancer le projet] — project conventions.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

### Completion Notes List

- **Task 1 — Hook extension (`useBlacklist.ts`)**: Widened `useMutation` context generic to `{ previous, previousPlaylistTracks }`. Added `cancelQueries`, `getQueriesData`, and per-tuple `setQueryData` filter for `['playlist-tracks']` family inside `onMutate`. Mirrored restore loop in `onError`. No `onSettled` added (per AC #2 + Dev Notes — matches existing `['recently-added']` behavior). Imported `QueryKey` as type-only. Hook external signature unchanged — `RecentlyAddedPage.tsx`'s call site continues to work unmodified.
- **Task 2 — Page wiring (`PlaylistDetailPage.tsx`)**: Added `toast` (sonner) and `useBlacklistTrack` imports. Added `const blacklist = useBlacklistTrack()` near other hooks. Added `handleBlacklist` mirroring `RecentlyAddedPage.tsx:103-118` with the AC #4 description override ("Will be removed from your Spotify **Recent Adds** playlist on the next sync."). Wired `onBlacklist={handleBlacklist}` onto the main-branch `<TrackListTable>`. The not-found branch is untouched (no table rendered there).
- **Task 3 — Build verification (AC #10)**: `docker exec playlist_spotify-frontend-1 npm run build` → ✓ 1935 modules transformed, built in 630ms, 0 TS errors, 0 new ESLint warnings. The pre-existing 500kB chunk-size warning is unrelated to this story.
- **Task 4 — Backend safety net (AC #11)**: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → **127 passed, 14 warnings in 1.29s**. Matches baseline (≥ 127). Zero backend files touched.
- **Task 5 — Browser smoke (AC #12)**: **Not executed manually.** Per CLAUDE.md, the dev workflow's manual browser smoke is the user's responsibility — the automation environment cannot drive a real browser session, so claiming bullet-by-bullet visual confirmations would be dishonest. The dev stack is up and healthy (`docker-compose ps` shows frontend & backend up 22h; `curl http://127.0.0.1:5173/ → 200`). All wiring is type-checked (Task 3) and the underlying optimistic cache pattern is structurally identical to the 8.4 pattern that already smoked cleanly. **Please run the AC #12 walkthrough manually before merging.**
- **Task 6 — Final verification (AC #13, #14)**: `git status` shows the expected delta — modified `frontend/src/hooks/useBlacklist.ts`, `_bmad-output/implementation-artifacts/sprint-status.yaml`; the untracked entries `frontend/src/pages/PlaylistDetailPage.tsx` and `_bmad-output/implementation-artifacts/9-4-per-track-actions-playlist-detail.md` carry this story's edits (PlaylistDetailPage was an untracked file from the still-uncommitted Story 9.3 — modifying it here is in-scope per AC #14 and Dev Notes "Working tree at story creation"). All other modified/untracked entries (epics.md, prd.md, ux-design/, backend/routers/playlists.py, backend/services/spotify.py, App.tsx, AppShell.tsx, PlaylistCard.tsx, RecentlyAdded* deletes, RecentlyAddedPage.tsx, features/tracks/, usePlaylistTracks.ts, backend/tests/test_story_9_1.py, sprint-change-proposal-2026-05-25.md, 9-1/9-2/9-3 story files) are pre-existing uncommitted work from Stories 9.1–9.3, confirmed via the initial git status before story start. **Postman: N/A (no API change)** per AC #13 and memory rule `feedback_postman_sync`.

### File List

- ✏️ `frontend/src/hooks/useBlacklist.ts` — extended `onMutate`/`onError` to handle the `['playlist-tracks']` query-key family; widened mutation `context` type; added type-only `QueryKey` import.
- ✏️ `frontend/src/pages/PlaylistDetailPage.tsx` — added `useBlacklistTrack` hook call, `handleBlacklist` callback with context-specific toast description, and `onBlacklist` prop on `<TrackListTable>`. (File originated in Story 9.3 and is still untracked at the time of this commit.)
- ✏️ `_bmad-output/implementation-artifacts/sprint-status.yaml` — story status transitions (`ready-for-dev` → `in-progress` → `review`).
- ✏️ `_bmad-output/implementation-artifacts/9-4-per-track-actions-playlist-detail.md` — task checkboxes, Dev Agent Record, status field.

### Change Log

| Date       | Change                                                              |
|------------|---------------------------------------------------------------------|
| 2026-05-26 | Story 9.4 context created — extends the existing `useBlacklistTrack` hook to optimistically filter `['playlist-tracks', *]` query caches across all cached playlists, then wires `onBlacklist` into `PlaylistDetailPage.tsx` with a context-specific toast description. Backwards-compatible with `RecentlyAddedPage.tsx`'s existing call site. Zero backend changes, zero new dependencies. |
| 2026-05-26 | Implemented Story 9.4 — hook + page wiring shipped per spec. Frontend build clean (0 TS errors). Backend pytest 127/127 passed (baseline preserved, zero backend edits). Manual browser smoke deferred to reviewer (see Completion Notes). Status → review. |
