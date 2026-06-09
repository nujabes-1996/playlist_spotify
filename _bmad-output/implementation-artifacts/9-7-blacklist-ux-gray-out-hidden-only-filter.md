# Story 9.7: Blacklist UX — Visible Gray-Out + Hidden-Only Filter

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want blacklisted tracks to stay visible in track lists (rendered grayed-out) with an inverse "Unhide" action, AND a "Hidden only" filter toggle on the Playlist Detail page,
so that the blacklist becomes a **reviewable soft-flag** instead of an opaque destructive delete — and I can audit / restore my hidden tracks at any time.

## Acceptance Criteria

> **Source of truth** for this story: [sprint-change-proposal-2026-05-26-blacklist-ux-pivot.md §4.1](../planning-artifacts/sprint-change-proposal-2026-05-26-blacklist-ux-pivot.md).
> Reverses the destructive `filter()` mutation introduced in Stories 8.4 / 9.4 (now amended in §4.2 / §4.3 of the proposal).

### Backend

1. **Track DTOs gain `is_blacklisted: bool`.** The Pydantic `RecentlyAddedTrack` in [`backend/routers/recently_added.py`](../../backend/routers/recently_added.py) AND `PlaylistTrack` in [`backend/routers/playlists.py`](../../backend/routers/playlists.py) **both** gain a new required field `is_blacklisted: bool`. No default — every dict returned from the service layer must set it explicitly. snake_case in the JSON response per [`CLAUDE.md#Backend`](../../CLAUDE.md) ("Champs JSON en snake_case partout — pas de camelCase").

