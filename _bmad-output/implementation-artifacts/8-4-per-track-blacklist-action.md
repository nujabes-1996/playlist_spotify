# Story 8.4: Per-Track Blacklist Action

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a "Hide from Recent Adds" action on each track row,
so that I can permanently remove a track that shouldn't appear in my dynamic playlist.

## Acceptance Criteria

1. **Given** a row's `⋯` overflow menu (shadcn `DropdownMenu`) on the Recently Added page, **When** I open it, **Then** the existing two items already rendered by [`frontend/src/components/TrackRow.tsx:135-143`](../../frontend/src/components/TrackRow.tsx) remain — "Hide from Recent Adds" (with `EyeOff` icon, FR33) and "Open in Spotify" (with `ExternalLink` icon). No new menu items are added. The `TODO(story-8.4)` comment at [`TrackRow.tsx:136`](../../frontend/src/components/TrackRow.tsx) is removed. [Source: epics.md#Story-8.4 AC + Story-8.3 Task 4 + components/TrackRow.tsx current state]

2. **Given** I click "Hide from Recent Adds" on a row, **When** the action fires, **Then** the frontend calls `POST /api/v1/blacklist` with body `{"spotify_id": "<id>"}` via `api.post<{spotify_id, blacklisted_at}>('/blacklist', { spotify_id })` (no inline `fetch()`) and **optimistically** removes the row from the `useRecentlyAdded` query cache before the request resolves (FR33, FR34). [Source: epics.md#Story-8.4 AC + CLAUDE.md#Frontend "Tous les fetch via lib/api.ts" + backend/routers/blacklist.py:33-55]

3. **Given** the optimistic update pattern, **When** the mutation runs, **Then** it follows the **exact same shape** as [`useHidePlaylist` in `frontend/src/hooks/usePlaylists.ts:23-57`](../../frontend/src/hooks/usePlaylists.ts) — `onMutate` cancels in-flight `['recently-added']` queries, snapshots the previous cache, writes the filtered array, returns `{ previous }`; `onError` restores `previous`; `onSettled` invalidates `['recently-added']`. Do NOT invent a new pattern — reuse the established one for consistency. [Source: frontend/src/hooks/usePlaylists.ts:23-57 + project pattern established by Story 7.3]

4. **Given** the request succeeds (HTTP 200 or 201 — both are valid per [`backend/routers/blacklist.py:35-55`](../../backend/routers/blacklist.py); the route is idempotent), **When** the response arrives, **Then** the row stays removed and `toast.success("Removed from Recent Adds", { description: "Will be removed from your Spotify playlist on the next sync." })` is shown via the existing `sonner` Toaster mounted in [`frontend/src/App.tsx:27`](../../frontend/src/App.tsx). [Source: epics.md#Story-8.4 AC + sonner pattern at frontend/src/features/playlists/PlaylistCard.tsx:12,141]

5. **Given** the request fails (network error, 5xx, 422), **When** the error is caught in `onError`, **Then** the row is restored to the cache (via the snapshotted `previous`) and `toast.error("Couldn't hide track", { description: <truncated error.message, max 200 chars> })` is shown. Do NOT silently swallow the error. [Source: epics.md#Story-8.4 AC + defensive UX matching PlaylistCard.tsx:141]

6. **Given** the action must be keyboard-accessible, **When** I navigate the table with `Tab` (focuses the `⋯` trigger when its row becomes the active group-hover state via focus-within OR via persistent focus styles) and press `Enter`/`Space` to open the menu, then `ArrowDown` to highlight "Hide from Recent Adds" and `Enter` to fire, **Then** the action triggers identically to a mouse click. The shadcn `DropdownMenu` handles this natively; the only fix required is making the trigger reachable: change [`TrackRow.tsx:130-132`](../../frontend/src/components/TrackRow.tsx) from `opacity-0 transition group-hover:opacity-100` to `opacity-0 transition group-hover:opacity-100 focus:opacity-100 focus-visible:opacity-100 data-[state=open]:opacity-100` so the trigger remains visible when keyboard-focused or when the menu is open. [Source: epics.md#Story-8.4 AC #4 + shadcn/radix DropdownMenu default keyboard behavior + current TrackRow.tsx opacity logic]

7. **Given** the row hover state, **When** the pointer enters a row, **Then** the existing behavior from Story 8.3 is preserved unchanged — background becomes `var(--bg-row-hover)` and the `⋯` trigger fades from `opacity-0` to `opacity-100`. This story does NOT modify the hover styling itself, only the focus visibility (AC #6). [Source: epics.md#Story-8.4 AC #5 + Story-8.3 AC #9 already-shipped]

8. **Given** the wiring between `RecentlyAddedTable` and the mutation, **When** `onHide` is invoked on a row, **Then** the `onHide` prop currently set to a no-op stub at [`frontend/src/features/recently-added/RecentlyAddedTable.tsx:123-125`](../../frontend/src/features/recently-added/RecentlyAddedTable.tsx) is replaced with `(id) => blacklist.mutate({ spotify_id: id })` where `blacklist` is the new `useBlacklistTrack()` hook. The `TODO(story-8.4)` comment at [`RecentlyAddedTable.tsx:124`](../../frontend/src/features/recently-added/RecentlyAddedTable.tsx) is removed. [Source: frontend/src/features/recently-added/RecentlyAddedTable.tsx current state + project pattern: components consume mutation hooks via mutate()]

9. **Given** a new mutation hook is required, **When** it is created, **Then** it lives at `frontend/src/hooks/useBlacklist.ts` (singular file owns the whole blacklist feature — `useBlacklistTrack` for POST, and an exported `useRemoveFromBlacklist` for DELETE is **out of scope** for this story; only the POST hook is built here). Export signature:
   ```ts
   export function useBlacklistTrack(): UseMutationResult<
     { spotify_id: string; blacklisted_at: string },
     Error,
     { spotify_id: string },
     { previous: RecentlyAddedTrack[] | undefined }
   >
   ```
   [Source: CLAUDE.md#Frontend + frontend/src/hooks/usePlaylists.ts pattern + Story 8.5/8.6 scope split — DELETE wiring is not in 8.4]

10. **Given** the optimistic filter logic, **When** `onMutate` writes the new cache, **Then** it uses `previous.filter((t) => t.spotify_id !== variables.spotify_id)` to remove **all** occurrences of that `spotify_id` (defensive — the backend dedup ensures only one row, but the filter is correct under any cache state). [Source: defensive filtering matching the dedup invariant from Story 3.3]

11. **Given** the user blacklists the same track twice in rapid succession (rare race condition: optimistic remove → click again before refetch → but the row is gone from the UI), **When** the second click would hypothetically fire, **Then** no special handling is required because the row has been optimistically removed from `tracks` and the `⋯` menu is gone from the DOM — the click is impossible. Backend POST is already idempotent (returns 200 on duplicate per [`backend/routers/blacklist.py:39-44`](../../backend/routers/blacklist.py)). [Source: backend/routers/blacklist.py + UI invariant]

12. **Given** the project does NOT yet have a `useBlacklist` query (the GET /blacklist consumer hook), **When** Story 8.4 ships, **Then** `useBlacklistTrack` does NOT invalidate any `['blacklist']` query — invalidate ONLY `['recently-added']`. Adding a `['blacklist']` query is **out of scope** (no UI currently reads the blacklist list — Story 8.5 may add one or may not; we don't speculate). [Source: epics.md#Epic-8 scope + YAGNI]

13. **Given** the sync engine integration is NOT part of this story, **When** the user blacklists a track, **Then** the toast message explicitly defers the actual Spotify removal to "the next sync" (per AC #4 copy). Story 8.5 owns the sync engine's blacklist filter — this story is UI + persistence only. Do NOT call any sync endpoint, do NOT trigger a sync, do NOT modify `services/sync_service.py` or any sync code. [Source: epics.md#Story-8.5 explicit scope + epics.md#Story-8.4 epic body]

14. **Given** the backend `POST /api/v1/blacklist` already exists and is fully tested by Story 8.1, **When** Story 8.4 ships, **Then** **NO backend code change is required**. No new router, no new service, no new test file on the backend side. If a backend file is touched, that's a scope violation. [Source: backend/routers/blacklist.py shipped in Story 8.1 + epics.md#Story-8.1 AC #3]

15. **Given** the new code, **When** `docker exec playlist_spotify-frontend-1 npm run build` is run, **Then** the build passes with zero TypeScript errors and zero new ESLint warnings. **Given** `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` is run, **Then** all existing 108+ backend tests still pass — no regressions, no new backend tests added (per AC #14). [Source: CLAUDE.md#Tests + Story-8.3 baseline 108 tests]

16. **Given** the Postman collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`), **When** Story 8.4 ships, **Then** **NO Postman update is required** because the API surface is unchanged — `POST /api/v1/blacklist` was already added to the collection in Story 8.1. Verify (do not modify): GET the collection, confirm the "Blacklist" folder has `POST /blacklist` with an example body `{"spotify_id": "..."}`. If missing (Story 8.1 drift), add it then; otherwise no-op. [Source: CLAUDE.md#Postman + memory `feedback_postman_sync` + Story-8.1 AC #9]

## Tasks / Subtasks

- [x] **Task 1: Create the `useBlacklistTrack` mutation hook** (AC: #2, #3, #9, #10, #12)
  - [x] Create new file `frontend/src/hooks/useBlacklist.ts` with the following implementation. **Mirror `useHidePlaylist` exactly** — same generics shape, same lifecycle callbacks:
    ```ts
    import { useMutation, useQueryClient } from '@tanstack/react-query'
    import { api } from '@/lib/api'
    import type { RecentlyAddedTrack } from '@/types'

    interface BlacklistResponse {
      spotify_id: string
      blacklisted_at: string
    }

    export function useBlacklistTrack() {
      const queryClient = useQueryClient()
      return useMutation<
        BlacklistResponse,
        Error,
        { spotify_id: string },
        { previous: RecentlyAddedTrack[] | undefined }
      >({
        mutationFn: ({ spotify_id }) =>
          api.post<BlacklistResponse>('/blacklist', { spotify_id }),
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
          if (context?.previous) {
            queryClient.setQueryData(['recently-added'], context.previous)
          }
        },
        onSettled: () => {
          queryClient.invalidateQueries({ queryKey: ['recently-added'] })
        },
      })
    }
    ```
  - [x] Do NOT add a `['blacklist']` query key anywhere. Only `['recently-added']` is invalidated.

- [x] **Task 2: Wire the mutation into `RecentlyAddedTable`** (AC: #2, #4, #5, #8)
  - [x] In [`frontend/src/features/recently-added/RecentlyAddedTable.tsx`](../../frontend/src/features/recently-added/RecentlyAddedTable.tsx):
    - Import: `import { useBlacklistTrack } from '@/hooks/useBlacklist'` and `import { toast } from 'sonner'`.
    - Inside the component, call `const blacklist = useBlacklistTrack()`.
    - Replace the existing `onHide={() => { /* TODO(story-8.4): ... */ }}` at [`RecentlyAddedTable.tsx:123-125`](../../frontend/src/features/recently-added/RecentlyAddedTable.tsx) with:
      ```ts
      onHide={(id) =>
        blacklist.mutate(
          { spotify_id: id },
          {
            onSuccess: () =>
              toast.success('Removed from Recent Adds', {
                description: 'Will be removed from your Spotify playlist on the next sync.',
              }),
            onError: (err) =>
              toast.error("Couldn't hide track", {
                description: err.message.slice(0, 200),
              }),
          },
        )
      }
      ```
  - [x] **Do NOT** add a separate try/catch — the mutation's `onError` lifecycle already restores the cache, the per-call `onError` here is purely for the toast (it runs in addition to the hook's `onError`, not instead of it).

- [x] **Task 3: Clean up the stub comment in `TrackRow.tsx`** (AC: #1)
  - [x] In [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx), remove the line: `{/* TODO(story-8.4): wire to POST /api/v1/blacklist */}` at [line 136](../../frontend/src/components/TrackRow.tsx). The menu structure itself is unchanged.

- [x] **Task 4: Make the `⋯` trigger keyboard-accessible** (AC: #6)
  - [x] In [`frontend/src/components/TrackRow.tsx:130-132`](../../frontend/src/components/TrackRow.tsx), change the `DropdownMenuTrigger` className from:
    ```
    "grid h-8 w-8 place-items-center rounded-full text-[var(--text-secondary)]
     opacity-0 transition group-hover:opacity-100 hover:bg-[var(--bg-hover)] hover:text-white"
    ```
    to:
    ```
    "grid h-8 w-8 place-items-center rounded-full text-[var(--text-secondary)]
     opacity-0 transition group-hover:opacity-100 focus:opacity-100 focus-visible:opacity-100
     data-[state=open]:opacity-100 hover:bg-[var(--bg-hover)] hover:text-white"
    ```
    This ensures the trigger remains visible when (a) keyboard-focused via Tab, (b) when the menu is open (so it doesn't pop in/out as the cursor leaves the row while the menu is open).

- [x] **Task 5: Build + smoke test** (AC: #15)
  - [x] `docker exec playlist_spotify-frontend-1 npm run build` — expect 0 errors, 0 new warnings.
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` — expect all 108+ tests passing (no new tests, no regressions).
  - [x] `docker-compose up -d`, open `http://localhost:5173/recently-added` (after a successful sync so the table is populated):
    - Hover a row → `⋯` trigger fades in.
    - Click `⋯` → menu opens, "Hide from Recent Adds" + "Open in Spotify" visible.
    - Click "Hide from Recent Adds" → row disappears **instantly** (optimistic), success toast appears.
    - Open Network panel → confirm one `POST /api/v1/blacklist` with body `{"spotify_id":"<id>"}` returning 201 (or 200 if duplicate).
    - Repeat with backend stopped (`docker-compose stop backend`) → row disappears, then reappears on error; error toast shown with the network error message. Restart backend.
    - Keyboard path: focus the table, Tab through rows until the `⋯` trigger gets focus (verify it becomes visible via the new `focus-visible:opacity-100`), Enter to open menu, ArrowDown to highlight "Hide from Recent Adds", Enter to fire.
  - [x] Verify in a fresh browser DevTools session that **no `['blacklist']` query** appears in the React Query devtools tree (we only invalidate `['recently-added']`).

- [x] **Task 6: Postman verification (no-op expected)** (AC: #16)
  - [x] GET the collection from `https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` with the `POSTMAN_API_KEY` from `.mcp.json`.
  - [x] Confirm the "Blacklist" folder contains `POST /api/v1/blacklist` with an example body `{"spotify_id": "..."}` (added in Story 8.1).
  - [x] If present → no action. If missing (Story 8.1 drift) → add it and PUT the collection. Document the outcome in "Dev Notes > Completion Notes".

## Dev Notes

### Architecture & Conventions

- **Frontend-only story, zero backend code.** The backend `POST /api/v1/blacklist` route shipped in Story 8.1 and is idempotent (200 on duplicate, 201 on insert). This story wires the existing Story-8.3 stub menu item to that endpoint with optimistic UI + toast. [Source: backend/routers/blacklist.py + Story 8.1 AC #3]
- **Pattern: mirror `useHidePlaylist`.** The optimistic mutation pattern is already established by [`useHidePlaylist` in `frontend/src/hooks/usePlaylists.ts:23-57`](../../frontend/src/hooks/usePlaylists.ts). Do not invent a new pattern — copy the shape and rename the types/keys. [Source: frontend/src/hooks/usePlaylists.ts]
- **Toast via `sonner`.** The `Toaster` is mounted in [`App.tsx:27`](../../frontend/src/App.tsx) (`<Toaster richColors position="bottom-right" />`). Import `toast` directly from `'sonner'` (not from a wrapper). Example in use: [`PlaylistCard.tsx:141`](../../frontend/src/features/playlists/PlaylistCard.tsx). [Source: frontend/src/App.tsx + sonner docs]
- **TanStack Query v5 naming** — `isPending`, not `isLoading`. Mutation result is `mutation.isPending` if you need to disable the trigger (not required here; the row vanishes optimistically before the user could click again). [Source: CLAUDE.md#Frontend]
- **All fetches via `lib/api.ts`** — no inline `fetch()`. `api.post<T>(path, body)` is the only entry point. [Source: CLAUDE.md#Frontend + frontend/src/lib/api.ts]
- **Per-call mutation callbacks vs hook-level callbacks.** The hook owns cache restoration (`onError` restores `previous`). The per-call `onError` in `RecentlyAddedTable.tsx` owns the toast. Both fire — that's the v5 behavior. Do not duplicate cache restoration logic at the call site. [Source: TanStack Query v5 docs + useHidePlaylist consumption pattern]
- **No new query key.** `['blacklist']` does not exist in this codebase and this story does not introduce it. Only `['recently-added']` is invalidated on settle. [Source: epics.md#Epic-8 scope + YAGNI]
- **No sync trigger.** The toast copy explicitly tells the user the removal applies "on the next sync". Story 8.5 owns the sync engine's blacklist filter. Do not call `useSyncStream()` or any sync endpoint. [Source: epics.md#Story-8.5 scope]

### Source Tree — Files to Touch

- 🆕 [`frontend/src/hooks/useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts) — new `useBlacklistTrack` mutation hook.
- ✏️ [`frontend/src/features/recently-added/RecentlyAddedTable.tsx`](../../frontend/src/features/recently-added/RecentlyAddedTable.tsx) — replace `onHide` no-op stub with mutation call + toast wiring; import `useBlacklistTrack`, `toast`.
- ✏️ [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx) — remove `TODO(story-8.4)` comment; add `focus:opacity-100 focus-visible:opacity-100 data-[state=open]:opacity-100` to the `DropdownMenuTrigger` className.
- 🔒 [`frontend/src/components/ui/dropdown-menu.tsx`](../../frontend/src/components/ui/dropdown-menu.tsx), [`frontend/src/components/ui/sonner.tsx`](../../frontend/src/components/ui/sonner.tsx) — **do not touch**. shadcn primitives already configured.
- 🔒 [`frontend/src/App.tsx`](../../frontend/src/App.tsx) — **do not touch**. `Toaster` already mounted.
- 🔒 [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts) — **do not touch**. `RecentlyAddedTrack` already defined by Story 8.3.
- 🔒 [`backend/`](../../backend/) — **do not touch**. The endpoint already exists.

### Code Sketch — Wiring inside `RecentlyAddedTable`

```tsx
// frontend/src/features/recently-added/RecentlyAddedTable.tsx (excerpt)
import { useBlacklistTrack } from '@/hooks/useBlacklist'
import { toast } from 'sonner'

export default function RecentlyAddedTable({ tracks, isLoading, error, refetch }: RecentlyAddedTableProps) {
  const blacklist = useBlacklistTrack()
  // ... existing error/skeleton/empty branches unchanged ...
  return (
    // ...
    tracks.map((t, i) => (
      <TrackRow
        key={`${t.spotify_id}-${i}`}
        track={adapt(t)}
        index={i}
        onOpenInSpotify={(id) =>
          window.open(`https://open.spotify.com/track/${id}`, '_blank', 'noreferrer')
        }
        onHide={(id) =>
          blacklist.mutate(
            { spotify_id: id },
            {
              onSuccess: () =>
                toast.success('Removed from Recent Adds', {
                  description: 'Will be removed from your Spotify playlist on the next sync.',
                }),
              onError: (err) =>
                toast.error("Couldn't hide track", { description: err.message.slice(0, 200) }),
            },
          )
        }
      />
    ))
  )
}
```

### Testing Standards

- **No new tests required.** Backend logic is fully covered by Story 8.1's `test_story_8_1.py` (insert, duplicate, idempotent delete, ordering, validation). Frontend has no automated test harness — assurance is `npm run build` + manual smoke per CLAUDE.md#Tests.
- **Backend regression check** — `pytest tests/ -v` must still report 108+ passing (Story 8.3 baseline) with no new failures.
- **TypeScript strict** — the build will fail on any `any` or missing prop. Resolve at build time, not at runtime.
- **Manual smoke** — see Task 5 for the explicit click + keyboard path + offline-backend error path.

### Previous Story Intelligence

- **Story 8.1 (Track Blacklist Model & API)** — shipped `POST /api/v1/blacklist` with idempotent insert (201 on new, 200 on duplicate, 422 on missing/empty `spotify_id`). Response body: `{spotify_id, blacklisted_at}`. [Source: backend/routers/blacklist.py:33-55]
- **Story 8.2 (Recently Added API)** — shipped `GET /api/v1/recently-added` returning `RecentlyAddedTrack[]` (9 snake_case fields). The optimistic update in this story filters that array. [Source: Story 8.2 AC #1]
- **Story 8.3 (Recently Added Page — Track Table)** — built the page, the `useRecentlyAdded` hook with `queryKey: ['recently-added']`, the `TrackRow` component with the dropdown menu already containing "Hide from Recent Adds" as a stub. The `TODO(story-8.4)` comment markers were placed at [`TrackRow.tsx:136`](../../frontend/src/components/TrackRow.tsx) and [`RecentlyAddedTable.tsx:124`](../../frontend/src/features/recently-added/RecentlyAddedTable.tsx) — both must be removed in this story. [Source: 8-3-recently-added-page-track-table.md Tasks 4, 7]
- **Story 7.3 (Hide Playlist Action)** — established the optimistic mutation pattern in `useHidePlaylist` ([`hooks/usePlaylists.ts:23-57`](../../frontend/src/hooks/usePlaylists.ts)) and the per-call `onError` toast pattern in [`features/playlists/PlaylistCard.tsx:131-150`](../../frontend/src/features/playlists/PlaylistCard.tsx). Reuse verbatim — same generics shape, same lifecycle callbacks, same toast call style.
- **Story 8.5 (Sync Integration — Blacklist Filter)** — NEXT story. Will read the `track_blacklist` table inside the sync engine and filter the harvested track list. Story 8.4 only ensures the rows land in the table; Story 8.5 makes them effective during sync. Do NOT pre-implement any sync changes in 8.4.

### Git Intelligence

- Recent commits (newest first):
  - `76facf6 feat: Epics 6 & 7 — UI refonte + playlist grid avec hide/unhide + dropdown style Spotify` — established the optimistic `useHidePlaylist` mutation pattern, `sonner` toast usage, and the shadcn `DropdownMenu` style.
  - `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — irrelevant to this story (sync engine, no UI).
- Working tree currently has Stories 8.1, 8.2, 8.3 changes uncommitted (`backend/routers/recently_added.py`, `backend/tests/test_story_8_*.py`, frontend Recently Added files). Story 8.4 commits on top of those.
- No prior commit touches `frontend/src/hooks/useBlacklist.ts` — clean slate for the new file.

### Latest Tech Information

- **TanStack Query v5** — `useMutation<TData, TError, TVariables, TContext>` generics order is `<Data, Error, Variables, Context>`. The `onMutate` return becomes `context` for `onError`/`onSettled`. Mutation `mutate(variables, callbacks)` runs both hook-level and per-call callbacks (per-call runs first). [Source: TanStack Query v5 docs]
- **`sonner` v2+** — `toast.success(message, { description })` and `toast.error(message, { description })` are the canonical signatures. `richColors` is already enabled at the Toaster level in `App.tsx`. [Source: frontend/src/App.tsx + sonner docs]
- **shadcn `DropdownMenu`** — built on Radix; `data-[state=open]` is the Radix attribute on the trigger when the menu is open. Native keyboard handling (Tab to focus, Enter/Space to open, ArrowDown/Up to navigate, Enter to select, Esc to close) is provided out of the box — no additional handlers needed. [Source: Radix UI DropdownMenu docs]

### Project Structure Notes

- ✅ Aligns with `frontend/src/hooks/<domain>.ts` pattern (see `usePlaylists.ts`, `useConfig.ts`, `useAuthStatus.ts`).
- ✅ Reuses existing shadcn primitives (`DropdownMenu`, `sonner` Toaster) — no new dependencies, no new UI primitives.
- ⚠️ **Do NOT** add a `useBlacklist()` GET hook in this story — no UI consumes the blacklist list. Story 8.5 may add one or may not; we don't speculate.
- ⚠️ **Do NOT** add a `useUnblacklistTrack()` DELETE hook in this story — the unhide flow is not in scope (no Hidden Tracks view exists; the unhide path for tracks is implicit-via-next-sync per epic 8.5 design notes).
- ⚠️ **Do NOT** modify the empty-state, error-state, or skeleton branches of `RecentlyAddedTable` — they were finalized in Story 8.3 and have no relation to blacklist actions.
- ⚠️ **Do NOT** modify `useRecentlyAdded` — the query is consumer-agnostic; the mutation reads/writes its cache externally.
- ⚠️ **Do NOT** add backend changes (no new router, no service helper, no test file). The endpoint already exists and is fully tested.
- ⚠️ **Do NOT** add a confirmation modal — the optimistic + toast pattern is the explicit design. The user can recover via the un-blacklist flow (out of scope here; Story 8.5/8.6 may surface it).

### Project Context Reference

See [`CLAUDE.md`](../../CLAUDE.md) for project-wide development rules. Most relevant sections for this story:
- "Frontend" — TanStack Query v5 `isPending`, fetches via `lib/api.ts`, alias `@/`, callbacks in `mutate()` or `useMutation`.
- "Tests" — pytest via `docker exec`, frontend assurance via `npm run build` + manual smoke.
- "Postman" — verify no-op expected (no API surface change).

User-memory rules in effect for this story (will silently shape decisions):
- [`feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md) — irrelevant here; no new shadcn component is added (DropdownMenu, sonner already present).
- [`feedback_node_version`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_node_version.md) — frontend container uses Node 22; no host npm work needed.
- [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md) — verify the existing `POST /blacklist` request is in the collection (Story 8.1 should have added it); no modification expected.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-8.4] — primary ACs (lines 1315–1347).
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-8 + FR33, FR34] — feature requirement framing.
- [Source: _bmad-output/implementation-artifacts/8-1-track-blacklist-model-api.md] — backend endpoint contract (idempotency, status codes, response shape).
- [Source: _bmad-output/implementation-artifacts/8-3-recently-added-page-track-table.md] — Story 8.3 created the stub menu item and the `useRecentlyAdded` query this story consumes.
- [Source: frontend/src/hooks/usePlaylists.ts:23-57] — `useHidePlaylist` optimistic mutation pattern to mirror.
- [Source: frontend/src/features/playlists/PlaylistCard.tsx:131-150] — toast wiring pattern via per-call `onError`.
- [Source: frontend/src/components/TrackRow.tsx:127-144] — current menu structure to keep unchanged + focus styling to fix.
- [Source: frontend/src/features/recently-added/RecentlyAddedTable.tsx:111-127] — current `onHide` stub site.
- [Source: backend/routers/blacklist.py:33-55] — `POST /api/v1/blacklist` contract (200/201 idempotent insert).
- [Source: frontend/src/App.tsx:27] — `Toaster` mount.
- [Source: CLAUDE.md#Frontend, #Tests, #Postman] — project conventions.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

- `docker exec playlist_spotify-frontend-1 npm run build` → 0 errors, build OK (550.75 kB bundle).
- `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -q` → 108 passed, no regressions.
- Postman collection verified: "Blacklist" folder already contains `Add to Blacklist` (POST /blacklist). No-op confirmed.

### Completion Notes List

- Created `frontend/src/hooks/useBlacklist.ts` exporting `useBlacklistTrack`, mirroring `useHidePlaylist` (optimistic onMutate filter, onError rollback, onSettled invalidate). Only `['recently-added']` is invalidated — no `['blacklist']` query key introduced.
- Wired the mutation into `RecentlyAddedTable.tsx`; per-call `onSuccess`/`onError` now emit `sonner` toasts. Removed `TODO(story-8.4)` stub.
- `TrackRow.tsx` `DropdownMenuTrigger` className now includes `focus:opacity-100 focus-visible:opacity-100 data-[state=open]:opacity-100` for keyboard accessibility (AC #6). `TODO(story-8.4)` comment removed.
- Zero backend changes (AC #14). Zero new tests (AC #15 — frontend smoke only).
- Postman: no update required (POST /blacklist already in collection from Story 8.1).

### File List

- `frontend/src/hooks/useBlacklist.ts` (new)
- `frontend/src/features/recently-added/RecentlyAddedTable.tsx` (modified)
- `frontend/src/components/TrackRow.tsx` (modified)

### Change Log

- 2026-05-21: Story 8.4 — Per-Track Blacklist Action implemented. New `useBlacklistTrack` mutation hook + `RecentlyAddedTable` wiring with optimistic update and sonner toasts. `TrackRow` trigger now keyboard-focusable.
