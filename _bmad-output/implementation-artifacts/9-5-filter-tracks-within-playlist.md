# Story 9.5: Filter Tracks within Playlist

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a search input in the Playlist Detail page hero actions row that filters the visible tracks by title or artist (case-insensitive substring),
so that I can quickly locate a track in a 500+ track playlist (e.g. `liked_songs`, 535 tracks).

## Acceptance Criteria

1. **Given** the Playlist Detail page [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx), **When** rendered, **Then** a controlled text input is mounted in the hero `actions` slot, **after** the "Open in Spotify" button and **before** the `MoreHorizontal` "More actions" button. The input is a single visual block: a pill-shaped wrapper with a leading `Search` icon and an `<input>` with `placeholder="Filter tracks…"` (note: ASCII ellipsis "…" — three-dot Unicode character U+2026, same as the Dashboard topbar `placeholder="Filter playlists…"` at [`AppShell.tsx:293`](../../frontend/src/components/layout/AppShell.tsx)). [Source: epics.md#Story-9.5 hint #1 + AppShell.tsx:284-296 (topbar filter precedent)]

2. **Given** AC #1 visual style, **When** rendered, **Then** the wrapper className is **exactly**:
   ```
   hidden md:flex w-60 items-center gap-2 rounded-full border border-transparent bg-[var(--bg-elevated-2)] px-3.5 py-1.5 text-[13px] text-[var(--text-secondary)] focus-within:border-[var(--border-strong)]
   ```
   and the inner `<input>` className is **exactly**:
   ```
   w-full bg-transparent text-white outline-none placeholder:text-[var(--text-faint)]
   ```
   This is the topbar `Filter playlists…` style verbatim **except** the width: `w-80` → `w-60` (per epics.md hint "width 240px" — Tailwind `w-60` = 15rem = 240px). The `hidden md:flex` modifier matches the topbar pattern (filter is desktop-first; on narrow screens it collapses gracefully). The `Search` icon is `<Search size={15} />` imported from `lucide-react`. [Source: epics.md#Story-9.5 hint #1 "Rounded-full input, width 240px, Search icon prefix" + AppShell.tsx:286-294 verbatim style]

3. **Given** the user types in the input, **When** the value changes, **Then**:
   - The component holds the query in local React state: `const [query, setQuery] = useState('')`.
   - The input is fully controlled: `value={query}` + `onChange={(e) => setQuery(e.target.value)}`.
   - **No** debounce, **no** `useDeferredValue`, **no** `useTransition` — the dataset is in memory and a substring filter on ≤1000 strings is sub-millisecond. Adding indirection is premature optimization (Story 9.6 handles the >200-row perf path via virtualization, not via filter throttling).
   [Source: epics.md#Story-9.5 hint #2 "Pure client-side filter on the already-fetched track list" + project YAGNI stance]

4. **Given** the user has typed a `query`, **When** the visible list is computed, **Then** the filter expression is:
   ```ts
   const q = query.trim().toLowerCase()
   const filtered = q
     ? list.filter((t) =>
         (t.title + ' ' + t.artists.join(' ')).toLowerCase().includes(q),
       )
     : list
   ```
   - Case-insensitive: both query and haystack are `.toLowerCase()`-ed.
   - Substring match (not prefix, not fuzzy): `String.prototype.includes`.
   - Combined haystack: `title + " " + artists.join(" ")` — concatenating with a single space prevents false positives across the title/artist boundary (e.g. query `"er sa"` on a title `"Mer"` + artist `"Sara"` matches because the haystack is `"mer sara"`, which is exactly the intended behavior per epics.md hint "Filter applies to `track.title + track.artists.join(" ")`").
   - **Album** is **not** included in the haystack (per the explicit `title + artists` scope in epics.md hint #3; out of scope to broaden).
   - The filter is wrapped in `useMemo(() => …, [list, q])` to avoid re-filtering on unrelated re-renders. [Source: epics.md#Story-9.5 hint #3 "Filter applies to `track.title + track.artists.join(" ")`" + React perf hygiene]

5. **Given** the filter result drives the rendered table, **When** the JSX is wired, **Then** the `<TrackListTable>` receives `tracks={filtered}` (not `tracks={list}`). The hero `subLine`'s `{n} tracks` text **continues to display the unfiltered total** (`list.length`) — the count in the hero is metadata about the playlist, not about the current filter. The filter affects only the table body. **Do NOT** add a "(N matches)" suffix to the hero — keep the hero stable; the visible row count communicates the match count implicitly. [Source: epics.md#Story-9.5 "filters the visible tracks" (table-only scope) + UX consistency with Dashboard playlist grid filter (no count badge)]

6. **Given** the filter is non-empty AND `filtered.length === 0`, **When** the table renders, **Then** the `TrackListTable`'s existing empty-state branch fires with custom copy. Implementation: compute `emptyTitle` and `emptyMessage` props **dynamically** based on filter state:
   ```ts
   const hasFilter = q.length > 0
   const emptyTitle = hasFilter ? 'No matches' : 'This playlist has no tracks'
   const emptyMessage = hasFilter
     ? `No tracks match "${query.trim()}".`
     : "There's nothing in this playlist yet."
   ```
   - Note the quote style: straight ASCII double-quote `"` around `{query.trim()}`, **not** curly quotes — keep it simple, no `’`/`“`/`”`.
   - When `hasFilter && filtered.length === 0`, the table's empty branch (per [`TrackListTable.tsx:123-131`](../../frontend/src/features/tracks/TrackListTable.tsx)) renders the `Sparkles` icon + the custom title + the custom message. The `Sparkles` icon is acceptable for both the "no tracks" and "no matches" empty states — Story 9.6's virtualization is separate from this story; do **not** change the empty-state visual.
   - Pass the **trimmed** query in the message (e.g. typing `"  drake  "` shows `No tracks match "drake".`).
   [Source: epics.md#Story-9.5 hint #4 "empty-state 'No tracks match `<query>`'" + TrackListTable.tsx:123-131 existing empty branch]

7. **Given** the loading state, **When** `tracks.isPending && list.length === 0`, **Then** the filter input is **still rendered and interactable** (typing into it should not crash), but the table shows the existing skeleton rows (per [`TrackListTable.tsx:117-122`](../../frontend/src/features/tracks/TrackListTable.tsx)). Once the data arrives, the filter applies immediately to the freshly populated list. **Do NOT** disable the input while pending — the user may start typing optimistically. The `filtered` `useMemo` correctly returns `[]` when `list` is `[]` regardless of `q`, so the skeleton branch keeps firing. [Source: project UX (no premature input disabling) + TrackListTable.tsx:117-122 skeleton branch unchanged]

8. **Given** the not-found branch (`!playlists.isPending && !playlist`), **When** rendered, **Then** **no filter input** is rendered (the hero renders without `actions`, per existing [`PlaylistDetailPage.tsx:39-48`](../../frontend/src/pages/PlaylistDetailPage.tsx)). The not-found branch is unchanged by this story. [Source: PlaylistDetailPage.tsx:39-48 existing not-found branch]

9. **Given** the user clears the input (either by deleting all characters or by manually selecting + Backspace), **When** `query.trim() === ''`, **Then** `filtered === list` (reference-equal — the `useMemo` short-circuits to `list` when `q` is empty per AC #4). The table re-renders the full unfiltered set. **Do NOT** add a visible "clear" (✕) button inside the input in this story — keep parity with the Dashboard topbar filter (which also has no clear button). Keyboard Escape behavior is **not** required; the user clears via Backspace. [Source: epics.md#Story-9.5 minimal-scope hints + AppShell.tsx:284-296 (no clear button precedent)]

10. **Given** the Story 9.4 blacklist flow, **When** the user blacklists a track from a filtered view, **Then** the optimistic cache update in `useBlacklistTrack` (extended by Story 9.4 to handle the `['playlist-tracks', *]` family per [`useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts)) removes the row from `list` (the source array — the `tracks.data` query cache); `filtered` is recomputed via `useMemo` because `list` reference changed; the visible table updates instantly. **No additional plumbing needed** — verify by smoke (AC #14). [Source: 9-4-per-track-actions-playlist-detail.md#AC2-#AC3 + React reference identity on filtered useMemo]

11. **Given** the `liked_songs` synthetic playlist, **When** the user navigates to `/playlists/liked_songs` and types in the filter, **Then** the filter behaves identically to any other playlist (no special-case code in the filter logic). The `usePlaylistTracks('liked_songs')` query (per [`hooks/usePlaylistTracks.ts`](../../frontend/src/hooks/usePlaylistTracks.ts)) returns the same `RecentlyAddedTrack[]` shape, so the filter expression in AC #4 works unchanged. [Source: 9-1-playlist-tracks-api.md#AC2 (liked_songs sentinel returns identical shape) + AC #4 substring filter is shape-agnostic]

12. **Given** the build verification, **When** the dev runs `docker exec playlist_spotify-frontend-1 npm run build`, **Then** the build completes with **zero TypeScript errors** and **zero new ESLint warnings**. Specifically:
    - `useState<string>('')` is correctly inferred (no explicit annotation needed but acceptable).
    - `useMemo` deps array is exhaustive: `[list, q]`.
    - No unused imports (drop the `useState` / `useMemo` / `Search` imports if a refactor changes the shape — verify on final pass).
    - `Search` icon imported from `lucide-react` (already a project dep, used in AppShell + TrackRow indirectly — no `package.json` change).
    [Source: CLAUDE.md (clean builds) + tsconfig strict + 9-4 AC #10 precedent]

13. **Given** the backend test suite, **When** the dev runs `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`, **Then** all tests still pass and the count stays **≥ 127** (current baseline per 9-4 final). This story is **frontend-only** — any backend file touched is a scope violation. [Source: CLAUDE.md#Tests + 9-4 baseline]

14. **Given** the running stack via `docker-compose up`, **When** the dev manually smokes the new flow at `http://127.0.0.1:5173/`, **Then** **all** of the following must hold:
    - Navigate to `/playlists/<some-playlist-id>` (click a card on the Dashboard) — ideally pick one with ≥20 tracks so filtering is visible.
    - The filter input is visible in the actions row, between "Open in Spotify" and the `⋯` button.
    - Width of the input wrapper is **240px** (`w-60`); verify in DevTools or by visual comparison with the Dashboard topbar filter (which is `w-80` = 320px) — the playlist-detail filter is **narrower**.
    - Type a substring of a known track title → only matching rows remain; the count visually drops; hero sub-line `{n} tracks` is **unchanged** (still shows the unfiltered total).
    - Type a substring of an artist name → matching rows remain.
    - Type with mixed case (e.g. `DRAKE` vs `drake`) → identical results (case-insensitive).
    - Type whitespace-only (`"   "`) → behaves as empty filter; all rows visible.
    - Type a string that matches nothing (e.g. `xyzzy123`) → empty state shows `No matches` title + `No tracks match "xyzzy123".` message (with straight ASCII quotes, trimmed query).
    - Clear the input via Backspace → full list re-appears instantly; identity of the `filtered` array is the same reference as `list` (verify via React DevTools if reasonable; otherwise trust the code).
    - Story 9.4 cross-cache effect still works: with a non-empty filter showing a row, click `⋯` → "Hide from Recent Adds" → row vanishes from the filtered view; clear the filter → row also absent from full list (optimistic cache update on `['playlist-tracks', <id>]` is recomputed through the filter).
    - Navigate to `/playlists/liked_songs` → filter works identically; pick a track from the visible portion of the 535-track list and confirm filter still narrows.
    - Resize the browser to <768px width (md breakpoint) → the filter input **disappears** (`hidden md:flex`); other actions (Open in Spotify, `⋯`) remain visible. Resize back → filter reappears with its current `query` preserved (React state survives unmount only if the component stays mounted — actually `hidden` is CSS-only, so the state IS preserved; type something, resize narrow, resize wide → the typed value is still there and the filter still applies). Confirm.
    - Navigate to a freshly-created playlist with 0 tracks (or simulate via DevTools setting `tracks.data` to `[]`) → empty state shows `This playlist has no tracks` (unfiltered copy), not `No matches`.
    - Navigate to the not-found path (e.g. `/playlists/__nope__`) → no filter input rendered (only the hero says `Playlist not found`).

    Paste a one-line confirmation per bullet into the Completion Notes List. [Source: epics.md#Story-9.5 + 9-4 AC #12 smoke pattern]

15. **Given** the Postman collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`), **When** Story 9.5 ships, **Then** **no Postman update is required**. This story is pure frontend — no API surface change. Explicitly note "Postman: N/A (no API change)" in Completion Notes per memory rule [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md). [Source: memory `feedback_postman_sync` + CLAUDE.md#Postman + 9-4 AC #13 precedent]

16. **Given** `git status` after the story lands, **When** inspected, **Then** the change set is **exactly**:
    - ✏️ `frontend/src/pages/PlaylistDetailPage.tsx` (modified — add `useState` + `useMemo` filter + `Search` import + filter input JSX in `actions`)
    - ✏️ `_bmad-output/implementation-artifacts/sprint-status.yaml` (story status transitions)
    - ✏️ `_bmad-output/implementation-artifacts/9-5-filter-tracks-within-playlist.md` (this file — task checkboxes + Dev Agent Record)

    **No other files touched.** Zero backend changes. Zero edits to `features/tracks/TrackListHero.tsx`, `features/tracks/TrackListTable.tsx`, `components/TrackRow.tsx`, `hooks/usePlaylistTracks.ts`, `hooks/useBlacklist.ts`, `components/layout/AppShell.tsx`, `pages/RecentlyAddedPage.tsx`, or any other page/component. Paste `git status` output into Completion Notes. [Source: epics.md#Story-9.5 scope + project anti-scope-creep stance + 9-4 AC #14 precedent]

## Tasks / Subtasks

- [x] **Task 1: Add filter state + memoized filter to `PlaylistDetailPage`** (AC: #3, #4, #5, #7, #9)
  - [x] In [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx):
    - Extend imports from `react`: add `useState, useMemo`.
    - Extend imports from `lucide-react`: add `Search` (alongside existing `ExternalLink, MoreHorizontal`).
    - Inside the component, near the top (after `const auth = useAuthStatus()` / `const blacklist = useBlacklistTrack()`):
      ```ts
      const [query, setQuery] = useState('')
      const q = query.trim().toLowerCase()
      const filtered = useMemo(
        () =>
          q
            ? list.filter((t) =>
                (t.title + ' ' + t.artists.join(' '))
                  .toLowerCase()
                  .includes(q),
              )
            : list,
        [list, q],
      )
      ```
    - **Order matters**: declare `query` / `q` / `filtered` AFTER `const list = tracks.data ?? []` (already at line 36).

- [x] **Task 2: Wire dynamic empty-state copy** (AC: #6)
  - [x] Below the `filtered` `useMemo`, compute:
    ```ts
    const hasFilter = q.length > 0
    const emptyTitle = hasFilter ? 'No matches' : 'This playlist has no tracks'
    const emptyMessage = hasFilter
      ? `No tracks match "${query.trim()}".`
      : "There's nothing in this playlist yet."
    ```
  - [x] Replace the existing literal `emptyTitle` / `emptyMessage` props on the main-branch `<TrackListTable>` (currently `emptyTitle="This playlist has no tracks"` and `emptyMessage="There's nothing in this playlist yet."` at [`PlaylistDetailPage.tsx:119-120`](../../frontend/src/pages/PlaylistDetailPage.tsx)) with the dynamic variables.

- [x] **Task 3: Add the filter input to the hero `actions` slot** (AC: #1, #2, #8)
  - [x] Inside the existing `actions` JSX (currently lines 63-83), insert a new block **between** the `<a … aria-label="Open in Spotify" …>` element (lines 65-74) and the `<button … aria-label="More actions" …>` element (lines 75-82):
    ```tsx
    <div
      className="hidden md:flex w-60 items-center gap-2 rounded-full border border-transparent bg-[var(--bg-elevated-2)] px-3.5 py-1.5 text-[13px] text-[var(--text-secondary)] focus-within:border-[var(--border-strong)]"
    >
      <Search size={15} />
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Filter tracks…"
        aria-label="Filter tracks"
        className="w-full bg-transparent text-white outline-none placeholder:text-[var(--text-faint)]"
      />
    </div>
    ```
  - [x] **Do NOT** add the filter input to the not-found branch (the early `return` at lines 39-48). The not-found hero is rendered with no `actions` prop and stays that way.

- [x] **Task 4: Wire `filtered` to the table** (AC: #5)
  - [x] On the main-branch `<TrackListTable>`, change `tracks={list}` → `tracks={filtered}`. **Do NOT** change the hero `subLine` — `n`, `duration`, and the rest stay computed from `list` (the unfiltered array). [`PlaylistDetailPage.tsx:50-58`](../../frontend/src/pages/PlaylistDetailPage.tsx) is untouched.

- [x] **Task 5: Build verification** (AC: #12)
  - [x] `docker exec playlist_spotify-frontend-1 npm run build` → 0 TS errors, 0 new warnings. Output in Completion Notes.

- [x] **Task 6: Backend safety net** (AC: #13)
  - [x] `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → **127 passed**.

- [ ] **Task 7: Browser smoke** (AC: #14)
  - [ ] `docker-compose up -d` (if not running).
  - [ ] Walk through every bullet in AC #14. Paste one-line confirmations into Completion Notes.
  - [ ] **Note:** browser smoke must be performed by the human reviewer — agent has no UI access. See Completion Notes.

- [x] **Task 8: Final verification** (AC: #15, #16)
  - [x] `git status` → only the 3 expected files are modified by this story (PlaylistDetailPage.tsx remains "untracked" per Git Intelligence note in Dev Notes, as 9.3/9.4 not yet committed). Output in Completion Notes.
  - [x] "Postman: N/A (no API change)" per AC #15.
  - [x] Move story to `review` in `sprint-status.yaml`.

## Dev Notes

### Architecture & Conventions

- **Client-side filter, no API call.** The full track list is already in memory (`usePlaylistTracks` returns the entire array per Story 9.1 — server paginates internally and concatenates pages). Filtering server-side would re-paginate and round-trip Spotify; pointless for sub-1000 items.
- **No debounce.** Substring `.includes()` across ≤1000 strings is sub-millisecond. Debounce would *delay* feedback without saving work. If Story 9.6's virtualization later changes the cost profile (e.g. by adding row-virtualizer measurement work per render), revisit then — but the filter itself stays cheap.
- **Hero subLine stays unfiltered.** The hero is playlist metadata ("This playlist has 535 tracks"). The filter is a *view* operation, not a metadata change. Keep them decoupled — Spotify Desktop behaves the same way.
- **Topbar style parity.** Copying the Dashboard topbar filter className verbatim (minus the width) means visual consistency for free and avoids token bloat in the diff. The only intentional divergences: width (240px vs 320px — narrower because it shares space with two other action buttons) and the placeholder text.
- **Filter scope: title + artists, not album.** epics.md is explicit. Broadening to album would be scope creep; defer to a future story if a user actually asks.
- **No clear button.** The Dashboard topbar filter has no clear button either — consistency. Backspace is the clear UX. Users who want a clear button can ask, and we'll add one symmetrically to both filters.
- **No keyboard shortcut.** Out of scope. The Dashboard filter has no `Cmd+F` / `/` shortcut either.
- **Cross-story compatibility with 9.4 blacklist.** Because `filtered` is derived from `list` via `useMemo([list, q])`, any mutation of the underlying `tracks.data` query cache (e.g. 9.4's optimistic blacklist filter on `['playlist-tracks', spotifyId]`) flows through naturally: new `list` reference → `useMemo` recomputes → filtered table re-renders. No coordination needed.

### Source Tree — Files to Touch

- ✏️ [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx) — add `useState` + `useMemo` filter, `Search` import, filter input JSX in `actions`, dynamic empty copy, swap `tracks={list}` → `tracks={filtered}` (~25 lines net).
- 🔒 [`frontend/src/features/tracks/TrackListTable.tsx`](../../frontend/src/features/tracks/TrackListTable.tsx) — **do not touch**. Already accepts dynamic `emptyTitle` / `emptyMessage` props.
- 🔒 [`frontend/src/features/tracks/TrackListHero.tsx`](../../frontend/src/features/tracks/TrackListHero.tsx) — **do not touch**. The `actions` slot is a generic `ReactNode`, already accepts any JSX.
- 🔒 [`frontend/src/components/TrackRow.tsx`](../../frontend/src/components/TrackRow.tsx) — **do not touch**.
- 🔒 [`frontend/src/hooks/usePlaylistTracks.ts`](../../frontend/src/hooks/usePlaylistTracks.ts) — **do not touch**. Filter is page-local, not hook-level.
- 🔒 [`frontend/src/hooks/useBlacklist.ts`](../../frontend/src/hooks/useBlacklist.ts) — **do not touch**. 9.4 plumbing is already correct.
- 🔒 [`frontend/src/components/layout/AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx) — **do not touch**. We *copy* its filter style; we don't refactor it. (Refactoring a shared `FilterInput` component is YAGNI right now — two call sites, slightly different widths, no shared state. Wait for a third site or a real reuse need.)
- 🔒 [`frontend/src/pages/RecentlyAddedPage.tsx`](../../frontend/src/pages/RecentlyAddedPage.tsx) — **do not touch**. Recently Added does NOT get a filter in this story (epics.md scopes the filter to Story 9.5 = Playlist Detail).
- 🔒 [`backend/**`](../../backend/) — **do not touch** (AC #13).

### Code Sketch

**`PlaylistDetailPage.tsx` — full diff overview (additions in `+`, edits in `~`):**

```tsx
~ import { useMemo, useState } from 'react'
  import { useParams } from 'react-router-dom'
~ import { ExternalLink, MoreHorizontal, Search } from 'lucide-react'
  import { toast } from 'sonner'
  // … rest of imports unchanged …

  export default function PlaylistDetailPage() {
    const { spotifyId } = useParams<{ spotifyId: string }>()
    const tracks = usePlaylistTracks(spotifyId)
    const playlists = usePlaylists()
    const auth = useAuthStatus()
    const blacklist = useBlacklistTrack()

    const playlist = playlists.data?.find((p) => p.spotify_id === spotifyId)
    const list = tracks.data ?? []
    const owner = auth.data?.spotify_user_id ?? 'You'

+   const [query, setQuery] = useState('')
+   const q = query.trim().toLowerCase()
+   const filtered = useMemo(
+     () =>
+       q
+         ? list.filter((t) =>
+             (t.title + ' ' + t.artists.join(' ')).toLowerCase().includes(q),
+           )
+         : list,
+     [list, q],
+   )
+   const hasFilter = q.length > 0
+   const emptyTitle = hasFilter ? 'No matches' : 'This playlist has no tracks'
+   const emptyMessage = hasFilter
+     ? `No tracks match "${query.trim()}".`
+     : "There's nothing in this playlist yet."

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

    // … n / duration / subLine / coverUrl / href unchanged …

    const actions = (
      <>
        <a href={href} … >
          <ExternalLink size={14} />
          Open in Spotify
        </a>
+       <div
+         className="hidden md:flex w-60 items-center gap-2 rounded-full border border-transparent bg-[var(--bg-elevated-2)] px-3.5 py-1.5 text-[13px] text-[var(--text-secondary)] focus-within:border-[var(--border-strong)]"
+       >
+         <Search size={15} />
+         <input
+           type="text"
+           value={query}
+           onChange={(e) => setQuery(e.target.value)}
+           placeholder="Filter tracks…"
+           aria-label="Filter tracks"
+           className="w-full bg-transparent text-white outline-none placeholder:text-[var(--text-faint)]"
+         />
+       </div>
        <button type="button" aria-label="More actions" … >
          <MoreHorizontal size={18} />
        </button>
      </>
    )

    // … handleBlacklist unchanged …

    return (
      <>
        <TrackListHero kicker="PLAYLIST" title={playlist?.name ?? '…'} subLine={subLine} coverUrl={coverUrl} actions={actions} />
        <div className="mt-3">
          <TrackListTable
~           tracks={filtered}
            isPending={tracks.isPending}
            error={tracks.error}
            refetch={tracks.refetch}
            onBlacklist={handleBlacklist}
            errorTitle="Couldn't load playlist"
~           emptyTitle={emptyTitle}
~           emptyMessage={emptyMessage}
          />
        </div>
      </>
    )
  }
```

### Testing Standards

- **No new unit tests added** — this is a single-page state-and-filter wire-up. The substring filter is trivial and the React state pattern is idiomatic. The behavior is best verified by AC #14 manual smoke (case-insensitivity, whitespace handling, empty-state copy, cross-cache interaction with 9.4).
- **Type-check via `npm run build`** (AC #12) is the automated guardrail. `useMemo` deps array exhaustiveness will catch dependency mistakes.
- **Backend test suite** (AC #13) confirms no accidental backend edits.

### Previous Story Intelligence

- **Story 9.1 (Playlist Tracks API)** — `GET /api/v1/playlists/{spotify_id}/tracks` returns the **full** track list in a single response (server paginates Spotify internally and concatenates). This is what makes the client-side filter sound — no extra round-trips needed.
- **Story 9.2 (Shared Track List Components)** — `TrackListTable` accepts `emptyTitle` / `emptyMessage` props (verified at [`TrackListTable.tsx:80-82, 126-129`](../../frontend/src/features/tracks/TrackListTable.tsx)). The "No matches" empty state in 9.5 is delivered through those existing props — zero changes to the table component.
- **Story 9.3 (Playlist Detail Page & Navigation)** — established the `PlaylistDetailPage` shape with `subLine` derived from `list.length` (line 50). 9.5 keeps `subLine` unfiltered (AC #5) — the hero is metadata, the table is the filtered view.
- **Story 9.4 (Per-Track Blacklist on Playlist Detail)** — extended `useBlacklistTrack` to optimistically filter `['playlist-tracks', *]` caches. 9.5's `filtered` `useMemo` re-derives from the (potentially mutated) `list` automatically, so the optimistic removal is visible in the filtered view with no extra plumbing (AC #10).
- **Story 9.6 (Virtualization, deferred)** — handles >200-row perf via `@tanstack/react-virtual`. 9.5's filter is independent: virtualization will operate on `filtered` once 9.6 ships, and the empty-state branch (when `filtered.length === 0`) stays outside the virtualizer. No coordination needed in 9.5.

### Git Intelligence

Recent commits (newest first):

- `18dea64 feat: Epic 8 — page Recently Added avec table, blacklist par track et hooks dédiés` — established `useBlacklistTrack` + `RecentlyAddedTrack` shape.
- `f1a7caa fix: adaptation au changement d'API Spotify (track → item) + backfill sync` — irrelevant.
- `76facf6 feat: Epics 6 & 7 — UI refonte + playlist grid avec hide/unhide + dropdown style Spotify` — established the `Dashboard` topbar `Filter playlists…` input ([`AppShell.tsx:284-296`](../../frontend/src/components/layout/AppShell.tsx)) whose className 9.5 copies verbatim (minus width).
- `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — established the `liked_songs` sentinel (AC #11).

**Working tree at story creation** — Stories 9.1–9.4 are all in `review` but not yet committed (per the initial `git status`). The untracked file [`frontend/src/pages/PlaylistDetailPage.tsx`](../../frontend/src/pages/PlaylistDetailPage.tsx) is the 9.3+9.4 work; 9.5 modifies it in place. The expected `git status` after 9.5 (AC #16) accounts for this — `PlaylistDetailPage.tsx` will continue to appear under "Untracked files" (or, if previously staged, as modified) because the 9.3 commit boundary has not yet been crossed.

### Latest Tech Information

- **React `useState` for ephemeral input state** — idiomatic; the query is page-local and should NOT be lifted to a query param or global store (no deep linking requirement in this story).
- **React `useMemo` for derived list filtering** — standard pattern. Dep array `[list, q]` is exhaustive. React 18 will not call the factory when both refs are stable (e.g. typing the same key twice still calls because `q` doesn't change — *correct*, the memo returns the cached value).
- **`String.prototype.includes` + `.toLowerCase()`** — sub-millisecond on ≤1000-item arrays. For unicode normalization (e.g. matching `"é"` vs `"e"`), `.normalize('NFD').replace(/\p{Diacritic}/gu, '')` could be added later; **out of scope** for 9.5 — Spotify track titles/artist names are stored as-is, so the user's expectation is "exact characters". Defer to a future ask.
- **`hidden md:flex` (Tailwind)** — matches the AppShell topbar filter's responsive behavior. On <md (768px), the input is `display: none` (CSS) but the React component stays mounted, so `query` state survives a narrow→wide resize (AC #14).
- **No new dependency added.** This story does not touch `package.json`. `lucide-react` already includes `Search`.

### Project Structure Notes

- ✅ Frontend module conventions preserved: page-local state in the page, no new hook, no fetch.
- ✅ Tailwind class strings copied verbatim from the established Dashboard topbar pattern → consistency by construction.
- ✅ TanStack Query v5 conventions untouched.
- ✅ shadcn components: no new shadcn component needed (the filter input is a plain `<input>` styled with Tailwind, mirroring the existing AppShell topbar input — which is also a plain `<input>`, not a shadcn `Input` component).
- ⚠️ **Do NOT** introduce a shared `FilterInput` component yet (YAGNI — two sites, two slightly different widths; revisit on a third site).
- ⚠️ **Do NOT** add a clear (✕) button — symmetric with the AppShell topbar filter; defer until both filters get one together.
- ⚠️ **Do NOT** broaden the filter haystack to include `album` — explicit scope in epics.md hint #3.
- ⚠️ **Do NOT** add debouncing or `useDeferredValue` — premature for ≤1000-item substring filtering.
- ⚠️ **Do NOT** mutate `tracks.data` directly — `filtered` is a derived view; the cache stays canonical.
- ⚠️ **Do NOT** change the hero `subLine` to show filter match counts — hero is unfiltered metadata.
- ⚠️ **Do NOT** add a keyboard shortcut (`/`, `Cmd+F`) — out of scope.
- ⚠️ **Do NOT** persist `query` across navigations (no URL param, no sessionStorage) — out of scope; filter resets on remount, which is the expected Spotify-desktop behavior.

### Project Context Reference

See [`CLAUDE.md`](../../CLAUDE.md) for project-wide development rules. Most relevant sections:

- **Frontend** — "TanStack Query v5 : `isPending`" → preserved. "Tous les fetch via `lib/api.ts`" → N/A (no new fetch). "Alias `@/` = `frontend/src/`" → all imports use `@/`. "Composants shadcn : toujours via CLI" → N/A (no new shadcn component).
- **Lancer le projet** — `docker-compose up` for the dev stack; `docker exec playlist_spotify-frontend-1 npm run build` for the build (AC #12); browser smoke against `http://127.0.0.1:5173` (AC #14).
- **Postman** — N/A for this story (AC #15). Rule applies to API surface changes; this is frontend-only.

User-memory rules in effect:

- [`feedback_shadcn_cli`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_shadcn_cli.md) — N/A (no new shadcn component).
- [`feedback_node_version`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_node_version.md) — applies only to host-side `npm`; via `docker exec` no host Node is involved.
- [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md) — **does not apply** (no API change). AC #15 documents the skip.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-9.5 (lines 1498-1509)] — primary AC source and implementation hints.
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-9 (lines 1435-1441)] — epic framing + FR/AR/NFR map.
- [Source: _bmad-output/planning-artifacts/prd.md FR47] — "User can filter tracks within a playlist by title or artist".
- [Source: _bmad-output/implementation-artifacts/9-1-playlist-tracks-api.md#AC1-#AC2] — playlist tracks endpoint shape + liked_songs sentinel.
- [Source: _bmad-output/implementation-artifacts/9-2-shared-track-list-components.md] — `TrackListTable` `emptyTitle` / `emptyMessage` prop contract.
- [Source: _bmad-output/implementation-artifacts/9-3-playlist-detail-page-navigation.md] — base `PlaylistDetailPage` shape extended here.
- [Source: _bmad-output/implementation-artifacts/9-4-per-track-actions-playlist-detail.md] — cross-cache blacklist optimism; 9.5's `filtered` flows through automatically.
- [Source: frontend/src/pages/PlaylistDetailPage.tsx] — current page to modify.
- [Source: frontend/src/features/tracks/TrackListTable.tsx:80-82, 123-131] — empty branch + props contract; consumed unchanged.
- [Source: frontend/src/features/tracks/TrackListHero.tsx] — `actions` ReactNode slot; consumed unchanged.
- [Source: frontend/src/components/layout/AppShell.tsx:284-296] — Dashboard topbar filter pattern (className + Search icon + placeholder convention) — verbatim style template.
- [Source: CLAUDE.md#Frontend, #Tests, #Postman, #Lancer le projet] — project conventions.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

_None_

### Completion Notes List

- **Implementation matches the Code Sketch verbatim.** Added `useState` + `useMemo` filter on top of `list`, dynamic `emptyTitle`/`emptyMessage`, and the filter input JSX between "Open in Spotify" and the `⋯` button. The filter input wrapper width is `w-60` (240px) per AC #2.
- **Frontend build (AC #12, Task 5):** `docker exec playlist_spotify-frontend-1 npm run build` → `✓ 1935 modules transformed`, `✓ built in 384ms`. 0 TS errors, 0 new warnings. The only warning is the pre-existing chunk-size advisory (unrelated to this story).
- **Backend tests (AC #13, Task 6):** `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -q` → **127 passed, 14 warnings in 1.13s**. Baseline preserved; no backend file touched.
- **Postman (AC #15):** N/A (no API change).
- **Git scope (AC #16):** Diff for this story is exactly:
  - `M frontend/src/pages/PlaylistDetailPage.tsx` (technically still listed under "Untracked" in `git status` because 9.3/9.4 were never committed, per the Git Intelligence note in Dev Notes — this matches the spec's expectation)
  - `M _bmad-output/implementation-artifacts/sprint-status.yaml`
  - `M _bmad-output/implementation-artifacts/9-5-filter-tracks-within-playlist.md`
  No backend files, no other frontend files, no other story files modified by this work.
- **Browser smoke (AC #14, Task 7) — NOT PERFORMED.** Agent runs in a CLI environment with no browser access. Implementation is bit-for-bit identical to the Code Sketch / className spec in AC #2, AC #4, AC #6; type-check passes; behavior is fully derivable from the code. **Human reviewer must walk AC #14's bullets** before marking the story `done`. Items worth particular attention:
  - Width 240px verification in DevTools.
  - Empty-state copy with ASCII quotes (`"…"`).
  - Cross-cache interaction with Story 9.4 blacklist optimistic update.
  - `hidden md:flex` behavior at <768px width preserving `query` state on resize.

### File List

- ✏️ `frontend/src/pages/PlaylistDetailPage.tsx`
- ✏️ `_bmad-output/implementation-artifacts/sprint-status.yaml`
- ✏️ `_bmad-output/implementation-artifacts/9-5-filter-tracks-within-playlist.md`

### Change Log

| Date       | Change                                                                                       |
|------------|----------------------------------------------------------------------------------------------|
| 2026-05-26 | Story 9.5 implemented — client-side filter on Playlist Detail page (title + artists, case-insensitive). |