2. **`services.spotify.get_recently_added_tracks()` joins the blacklist.** Inside the existing `with Session(engine) as session:` block at [`backend/services/spotify.py:365`](../../backend/services/spotify.py#L365), call `blacklist_service.get_blacklisted_ids(session)` to obtain the `set[str]` of blacklisted spotify_ids **once**, BEFORE the pagination loop. Set `"is_blacklisted": track["id"] in blacklisted_ids` inside the per-track dict construction at [`backend/services/spotify.py:404-415`](../../backend/services/spotify.py#L404-L415). Re-use the existing `Session` — DO NOT open a second one. Reuse [`backend/services/blacklist_service.py`](../../backend/services/blacklist_service.py) — DO NOT inline a duplicate `select(TrackBlacklist)` query.

3. **`services.spotify.get_playlist_tracks_full()` joins the blacklist.** Currently this function does NOT open a DB session ([`backend/services/spotify.py:301-355`](../../backend/services/spotify.py#L301-L355)). Wrap the body in `with Session(engine) as session:` and call `blacklist_service.get_blacklisted_ids(session)` once, BEFORE the pagination loop. Pass the resulting `set[str]` to `_build_track_row()` (see AC #4) so the join happens at row-build time. Both the LIKED_SONGS branch (line 312-326) AND the regular-playlist branch (line 328-354) must set `is_blacklisted` correctly. Imports to add at top of file: `from services import blacklist_service` (avoid circular import — `blacklist_service` only imports models, no service-layer dep).

4. **`_build_track_row()` accepts the blacklist set.** Extend the helper at [`backend/services/spotify.py:284-298`](../../backend/services/spotify.py#L284-L298) to:
   ```python
   def _build_track_row(track: dict, added_at: str, blacklisted_ids: set[str]) -> dict:
       ...
       return {
           ...existing fields...,
           "is_blacklisted": track["id"] in blacklisted_ids,
       }
   ```
   Update both call sites in `get_playlist_tracks_full()` to pass `blacklisted_ids`. The inline dict construction in `get_recently_added_tracks()` (line 404-415) does NOT use `_build_track_row` — set `is_blacklisted` inline there for consistency. **DO NOT refactor `get_recently_added_tracks` to use `_build_track_row`** in this story — that's a tempting tangent but out of scope (would conflict with the line-anchored test fixtures in `test_story_8_5.py` / `test_story_3_3.py`).

5. **Tests — backend.** New file `backend/tests/test_story_9_7.py` covering:
   - **(a)** `get_recently_added_tracks` returns `is_blacklisted=True` for tracks present in `track_blacklist` and `False` otherwise. Mock `spotipy.client.Spotify.playlist` and `playlist_items` to return a fixed 3-track page; seed 1 of 3 ids into `TrackBlacklist`; assert the resulting list of dicts has `is_blacklisted` set correctly per track.
   - **(b)** `get_playlist_tracks_full` (non-`liked_songs` branch) sets `is_blacklisted` correctly via the same fixture pattern.
   - **(c)** `get_playlist_tracks_full(LIKED_SONGS_ID)` (Liked Songs branch via `current_user_saved_tracks`) sets `is_blacklisted` correctly.
   - **(d)** Empty blacklist → every track has `is_blacklisted=False`.
   - **(e)** API contract: `GET /recently-added` and `GET /playlists/{id}/tracks` HTTP responses include `is_blacklisted` in every track JSON object.

   Use the established fixture pattern from [`backend/tests/test_story_8_5.py`](../../backend/tests/test_story_8_5.py) (session + client + dependency_overrides; `patch("services.spotify.spotipy.Spotify.…", …)`). Backend baseline goes from **127 → ≥130** passing.

6. **No schema migration.** `track_blacklist` table is unchanged. No new columns. No Alembic step (project doesn't use Alembic — SQLModel creates tables at startup).

### Frontend

7. **`RecentlyAddedTrack` type extended.** In [`frontend/src/types/index.ts:51-61`](../../frontend/src/types/index.ts#L51-L61), add a new required field:
   ```ts
   export interface RecentlyAddedTrack {
     ...existing fields...
     is_blacklisted: boolean
   }
   ```
   **Note:** snake_case in the interface (matches the API JSON shape per [`CLAUDE.md#Backend`](../../CLAUDE.md)). The `Track` adapter (see AC #8) is where camelCase happens.

8. **`Track` adapter and UI type gain `isBlacklisted`.** In [`frontend/src/components/TrackRow.tsx:10-23`](../../frontend/src/components/TrackRow.tsx#L10-L23), extend the `Track` interface:
   ```ts
   export interface Track {
     ...existing fields...
     isBlacklisted?: boolean
   }
   ```
   In the `adapt()` function at [`frontend/src/features/tracks/TrackListTable.tsx:32-50`](../../frontend/src/features/tracks/TrackListTable.tsx#L32-L50), set `isBlacklisted: t.is_blacklisted` on the returned object.

9. **`TrackRow` visual gray-out.** In [`frontend/src/components/TrackRow.tsx:54-154`](../../frontend/src/components/TrackRow.tsx) (the `TrackRowInner` component):
   - When `track.isBlacklisted === true`, apply `opacity-60` to the title, artist, album, and date-added text containers (NOT the row's `<div>` — see anti-pattern note below).
   - The cover-art `<img>` (lines 81-93) stays at full opacity (small visual anchor that the row still exists).
   - The hover state continues to work (the row still highlights on hover via `hover:bg-[var(--bg-row-hover)]` at line 66).
   - The dropdown trigger (the `⋯` button at line 135-143) stays at full opacity so the user can find the "Unhide" action.
   - The play icon (line 72-76) stays at full opacity.
   - **Anti-pattern:** DO NOT set `opacity-60` on the outer `<div role="row">` — that would fade the dropdown trigger too and make "Unhide" hard to discover. Apply opacity to the specific text spans/divs only.

10. **`TrackRow` dropdown toggles between Hide and Unhide.** In [`frontend/src/components/TrackRow.tsx:144-151`](../../frontend/src/components/TrackRow.tsx#L144-L151):
    - Add a new optional prop `onUnhide?: (id: string) => void` to `TrackRowProps` (line 47-52).
    - Render the first `DropdownMenuItem` conditionally:
      ```tsx
      {track.isBlacklisted ? (
        <DropdownMenuItem onClick={() => onUnhide?.(track.id)}>
          <Eye size={15} className="mr-2" />Unhide
        </DropdownMenuItem>
      ) : (
        <DropdownMenuItem onClick={() => onHide?.(track.id)}>
          <EyeOff size={15} className="mr-2" />Hide from Recent Adds
        </DropdownMenuItem>
      )}
      ```
    - Import `Eye` from `lucide-react` at the top of the file. Both `Eye` and `EyeOff` are already in the lucide-react bundle the project uses.
    - The "Open in Spotify" item stays unchanged.

11. **`TrackListTable` plumbs `onUnhide` through.** In [`frontend/src/features/tracks/TrackListTable.tsx`](../../frontend/src/features/tracks/TrackListTable.tsx):
    - Add `onUnblacklist?: (spotifyId: string) => void` to `TrackListTableProps` (line 17-27).
    - Add `handleUnhide = useCallback((id) => onUnblacklist?.(id), [onUnblacklist])` alongside the existing `handleHide` (line 84-87).
    - Pass `onUnhide={handleUnhide}` to BOTH the virtualized branch's `<TrackRow>` (line 175-180) AND the non-virtualized branch's `<TrackRow>` (line 188-195). **Both branches must be updated** — Story 9.6 introduced the virtualized branch, and missing one of the two would create a subtle "Unhide doesn't fire for >200-track lists" bug.

12. **`useBlacklistTrack` — optimistic FLAG, not filter.** Rewrite [`frontend/src/hooks/useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts) (entire file). The current implementation at lines 24-42 removes the row from `['recently-added']` and `['playlist-tracks', *]` caches via `.filter()`. Replace with an in-place mutation:
    ```ts
    // ['recently-added']
    queryClient.setQueryData<RecentlyAddedTrack[]>(
      ['recently-added'],
      previous.map((t) =>
        t.spotify_id === spotify_id ? { ...t, is_blacklisted: true } : t,
      ),
    )
    // ['playlist-tracks', *]
    previousPlaylistTracks.forEach(([key, data]) => {
      if (data) {
        queryClient.setQueryData<RecentlyAddedTrack[]>(
          key,
          data.map((t) =>
            t.spotify_id === spotify_id ? { ...t, is_blacklisted: true } : t,
          ),
        )
      }
    })
    ```
    The `onError` rollback path stays identical (restores the snapshot from context). The `Ctx` type stays identical.

13. **New `useUnblacklistTrack` hook.** Add to [`frontend/src/hooks/useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts) (same file, exported alongside `useBlacklistTrack`):
    ```ts
    export function useUnblacklistTrack() {
      const queryClient = useQueryClient()
      return useMutation<void, Error, { spotify_id: string }, Ctx>({
        mutationFn: ({ spotify_id }) =>
          api.delete(`/blacklist/${encodeURIComponent(spotify_id)}`),
        onMutate: async ({ spotify_id }) => {
          // mirror useBlacklistTrack: snapshot + flip is_blacklisted false
          await queryClient.cancelQueries({ queryKey: ['recently-added'] })
          const previous = queryClient.getQueryData<RecentlyAddedTrack[]>(['recently-added'])
          if (previous) {
            queryClient.setQueryData<RecentlyAddedTrack[]>(
              ['recently-added'],
              previous.map((t) =>
                t.spotify_id === spotify_id ? { ...t, is_blacklisted: false } : t,
              ),
            )
          }

          await queryClient.cancelQueries({ queryKey: ['playlist-tracks'] })
          const previousPlaylistTracks = queryClient.getQueriesData<RecentlyAddedTrack[]>({
            queryKey: ['playlist-tracks'],
          })
          previousPlaylistTracks.forEach(([key, data]) => {
            if (data) {
              queryClient.setQueryData<RecentlyAddedTrack[]>(
                key,
                data.map((t) =>
                  t.spotify_id === spotify_id ? { ...t, is_blacklisted: false } : t,
                ),
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
    Verify that `api.delete` exists in [`frontend/src/lib/api.ts`](../../frontend/src/lib/api.ts) — if not, the existing pattern in the codebase (e.g. `api.post`) tells you the method signature; the `DELETE /blacklist/{spotify_id}` endpoint returns 204 No Content (see [`backend/routers/blacklist.py:57-65`](../../backend/routers/blacklist.py#L57-L65)) so the mutation return type is `void`.

14. **`RecentlyAddedPage` wires up `onUnblacklist`.** In [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx):
    - Import `useUnblacklistTrack` from `@/hooks/useBlacklist`.
    - Add `const unblacklist = useUnblacklistTrack()` alongside the existing `const blacklist = useBlacklistTrack()` (line 34).
    - Add a `handleUnblacklist` callback mirroring the existing `handleBlacklist` (line 103-118), with the success toast text `"Track unhidden"` and description `"Visible again in your list. Will return to the dynamic playlist on the next sync."`.
    - Pass `onUnblacklist={handleUnblacklist}` to `<TrackListTable />` (line 130-137).

15. **`PlaylistDetailPage` wires up `onUnblacklist` AND adds the "Hidden only" toggle.** In [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx):
    - Same `useUnblacklistTrack` + `handleUnblacklist` plumbing as AC #14.
    - Pass `onUnblacklist={handleUnblacklist}` to `<TrackListTable />`.
    - **NEW: Hidden-only toggle.** Add a new local state `const [showHiddenOnly, setShowHiddenOnly] = useState(false)`.
    - Extend the `filtered` `useMemo` (currently line 41-50) to compose the search filter with the hidden-only filter:
      ```ts
      const filtered = useMemo(() => {
        let result = q
          ? list.filter((t) =>
              (t.title + ' ' + t.artists.join(' ')).toLowerCase().includes(q),
            )
          : list
        if (showHiddenOnly) result = result.filter((t) => t.is_blacklisted)
        return result
      }, [list, q, showHiddenOnly])
      ```
      Composition order is search FIRST, then hidden-only — semantically equivalent either way (filters compose via logical AND) but search-first reads more naturally.
    - Add the toggle button to the `actions` JSX (line 81-110), **between** the search input and the existing `<MoreHorizontal>` overflow button:
      ```tsx
      <button
        type="button"
        onClick={() => setShowHiddenOnly((v) => !v)}
        aria-pressed={showHiddenOnly}
        aria-label="Show hidden tracks only"
        title={showHiddenOnly ? 'Show all tracks' : 'Show hidden tracks only'}
        className={cn(
          'grid h-9 w-9 place-items-center rounded-full transition',
          showHiddenOnly
            ? 'bg-[var(--accent-color)] text-black hover:bg-[var(--accent-hover)]'
            : 'text-[var(--text-secondary)] hover:bg-white/5 hover:text-white',
        )}
      >
        <EyeOff size={16} />
      </button>
      ```
      Imports to add: `EyeOff` from `lucide-react`, `cn` from `@/lib/utils`.
    - Update `emptyTitle` / `emptyMessage` to acknowledge the new filter dimension when relevant:
      ```ts
      const emptyTitle = showHiddenOnly
        ? 'No hidden tracks'
        : hasFilter
          ? 'No matches'
          : 'This playlist has no tracks'
      const emptyMessage = showHiddenOnly
        ? "You haven't hidden any tracks in this playlist yet."
        : hasFilter
          ? `No tracks match "${query.trim()}".`
          : "There's nothing in this playlist yet."
      ```

16. **Cross-page consistency — "Hidden only" toggle scope.** The "Hidden only" toggle is added **ONLY** to `PlaylistDetailPage` in this story. **DO NOT** add it to `RecentlyAddedPage`. The Recently Added page benefits from the gray-out treatment (shared `TrackRow`) but a hidden-only filter there is out of scope per [sprint-change-proposal §4.1 AC #8](../planning-artifacts/sprint-change-proposal-2026-05-26-blacklist-ux-pivot.md). The user can revisit it later if useful.

17. **Sync behavior unchanged.** [Story 8.5's sync filter](8-5-sync-integration-blacklist-filter.md) still excludes blacklisted tracks from the dynamic playlist push. After the next sync, blacklisted tracks naturally fall out of `/recently-added` (no longer in the Spotify playlist). The gray-out is the UI affordance for **(a)** the window between blacklist click and next sync, AND **(b)** blacklisted tracks that still exist in source playlists (visible-and-grayed on Playlist Detail). Do NOT touch [`backend/services/sync_engine.py`](../../backend/services/sync_engine.py) or any sync code.

### Quality gates

18. **Frontend build.** `docker exec playlist_spotify-frontend-1 npm run build` → 0 TS errors, 0 new ESLint warnings. Specifically:
    - `RecentlyAddedTrack.is_blacklisted` is typed `boolean` (no optional).
    - `Track.isBlacklisted` is typed `boolean | undefined`.
    - `TrackRow` props `onHide` / `onUnhide` are both optional.
    - The conditional dropdown render in `TrackRow` compiles without "possibly undefined" warnings (Eye and EyeOff both imported).
    - The pre-existing chunk-size warning is the only allowed warning.

19. **Backend tests.** `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → all green, total **≥130** (was 127 after Story 9.6; this story adds ≥5 new tests per AC #5).

20. **Postman collection update.** Per [`CLAUDE.md#Postman`](../../CLAUDE.md) and [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md). Update the collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`) example responses for:
    - `GET /recently-added` — add `is_blacklisted: false` (and one example with `true`) to the array example.
    - `GET /playlists/{id}/tracks` — same.
    - The `POST /blacklist` and `DELETE /blacklist/{id}` endpoints already exist in the collection (from Stories 8.1 and 8.4) — verify they're still present, no shape change needed.

    Procedure per [`CLAUDE.md`](../../CLAUDE.md): `GET https://api.getpostman.com/collections/{uid}` → edit JSON → `PUT https://api.getpostman.com/collections/{uid}` → re-GET to verify. API key in `.mcp.json` env `POSTMAN_API_KEY`.

21. **Manual browser smoke** (DEFERRED to human reviewer — agent cannot drive the browser). At `http://127.0.0.1:5173`:
    - On `/recently-added`, click `⋯` → "Hide from Recent Adds" on any track. The row stays visible, grayed out. The dropdown now shows "Unhide" instead of "Hide". Click "Unhide" → row returns to normal.
    - On `/playlists/liked_songs` (or any large playlist), do the same. Verify gray-out + Unhide round-trip.
    - Click the new `EyeOff` toggle in the hero actions row. List narrows to only hidden tracks. Toggle off → list returns to full. Compose with the search input (type a query AND toggle hidden-only → list shows hidden tracks that also match the query).
    - On a playlist with **no** hidden tracks, click the toggle → empty state shows "No hidden tracks" / "You haven't hidden any tracks in this playlist yet."
    - On `/playlists/liked_songs` (535 tracks, virtualized), verify the gray-out still applies to virtualized rows (scroll to row ~250, hide a track → it grays in place; scroll away and back → it's still grayed).
    - Refresh the page. Hidden state survives (server-backed) — grayed rows are still grayed after a hard reload.
    - Confirm the **filter result count** in the hero subline reflects the active filter. (If the hero displays "535 tracks" but Hidden only is on with 3 hidden → there's a known cosmetic gap; **do NOT** rewrite the hero in this story — note it in Completion Notes for a future polish story.)

22. **Scope clean — `git status` whitelist.** After the story lands, `git status` shows changes to exactly these files (in addition to expected sprint-status / story-file edits):

    ```
    M backend/routers/recently_added.py            # is_blacklisted on Pydantic model
    M backend/routers/playlists.py                 # is_blacklisted on PlaylistTrack model
    M backend/services/spotify.py                  # join blacklist set into both *_tracks fns
    A backend/tests/test_story_9_7.py              # 5+ new tests
    M frontend/src/types/index.ts                  # is_blacklisted on RecentlyAddedTrack
    M frontend/src/components/TrackRow.tsx         # Track.isBlacklisted, opacity, dropdown toggle
    M frontend/src/features/tracks/TrackListTable.tsx  # adapt() sets isBlacklisted, plumb onUnhide
    M frontend/src/hooks/useBlacklist.ts           # optimistic flag (not filter) + new useUnblacklistTrack
    M frontend/src/pages/RecentlyAddedPage.tsx     # wire useUnblacklistTrack
    M frontend/src/pages/PlaylistDetailPage.tsx    # wire useUnblacklistTrack + EyeOff toggle + filter compose
    M _bmad-output/implementation-artifacts/sprint-status.yaml
    M _bmad-output/implementation-artifacts/9-7-blacklist-ux-gray-out-hidden-only-filter.md
    ```

    **No edits to:** `backend/services/sync_engine.py`, `backend/services/blacklist_service.py` (reused as-is), `backend/routers/blacklist.py`, `frontend/src/features/tracks/TrackListHero.tsx`, `frontend/src/hooks/usePlaylistTracks.ts`, `frontend/src/hooks/useRecentlyAdded.ts`, `AppShell.tsx`, any shadcn `ui/*` file. Paste `git status` output into Completion Notes.

## Tasks / Subtasks

- [x] **Task 1: Backend — Pydantic models + service join** (AC: #1, #2, #3, #4)
  - [x] Add `is_blacklisted: bool` to `RecentlyAddedTrack` in [`backend/routers/recently_added.py`](../../backend/routers/recently_added.py).
  - [x] Add `is_blacklisted: bool` to `PlaylistTrack` in [`backend/routers/playlists.py`](../../backend/routers/playlists.py).
  - [x] Extend `_build_track_row(track, added_at, blacklisted_ids)` in [`backend/services/spotify.py:284-298`](../../backend/services/spotify.py#L284-L298) to set `is_blacklisted`.
  - [x] In `get_playlist_tracks_full()`, wrap body in `with Session(engine) as session:`, call `blacklist_service.get_blacklisted_ids(session)`, pass to both call sites of `_build_track_row()`.
  - [x] In `get_recently_added_tracks()`, reuse the existing `Session(engine)` context to fetch `blacklisted_ids`, set `is_blacklisted` inline at the dict-construction site (line 404-415). Do NOT refactor to use `_build_track_row`.
  - [x] Add `from services import blacklist_service` near top of `services/spotify.py` (verify no circular import — `blacklist_service` only depends on `models/`).

- [x] **Task 2: Backend tests** (AC: #5)
  - [x] Create [`backend/tests/test_story_9_7.py`](../../backend/tests/test_story_9_7.py) with at least 5 tests (cases a–e in AC #5).
  - [x] Use the fixture pattern from [`backend/tests/test_story_8_5.py`](../../backend/tests/test_story_8_5.py).
  - [x] Run `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → ≥130 passed.

- [x] **Task 3: Frontend types + adapter** (AC: #7, #8)
  - [x] Extend `RecentlyAddedTrack` in [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts).
  - [x] Extend `Track` interface in [`frontend/src/components/TrackRow.tsx:10-23`](../../frontend/src/components/TrackRow.tsx#L10-L23).
  - [x] Set `isBlacklisted` in `adapt()` at [`frontend/src/features/tracks/TrackListTable.tsx:32-50`](../../frontend/src/features/tracks/TrackListTable.tsx#L32-L50).

- [x] **Task 4: TrackRow visual + dropdown toggle** (AC: #9, #10)
  - [x] Add `onUnhide?: (id: string) => void` to `TrackRowProps`.
  - [x] Import `Eye` from `lucide-react`.
  - [x] Apply `opacity-60` to title/artist/album/date-added text containers when `track.isBlacklisted` (NOT the outer row).
  - [x] Render the first `DropdownMenuItem` conditionally based on `track.isBlacklisted` (Hide ↔ Unhide).

- [x] **Task 5: TrackListTable plumbing** (AC: #11)
  - [x] Add `onUnblacklist?: (id: string) => void` to `TrackListTableProps`.
  - [x] Add `handleUnhide = useCallback(...)` alongside `handleHide`.
  - [x] Pass `onUnhide={handleUnhide}` to BOTH the virtualized branch (line ~175) AND the non-virtualized branch (line ~188) of `<TrackRow>`. Both branches must be updated.

- [x] **Task 6: useBlacklistTrack optimistic flag + new useUnblacklistTrack** (AC: #12, #13)
  - [x] Rewrite the optimistic mutations in `useBlacklistTrack` to use `.map(t => t.spotify_id === id ? { ...t, is_blacklisted: true } : t)` instead of `.filter(...)`.
  - [x] Add `useUnblacklistTrack` to the same file ([`frontend/src/hooks/useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts)) with the inverse optimistic mutation and `DELETE /blacklist/{id}` call.
  - [x] Verify `api.delete` exists in [`frontend/src/lib/api.ts`](../../frontend/src/lib/api.ts); if missing, add it following the existing pattern.

- [x] **Task 7: Wire useUnblacklistTrack into pages** (AC: #14, #15 onUnblacklist part)
  - [x] [`RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx): add `useUnblacklistTrack` + `handleUnblacklist` + pass to `<TrackListTable>`.
  - [x] [`PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx): same.

- [x] **Task 8: Hidden-only toggle on Playlist Detail** (AC: #15 toggle part, #16)
  - [x] Add `showHiddenOnly` state + extend `filtered` `useMemo` to compose with the search filter.
  - [x] Add the toggle button (`EyeOff` icon) between the search input and the `<MoreHorizontal>` overflow in the hero `actions` JSX.
  - [x] Update `emptyTitle` / `emptyMessage` to cover the "no hidden tracks" case.
  - [x] Do **not** add the toggle to `RecentlyAddedPage` (out of scope).

- [x] **Task 9: Build verification** (AC: #18)
  - [x] `docker exec playlist_spotify-frontend-1 npm run build` → 0 TS errors, 0 new warnings. Paste output to Completion Notes.

- [x] **Task 10: Backend safety net** (AC: #19)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → ≥130 passed.

- [x] **Task 11: Postman update** (AC: #20)
  - [x] `GET` collection → edit `is_blacklisted` into the `/recently-added` and `/playlists/{id}/tracks` example responses → `PUT` → re-`GET` to verify.

- [x] **Task 12: Browser smoke** (AC: #21) — **DEFERRED TO HUMAN REVIEWER**
  - [x] `docker-compose up -d` (if not running).
  - [x] Walk every bullet in AC #21. Paste one-line confirmations into Completion Notes.

- [x] **Task 13: Final verification + sprint status** (AC: #22)
  - [x] `git status` → only the whitelisted files appear modified. Paste to Completion Notes.
  - [x] Update `_bmad-output/implementation-artifacts/sprint-status.yaml`: `9-7-…` → `review`.
  - [x] Move this story `Status:` to `review`.

## Dev Notes

### Architecture & Conventions

- **Why a flag on the response and not a separate `/blacklist` fetch + client-side join.** A separate `GET /blacklist` from the frontend + client-side `set.has(id)` would work but means **two round-trips on every page load** and a synchronization concern (which fires first?). One join in the backend per request keeps the page strictly single-round-trip and avoids stale-set glitches when the user blacklists+navigates rapidly. The join is cheap — `select(TrackBlacklist.spotify_id)` returns ≤ a few hundred ids in any realistic case.
- **Why reuse `blacklist_service.get_blacklisted_ids`.** It already exists ([`backend/services/blacklist_service.py:7-13`](../../backend/services/blacklist_service.py#L7-L13)) and is used by the sync engine. Reusing it keeps the "blacklist set" semantics centralized and means a future schema change (e.g. soft-delete column) ripples through one function.
- **Why opacity on text containers and not on `<div role="row">`.** Putting opacity on the row dims the dropdown trigger too, which makes "Unhide" hard to discover — the entire UX pivot exists *because* destructive UX hides the recovery path. Visually we keep the affordances (play icon, cover, dropdown) at full opacity so the user can act on grayed rows.
- **Why an in-place `.map()` mutation in TanStack Query cache.** TanStack Query v5 treats query data as immutable — `.map()` returns a new array that TQ will diff against React state, triggering re-render only for the changed track row. (`.filter()` would do the same but lose the track from the list — the bug we're fixing.) The `Ctx` snapshot stores the **pre-mutation** array so `onError` rollback restores the exact original.
- **Why optional `onUnhide` on `TrackRow`.** Some consumers may not want to expose Unhide (e.g. if a future page renders read-only). Keeping it optional matches the pattern of `onHide` (also optional). When the prop is undefined and `track.isBlacklisted` is true, the menu item still renders but its click is a no-op — that's fine because no current page reaches that combination (both `RecentlyAddedPage` and `PlaylistDetailPage` pass both callbacks).
- **Why scope the "Hidden only" toggle to Playlist Detail only.** Recently Added represents the **synthesized dynamic playlist** — blacklisted tracks get pushed out at the next sync, so the gray-out is transient (window of seconds-to-minutes). A "Hidden only" filter there would mostly be empty post-sync. On Playlist Detail (especially source playlists), blacklisted tracks persist indefinitely — the toggle is a real audit tool. If the user requests parity later, the toggle is a 10-line copy-paste.
- **Why no `useReducer` / no `useFilterState` extraction.** `PlaylistDetailPage` now has two filter dimensions (query + showHiddenOnly). Two booleans don't justify a reducer; the `useMemo` cleanly expresses the AND-composition. Resist the urge to add a `FilterState` abstraction until there are three+ dimensions.
- **No sync_engine changes.** The sync engine ([`backend/services/sync_engine.py`](../../backend/services/sync_engine.py)) already filters blacklisted tracks on push (Story 8.5). The "is_blacklisted" flag on the read API does not change push behavior — it only changes how the same data renders.

### Source Tree — Files to Touch

**Backend (modify):**
- ✏️ [`backend/routers/recently_added.py`](../../backend/routers/recently_added.py) — add `is_blacklisted: bool` to Pydantic model.
- ✏️ [`backend/routers/playlists.py`](../../backend/routers/playlists.py) — add `is_blacklisted: bool` to `PlaylistTrack`.
- ✏️ [`backend/services/spotify.py`](../../backend/services/spotify.py) — `_build_track_row` signature change, join blacklist set in both `get_*_tracks` functions, add import.

**Backend (create):**
- ➕ [`backend/tests/test_story_9_7.py`](../../backend/tests/test_story_9_7.py) — ≥5 tests covering the join.

**Backend (DO NOT touch):**
- 🔒 [`backend/services/blacklist_service.py`](../../backend/services/blacklist_service.py) — reused as-is.
- 🔒 [`backend/routers/blacklist.py`](../../backend/routers/blacklist.py) — POST/DELETE endpoints already correct.
- 🔒 [`backend/services/sync_engine.py`](../../backend/services/sync_engine.py) — sync behavior unchanged (AC #17).
- 🔒 [`backend/models/track_blacklist.py`](../../backend/models/track_blacklist.py) — schema unchanged.

**Frontend (modify):**
- ✏️ [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts) — `is_blacklisted` on `RecentlyAddedTrack`.
- ✏️ [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx) — `Track.isBlacklisted`, opacity, `onUnhide`, dropdown toggle, import `Eye`.
- ✏️ [`frontend/src/features/tracks/TrackListTable.tsx`](../../frontend/src/features/tracks/TrackListTable.tsx) — `adapt()` sets `isBlacklisted`; `onUnblacklist` prop; pass `onUnhide` to BOTH branches.
- ✏️ [`frontend/src/hooks/useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts) — `.map()` instead of `.filter()`; new `useUnblacklistTrack`.
- ✏️ [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx) — `useUnblacklistTrack` + `handleUnblacklist`.
- ✏️ [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx) — `useUnblacklistTrack` + Hidden-only toggle + filter compose.

**Frontend (DO NOT touch):**
- 🔒 [`frontend/src/features/tracks/TrackListHero.tsx`](../../frontend/src/features/tracks/TrackListHero.tsx) — hero is layout-only.
- 🔒 [`frontend/src/hooks/usePlaylistTracks.ts`](../../frontend/src/hooks/usePlaylistTracks.ts), [`useRecentlyAdded.ts`](../../frontend/src/hooks/useRecentlyAdded.ts) — fetch hooks unchanged; only the inferred `RecentlyAddedTrack` shape changes (transparent).
- 🔒 `frontend/src/components/ui/*` — no new shadcn component needed per [`feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md).
- 🔒 [`AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx) — out of scope.

### Code Sketch

**Backend — `_build_track_row` + `get_playlist_tracks_full` (delta):**

```python
# backend/services/spotify.py
from services import blacklist_service  # new import (top of file)

def _build_track_row(track: dict, added_at: str, blacklisted_ids: set[str]) -> dict:
    album = track.get("album") or {}
    images = album.get("images") or []
    artists = [a.get("name") for a in (track.get("artists") or []) if a.get("name")]
    return {
        "spotify_id": track["id"],
        "title": track.get("name", ""),
        "artists": artists,
        "album": album.get("name", ""),
        "image_url": images[0]["url"] if images else None,
        "added_at": added_at or "",
        "duration_ms": int(track.get("duration_ms") or 0),
        "explicit": bool(track.get("explicit", False)),
        "has_video": bool(track.get("is_video", False)),
        "is_blacklisted": track["id"] in blacklisted_ids,  # NEW
    }


def get_playlist_tracks_full(playlist_id: str) -> list[dict]:
    sp = get_authenticated_client()
    with Session(engine) as session:               # NEW
        blacklisted_ids = blacklist_service.get_blacklisted_ids(session)  # NEW

    results: list[dict] = []
    offset = 0
    if playlist_id == LIKED_SONGS_ID:
        # … unchanged …
        results.append(_build_track_row(track, item.get("added_at") or "", blacklisted_ids))
        # … unchanged …
        return results

    sp.playlist(playlist_id, fields="id")
    # … unchanged pagination …
    results.append(_build_track_row(track, item.get("added_at") or "", blacklisted_ids))
    # … unchanged …
    return results
```

**Backend — `get_recently_added_tracks` (delta, inline):**

```python
def get_recently_added_tracks() -> list[dict]:
    with Session(engine) as session:
        config = session.exec(select(Config)).first()
        playlist_id = config.dynamic_playlist_id if config else None
        blacklisted_ids = blacklist_service.get_blacklisted_ids(session)  # NEW
    if not playlist_id:
        return []
    # … unchanged …
    results.append({
        # … existing fields …,
        "is_blacklisted": track["id"] in blacklisted_ids,  # NEW
    })
```

**Frontend — `TrackRow.tsx` dropdown + opacity (delta):**

```tsx
import { MoreHorizontal, Play, ExternalLink, EyeOff, Eye } from "lucide-react"  // + Eye

interface TrackRowProps {
  track: Track
  index: number
  onHide?: (id: string) => void
  onUnhide?: (id: string) => void   // NEW
  onOpenInSpotify?: (id: string) => void
}

// inside the row, the title block becomes:
<div className={cn("truncate text-[14.5px] font-medium",
                   track.isActive ? "text-[var(--accent-color)]" : "text-white",
                   track.isBlacklisted && "opacity-60")}>
  {track.title} { /* … */ }
</div>
// repeat the `track.isBlacklisted && "opacity-60"` for the artist row, album cell, addedAgo cell.

// dropdown:
<DropdownMenuContent align="end">
  {track.isBlacklisted ? (
    <DropdownMenuItem onClick={() => onUnhide?.(track.id)}>
      <Eye size={15} className="mr-2" />Unhide
    </DropdownMenuItem>
  ) : (
    <DropdownMenuItem onClick={() => onHide?.(track.id)}>
      <EyeOff size={15} className="mr-2" />Hide from Recent Adds
    </DropdownMenuItem>
  )}
  <DropdownMenuItem onClick={() => onOpenInSpotify?.(track.id)}>
    <ExternalLink size={15} className="mr-2" />Open in Spotify
  </DropdownMenuItem>
</DropdownMenuContent>
```

**Frontend — `useBlacklist.ts` rewrite (full file):**

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

function flagTrack(
  id: string,
  flag: boolean,
): (data: RecentlyAddedTrack[]) => RecentlyAddedTrack[] {
  return (data) =>
    data.map((t) => (t.spotify_id === id ? { ...t, is_blacklisted: flag } : t))
}

export function useBlacklistTrack() {
  const queryClient = useQueryClient()
  return useMutation<BlacklistResponse, Error, { spotify_id: string }, Ctx>({
    mutationFn: ({ spotify_id }) =>
      api.post<BlacklistResponse>('/blacklist', { spotify_id }),
    onMutate: async ({ spotify_id }) => {
      await queryClient.cancelQueries({ queryKey: ['recently-added'] })
      const previous = queryClient.getQueryData<RecentlyAddedTrack[]>(['recently-added'])
      if (previous) {
        queryClient.setQueryData<RecentlyAddedTrack[]>(
          ['recently-added'],
          flagTrack(spotify_id, true)(previous),
        )
      }
      await queryClient.cancelQueries({ queryKey: ['playlist-tracks'] })
      const previousPlaylistTracks = queryClient.getQueriesData<RecentlyAddedTrack[]>({
        queryKey: ['playlist-tracks'],
      })
      previousPlaylistTracks.forEach(([key, data]) => {
        if (data) queryClient.setQueryData<RecentlyAddedTrack[]>(key, flagTrack(spotify_id, true)(data))
      })
      return { previous, previousPlaylistTracks }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(['recently-added'], context.previous)
      context?.previousPlaylistTracks?.forEach(([key, data]) => queryClient.setQueryData(key, data))
    },
  })
}

export function useUnblacklistTrack() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, { spotify_id: string }, Ctx>({
    mutationFn: ({ spotify_id }) =>
      api.delete(`/blacklist/${encodeURIComponent(spotify_id)}`),
    onMutate: async ({ spotify_id }) => {
      await queryClient.cancelQueries({ queryKey: ['recently-added'] })
      const previous = queryClient.getQueryData<RecentlyAddedTrack[]>(['recently-added'])
      if (previous) {
        queryClient.setQueryData<RecentlyAddedTrack[]>(
          ['recently-added'],
          flagTrack(spotify_id, false)(previous),
        )
      }
      await queryClient.cancelQueries({ queryKey: ['playlist-tracks'] })
      const previousPlaylistTracks = queryClient.getQueriesData<RecentlyAddedTrack[]>({
        queryKey: ['playlist-tracks'],
      })
      previousPlaylistTracks.forEach(([key, data]) => {
        if (data) queryClient.setQueryData<RecentlyAddedTrack[]>(key, flagTrack(spotify_id, false)(data))
      })
      return { previous, previousPlaylistTracks }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(['recently-added'], context.previous)
      context?.previousPlaylistTracks?.forEach(([key, data]) => queryClient.setQueryData(key, data))
    },
  })
}
```

The `flagTrack` helper deduplicates the four call sites without dragging in a separate util file.

**Frontend — `PlaylistDetailPage.tsx` filter delta:**

```tsx
import { useMemo, useState } from 'react'
import { ExternalLink, MoreHorizontal, Search, EyeOff } from 'lucide-react'  // + EyeOff
import { cn } from '@/lib/utils'  // already-likely; add if missing
import { useUnblacklistTrack } from '@/hooks/useBlacklist'  // NEW
// …

const [showHiddenOnly, setShowHiddenOnly] = useState(false)
const filtered = useMemo(() => {
  let result = q
    ? list.filter((t) => (t.title + ' ' + t.artists.join(' ')).toLowerCase().includes(q))
    : list
  if (showHiddenOnly) result = result.filter((t) => t.is_blacklisted)
  return result
}, [list, q, showHiddenOnly])

// in the actions JSX, between the search input and the MoreHorizontal button:
<button
  type="button"
  onClick={() => setShowHiddenOnly((v) => !v)}
  aria-pressed={showHiddenOnly}
  aria-label="Show hidden tracks only"
  title={showHiddenOnly ? 'Show all tracks' : 'Show hidden tracks only'}
  className={cn(
    'grid h-9 w-9 place-items-center rounded-full transition',
    showHiddenOnly
      ? 'bg-[var(--accent-color)] text-black hover:bg-[var(--accent-hover)]'
      : 'text-[var(--text-secondary)] hover:bg-white/5 hover:text-white',
  )}
>
  <EyeOff size={16} />
</button>
```

### Testing Standards

- **Backend.** New file `tests/test_story_9_7.py` (≥5 tests, AC #5). Reuse fixtures from `test_story_8_5.py`. Patch `services.spotify.spotipy.Spotify.playlist` and `playlist_items` / `current_user_saved_tracks` to return fixed-shape pages. Seed `TrackBlacklist` via the in-memory test session. Baseline → ≥130 passed.
- **Frontend.** Type-check via `npm run build` (AC #18) catches the type drift (e.g. forgetting to set `isBlacklisted` somewhere). No new unit tests — the project doesn't have a JS test runner installed (per Story 9.6 precedent: "best verified by browser smoke"). The optimistic mutation flip is exercised live in AC #21 (the gray-out + Unhide round-trip).
- **Cross-story regressions** are covered by the browser smoke bullets in AC #21 (filter compose with Story 9.5 search, virtualization in Story 9.6 still works, Story 8.5 sync still excludes blacklisted on push).

### Previous Story Intelligence

- **Story 8.1 (Track Blacklist Model & API).** Established `TrackBlacklist` SQLModel and POST/DELETE/GET endpoints. We reuse all of it — no schema or endpoint change.
- **Story 8.2 (Recently Added API).** Established `RecentlyAddedTrack` Pydantic model shape and the `get_recently_added_tracks()` service function. We add ONE field to both.
- **Story 8.4 (Per-Track Blacklist Action).** Introduced `useBlacklistTrack` with the **destructive** `.filter()` optimistic mutation that this story replaces with `.map(... is_blacklisted: true)`. The toast text and `mutate` call sites in `RecentlyAddedPage` are preserved. The amendment text in [sprint-change-proposal §4.2](../planning-artifacts/sprint-change-proposal-2026-05-26-blacklist-ux-pivot.md) applies to Story 8.4's AC retroactively (no code change in 8.4 — code change is here in 9.7).
- **Story 8.5 (Sync Integration: Blacklist Filter).** The sync engine reads `blacklist_service.get_blacklisted_ids()` at sync time and excludes those ids from the push. After the next sync, blacklisted tracks vanish from Spotify (and thus from `/recently-added`). **Unchanged.**
- **Story 9.1 (Playlist Tracks API).** Established `GET /playlists/{id}/tracks` and the `PlaylistTrack` Pydantic model. We add ONE field.
- **Story 9.2 (Shared Track List Components).** Extracted `TrackListTable` — this story benefits transparently on both pages.
- **Story 9.3 (Playlist Detail Page).** Established `PlaylistDetailPage` hero+table layout. The hero `actions` JSX is where the new toggle slots in.
- **Story 9.4 (Per-Track Actions on Playlist Detail).** Introduced the `handleBlacklist` callback on `PlaylistDetailPage` and the `useBlacklistTrack` integration with `['playlist-tracks', spotifyId]` cache key. The cache-mutation pattern propagates from `useBlacklist.ts` automatically — `PlaylistDetailPage.tsx` body is unchanged for the blacklist path; we only ADD the unblacklist + toggle plumbing.
- **Story 9.5 (Filter Tracks within Playlist).** Introduced the search-input + `filtered` `useMemo`. We **extend** this `useMemo` to compose with `showHiddenOnly`. Logical AND.
- **Story 9.6 (Virtualization).** Virtualization is internal to `TrackListTable` and is transparent. The new `onUnblacklist` prop must be wired into **both** the virtualized AND non-virtualized branches' `<TrackRow>` invocations (AC #11) — easy to miss; flag in code review.

### Git Intelligence

Recent commits (newest first):

- `18dea64 feat: Epic 8 — page Recently Added avec table, blacklist par track et hooks dédiés` — established `useBlacklistTrack` (destructive filter — what we're replacing).
- `f1a7caa fix: adaptation au changement d'API Spotify (track → item) + backfill sync` — the `track or item` Spotify-API fallback at [`services/spotify.py:348`](../../backend/services/spotify.py#L348). Don't disturb.
- `76facf6 feat: Epics 6 & 7 — UI refonte + playlist grid avec hide/unhide + dropdown style Spotify` — dropdown menu pattern (`DropdownMenuTrigger` opacity transition on hover) inherited by our new "Unhide" item; CSS variables (`--accent-color`, `--accent-hover`, `--bg-row-hover`, etc.) used by the toggle button.
- `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — `LIKED_SONGS_ID` sentinel; our `get_playlist_tracks_full` branch on `LIKED_SONGS_ID` is still in the code path.

**Working tree at story creation.** Stories 9.1–9.6 are all in `review` but not yet committed (per the `git status` snapshot at session start: `M backend/routers/playlists.py`, `M backend/services/spotify.py`, plus several `?? frontend/src/features/tracks/…` and `?? frontend/src/pages/PlaylistDetailPage.tsx`). Story 9.7 modifies several of those uncommitted files in place. After the commit, 9.7's diff will show as edits to the (then-committed) 9.1–9.6 files plus the new `test_story_9_7.py`.

### Latest Tech Information

- **`api.delete` in `lib/api.ts`.** The custom HTTP helper. If it doesn't exist yet (check `frontend/src/lib/api.ts`), add it following the existing `api.post` pattern — `DELETE /blacklist/{id}` returns 204 No Content, so the helper should resolve `void` (no JSON parse on 204).
- **TanStack Query v5.** Optimistic update via `onMutate` returning a `Ctx`, rollback in `onError`. Same pattern as Story 8.4. v5's `cancelQueries({ queryKey: ['playlist-tracks'] })` cancels ALL `['playlist-tracks', *]` queries — that's what we want (the user may have several playlists cached and any of them could contain the blacklisted track).
- **`api.delete(...)` URL encoding.** Use `encodeURIComponent(spotify_id)` even though Spotify ids are alphanumeric — defense-in-depth in case Spotify ever changes the id alphabet (already includes `_` for `liked_songs`; track ids are alphanumeric but the encoding cost is zero).
- **SQLModel `Session` + import order.** The new `from services import blacklist_service` import in `services/spotify.py` must be checked for circularity. `blacklist_service` currently only imports `from sqlmodel ...` and `from models.track_blacklist ...` — no circular dependency.
- **Lucide-react icons.** `Eye` and `EyeOff` are both shipped in the package; no additional install. `react-virtual` from Story 9.6 stays at the same version.

### Project Structure Notes

- ✅ Backend: business logic stays in `services/`; routers only declare Pydantic models + dispatch.
- ✅ Backend: snake_case JSON shape preserved (`is_blacklisted`, not `isBlacklisted`).
- ✅ Backend: response arrays remain unwrapped (per [`CLAUDE.md#Backend`](../../CLAUDE.md)).
- ✅ Frontend: TanStack Query v5 `useMutation` with `onMutate`/`onError` (consistent with existing `useBlacklistTrack`).
- ✅ Frontend: all fetches go through `@/lib/api` — no direct `fetch()` calls.
- ✅ Frontend: `@/` alias for all `frontend/src/*` imports.
- ✅ shadcn: no new shadcn component ([`feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md) — N/A).
- ✅ Tests: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` per [`CLAUDE.md#Tests`](../../CLAUDE.md).
- ⚠️ **DO NOT** refactor `get_recently_added_tracks` to use `_build_track_row` in this story (out of scope; would touch fixtures in 8.5 / 3.3 tests).
- ⚠️ **DO NOT** add a "Hidden only" toggle to `RecentlyAddedPage` (out of scope per AC #16).
- ⚠️ **DO NOT** touch `sync_engine.py` — sync behavior unchanged (AC #17).
- ⚠️ **DO NOT** add a Linear / Sentry / observability hook for "track unhidden" — this is plain UI plumbing.
- ⚠️ **DO NOT** add an "Unblacklist all" bulk action — single-track only in this story.
- ⚠️ **DO NOT** change the `DELETE /blacklist/{id}` endpoint signature — it already returns 204 (correct).
- ⚠️ **DO NOT** persist `showHiddenOnly` to localStorage / URL params — keep it ephemeral per-page-load in this story; revisit if the user requests persistence.

### Project Context Reference

See [`CLAUDE.md`](../../CLAUDE.md) for project-wide development rules. Most relevant sections for this story:

- **Backend** — business logic in `services/`; spotipy calls only through `services/spotify.py`; snake_case JSON; arrays unwrapped. All satisfied.
- **Frontend** — TanStack Query v5 (`isPending`, mutation callbacks); fetch through `@/lib/api`; `@/` alias; shadcn via CLI. All satisfied (no new shadcn needed).
- **Tests** — backend via `docker exec ... pytest`; fixture pattern from `test_story_2_4.py` / `test_story_3_1.py` (session + client + dependency_overrides); mock spotipy via `patch("services.spotify.spotipy.Spotify.<method>", ...)`.
- **Postman** — collection UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`. Update procedure: GET → edit → PUT → re-GET to verify. **MANDATORY this story** per AC #20 (response shape change).
- **Lancer le projet** — Docker Compose for all backend tests, frontend builds, and the browser smoke (AC #21).

User-memory rules in effect:

- [`feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md) — N/A (no new shadcn component).
- [`feedback_node_version`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_node_version.md) — applies if any `npm` command is needed outside the container; prefer `docker exec` (no install needed this story, but `npm run build` per AC #18 must run in the container).
- [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md) — **applies**: response shape changes → Postman update mandatory (AC #20).

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-05-26-blacklist-ux-pivot.md §4.1] — story content authoritative source.
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-05-26-blacklist-ux-pivot.md §4.4] — PRD FR amendments (FR33 + new FRxx).
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-05-26-blacklist-ux-pivot.md §4.5] — UX README updates.
- [Source: _bmad-output/planning-artifacts/prd.md FR33] — original "Hide from Recent Adds" requirement.
- [Source: _bmad-output/implementation-artifacts/8-1-track-blacklist-model-api.md] — `TrackBlacklist` model + `POST/DELETE/GET /blacklist` endpoints (reused).
- [Source: _bmad-output/implementation-artifacts/8-2-recently-added-api.md] — `RecentlyAddedTrack` Pydantic shape baseline (we add one field).
- [Source: _bmad-output/implementation-artifacts/8-4-per-track-blacklist-action.md] — `useBlacklistTrack` (destructive filter; we rewrite to flag).
- [Source: _bmad-output/implementation-artifacts/8-5-sync-integration-blacklist-filter.md] — sync engine still excludes blacklisted on push; unchanged.
- [Source: _bmad-output/implementation-artifacts/9-1-playlist-tracks-api.md] — `GET /playlists/{id}/tracks` + `PlaylistTrack` Pydantic shape baseline.
- [Source: _bmad-output/implementation-artifacts/9-2-shared-track-list-components.md] — `TrackListTable` extraction (transparent shared UI).
- [Source: _bmad-output/implementation-artifacts/9-3-playlist-detail-page-navigation.md] — hero `actions` JSX shape (where the new toggle lives).
- [Source: _bmad-output/implementation-artifacts/9-4-per-track-actions-playlist-detail.md] — `handleBlacklist` on `PlaylistDetailPage`; `['playlist-tracks', id]` cache key.
- [Source: _bmad-output/implementation-artifacts/9-5-filter-tracks-within-playlist.md] — `filtered` `useMemo` (we extend with `showHiddenOnly`).
- [Source: _bmad-output/implementation-artifacts/9-6-virtualization-large-playlists.md] — both branches of `TrackListTable` must receive `onUnhide`.
- [Source: backend/routers/recently_added.py] — Pydantic `RecentlyAddedTrack`; +`is_blacklisted: bool`.
- [Source: backend/routers/playlists.py] — Pydantic `PlaylistTrack`; +`is_blacklisted: bool`.
- [Source: backend/services/spotify.py:284-298, 301-355, 358-419] — `_build_track_row` + two `*_tracks` functions to extend.
- [Source: backend/services/blacklist_service.py] — `get_blacklisted_ids(session)` reused as-is.
- [Source: frontend/src/types/index.ts:51-61] — `RecentlyAddedTrack` interface extension point.
- [Source: frontend/src/components/TrackRow.tsx] — `Track` interface, opacity, dropdown toggle, `onUnhide`.
- [Source: frontend/src/features/tracks/TrackListTable.tsx] — `adapt()` sets `isBlacklisted`; plumb `onUnblacklist` to both branches.
- [Source: frontend/src/hooks/useBlacklist.ts] — full rewrite (flag, not filter) + new `useUnblacklistTrack`.
- [Source: frontend/src/pages/RecentlyAddedPage.tsx, PlaylistDetailPage.tsx] — wire `useUnblacklistTrack`; PlaylistDetail also gets the toggle.
- [Source: CLAUDE.md#Backend, #Frontend, #Tests, #Postman, #Lancer le projet] — project conventions.
- [Source: TanStack Query v5 docs https://tanstack.com/query/v5/docs/framework/react/guides/optimistic-updates] — `onMutate` + `Ctx` rollback pattern.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

_None yet._

### Completion Notes List

- **Backend**
  - Added `is_blacklisted: bool` to `RecentlyAddedTrack` ([`backend/routers/recently_added.py`](../../backend/routers/recently_added.py)) and `PlaylistTrack` ([`backend/routers/playlists.py`](../../backend/routers/playlists.py)).
  - Extended `_build_track_row(track, added_at, blacklisted_ids)` and wired both `get_playlist_tracks_full()` (Liked Songs + regular playlist branches) and `get_recently_added_tracks()` to fetch the blacklist set once per request via `blacklist_service.get_blacklisted_ids(session)` and stamp `is_blacklisted` on every row.
  - No circular import: `blacklist_service` only imports `sqlmodel` + `models.track_blacklist`.
- **Backend tests** — new file `backend/tests/test_story_9_7.py` (7 tests, exceeds the AC #5 minimum of 5): covers `get_recently_added_tracks` flag-per-track, both `get_playlist_tracks_full` branches (regular + `liked_songs`), the empty-blacklist baseline, and HTTP-shape contracts for both endpoints. Final run: **133 passed** (was 127 → +6 over baseline, AC #19 ≥130 satisfied).
- **Pre-existing test fixture updates** — `tests/test_story_8_2.py` and `tests/test_story_9_1.py` assert exact JSON-key sets, so they had to be extended with `is_blacklisted` to stay green. Logical extension of the same response contract; no behavioral test changed.
- **Frontend types** — `RecentlyAddedTrack.is_blacklisted: boolean` (required, snake_case) in [`types/index.ts`](../../frontend/src/types/index.ts); `Track.isBlacklisted?: boolean` (camelCase, optional) in `TrackRow`; `adapt()` in `TrackListTable` sets `isBlacklisted: t.is_blacklisted`.
- **TrackRow visual + dropdown** — `opacity-60` applied to the title/artist row/album cell/date-added cell when `track.isBlacklisted`. Cover art, play icon, and dropdown trigger stay at full opacity (anti-pattern observed: never opacity the outer row). First dropdown item now toggles between `EyeOff` ("Hide from Recent Adds") and `Eye` ("Unhide") based on `track.isBlacklisted`.
- **TrackListTable plumbing** — `onUnblacklist?: (id) => void` added to props; `handleUnhide` callback alongside `handleHide`; passed to BOTH the virtualized AND the non-virtualized `<TrackRow>` branches (AC #11 — both branches verified updated).
- **useBlacklist** — rewrote optimistic mutation in `useBlacklistTrack` from `.filter()` (destructive) to `.map(... is_blacklisted: true)` (in-place flag). Added new `useUnblacklistTrack` with the inverse map and `DELETE /blacklist/{spotify_id}` mutation; both mutations cover `['recently-added']` and `['playlist-tracks', *]` caches with snapshot/rollback. Factored a tiny `flagTrack(id, flag)` helper to deduplicate the four call sites.
- **api.delete** added to [`lib/api.ts`](../../frontend/src/lib/api.ts) — `api.delete` did not exist; created an `apiFetchNoBody` helper to handle the 204 No Content response (no JSON body to parse, returns `Promise<void>`). AC #13 explicitly authorized this addition ("if it doesn't exist yet, add it following the existing api.post pattern").
- **Pages wiring** — `RecentlyAddedPage` and `PlaylistDetailPage` both got `useUnblacklistTrack()` + a `handleUnblacklist` callback (toast: "Track unhidden" / "Visible again in your list. Will return to the dynamic playlist on the next sync.") + `onUnblacklist={handleUnblacklist}` plumbed into `<TrackListTable>`.
- **Hidden-only toggle (Playlist Detail only, AC #16)** — new local `showHiddenOnly` state; extended the `filtered` `useMemo` to compose search-then-hidden-only (logical AND); inserted an `EyeOff` round toggle button between the search input and the `<MoreHorizontal>` overflow, with proper `aria-pressed` / `aria-label` / accent-color active state; empty-state copy adapts to "No hidden tracks" / "You haven't hidden any tracks in this playlist yet." when the toggle is on.
- **Frontend build** — `npm run build` → 0 TS errors. Output: 1 chunk-size warning (`> 500kB`) — pre-existing per AC #18.
- **Postman collection updated** (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`):
  - `GET /recently-added` example response now contains `is_blacklisted: false` and `is_blacklisted: true` in a two-track array.
  - `GET /playlists/{id}/tracks` example response same.
  - Verified post-PUT via re-GET (script confirms `is_blacklisted` present in both endpoints' example bodies).
- **Browser smoke (AC #21, Task 12)** — DEFERRED TO HUMAN REVIEWER per the story. Agent cannot drive a browser; the type-checker + green test suite cover the wiring side. Human reviewer to walk the AC #21 bullets (hide → gray out → Unhide round-trip; toggle + search compose; virtualized rows; hard reload persistence; no-hidden empty state).
- **Out-of-scope respected** — no edits to `sync_engine.py`, `blacklist_service.py`, `routers/blacklist.py`, `TrackListHero.tsx`, `usePlaylistTracks.ts`, `useRecentlyAdded.ts`, `AppShell.tsx`, or any shadcn `ui/*` file.
- **git status (AC #22) — Story 9.7 deltas only:**

  ```
  M backend/routers/recently_added.py
  M backend/routers/playlists.py
  M backend/services/spotify.py
  M backend/tests/test_story_8_2.py        # added is_blacklisted to existing exact-shape assertion
  M backend/tests/test_story_9_1.py        # added is_blacklisted to EXPECTED_KEYS set + payload
  A backend/tests/test_story_9_7.py        # 7 new tests
  M frontend/src/types/index.ts
  M frontend/src/components/TrackRow.tsx
  M frontend/src/features/tracks/TrackListTable.tsx
  M frontend/src/hooks/useBlacklist.ts
  M frontend/src/lib/api.ts                # added api.delete helper (authorized by AC #13)
  M frontend/src/pages/RecentlyAddedPage.tsx
  M frontend/src/pages/PlaylistDetailPage.tsx
  M _bmad-output/implementation-artifacts/sprint-status.yaml
  M _bmad-output/implementation-artifacts/9-7-blacklist-ux-gray-out-hidden-only-filter.md
  ```

  All other entries in `git status` are pre-existing uncommitted state from Stories 9.1–9.6 (called out in Dev Notes → Git Intelligence).

### File List

**Modified (backend):**
- `backend/routers/recently_added.py` — `RecentlyAddedTrack.is_blacklisted: bool`.
- `backend/routers/playlists.py` — `PlaylistTrack.is_blacklisted: bool`.
- `backend/services/spotify.py` — `_build_track_row` signature change + `blacklist_service` import + join blacklist set in both `get_playlist_tracks_full()` and `get_recently_added_tracks()`.
- `backend/tests/test_story_8_2.py` — extended exact-shape assertion with `is_blacklisted`.
- `backend/tests/test_story_9_1.py` — extended `EXPECTED_KEYS` + payload with `is_blacklisted`.

**Created (backend):**
- `backend/tests/test_story_9_7.py` — 7 tests covering AC #5 (a)–(e).

**Modified (frontend):**
- `frontend/src/types/index.ts` — `RecentlyAddedTrack.is_blacklisted: boolean`.
- `frontend/src/components/TrackRow.tsx` — `Track.isBlacklisted?: boolean`, opacity-60 on text containers, conditional Hide/Unhide dropdown, `Eye` import, `onUnhide` prop.
- `frontend/src/features/tracks/TrackListTable.tsx` — `onUnblacklist` prop, `handleUnhide` callback, `isBlacklisted` set in `adapt()`, `onUnhide` passed to both virtualized AND non-virtualized `<TrackRow>` branches.
- `frontend/src/hooks/useBlacklist.ts` — rewrote `useBlacklistTrack` to in-place flag (`.map()` instead of `.filter()`); new `useUnblacklistTrack` mutation.
- `frontend/src/lib/api.ts` — added `api.delete` helper (204 No Content support).
- `frontend/src/pages/RecentlyAddedPage.tsx` — `useUnblacklistTrack` + `handleUnblacklist` + `onUnblacklist` wired to `<TrackListTable>`.
- `frontend/src/pages/PlaylistDetailPage.tsx` — `useUnblacklistTrack` + `handleUnblacklist` + `EyeOff` toggle + composed search/hidden-only filter + adapted empty-state copy.

**Modified (artifacts):**
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Story 9.7 → in-progress → review.
- `_bmad-output/implementation-artifacts/9-7-blacklist-ux-gray-out-hidden-only-filter.md` — Status, Tasks/Subtasks checked, Dev Agent Record filled, Change Log appended.

### Change Log

| Date       | Change                                                                                                                                |
|------------|---------------------------------------------------------------------------------------------------------------------------------------|
| 2026-05-26 | Story 9.7 created — gray-out semantics for blacklisted tracks + inverse "Unhide" action + "Hidden only" toggle on Playlist Detail.    |
| 2026-05-26 | Story 9.7 implemented — backend join + frontend gray-out + Hidden-only toggle. 133 backend tests pass (≥130 baseline). Postman updated. |
