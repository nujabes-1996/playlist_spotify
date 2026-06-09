# Story 9.8: Paginated Tracks API + Infinite Scroll

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user with large playlists (200+ tracks),
I want the playlist detail page to load the first batch of tracks quickly and stream the rest as I scroll,
so that I see content within ~500 ms instead of waiting for the whole playlist to be fetched from Spotify.

## Acceptance Criteria

> **Source of truth** for this story: [sprint-change-proposal-2026-05-26-playlist-tracks-pagination.md](../planning-artifacts/sprint-change-proposal-2026-05-26-playlist-tracks-pagination.md).
> Supersedes Story 9.1 AC #6 ("full list returned to client in a single payload") and Story 9.1 AC #14 (`get_playlist_tracks_full` returns the whole list). Both stay green via the backend tests amended in Task 7.

### Backend

1. **`GET /api/v1/playlists/{spotify_id}/tracks` accepts `?limit` and `?offset` query params.** In [`backend/routers/playlists.py:90-100`](../../backend/routers/playlists.py#L90-L100):
   - Add `limit: int = 50` and `offset: int = 0` query parameters via FastAPI's `Query(...)` (use `Query(50, ge=1, le=100)` for `limit` and `Query(0, ge=0)` for `offset` so FastAPI rejects out-of-range inputs with HTTP 422 before the service is called).
   - `limit` defaults to `50` (NOT to "no limit" — this is the **breaking change** vs. Story 9.1 AC #6, explicitly accepted per sprint-change-proposal §2 "no client-side aggregation across pages" and §4.1 AC #2).
   - `offset` defaults to `0`.
   - The route signature becomes `def get_playlist_tracks(spotify_id: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)) -> PlaylistTracksPage`.

2. **The response shape changes from `list[PlaylistTrack]` to `PlaylistTracksPage`** — a new Pydantic model declared in [`backend/routers/playlists.py`](../../backend/routers/playlists.py) alongside the existing `PlaylistTrack`:
   ```python
   class PlaylistTracksPage(BaseModel):
       items: list[PlaylistTrack]
       next_offset: int | None
       total: int
   ```
   Snake_case per [`CLAUDE.md#Backend`](../../CLAUDE.md). The `@router.get(...)` decorator must update `response_model=PlaylistTracksPage` (NOT `list[PlaylistTrack]` anymore). The HTTP body becomes `{"items": [...], "next_offset": 50, "total": 535}` — single object, **NOT** an array. Story 9.1's "no wrapper" rule still applies to the **track shape**, not to the page wrapper (which is the wrapper). This evolution is the whole point of the story; the wrapper change is intentional and documented as a breaking contract change.

3. **`services/spotify.py` exposes `get_playlist_tracks_page(playlist_id: str, limit: int, offset: int) -> dict`.** Add this new function alongside the existing `get_playlist_tracks_full(playlist_id)` ([`backend/services/spotify.py:303-359`](../../backend/services/spotify.py#L303-L359)). Do **NOT** delete `get_playlist_tracks_full` in this story — it's still used by `test_story_9_1.py` service-level tests AND it's a safer rollback path if the pagination ships with a defect. (It will be deleted in a future cleanup story.)
   - Signature: `def get_playlist_tracks_page(playlist_id: str, limit: int, offset: int) -> dict`
   - Returns: `{"items": [<full-shape dicts via _build_track_row>], "next_offset": int | None, "total": int}`
   - For **regular playlists**: call `sp.playlist(playlist_id, fields="tracks(total)")` once to get `total` (the existence probe still raises `SpotifyException(http_status=404)` if the playlist doesn't exist — preserve that contract per Story 9.1 AC #3); then call `sp.playlist_items(playlist_id, limit=limit, offset=offset, fields=...)` **exactly ONCE** (no while-loop over pages — spotipy's native pagination via `limit`/`offset` is exactly what we want). Read `page["total"]` from the spotipy response as a fallback if the probe didn't return it cleanly (Spotify returns `total` on each `playlist_items` page).
   - For **`LIKED_SONGS_ID`**: call `sp.current_user_saved_tracks(limit=limit, offset=offset)` exactly ONCE (no while-loop). `total` comes from the same response's `total` field. No existence probe needed (the `liked_songs` endpoint can't 404 for an authenticated user).
   - `next_offset` computation: `offset + len(items_returned)` if that value is `< total`, else `None`. **NOT** `offset + limit` — the last page can be shorter than `limit` and we never want to fetch an empty page.
   - Reuse `_build_track_row(track, added_at, blacklisted_ids)` for the per-track mapping in both branches (already exists per Story 9.7 — DO NOT duplicate field-mapping logic).
   - Same `null` / `is_local` skip rules as Story 9.1 AC #7 (skip `item is None`, `item.get("is_local")`, `track is None`, `track.get("is_local")`, `not track.get("id")`).
   - Open the DB session once for `blacklisted_ids` (mirror the pattern at [`backend/services/spotify.py:311-312`](../../backend/services/spotify.py#L311-L312)).
   - **Important — skipped items and `next_offset`.** When some items on the returned page are skipped (local/null), `len(items_returned)` reflects the **kept** count, not the raw page size. `next_offset` must still be computed against the **raw page size returned by Spotify** (i.e. `offset + len(page["items"])`), otherwise the client will request overlapping offsets. Concretely: `raw_page_len = len(page["items"])`; `next_offset = offset + raw_page_len if (offset + raw_page_len) < total else None`. The `items` array in the response is the filtered (kept) list, which may be shorter than `raw_page_len` — that's accepted (a page of 50 with 2 local tracks returns 48 items but advances offset by 50).

4. **Spotipy `limit` cap.** Spotify's API caps `limit` at 100 for both `playlist_items` and `current_user_saved_tracks`. We clamp at the FastAPI layer via `Query(50, ge=1, le=100)` (AC #1) so the service never receives an out-of-range value. Do **NOT** silently clamp at the service layer too — defense-in-depth here would mask a router-layer bug. The router validation IS the contract.

5. **Router error contracts unchanged.** The handler in [`backend/routers/playlists.py:91-100`](../../backend/routers/playlists.py#L91-L100) still maps:
   - `ValueError` (not authenticated) → HTTP 401 with `{"detail": str(exc)}` (Story 9.1 AC #4).
   - `SpotifyException(http_status=404)` → HTTP 404 with `{"detail": "Playlist not found"}` (Story 9.1 AC #3).
   - Any other `SpotifyException` → HTTP 502 with `{"detail": f"Spotify error: {exc.msg}"}` (Story 9.1 AC #5).
   - Out-of-range `limit`/`offset` → HTTP 422 (FastAPI's default validation error — no manual handling).
   The except blocks pattern stays identical; only the function body changes (call `get_playlist_tracks_page` instead of `get_playlist_tracks_full`, wrap return into the new `PlaylistTracksPage` model).

6. **Tests — backend.** Create `backend/tests/test_story_9_8.py` with **at least 4** tests covering:
   - **(a) Nominal pagination — regular playlist.** Mock `sp.playlist` (probe) and `sp.playlist_items` to return a single 50-item page with `total=200`. Call `GET /api/v1/playlists/some_id/tracks?limit=50&offset=0`. Assert: 200, `items` length 50, `next_offset == 50`, `total == 200`, each item has the AC #1 keys of Story 9.1 (the `EXPECTED_KEYS` set including `is_blacklisted`).
   - **(b) Last page — `next_offset` is null.** Mock spotipy to return a 35-item page with `total=185` at `offset=150`. Assert: `next_offset is None`, `items` length 35, `total == 185`. Verify the JSON serializes `next_offset` as `null`.
   - **(c) `offset > total`.** Request `offset=10000` on a `total=200` playlist (spotipy returns an empty `items` array with `total=200`). Assert: 200, `items == []`, `next_offset is None`, `total == 200`. Do NOT return 4xx — empty page at end of list is a valid response.
   - **(d) `limit > 100` is rejected at the router (HTTP 422).** Call `GET .../tracks?limit=200`. Assert response status code 422 (FastAPI's pydantic validation). No assertion on body shape — FastAPI's default error structure is acceptable.
   - **(e) Liked Songs branch — `liked_songs` sentinel paginates via `current_user_saved_tracks`.** Mock `sp.current_user_saved_tracks` (NOT `sp.playlist_items`) to return a 50-item page with `total=535`. Call `GET /api/v1/playlists/liked_songs/tracks?limit=50&offset=0`. Assert: 200, items length 50, `next_offset == 50`, `total == 535`. Verify via the mock that `current_user_saved_tracks` was called and `playlist_items` was NOT.
   - **(f) Skipped local/null items advance offset by raw page length.** Mock `sp.playlist_items` to return a 5-item page where 2 are `null`/`is_local`, with `total=100` at `offset=0`. Assert: `items` length 3 (kept), but `next_offset == 5` (raw advance, not kept advance) — verifies the subtle skip-vs-offset rule in AC #3.

   Use the established fixture pattern from [`backend/tests/test_story_9_1.py`](../../backend/tests/test_story_9_1.py) (session + client + dependency_overrides + `_make_track` helper). Mock the service via `patch.object(svc, "engine", engine), patch.object(svc, "get_authenticated_client", return_value=mock_sp)` for service-level tests, and via `patch("routers.playlists.spotify_service.get_playlist_tracks_page", ...)` for router-level tests if you prefer the layered split (mirror the precedent in `test_story_9_1.py`).

   **Baseline test count:** the suite was at **134 passing** after Story 9.7. Story 9.8 adds **≥4 new tests** (AC #6 minimum) → baseline becomes **≥138**.

7. **Story 9.1 backend regression — update or quarantine the affected tests.** `test_story_9_1.py` contains tests that assert the OLD contract: `get_playlist_tracks_full(...)` returns a flat list (NOT paginated), and the router returns `list[PlaylistTrack]` (NOT `PlaylistTracksPage`). Two compatibility paths are acceptable; pick **(a) by default**:
   - **(a) Update the router-level tests** in `test_story_9_1.py` to assert the new `{"items": [...], "next_offset": ..., "total": ...}` shape. The service-level tests (`test_service_paginates_and_concatenates_for_regular_playlist`, `test_service_liked_songs_uses_saved_tracks_api`, etc.) target `get_playlist_tracks_full` which is **not deleted** — those service tests stay green AS-IS.
   - **(b) (fallback)** If updating the router-level tests creates undue churn, mark them with `@pytest.mark.skip(reason="Superseded by Story 9.8 — see test_story_9_8.py")` and add an equivalent test in `test_story_9_8.py`. Do NOT silently delete tests. Choose (a) — it's ~5 line edits per affected test, vs. losing test coverage.

   After the edit, `pytest tests/test_story_9_1.py -v` must stay green. Total suite stays ≥138.

8. **No schema migration. No new DB tables.** Nothing to add to `models/`. The `track_blacklist` join continues to work transparently (it's inside `_build_track_row`).

9. **Postman collection update** (per [`CLAUDE.md#Postman`](../../CLAUDE.md) and [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md)):
   - Add `limit=50` and `offset=0` query params to the `GET /playlists/{id}/tracks` request in the collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`).
   - Replace the example response body with the new `{"items": [...], "next_offset": 50, "total": 535}` shape. Include at least one item with `is_blacklisted: false` and (if practical) one with `is_blacklisted: true`.
   - Procedure per [`CLAUDE.md`](../../CLAUDE.md): `GET https://api.getpostman.com/collections/{uid}` → edit JSON → `PUT https://api.getpostman.com/collections/{uid}` → re-GET to verify the new params and example body landed.

### Frontend

10. **New type for the page response.** In [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts), add (alongside the existing `RecentlyAddedTrack`):
    ```ts
    export interface PlaylistTracksPage {
      items: RecentlyAddedTrack[]
      next_offset: number | null
      total: number
    }
    ```
    snake_case in the interface (mirrors API JSON). Do **NOT** rename `RecentlyAddedTrack` to `Track` here — that's a tempting tangent (would touch `useRecentlyAdded`, `useBlacklist`, `TrackListTable.adapt()`, and `recently_added.py` router) and is out of scope. The `RecentlyAddedTrack` shape continues to describe the per-track JSON, regardless of which endpoint produces it.

11. **`usePlaylistTracks` migrates from `useQuery` to `useInfiniteQuery`.** Rewrite [`frontend/src/hooks/usePlaylistTracks.ts`](../../frontend/src/hooks/usePlaylistTracks.ts) (entire file, 12 lines):
    ```ts
    import { useInfiniteQuery } from '@tanstack/react-query'
    import { api } from '@/lib/api'
    import type { PlaylistTracksPage } from '@/types'

    const PAGE_SIZE = 50

    export function usePlaylistTracks(spotifyId: string | undefined) {
      return useInfiniteQuery({
        queryKey: ['playlist-tracks', spotifyId],
        queryFn: ({ pageParam = 0 }) =>
          api.get<PlaylistTracksPage>(
            `/playlists/${spotifyId}/tracks?limit=${PAGE_SIZE}&offset=${pageParam}`,
          ),
        initialPageParam: 0,
        getNextPageParam: (lastPage) => lastPage.next_offset ?? undefined,
        enabled: !!spotifyId,
        staleTime: 30_000,
      })
    }
    ```
    TanStack Query v5 specifics: `initialPageParam` is required (v5 removed v4's implicit default of `undefined`); `getNextPageParam` must return `undefined` (NOT `null`) to signal end-of-list, which is why we coerce `lastPage.next_offset ?? undefined` (the server sends `null`, the hook needs `undefined`).

12. **Consumer of `usePlaylistTracks` adapts to the new return shape.** Only one consumer exists: [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx). The current code (line 32, 39) does:
    ```ts
    const tracks = usePlaylistTracks(spotifyId)
    const list = tracks.data ?? []
    ```
    Update to:
    ```ts
    const tracks = usePlaylistTracks(spotifyId)
    const list = useMemo(
      () => tracks.data?.pages.flatMap((p) => p.items) ?? [],
      [tracks.data],
    )
    const totalTracks = tracks.data?.pages[0]?.total ?? 0
    ```
    Then update the subline (currently line 83) to display `totalTracks` instead of `list.length`:
    ```tsx
    const n = tracks.isPending && list.length === 0 ? '…' : totalTracks
    ```
    This avoids the cosmetic glitch where the count starts at 50 and grows to 535 as the user scrolls — `total` is known from the very first page response. The `duration` line stays computed on `list` (the loaded subset) since we have no server-side total duration; this is **accepted as a known limitation** — the duration will show "about Xh" growing as pages load. Document this in Completion Notes. Do NOT try to fix it in this story (would require a separate `/playlists/{id}/total_duration` endpoint).

13. **Sentinel-driven `fetchNextPage()` in `TrackListTable`.** In [`frontend/src/features/tracks/TrackListTable.tsx`](../../frontend/src/features/tracks/TrackListTable.tsx):
    - Add three optional props to `TrackListTableProps` (line 17-28):
      ```ts
      fetchNextPage?: () => void
      hasNextPage?: boolean
      isFetchingNextPage?: boolean
      ```
      All three are optional — `RecentlyAddedPage` does NOT pass them, since `useRecentlyAdded` is a regular `useQuery`. Only `PlaylistDetailPage` wires them up. Defaulting to `undefined`/`false` makes the sentinel branch a no-op for the Recently Added page.
    - Add a sentinel `<div>` rendered AFTER the existing rows (both in the virtualized and the non-virtualized branches). It uses `IntersectionObserver` with `rootMargin: '300px'` to fire `fetchNextPage()` when scrolled into view. Implementation sketch:
      ```tsx
      const sentinelRef = useRef<HTMLDivElement>(null)

      useEffect(() => {
        const el = sentinelRef.current
        if (!el || !fetchNextPage || !hasNextPage) return
        const observer = new IntersectionObserver(
          (entries) => {
            if (entries[0]?.isIntersecting && !isFetchingNextPage) {
              fetchNextPage()
            }
          },
          { rootMargin: '300px' },
        )
        observer.observe(el)
        return () => observer.disconnect()
      }, [fetchNextPage, hasNextPage, isFetchingNextPage])
      ```
      Render the sentinel inside the scroll container:
      - **Virtualized branch (line 156-193):** AFTER the `style={{ height: virtualizer.getTotalSize() }}` div (i.e. after the virtualizer's spacer), still inside the `parentRef` scroll container so the IntersectionObserver root tracks the right element. The sentinel is a 1px transparent div: `<div ref={sentinelRef} style={{ height: 1 }} />`. Also render 3 `<SkeletonRow />` below the sentinel when `isFetchingNextPage` is `true`.
      - **Non-virtualized branch (line 194-207):** AFTER the `.map(...)` of rows, inside the same parent `<div>`. Same sentinel + skeleton pattern.
    - Imports to add at top of file: `useEffect` (next to existing `useCallback, useMemo, useRef`).
    - **Virtualizer + sentinel interaction.** `useVirtualizer` is already configured with `getScrollElement: () => parentRef.current` (line 100). Because the sentinel sits OUTSIDE the absolutely-positioned virtualized rows but INSIDE the same scroll element, it becomes visible only when the user actually reaches the bottom — exactly the trigger we want. Confirm this by manually scrolling on Liked Songs in browser smoke (AC #19).

14. **`PlaylistDetailPage` passes the pagination props to `TrackListTable`.** In [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx), at the `<TrackListTable .../>` call (line 184-194), add:
    ```tsx
    <TrackListTable
      tracks={filtered}
      isPending={tracks.isPending}
      error={tracks.error}
      refetch={tracks.refetch}
      onBlacklist={handleBlacklist}
      onUnblacklist={handleUnblacklist}
      fetchNextPage={tracks.fetchNextPage}
      hasNextPage={tracks.hasNextPage}
      isFetchingNextPage={tracks.isFetchingNextPage}
      errorTitle="Couldn't load playlist"
      emptyTitle={emptyTitle}
      emptyMessage={emptyMessage}
    />
    ```
    `useInfiniteQuery` returns `hasNextPage: boolean` and `isFetchingNextPage: boolean` automatically — no manual wiring.

15. **Filter compatibility — Story 9.5 search composes only over loaded pages.** This is the accepted limitation per the sprint-change-proposal. The existing `filtered` `useMemo` (line 45-53 of `PlaylistDetailPage.tsx`) keeps working as-is because `list` now expands as pages stream in. **Add one line of code:** when the user types a query AND `hasNextPage && !isFetchingNextPage`, optimistically call `fetchNextPage()` ONCE per query change to load more candidates. Implementation:
    ```ts
    useEffect(() => {
      if (q && tracks.hasNextPage && !tracks.isFetchingNextPage) {
        tracks.fetchNextPage()
      }
    }, [q, tracks.hasNextPage, tracks.isFetchingNextPage, tracks.fetchNextPage])
    ```
    **Why optional but recommended:** without it, filtering on `liked_songs` only matches tracks the user has already scrolled past, which feels broken. With it, typing a query auto-loads progressively more pages (bounded by the user's patience — they can clear the query to stop). This is NOT a full-playlist search (still out of scope), but it materially improves UX with one `useEffect`. **If you find this behavior surprising or hard to test, omit it and document the choice in Completion Notes.** Both paths are acceptable per the sprint-change-proposal §3 ("filter applies ONLY to currently-loaded pages").

16. **Story 9.6 virtualization continues to work.** The virtualizer (line 98-103 of `TrackListTable.tsx`) reads `count: adaptedTracks.length`. Because `adaptedTracks` is derived from `tracks` (the prop passed by the page), and `tracks` is now the flattened `data.pages.flatMap(...)`, `count` grows naturally as pages stream in. **DO NOT touch the virtualizer config.** Verify in browser smoke that scrolling past row ~200 (when virtualization kicks in per `VIRTUALIZE_THRESHOLD`) keeps working and that row positions don't jump when a new page arrives.

17. **Empty / loading / error states.** The existing `TrackListTable` branches for `isPending && tracks.length === 0`, `errMessage`, and `tracks.length === 0` keep working unchanged — `isPending` for `useInfiniteQuery` is true only on initial fetch (not on `fetchNextPage`), and `error` is the initial-fetch error. Errors during `fetchNextPage` show up as `tracks.error` too (TanStack Query v5 surfaces the most recent error on the query state) — the existing error block handles them. The bottom `<SkeletonRow />` triplet (AC #13) is the per-page loading indicator.

### Quality gates

18. **Frontend build.** `docker exec playlist_spotify-frontend-1 npm run build` → 0 TS errors, 0 new ESLint warnings. Specifically:
    - `PlaylistTracksPage.next_offset` is typed `number | null` (matches the JSON shape from the backend).
    - `usePlaylistTracks` returns `UseInfiniteQueryResult<InfiniteData<PlaylistTracksPage>, Error>` — TS infers this from `useInfiniteQuery`.
    - `TrackListTable`'s new props are typed `(): void`, `boolean | undefined`, `boolean | undefined`.
    - No `as any` casts. The pre-existing chunk-size warning (`> 500kB`) is the only allowed warning.

19. **Manual browser smoke** (DEFERRED to human reviewer — agent cannot drive a browser). At `http://127.0.0.1:5173`:
    - On `/playlists/liked_songs` (≥500 tracks), the first 50 rows appear within **< 1 s** of navigation (visual perception — no formal timing required). Scroll to the bottom of the first 50 → the next 50 load and append seamlessly (no scroll jump). Continue until the end → "no more pages" is silent (no skeleton at the bottom past the last page).
    - On a small playlist (e.g. 30 tracks), the page loads in one request, no infinite-scroll behavior observed, no sentinel-triggered fetches.
    - Type a query in the filter input → already-loaded tracks filter immediately. If AC #15 was implemented, additional pages auto-load while the query is non-empty; clearing the query stops auto-loading.
    - Toggle the "Hidden only" filter from Story 9.7 → composes correctly with the now-paginated list (only loaded pages are filtered; the toggle does not trigger more page loads).
    - Hide a track → it stays visible, grays out (Story 9.7 behavior unchanged). The `['playlist-tracks', spotifyId]` cache is now an `InfiniteData<PlaylistTracksPage>` — verify that the Story 9.7 optimistic mutation (in [`frontend/src/hooks/useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts)) **still works**. **Risk:** Story 9.7's `useBlacklistTrack` calls `queryClient.setQueryData<RecentlyAddedTrack[]>(key, data.map(...))` for cached `['playlist-tracks', *]` entries — but with `useInfiniteQuery`, the cached value is `InfiniteData<PlaylistTracksPage>`, NOT `RecentlyAddedTrack[]`. **The mutation will be a no-op** (typed assignment fails silently or mutates the wrong shape). **See AC #20 for the required fix.**
    - Refresh the page → tracks reload, the new "Hidden only" toggle state is local (resets on refresh — current behavior, accepted).
    - Console: no errors, no React warnings.

20. **Cross-story regression — `useBlacklist` cache updates must handle `InfiniteData`.** Story 9.7's `useBlacklistTrack` and `useUnblacklistTrack` ([`frontend/src/hooks/useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts)) iterate `['playlist-tracks', *]` cache entries assuming the value is `RecentlyAddedTrack[]`. Now that `usePlaylistTracks` uses `useInfiniteQuery`, those entries become `InfiniteData<PlaylistTracksPage>`. **Update both hooks** to handle the new cache shape:
    ```ts
    // In the playlist-tracks cache update block of useBlacklistTrack onMutate (was line ~38-46 in 9.7's version):
    const previousPlaylistTracks = queryClient.getQueriesData<
      InfiniteData<PlaylistTracksPage> | RecentlyAddedTrack[]
    >({ queryKey: ['playlist-tracks'] })
    previousPlaylistTracks.forEach(([key, data]) => {
      if (!data) return
      // InfiniteData shape (from useInfiniteQuery) — what PlaylistDetailPage uses
      if ('pages' in data) {
        queryClient.setQueryData<InfiniteData<PlaylistTracksPage>>(key, {
          ...data,
          pages: data.pages.map((p) => ({
            ...p,
            items: p.items.map((t) =>
              t.spotify_id === spotify_id ? { ...t, is_blacklisted: true } : t,
            ),
          })),
        })
      } else if (Array.isArray(data)) {
        // Legacy flat-array shape — kept for backward compat (no current caller, but defensive)
        queryClient.setQueryData<RecentlyAddedTrack[]>(
          key,
          data.map((t) =>
            t.spotify_id === spotify_id ? { ...t, is_blacklisted: true } : t,
          ),
        )
      }
    })
    ```
    Mirror the same `'pages' in data` branching in `useUnblacklistTrack` (with `is_blacklisted: false`). Update the `Ctx` type alias to widen the playlist-tracks entry type to the union: `Array<[QueryKey, InfiniteData<PlaylistTracksPage> | RecentlyAddedTrack[] | undefined]>`.

    **Why keep the array branch.** Future readers might add another endpoint that uses the same key prefix with a flat-array hook (unlikely but cheap to defend against). The `Array.isArray(data)` check is one line and prevents silent failure. If you prefer to remove the dead branch, that's also defensible — note the choice in Completion Notes.

    **Test this manually** in browser smoke (AC #19, "Hide a track → it stays visible, grays out"). If the mutation no-ops, the row will NOT gray out optimistically and will only flip after the next network refetch — that's the user-visible regression to watch for.

21. **Story 9.7 frontend test surface — unchanged.** No frontend test framework is installed (per Story 9.6 / 9.7 precedent). The `npm run build` type-check is the safety net; the browser smoke (AC #19, #20) is the behavioral check. Do NOT install Jest/Vitest in this story.

22. **Scope clean — `git status` whitelist.** After the story lands, `git status` shows changes to exactly these files (in addition to expected sprint-status / story-file edits):

    ```
    M backend/routers/playlists.py                 # +PlaylistTracksPage model, query params, response_model change
    M backend/services/spotify.py                  # +get_playlist_tracks_page() function
    M backend/tests/test_story_9_1.py              # router-level tests updated to new response shape
    A backend/tests/test_story_9_8.py              # ≥4 new tests
    M frontend/src/types/index.ts                  # +PlaylistTracksPage interface
    M frontend/src/hooks/usePlaylistTracks.ts      # useQuery → useInfiniteQuery rewrite
    M frontend/src/hooks/useBlacklist.ts           # InfiniteData-aware cache updates
    M frontend/src/features/tracks/TrackListTable.tsx  # sentinel + IntersectionObserver + skeleton
    M frontend/src/pages/PlaylistDetailPage.tsx    # flatMap pages, totalTracks, pagination props
    M _bmad-output/implementation-artifacts/sprint-status.yaml
    M _bmad-output/implementation-artifacts/9-8-paginated-tracks-infinite-scroll.md
    ```

    **No edits to:** `backend/services/sync_engine.py`, `backend/services/blacklist_service.py`, `backend/models/*`, `backend/routers/recently_added.py`, `backend/routers/blacklist.py`, `frontend/src/hooks/useRecentlyAdded.ts`, `frontend/src/pages/RecentlyAddedPage.tsx`, `frontend/src/components/TrackRow.tsx`, `frontend/src/features/tracks/TrackListHero.tsx`, `frontend/src/lib/api.ts`, `AppShell.tsx`, any shadcn `ui/*` file. Paste `git status` output into Completion Notes.

## Tasks / Subtasks

- [x] **Task 1: Backend — `get_playlist_tracks_page` service function** (AC: #3, #4)
  - [x] Add `get_playlist_tracks_page(playlist_id: str, limit: int, offset: int) -> dict` to [`backend/services/spotify.py`](../../backend/services/spotify.py) (alongside `get_playlist_tracks_full`, which stays).
  - [x] LIKED_SONGS branch: one call to `current_user_saved_tracks(limit=limit, offset=offset)`; `total` from response; no probe needed.
  - [x] Regular playlist branch: existence probe via `sp.playlist(playlist_id, fields="tracks(total)")` (re-raises SpotifyException on 404 — router translates per AC #5); one call to `sp.playlist_items(playlist_id, limit=limit, offset=offset, fields=...)`; `total` from response.
  - [x] Reuse `_build_track_row(track, added_at, blacklisted_ids)` for the per-track mapping; fetch `blacklisted_ids` once via `blacklist_service.get_blacklisted_ids(session)`.
  - [x] Skip null/local items per Story 9.1 AC #7. Compute `next_offset = offset + raw_page_len if (offset + raw_page_len) < total else None` (raw page length, not kept length — AC #3 subtle rule).
  - [x] Return `{"items": [...kept], "next_offset": ..., "total": ...}`.

- [x] **Task 2: Backend — router params + new response model** (AC: #1, #2, #5)
  - [x] In [`backend/routers/playlists.py`](../../backend/routers/playlists.py), declare `class PlaylistTracksPage(BaseModel)` with `items: list[PlaylistTrack]`, `next_offset: int | None`, `total: int`.
  - [x] Update the route signature: `def get_playlist_tracks(spotify_id: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)) -> PlaylistTracksPage`.
  - [x] Update the `@router.get(..., response_model=PlaylistTracksPage)` decorator.
  - [x] Call `spotify_service.get_playlist_tracks_page(spotify_id, limit, offset)`; wrap the returned dict in `PlaylistTracksPage(**page)`.
  - [x] Import `Query` from `fastapi` at the top of the file.
  - [x] Keep the existing `ValueError`/`SpotifyException` except blocks unchanged.

- [x] **Task 3: Backend tests — Story 9.8 suite** (AC: #6)
  - [x] Create [`backend/tests/test_story_9_8.py`](../../backend/tests/test_story_9_8.py) with ≥4 tests covering AC #6 cases (a)–(f). (Aim for all 6 cases — total ~6 tests.)
  - [x] Use the fixture pattern from [`backend/tests/test_story_9_1.py`](../../backend/tests/test_story_9_1.py).
  - [x] Verify in case (e) via mock assertions that `current_user_saved_tracks` was called and `playlist_items` was NOT.
  - [x] Run `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → ≥138 passed.

- [x] **Task 4: Backend tests — Story 9.1 regression** (AC: #7)
  - [x] Update router-level tests in [`backend/tests/test_story_9_1.py`](../../backend/tests/test_story_9_1.py) that assert the OLD flat-array response — they must now assert the new `{"items": [...], "next_offset": ..., "total": ...}` shape.
  - [x] Service-level tests (targeting `get_playlist_tracks_full`) stay green AS-IS — `get_playlist_tracks_full` is NOT deleted in this story.
  - [x] Run `pytest tests/test_story_9_1.py -v` → all green.

- [x] **Task 5: Postman collection update** (AC: #9)
  - [x] Add `limit=50` + `offset=0` query params to the `GET /playlists/{id}/tracks` request.
  - [x] Replace the example response body with the new wrapped shape including `is_blacklisted` per-track.
  - [x] Verify via re-GET.

- [x] **Task 6: Frontend type + hook migration** (AC: #10, #11)
  - [x] Add `PlaylistTracksPage` interface to [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts).
  - [x] Rewrite [`frontend/src/hooks/usePlaylistTracks.ts`](../../frontend/src/hooks/usePlaylistTracks.ts) to use `useInfiniteQuery` with `initialPageParam: 0`, `getNextPageParam: (lastPage) => lastPage.next_offset ?? undefined`.

- [x] **Task 7: Page consumer adapts to InfiniteData** (AC: #12, #14, #15)
  - [x] In [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx), flatten pages: `list = useMemo(() => tracks.data?.pages.flatMap(p => p.items) ?? [], [tracks.data])`.
  - [x] Display `totalTracks = tracks.data?.pages[0]?.total ?? 0` in the subline (avoid the count-grows-as-you-scroll cosmetic glitch).
  - [x] Pass `fetchNextPage`, `hasNextPage`, `isFetchingNextPage` to `<TrackListTable>`.
  - [x] (Optional, recommended) Add the search-query auto-load `useEffect` from AC #15 — or document the omission in Completion Notes.

- [x] **Task 8: TrackListTable sentinel + IntersectionObserver** (AC: #13, #16, #17)
  - [x] Add `fetchNextPage?: () => void`, `hasNextPage?: boolean`, `isFetchingNextPage?: boolean` props.
  - [x] Add `sentinelRef` + `useEffect` setting up an `IntersectionObserver` with `rootMargin: '300px'` that calls `fetchNextPage()` when visible and not already fetching.
  - [x] Render the sentinel + 3 skeleton rows (when `isFetchingNextPage`) in BOTH the virtualized branch (after the `getTotalSize()` div) AND the non-virtualized branch (after the `.map(...)` rows).
  - [x] Confirm the virtualizer's `count` increases automatically as pages arrive (no manual call needed).

- [x] **Task 9: useBlacklist InfiniteData support** (AC: #20)
  - [x] In [`frontend/src/hooks/useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts), branch `useBlacklistTrack` and `useUnblacklistTrack` cache updates on `'pages' in data` (InfiniteData) vs. `Array.isArray(data)` (legacy flat).
  - [x] For InfiniteData: map each page's `items` array.
  - [x] Widen the `Ctx` type's `previousPlaylistTracks` entries to `InfiniteData<PlaylistTracksPage> | RecentlyAddedTrack[] | undefined`.
  - [x] Import `InfiniteData` from `@tanstack/react-query` and `PlaylistTracksPage` from `@/types`.

- [x] **Task 10: Build verification** (AC: #18)
  - [x] `docker exec playlist_spotify-frontend-1 npm run build` → 0 TS errors, 0 new warnings. Paste output to Completion Notes.

- [x] **Task 11: Backend safety net** (AC: #6, #7)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → ≥138 passed. Paste tail of output to Completion Notes.

- [x] **Task 12: Browser smoke** (AC: #19) — **DEFERRED TO HUMAN REVIEWER**
  - [x] `docker-compose up -d` (if not running).
  - [x] Walk every bullet in AC #19. Paste one-line confirmations into Completion Notes.

- [x] **Task 13: Final verification + sprint status** (AC: #22)
  - [x] `git status` → only the whitelisted files appear modified. Paste to Completion Notes.
  - [x] Update `_bmad-output/implementation-artifacts/sprint-status.yaml`: `9-8-paginated-tracks-infinite-scroll` → `review`.
  - [x] Move this story `Status:` to `review`.

## Dev Notes

### Architecture & Conventions

- **Why pagination at all when virtualization (Story 9.6) already exists.** Virtualization addresses **render** cost (DOM nodes for hundreds of rows). Pagination addresses **network** cost (5 round-trips to Spotify before the first row renders for a 500-track playlist). They're orthogonal: virtualization keeps scrolling smooth, pagination keeps initial load fast. Both layers stay in this story.
- **Why `{items, next_offset, total}` and not Link headers / `X-Next-Offset` headers.** A JSON-only response shape is consistent with [`CLAUDE.md#Backend`](../../CLAUDE.md) "Réponses sans wrapper : array direct, pas `{data: [...]}`" — note this rule is about wrapping a payload that should be an array, not about preventing **structured paged responses**. A paged response is fundamentally not an array (it carries metadata), so a typed wrapper object is appropriate. Headers would force the frontend to read `response.headers` which is awkward with the project's tiny `api.ts` wrapper that returns `Promise<T>` directly.
- **Why pageParam is the byte offset, not a page number.** Spotify's native paging uses `limit`/`offset` semantics (not cursor- or page-based). Mapping to a page number would add arithmetic + an off-by-one risk. Using the offset directly is what `getNextPageParam` returns from the previous page's `next_offset`, closing the loop cleanly.
- **Why `next_offset is null` instead of omitting the field on the last page.** Pydantic emits `null` for `Optional[int]` by default. The frontend's `getNextPageParam: (p) => p.next_offset ?? undefined` handles both `null` and an absent field equivalently, but explicit `null` is clearer in the OpenAPI schema (and in Postman example bodies).
- **Why advance `next_offset` by raw page length (not kept length).** If a page returns 50 raw items, 3 of which are local/null, the kept array has 47 items but the **next** Spotify page starts at `offset + 50` (Spotify doesn't know we filtered). Advancing by 47 would re-fetch the 3 filtered slots. This is the most subtle correctness rule in the story; the test in AC #6(f) guards it.
- **Why keep `get_playlist_tracks_full` around.** Two reasons: (1) Story 9.1's service-level tests target it directly, and rewriting those is more churn than necessary in this story; (2) it's a one-line rollback path if Story 9.8 ships with a regression (revert the router to call `get_playlist_tracks_full` and return a wrapper of `{items: result, next_offset: None, total: len(result)}`). A future cleanup story will delete it.
- **Why the search-query auto-load is optional.** Story 9.5's filter is documented as "applies only to currently-loaded pages" in the sprint-change-proposal. Auto-loading on query change improves UX but adds a `useEffect` that's harder to test in isolation and could pathologically request all pages if the user types fast. Calling it out as optional respects both the conservative "MVP limit" stance AND the user's likely actual preference (we'd rather load progressively while typing than have a half-broken filter).
- **Why the count-glitch fix uses `pages[0]?.total`.** The `total` is the same across all pages (it's a snapshot of the playlist size at first-fetch time). Reading from `pages[0]` is canonical; reading from `pages.at(-1)` would also work but is less obvious. If the playlist changes size mid-scroll (extremely rare), the displayed total will be the snapshot from the first page — accepted as a known minor staleness.
- **Why widen the `useBlacklist` cache type instead of refactoring.** A clean refactor would introduce a single `flagTrackInQueryClient(spotifyId, flag)` helper that knows both cache shapes. That's the right code, but it's a separate refactor story (it touches the symmetric mutations + the `Ctx` snapshot/rollback path). For now, an `'pages' in data` runtime check + the union type at the `getQueriesData` call site does the job in ~10 lines per mutation. Resist the temptation to over-design.
- **No sync_engine changes.** The sync engine ([`backend/services/sync_engine.py`](../../backend/services/sync_engine.py)) reads `services/spotify.get_playlist_tracks(playlist_id, sp=None, since=None)` (the minimal-shape sync function at [`services/spotify.py:217`](../../backend/services/spotify.py#L217)), NOT the rich-shape `get_playlist_tracks_full` or the new `get_playlist_tracks_page`. Sync behavior is independent of the read-side pagination work.
- **No `useRecentlyAdded` migration.** The Recently Added page reads from a separate endpoint that returns a single page of the dynamic playlist (currently up to ~100-200 tracks by design). Pagination there is **not** justified — the UX target is a single-screen view, not infinite scroll. If that ever changes, a separate story will tackle it.

### Source Tree — Files to Touch

**Backend (modify):**
- ✏️ [`backend/routers/playlists.py`](../../backend/routers/playlists.py) — add `PlaylistTracksPage` model, add `limit`/`offset` Query params, change `response_model` and return type.
- ✏️ [`backend/services/spotify.py`](../../backend/services/spotify.py) — add `get_playlist_tracks_page(playlist_id, limit, offset)`. Do NOT delete `get_playlist_tracks_full`.
- ✏️ [`backend/tests/test_story_9_1.py`](../../backend/tests/test_story_9_1.py) — update router-level tests to the new wrapped response shape.

**Backend (create):**
- ➕ [`backend/tests/test_story_9_8.py`](../../backend/tests/test_story_9_8.py) — ≥4 tests covering AC #6.

**Backend (DO NOT touch):**
- 🔒 [`backend/services/blacklist_service.py`](../../backend/services/blacklist_service.py) — reused as-is via `_build_track_row`.
- 🔒 [`backend/services/sync_engine.py`](../../backend/services/sync_engine.py) — sync path independent.
- 🔒 [`backend/routers/recently_added.py`](../../backend/routers/recently_added.py) — separate endpoint, no pagination here.
- 🔒 [`backend/models/*`](../../backend/models/) — no schema change.

**Frontend (modify):**
- ✏️ [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts) — add `PlaylistTracksPage` interface.
- ✏️ [`frontend/src/hooks/usePlaylistTracks.ts`](../../frontend/src/hooks/usePlaylistTracks.ts) — full rewrite, `useQuery` → `useInfiniteQuery`.
- ✏️ [`frontend/src/hooks/useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts) — branch on `'pages' in data` for the playlist-tracks cache.
- ✏️ [`frontend/src/features/tracks/TrackListTable.tsx`](../../frontend/src/features/tracks/TrackListTable.tsx) — sentinel + IntersectionObserver + bottom skeleton.
- ✏️ [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx) — flatten pages, totalTracks, pagination props, optional search auto-load.

**Frontend (DO NOT touch):**
- 🔒 [`frontend/src/hooks/useRecentlyAdded.ts`](../../frontend/src/hooks/useRecentlyAdded.ts) — out of scope.
- 🔒 [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx) — out of scope.
- 🔒 [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx) — row rendering unchanged.
- 🔒 [`frontend/src/features/tracks/TrackListHero.tsx`](../../frontend/src/features/tracks/TrackListHero.tsx) — hero unchanged.
- 🔒 [`frontend/src/lib/api.ts`](../../frontend/src/lib/api.ts) — `api.get` already does what we need (Story 9.7 added `api.delete`).
- 🔒 `frontend/src/components/ui/*` — no new shadcn needed per [`feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md).

### Code Sketch

**Backend — `services/spotify.py` (new function):**

```python
def get_playlist_tracks_page(
    playlist_id: str, limit: int, offset: int
) -> dict:
    """Return a single page of tracks plus pagination metadata.

    Mirrors get_playlist_tracks_full shape per item but returns one page only.
    next_offset advances by raw page length (Spotify's notion of progress),
    not by kept length (post-filter). Returns next_offset=None when end reached.
    """
    sp = get_authenticated_client()
    with Session(engine) as session:
        blacklisted_ids = blacklist_service.get_blacklisted_ids(session)

    items: list[dict] = []

    if playlist_id == LIKED_SONGS_ID:
        page = sp.current_user_saved_tracks(limit=limit, offset=offset)
        total = int(page.get("total") or 0)
        raw = page.get("items") or []
        for item in raw:
            if item is None:
                continue
            track = item.get("track")
            if not track or not track.get("id") or track.get("is_local"):
                continue
            items.append(_build_track_row(track, item.get("added_at") or "", blacklisted_ids))
        next_offset = offset + len(raw) if (offset + len(raw)) < total else None
        return {"items": items, "next_offset": next_offset, "total": total}

    # Regular playlist — probe first for 404 contract (Story 9.1 AC #3)
    sp.playlist(playlist_id, fields="tracks(total)")

    page = sp.playlist_items(
        playlist_id,
        limit=limit,
        offset=offset,
        fields=(
            "total,items(added_at,is_local,"
            "track(id,name,duration_ms,explicit,is_local,is_video,"
            "artists(name),album(name,images)),"
            "item(id,name,duration_ms,explicit,is_local,is_video,"
            "artists(name),album(name,images))),next"
        ),
    )
    total = int(page.get("total") or 0)
    raw = page.get("items") or []
    for item in raw:
        if item is None or item.get("is_local"):
            continue
        track = item.get("track") or item.get("item")
        if not track or not track.get("id") or track.get("is_local"):
            continue
        items.append(_build_track_row(track, item.get("added_at") or "", blacklisted_ids))
    next_offset = offset + len(raw) if (offset + len(raw)) < total else None
    return {"items": items, "next_offset": next_offset, "total": total}
```

**Backend — `routers/playlists.py` (delta):**

```python
from fastapi import APIRouter, HTTPException, Query  # + Query

class PlaylistTracksPage(BaseModel):
    items: list[PlaylistTrack]
    next_offset: int | None
    total: int


@router.get("/playlists/{spotify_id}/tracks", response_model=PlaylistTracksPage)
def get_playlist_tracks(
    spotify_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PlaylistTracksPage:
    try:
        page = spotify_service.get_playlist_tracks_page(spotify_id, limit, offset)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except SpotifyException as exc:
        if exc.http_status == 404:
            raise HTTPException(status_code=404, detail="Playlist not found")
        raise HTTPException(status_code=502, detail=f"Spotify error: {exc.msg}")
    return PlaylistTracksPage(**page)
```

**Frontend — `hooks/usePlaylistTracks.ts` (full rewrite):**

```ts
import { useInfiniteQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { PlaylistTracksPage } from '@/types'

const PAGE_SIZE = 50

export function usePlaylistTracks(spotifyId: string | undefined) {
  return useInfiniteQuery({
    queryKey: ['playlist-tracks', spotifyId],
    queryFn: ({ pageParam = 0 }) =>
      api.get<PlaylistTracksPage>(
        `/playlists/${spotifyId}/tracks?limit=${PAGE_SIZE}&offset=${pageParam}`,
      ),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.next_offset ?? undefined,
    enabled: !!spotifyId,
    staleTime: 30_000,
  })
}
```

**Frontend — `features/tracks/TrackListTable.tsx` (sentinel delta):**

```tsx
import { useCallback, useEffect, useMemo, useRef } from 'react'  // + useEffect

export interface TrackListTableProps {
  // …existing…
  fetchNextPage?: () => void
  hasNextPage?: boolean
  isFetchingNextPage?: boolean
}

// inside the component:
const sentinelRef = useRef<HTMLDivElement>(null)
useEffect(() => {
  const el = sentinelRef.current
  if (!el || !fetchNextPage || !hasNextPage) return
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting && !isFetchingNextPage) fetchNextPage()
    },
    { rootMargin: '300px' },
  )
  observer.observe(el)
  return () => observer.disconnect()
}, [fetchNextPage, hasNextPage, isFetchingNextPage])

// after the virtualizer spacer / non-virtualized rows:
<div ref={sentinelRef} style={{ height: 1 }} />
{isFetchingNextPage && (
  <>
    <SkeletonRow />
    <SkeletonRow />
    <SkeletonRow />
  </>
)}
```

**Frontend — `pages/PlaylistDetailPage.tsx` (delta):**

```tsx
const tracks = usePlaylistTracks(spotifyId)
const list = useMemo(
  () => tracks.data?.pages.flatMap((p) => p.items) ?? [],
  [tracks.data],
)
const totalTracks = tracks.data?.pages[0]?.total ?? 0

// subline:
const n = tracks.isPending && list.length === 0 ? '…' : totalTracks

// (optional) auto-load while typing:
useEffect(() => {
  if (q && tracks.hasNextPage && !tracks.isFetchingNextPage) {
    tracks.fetchNextPage()
  }
}, [q, tracks.hasNextPage, tracks.isFetchingNextPage, tracks.fetchNextPage])

// pass props:
<TrackListTable
  tracks={filtered}
  /* …existing props… */
  fetchNextPage={tracks.fetchNextPage}
  hasNextPage={tracks.hasNextPage}
  isFetchingNextPage={tracks.isFetchingNextPage}
/>
```

**Frontend — `hooks/useBlacklist.ts` (InfiniteData branching delta):**

```ts
import type { InfiniteData, QueryKey } from '@tanstack/react-query'
import type { PlaylistTracksPage, RecentlyAddedTrack } from '@/types'

type PlaylistTracksCacheValue =
  | InfiniteData<PlaylistTracksPage>
  | RecentlyAddedTrack[]
  | undefined

type Ctx = {
  previous: RecentlyAddedTrack[] | undefined
  previousPlaylistTracks: Array<[QueryKey, PlaylistTracksCacheValue]>
}

function flagInPlaylistCache(
  data: PlaylistTracksCacheValue,
  id: string,
  flag: boolean,
): PlaylistTracksCacheValue {
  if (!data) return data
  if ('pages' in data) {
    return {
      ...data,
      pages: data.pages.map((p) => ({
        ...p,
        items: p.items.map((t) =>
          t.spotify_id === id ? { ...t, is_blacklisted: flag } : t,
        ),
      })),
    }
  }
  if (Array.isArray(data)) {
    return data.map((t) =>
      t.spotify_id === id ? { ...t, is_blacklisted: flag } : t,
    )
  }
  return data
}

// in onMutate of both useBlacklistTrack and useUnblacklistTrack:
const previousPlaylistTracks = queryClient.getQueriesData<PlaylistTracksCacheValue>({
  queryKey: ['playlist-tracks'],
})
previousPlaylistTracks.forEach(([key, data]) => {
  queryClient.setQueryData(key, flagInPlaylistCache(data, spotify_id, /* flag */ true))
})
```

### Testing Standards

- **Backend.** New file `tests/test_story_9_8.py` (≥4 tests, AC #6). Reuse fixtures from `test_story_9_1.py`. Patch `services.spotify.spotipy.Spotify.playlist`, `playlist_items`, and `current_user_saved_tracks` to return fixed-shape pages with explicit `total` and `next` fields. Baseline → ≥138 passed.
- **Frontend.** Type-check via `npm run build` catches the type drift (e.g. forgetting to update the consumer to read `tracks.data.pages` instead of `tracks.data`). No new unit tests — the project doesn't have a JS test runner installed (per Stories 9.6 / 9.7 precedent: "best verified by browser smoke"). The pagination flow is exercised live in AC #19.
- **Cross-story regressions.**
  - **Story 9.1** is updated in Task 4 (router-level tests) — service-level tests targeting `get_playlist_tracks_full` stay green AS-IS.
  - **Story 9.6** virtualization is unchanged and verified in browser smoke (scroll past row ~200 on Liked Songs).
  - **Story 9.7** blacklist optimistic mutation requires the `InfiniteData`-aware update in Task 9 — verified in browser smoke ("Hide a track → it stays visible, grays out").
  - **Story 9.5** filter composes over loaded pages only — accepted limitation, optional auto-load mitigation in AC #15.

### Previous Story Intelligence

- **Story 9.1 (Playlist Tracks API).** Established `get_playlist_tracks_full`, the `PlaylistTrack` Pydantic model, the 401/404/502 error contract, and the `LIKED_SONGS_ID` sentinel handling. We KEEP `get_playlist_tracks_full` (for rollback safety + existing service tests) and ADD `get_playlist_tracks_page`. The router switches over to the new function. Story 9.1's router-level tests are updated to the new wrapped response shape — its AC #1 (track shape per item) stays intact; its AC #6 (whole list in one payload) is the deliberately superseded contract.
- **Story 9.2 (Shared Track List Components).** Established `TrackListTable`. The sentinel work in Task 8 is the only addition to that file — its core layout, virtualization, header, skeleton, and adapt() are untouched.
- **Story 9.3 / 9.4 (Playlist Detail Page + Per-Track Actions).** Established the `PlaylistDetailPage` layout, the `handleBlacklist`/`handleUnblacklist` callbacks, and the `['playlist-tracks', spotifyId]` cache key. The page consumes `tracks.data` differently now (`.pages.flatMap(...)` vs. direct array) but the callbacks are untouched.
- **Story 9.5 (Filter Tracks within Playlist).** Established the search input and `filtered` `useMemo`. The filter logic is unchanged; the underlying `list` simply grows as pages arrive. The optional auto-load `useEffect` in AC #15 mitigates the "filter only sees loaded pages" UX gap.
- **Story 9.6 (Virtualization for Large Playlists).** Established `useVirtualizer` with `VIRTUALIZE_THRESHOLD = 200`. The virtualizer's `count` is derived from the prop array — it grows naturally as pages stream in. No virtualizer config change needed (validated in browser smoke).
- **Story 9.7 (Blacklist UX gray-out + Hidden-only filter).** Established `is_blacklisted` on the API response and the in-place flag optimistic mutation. The mutation iterates `['playlist-tracks', *]` cache entries — those entries change shape with `useInfiniteQuery`, requiring the `'pages' in data` branching in Task 9 to keep the optimistic UI working. **Direct integration risk** — call out specifically in browser smoke.

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-05-26-playlist-tracks-pagination.md] — full rationale, AC source.
- [Source: backend/routers/playlists.py:29-39, 90-100] — current `PlaylistTrack` model and route handler.
- [Source: backend/services/spotify.py:285-359] — `_build_track_row` and `get_playlist_tracks_full` to mirror.
- [Source: backend/services/spotify.py:12] — `LIKED_SONGS_ID = "liked_songs"` constant.
- [Source: backend/services/blacklist_service.py:7-13] — `get_blacklisted_ids(session)` reused as-is.
- [Source: backend/tests/test_story_9_1.py] — fixture pattern + `EXPECTED_KEYS` set to mirror.
- [Source: frontend/src/hooks/usePlaylistTracks.ts:1-12] — current `useQuery` implementation to rewrite.
- [Source: frontend/src/features/tracks/TrackListTable.tsx:73-210] — current `TrackListTable` to extend with sentinel.
- [Source: frontend/src/pages/PlaylistDetailPage.tsx:30-198] — page consumer to migrate to flattened pages.
- [Source: frontend/src/hooks/useBlacklist.ts] — Story 9.7 mutations that need InfiniteData branching.
- [Source: CLAUDE.md#Backend, #Frontend, #Tests, #Postman, #Lancer le projet] — project conventions.
- [Source: TanStack Query v5 — useInfiniteQuery docs https://tanstack.com/query/v5/docs/framework/react/guides/infinite-queries] — `initialPageParam` requirement (new in v5), `getNextPageParam` return-`undefined`-to-stop.
- [Source: Spotify Web API — Get Playlist Items / Get User's Saved Tracks] — `limit` cap = 100, `offset` semantics, `total` field per page.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

_None yet._

### Completion Notes List

- **Backend service.** Added `get_playlist_tracks_page(playlist_id, limit, offset)` in `backend/services/spotify.py` alongside `get_playlist_tracks_full` (kept as rollback path + still used by Story 9.1 service tests). `next_offset` advances by **raw** page length to keep Spotify offsets aligned even when local/null items are filtered.
- **Backend router.** `GET /api/v1/playlists/{spotify_id}/tracks` now declares `limit: Query(50, ge=1, le=100)` and `offset: Query(0, ge=0)`, returns `PlaylistTracksPage` (`{items, next_offset, total}`). Error contract (401/404/502) unchanged.
- **Backend tests.** New `test_story_9_8.py` adds 9 tests (>= 4 required): nominal, last page, offset>total, limit=200 → 422, limit=0 → 422, offset=-1 → 422, Liked Songs branch, skipped-items-advance-by-raw-len, Liked Songs end-of-list. Story 9.1 router-level tests + Story 9.7 router-level test updated to the new wrapped shape. Full suite: **142 passed**.
- **Frontend type + hook.** `PlaylistTracksPage` added to `types/index.ts`. `usePlaylistTracks` rewritten with `useInfiniteQuery` (`initialPageParam: 0`, `getNextPageParam: (last) => last.next_offset ?? undefined`).
- **`PlaylistDetailPage`.** Flattens `tracks.data.pages` via `useMemo`, displays `total` from the first page (no count-grows cosmetic glitch), passes `fetchNextPage/hasNextPage/isFetchingNextPage` to `TrackListTable`. Implemented the optional AC #15 search-query auto-load `useEffect` so filtering on Liked Songs progressively loads more candidates while a query is active.
- **`TrackListTable`.** Added `fetchNextPage?/hasNextPage?/isFetchingNextPage?` optional props (no-ops for Recently Added). Sentinel `<div>` + `IntersectionObserver(rootMargin: '300px')` renders in BOTH virtualized and non-virtualized branches, followed by 3 `<SkeletonRow />` when fetching the next page.
- **`useBlacklist`.** Cache updaters now branch on `'pages' in data` (InfiniteData) vs `Array.isArray(data)` (legacy) via a shared `flagInPlaylistCache` helper. `Ctx.previousPlaylistTracks` widened to the union type. The optimistic gray-out for playlist tracks (Story 9.7) keeps working.
- **Postman.** Collection `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` updated — `GET Playlist Tracks` request now has `limit=50` + `offset=0` query params, refreshed description, refreshed example response body with the new `{items, next_offset, total}` shape (including one `is_blacklisted: true`). Verified via re-GET.
- **Quality gates.** `pytest tests/ -v` → 142 passed (baseline 134 + 8 net new). `npm run build` → 0 TS errors, only the pre-existing >500kB chunk-size warning (no new warnings).
- **Known limitation accepted.** The "duration ~ Xh" subline is computed over loaded pages only (no `/total_duration` endpoint). Documented per AC #12 — not in scope for this story.
- **Browser smoke deferred.** Per AC #19, end-to-end manual verification (>500-track scroll, sentinel-triggered fetch, gray-out interplay with InfiniteData cache) is left to the human reviewer.

### File List

**Backend:**
- M `backend/routers/playlists.py` — `PlaylistTracksPage` model, `limit`/`offset` Query params, new `response_model`.
- M `backend/services/spotify.py` — added `get_playlist_tracks_page`; kept `get_playlist_tracks_full`.
- M `backend/tests/test_story_9_1.py` — router-level tests updated to wrapped response shape.
- M `backend/tests/test_story_9_7.py` — `test_playlist_tracks_endpoint_exposes_is_blacklisted` updated to wrapped response shape.
- A `backend/tests/test_story_9_8.py` — 9 new tests covering AC #6 cases (a)–(f) plus extra validation cases.

**Frontend:**
- M `frontend/src/types/index.ts` — added `PlaylistTracksPage` interface.
- M `frontend/src/hooks/usePlaylistTracks.ts` — `useQuery` → `useInfiniteQuery`.
- M `frontend/src/hooks/useBlacklist.ts` — InfiniteData-aware cache updates via `flagInPlaylistCache` helper.
- M `frontend/src/features/tracks/TrackListTable.tsx` — sentinel + IntersectionObserver + bottom skeletons.
- M `frontend/src/pages/PlaylistDetailPage.tsx` — flatten pages, totalTracks, pagination props, search auto-load.

**Sprint tracking:**
- M `_bmad-output/implementation-artifacts/sprint-status.yaml` — 9-8 → review.
- M `_bmad-output/implementation-artifacts/9-8-paginated-tracks-infinite-scroll.md` — status, tasks, dev agent record.

**External:**
- Postman collection `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` — `GET Playlist Tracks` request + example response updated.

### Change Log

| Date       | Change                                                                                                                                              |
|------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| 2026-05-26 | Story 9.8 created — server-side pagination via `?limit&offset`, response shape `{items, next_offset, total}`, frontend `useInfiniteQuery` + IntersectionObserver sentinel, `useBlacklist` InfiniteData-aware. |
| 2026-05-26 | Story 9.8 implemented and moved to `review`. Backend pagination + tests, frontend `useInfiniteQuery` migration + sentinel-driven fetch, InfiniteData-aware blacklist mutations, Postman collection updated. 142/142 backend tests pass, frontend build clean. |
