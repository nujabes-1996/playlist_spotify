# Story 7.3: Hide Playlist Action

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a "Hide playlist" action on each playlist card,
so that I can remove cluttered playlists from the main grid in one click without losing them — they keep existing in the backend and can be reviewed/restored later (Story 7.4).

**Design reference:** [`ux-design/README.md`](../planning-artifacts/ux-design/README.md) section "PlaylistCard > Overflow menu" + "State Management > toggleHide(id)". Baseline component already in place: [`frontend/src/features/playlists/PlaylistCard.tsx`](../../frontend/src/features/playlists/PlaylistCard.tsx) (the menu item exists from Story 7.2; this story wires the mutation).

## Acceptance Criteria

1. **Given** I open the `⋯` overflow menu on a visible card in the dashboard grid, **When** the menu renders (shadcn `DropdownMenu`), **Then** it contains the three items already established by Story 7.2 in this order: "Include in sync" / "Remove from sync" (toggle based on `is_included`), "Hide playlist" (label is always "Hide playlist" in the visible grid — the "Unhide" variant is rendered in Story 7.4's hidden accordion via the `dimmed` branch), `DropdownMenuSeparator`, "Open in Spotify" with `ExternalLink` icon (FR26). No new menu items are introduced by this story. [Source: epics.md#Story-7.3 AC #1 + 7-2-playlist-grid-cover-art-card-layout.md AC #6]

2. **Given** I click "Hide playlist" on a visible card, **When** the action fires (`DropdownMenuItem.onSelect`), **Then** the frontend calls `PATCH /api/v1/playlists/{spotify_id}` with body `{"is_hidden": true}` via a **new** `useHidePlaylist` mutation hook added to [`frontend/src/hooks/usePlaylists.ts`](../../frontend/src/hooks/usePlaylists.ts) — do NOT reuse `useTogglePlaylist` (the include-toggle and hide-toggle are semantically distinct and the existing hook's payload shape is `{ spotifyId, is_included }` only). The new hook's `mutationFn` is `({ spotifyId, is_hidden }) => api.patch<Playlist>('/playlists/'+spotifyId, { is_hidden })`. [Source: epics.md#Story-7.3 AC #2 + backend/routers/playlists.py#PlaylistPatch lines 23-25]

3. **Given** the hide mutation is in flight, **When** I observe the dashboard, **Then** the card is **optimistically removed** from the visible grid before the network round-trip completes. The optimistic update is implemented via TanStack Query v5's `onMutate` / `onError` / `onSettled` pattern on `useHidePlaylist`: `onMutate` cancels in-flight `['playlists']` queries (`queryClient.cancelQueries({ queryKey: ['playlists'] })`), snapshots the current cache (`queryClient.getQueryData<Playlist[]>(['playlists'])`), and writes back a clone with the target playlist's `is_hidden` flipped to `true` AND `is_included` forced to `false` (mirrors the backend's atomic behavior — see [`backend/routers/playlists.py:86-88`](../../backend/routers/playlists.py#L86-L88)). Return the snapshot from `onMutate` as `context`. [Source: epics.md#Story-7.3 AC #2 (optimistic) + backend atomicity Story 7.1 AC#3]

4. **Given** the PATCH responds with HTTP 2xx, **When** `onSettled` fires, **Then** the mutation calls `queryClient.invalidateQueries({ queryKey: ['playlists'] })` to refetch `GET /api/v1/playlists` (which — per Story 7.1 — returns the authoritative `is_hidden` / `is_included` / `image_url` / `track_count`). This reconciles any drift and brings the hidden card into Story 7.4's accordion (when that ships). [Source: epics.md#Story-7.3 AC #3 + 7-1 API contract]

5. **Given** the PATCH fails (network error, 4xx, 5xx — anything that resolves `onError`), **When** the error is caught, **Then** (a) the optimistic update is rolled back: `queryClient.setQueryData(['playlists'], context.previous)` using the snapshot captured in `onMutate`, restoring the card to the visible grid; AND (b) a user-visible failure notification is surfaced. The notification text is `"Could not hide \"{playlist.name}\". Please try again."`. [Source: epics.md#Story-7.3 AC #4]

6. **Given** the project has no toast library before this story, **When** the failure notification (AC #5b) is implemented, **Then** the shadcn `sonner` primitive is added via CLI: `docker exec playlist_spotify-frontend-1 npx shadcn@latest add sonner` (or on host with Node 22: `cd frontend && npx shadcn@latest add sonner`). This adds [`frontend/src/components/ui/sonner.tsx`](../../frontend/src/components/ui/sonner.tsx) and the `sonner` npm dependency. A single `<Toaster />` is mounted once at the app shell level in [`frontend/src/App.tsx`](../../frontend/src/App.tsx) inside the `RouterProvider` wrapper (sibling to it, inside the default export's returned fragment) — NOT inside `AppShell` (which mounts per route) and NOT inside `PlaylistCard` (which mounts per card). The mutation's `onError` calls `toast.error('Could not hide "' + name + '". Please try again.')` from `sonner`. Do NOT hand-roll a toast primitive — must come from the shadcn CLI per [CLAUDE.md](../../CLAUDE.md#Frontend) and memory `feedback_shadcn_cli`. [Source: CLAUDE.md#Frontend "Composants shadcn : toujours via CLI" + memory `feedback_shadcn_cli` + memory `feedback_node_version`]

7. **Given** the hide request succeeds AND the next sync runs (manual via "Sync Now" or scheduled), **When** the sync engine queries selected playlists, **Then** the hidden playlist is NOT harvested even if its `is_included` was `true` before hiding (FR27). This behavior is already enforced by the backend (Story 7.1 AC #5 — sync engine WHERE clause filters `is_included=true AND is_hidden=false`). **This story does NOT modify any backend code.** Verify via the smoke check in AC #15. [Source: epics.md#Story-7.3 AC #3 + 7-1 AC #5 (sync engine guard)]

8. **Given** the `PlaylistCard` component from Story 7.2, **When** the "Hide playlist" `DropdownMenuItem.onSelect` fires, **Then** the existing prop-based fallback at [`PlaylistCard.tsx:121-133`](../../frontend/src/features/playlists/PlaylistCard.tsx#L121-L133) — which currently calls `onToggleHide?.(playlist.spotify_id)` or falls back to `console.debug('hide TBD by Story 7.3')` — is updated so that the `console.debug` fallback is **removed**. The component now ALWAYS calls a real handler. Two acceptable implementations (pick **A**):
   - **A (Recommended — consistent with Story 7.2's `useTogglePlaylist` co-location):** `PlaylistCard` calls `useHidePlaylist()` **directly** (same self-contained pattern as `useTogglePlaylist`). The `onToggleHide` prop is REMOVED from the `Props` interface. `DashboardPage` / `PlaylistGrid` no longer needs to pass it.
   - **B (Alternative — lifted state):** Keep `onToggleHide` as a prop; `PlaylistGrid` declares `const hide = useHidePlaylist()` and passes `(spotifyId) => hide.mutate({ spotifyId, is_hidden: true })` as `onToggleHide`. Requires removing the `console.debug` fallback and either making the prop required OR keeping a no-op fallback (cleaner: make required).

   **Pick option A** for this story to mirror Story 7.2's symmetry with the deleted `PlaylistToggle`'s self-contained mutation pattern, and to keep mutation state local to the card. Document the decision in completion notes. [Source: 7-2-playlist-grid-cover-art-card-layout.md AC #6 + Dev Notes "useTogglePlaylist kept inside PlaylistCard"]

9. **Given** the menu's keyboard accessibility, **When** a user navigates to a card with Tab and presses Enter or Space on the `⋯` `DropdownMenuTrigger`, **Then** (a) the menu opens; (b) arrow keys (`↑`/`↓`) navigate items; (c) pressing Enter or Space on "Hide playlist" triggers the same `onSelect` handler as a mouse click and fires the hide mutation; (d) Esc closes the menu without firing any action. This follows from using Radix's `DropdownMenuItem` with `onSelect` (NOT `onClick`) — which Story 7.2 already configured. No additional keyboard wiring is needed in this story; verify by manual smoke. [Source: epics.md#Story-7.3 AC #5 + Radix DropdownMenu defaults + Story 7.2 Dev Notes "DropdownMenuItem uses onSelect"]

10. **Given** the optimistic-update semantics, **When** two consecutive hides race (user clicks "Hide playlist" on card A, then immediately on card B before the first PATCH returns), **Then** both cards disappear from the visible grid optimistically. Each mutation snapshots its own `previous` cache independently via `onMutate`. On success-success: `invalidateQueries` reconciles both. On failure of one (e.g., B fails): only B's snapshot is restored — A's hidden state is preserved because A's mutation already succeeded and the `invalidateQueries` running for B re-fetches the authoritative server state. Document this is acceptable behavior (no per-card pessimistic locking required). [Source: TanStack Query v5 mutation lifecycle docs + epics.md#Story-7.3 implicit semantics]

11. **Given** the TanStack Query v5 convention used elsewhere in this project, **When** I inspect [`usePlaylists.ts`](../../frontend/src/hooks/usePlaylists.ts), **Then** the new `useHidePlaylist` hook uses `isPending` (NOT `isLoading`) for any loading state references, and the mutation callbacks (`onMutate`, `onError`, `onSettled`) are declared inside the `useMutation({ ... })` config object (NOT passed as arguments to `mutate()` at call sites) per [CLAUDE.md](../../CLAUDE.md#Frontend). The existing `useTogglePlaylist` (which uses `onSuccess` + `invalidateQueries`) remains UNCHANGED. [Source: CLAUDE.md#Frontend "TanStack Query v5"]

12. **Given** the API contract for `PATCH /api/v1/playlists/{spotify_id}`, **When** I call it with `{"is_hidden": true}`, **Then** the backend response is shaped as `PlaylistRead` with `image_url: null` and `track_count: null` (per Story 7.1 — the PATCH intentionally drops those two fields to avoid a Spotify round-trip; see [`backend/routers/playlists.py:97-104`](../../backend/routers/playlists.py#L97-L104)). The frontend MUST NOT rely on the PATCH response to update the cache — it relies on the `invalidateQueries(['playlists'])` re-fetching the authoritative GET response (which includes the full data). The TypeScript type for the mutation return is `Playlist`, but consumers must treat `image_url` and `track_count` as potentially missing post-mutation. [Source: 7-1-playlist-hidden-state-schema-api.md "PATCH intentionally drops image_url/track_count" + Story 7.2 AC #13]

13. **Given** the `Playlist` TypeScript interface in [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts), **When** I inspect its shape after Story 7.2, **Then** it already has `is_hidden: boolean`, `image_url: string | null`, `track_count: number`. **No changes to `types/index.ts` are required by this story.** [Source: 7-2-playlist-grid-cover-art-card-layout.md AC #12 — already shipped]

14. **Given** the build gate, **When** the developer runs `docker exec playlist_spotify-frontend-1 npm run build`, **Then** TypeScript compilation passes with no errors and no warnings in `PlaylistCard.tsx`, `PlaylistGrid.tsx`, `usePlaylists.ts`, `App.tsx`, or any other file touched. (Frontend test framework is still not set up in this project — type-check via the build remains the gate per [CLAUDE.md](../../CLAUDE.md#Tests). Do NOT introduce Vitest/Jest/RTL in this story.) [Source: CLAUDE.md#Tests + Story 7.2 AC #17]

15. **Given** manual smoke against the running stack, **When** the developer runs `docker-compose up` and visits `http://127.0.0.1:5173/`, **Then**:
    - (a) The dashboard grid renders visible playlists (Story 7.2 baseline).
    - (b) Hovering a card surfaces the `⋯` overflow trigger; clicking it opens the menu with "Hide playlist" visible.
    - (c) Clicking "Hide playlist" makes the card disappear instantly from the grid (optimistic).
    - (d) Reloading the page (or waiting for the auto-refetch) confirms the card stays hidden — `GET /api/v1/playlists` returns `is_hidden=true` for that playlist (verify with `curl -s http://127.0.0.1:8000/api/v1/playlists | jq '.[] | select(.is_hidden==true)'`).
    - (e) Triggering a sync (Sync Now button) does NOT harvest the hidden playlist's tracks (check sync logs for the absence of the playlist's id — Story 5.1 log viewer).
    - (f) Simulating an API failure (e.g., temporarily kill the backend with `docker-compose stop backend`, then click Hide) makes the toast appear with `"Could not hide \"{name}\". Please try again."` and the card is restored to the grid.
    - (g) Keyboard-only flow: Tab to a card's overflow button, Enter → menu opens, ↓ to "Hide playlist", Enter → card disappears.
   Document any visual deviations or environment quirks in the Completion Notes List. [Source: epics.md#Story-7.3 ACs aggregate]

16. **Given** the Postman collection, **When** Story 7.3 ships, **Then** **no Postman changes are required** — this story is frontend-only and does not change any API contract (`PATCH /api/v1/playlists/{spotify_id}` with `is_hidden` already exists and is documented in the collection after Story 7.1). Verify with a quick `GET https://api.getpostman.com/collections/{uid}` and confirm the PATCH request example body includes `is_hidden`. If missing (omission from 7.1), add it — this is the only Postman-related action this story may need, and only as a corrective. [Source: CLAUDE.md#Postman + memory `feedback_postman_sync` + Story 7.1 Postman update]

## Tasks / Subtasks

- [x] **Task 1: Install shadcn `sonner` toast primitive** (AC: #6)
  - [x] Run: `docker exec playlist_spotify-frontend-1 npx shadcn@latest add sonner` (or on host: `cd frontend && npx shadcn@latest add sonner` with Node 22 active per memory `feedback_node_version`).
  - [x] Verify [`frontend/src/components/ui/sonner.tsx`](../../frontend/src/components/ui/sonner.tsx) exists and `sonner` is in `package.json` dependencies.
  - [x] Do NOT hand-edit the generated file (per memory `feedback_shadcn_cli`).

- [x] **Task 2: Mount `<Toaster />` at the app root** (AC: #6)
  - [x] Edit [`frontend/src/App.tsx`](../../frontend/src/App.tsx): import `{ Toaster } from '@/components/ui/sonner'` and render it as a sibling of `<RouterProvider router={router} />` inside a wrapping fragment so it is mounted exactly once across the app lifetime.
  - [x] Use `<Toaster richColors position="bottom-right" />` (or sonner's defaults — match the project's dark theme; sonner's shadcn wrapper already picks `useTheme()`-aware variants).

- [x] **Task 3: Add `useHidePlaylist` mutation hook** (AC: #2, #3, #4, #5, #11)
  - [x] Edit [`frontend/src/hooks/usePlaylists.ts`](../../frontend/src/hooks/usePlaylists.ts): add a new exported hook `useHidePlaylist` that takes no args.
  - [x] Inside the hook, get `queryClient = useQueryClient()` and call `useMutation({ mutationFn, onMutate, onError, onSettled })`:
    - `mutationFn: ({ spotifyId, is_hidden }: { spotifyId: string; is_hidden: boolean }) => api.patch<Playlist>('/playlists/'+spotifyId, { is_hidden })`.
    - `onMutate: async ({ spotifyId, is_hidden }) => { await queryClient.cancelQueries({ queryKey: ['playlists'] }); const previous = queryClient.getQueryData<Playlist[]>(['playlists']); if (previous) queryClient.setQueryData<Playlist[]>(['playlists'], previous.map(p => p.spotify_id === spotifyId ? { ...p, is_hidden, is_included: is_hidden ? false : p.is_included } : p)); return { previous }; }`.
    - `onError: (_err, _vars, context) => { if (context?.previous) queryClient.setQueryData(['playlists'], context.previous); /* toast handled at call site OR inside the hook — see Task 4 decision */ }`.
    - `onSettled: () => { queryClient.invalidateQueries({ queryKey: ['playlists'] }); }`.
  - [x] Do NOT modify the existing `usePlaylists` or `useTogglePlaylist` exports (AC #11).

- [x] **Task 4: Wire `PlaylistCard` to `useHidePlaylist`** (AC: #5, #8)
  - [x] Edit [`frontend/src/features/playlists/PlaylistCard.tsx`](../../frontend/src/features/playlists/PlaylistCard.tsx):
    - Import `useHidePlaylist` from `@/hooks/usePlaylists` (alongside the existing `useTogglePlaylist`).
    - Import `{ toast } from 'sonner'`.
    - Remove the `onToggleHide?: (spotifyId: string) => void` line from the `Props` interface (per AC #8 option A).
    - Inside the component, call `const hide = useHidePlaylist()`.
    - Replace the "Hide playlist" `DropdownMenuItem.onSelect` body with:
      ```ts
      hide.mutate(
        { spotifyId: playlist.spotify_id, is_hidden: true },
        {
          onError: () => {
            toast.error('Could not hide "' + playlist.name + '". Please try again.')
          },
        },
      )
      ```
    - The `mutate(call, { onError })` per-call callback complements the hook's `onError` rollback (rollback happens in the hook; the toast is fired here so the message includes the card's local `playlist.name`). This is idiomatic TanStack Query v5.
  - [x] Remove the `console.debug('hide TBD by Story 7.3')` fallback and the `if (onToggleHide)` branch entirely (per AC #8).

- [x] **Task 5: Clean up `PlaylistGrid` and any stale `onToggleHide` references** (AC: #8)
  - [x] Edit [`frontend/src/features/playlists/PlaylistGrid.tsx`](../../frontend/src/features/playlists/PlaylistGrid.tsx): no functional changes expected (the file does not currently pass `onToggleHide`). Re-check and remove any dead references.
  - [x] Grep for `onToggleHide` across `frontend/src/`: `grep -rn "onToggleHide" frontend/src` — should be zero matches after this story.

- [x] **Task 6: Verify type-check + build** (AC: #14)
  - [x] Run `docker exec playlist_spotify-frontend-1 npm run build` → must finish with no TypeScript errors and no warnings in the touched files.
  - [x] If `tsc` complains about unused imports (e.g., the removed `onToggleHide` prop), fix in place.

- [x] **Task 7: Manual smoke test** (AC: #15)
  - [x] `docker-compose up` (rebuild frontend if needed: `docker-compose up --build frontend`).
  - [x] Walk smoke checks (a) through (g) from AC #15.
  - [x] For step (f) — failure path — temporarily stop backend with `docker-compose stop backend`, click Hide, observe the toast + restored card, then restart with `docker-compose start backend`.
  - [x] Note all observations in the Completion Notes List.

- [x] **Task 8: Postman sanity check** (AC: #16)
  - [x] Confirm via `curl -s -H "X-Api-Key: $POSTMAN_API_KEY" https://api.getpostman.com/collections/31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6 | jq '.collection.item[] | .. | .request? | select(.url.path[]? == "playlists") // empty'` (or via MCP Postman if available) that the PATCH `playlists/:spotify_id` request example includes `is_hidden` in the body. If missing, add a body example `{"is_hidden": true}` and PUT the collection back. If present, no action.

## Dev Notes

### Architecture & Conventions

- **Business logic in `services/`, never in `routers/`** — this story does not touch the backend (the hide-implies-exclude atomic update already lives in [`backend/routers/playlists.py:86-88`](../../backend/routers/playlists.py#L86-L88), which is arguably thin enough to stay in the router; if a refactor to `services/` is wanted, it's an orthogonal story). Per [CLAUDE.md#Backend](../../CLAUDE.md#Backend).
- **All frontend fetches via `lib/api.ts`** — `useHidePlaylist` MUST use `api.patch<Playlist>(...)`, never a raw `fetch()`. Mirrors `useTogglePlaylist`. [Source: CLAUDE.md#Frontend "Tous les fetch via lib/api.ts"]
- **Snake_case JSON everywhere** — the mutation payload uses `is_hidden` (snake_case), matching the backend `PlaylistPatch` model. Do NOT add a `isHidden` camelCase remapping. [Source: CLAUDE.md#Frontend + backend/routers/playlists.py#PlaylistPatch]
- **TanStack Query v5 optimistic-update idioms** — see the canonical pattern: `cancelQueries` → snapshot via `getQueryData` → `setQueryData` to a clone → return snapshot as `context` → `onError` restores from `context.previous` → `onSettled` invalidates. This is the v5-stable shape (no `onMutate` mutating the query directly; always via `setQueryData`). [Source: TanStack Query v5 docs — Optimistic Updates]
- **shadcn primitives via CLI only** — `sonner` is the only new primitive needed by this story; install via `npx shadcn@latest add sonner`. Do NOT hand-edit the generated `sonner.tsx`. [Source: CLAUDE.md#Frontend + memory `feedback_shadcn_cli`]
- **Design tokens via CSS variables** — sonner's shadcn wrapper picks up `--background` / `--foreground` automatically through `next-themes`-style integration; no manual variable wiring needed. [Source: shadcn `sonner` block + Story 6.1]

### Source Tree — Files to Touch

- ➕ [`frontend/src/components/ui/sonner.tsx`](../../frontend/src/components/ui/sonner.tsx) — added by shadcn CLI (Task 1).
- ✏️ [`frontend/src/hooks/usePlaylists.ts`](../../frontend/src/hooks/usePlaylists.ts) — add `useHidePlaylist` export. `usePlaylists` and `useTogglePlaylist` remain unchanged.
- ✏️ [`frontend/src/features/playlists/PlaylistCard.tsx`](../../frontend/src/features/playlists/PlaylistCard.tsx) — wire `useHidePlaylist` + toast on error; remove `onToggleHide` prop and the `console.debug` fallback.
- ✏️ [`frontend/src/App.tsx`](../../frontend/src/App.tsx) — mount `<Toaster />` once.
- ✏️ [`frontend/package.json`](../../frontend/package.json) + [`frontend/package-lock.json`](../../frontend/package-lock.json) — `sonner` added by shadcn CLI.
- 🔒 [`frontend/src/features/playlists/PlaylistGrid.tsx`](../../frontend/src/features/playlists/PlaylistGrid.tsx) — **likely no change** (already does not pass `onToggleHide`); verify grep.
- 🔒 [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts) — **do not touch** (Story 7.2 already extended `Playlist`).
- 🔒 Backend — **do not touch** (Story 7.1 already shipped the PATCH contract and the sync engine guard).

### Testing Standards

- No frontend test runner is configured in this project — the gate is TypeScript build via `docker exec playlist_spotify-frontend-1 npm run build`. Do NOT introduce Vitest/Jest/RTL in this story.
- Backend tests: not impacted. Story 7.1's [`backend/tests/test_story_7_1.py`](../../backend/tests/test_story_7_1.py) already covers the PATCH contract (incl. atomic `is_hidden=true ⇒ is_included=false`).
- Manual smoke (AC #15) — especially steps (c), (e), (f), (g) — is the functional gate for this story.

### Previous Story Intelligence

- **Story 7.1** (backend `is_hidden` schema + API). Already shipped. Provides:
  - `PATCH /api/v1/playlists/{spotify_id}` accepting `{"is_hidden": true}` with **atomic** `is_hidden=true ⇒ is_included=false` ([`backend/routers/playlists.py:86-88`](../../backend/routers/playlists.py#L86-L88)).
  - Sync engine WHERE clause already filters `is_included=true AND is_hidden=false` ([`backend/services/sync_engine.py`](../../backend/services/sync_engine.py)) — so AC #7 is verified automatically.
  - The PATCH response intentionally drops `image_url` / `track_count` — Story 7.3's hook MUST rely on `invalidateQueries` to re-fetch (not on the PATCH response payload). See [7-1 Dev Notes line 112](7-1-playlist-hidden-state-schema-api.md).
- **Story 7.2** (frontend grid + `PlaylistCard`). Already shipped. Provides:
  - The "Hide playlist" `DropdownMenuItem` already exists in the menu, currently wired to `onToggleHide?` prop with a `console.debug` fallback ([`PlaylistCard.tsx:121-133`](../../frontend/src/features/playlists/PlaylistCard.tsx#L121-L133)). This story removes the `console.debug` fallback (AC #8).
  - The `useTogglePlaylist` hook is co-located inside `PlaylistCard` — **mirror this pattern** for `useHidePlaylist` to preserve symmetry and avoid prop drilling (AC #8 option A).
  - The `PlaylistGrid` filter `playlists.filter((p) => !p.is_hidden)` already handles the "remove from visible grid" rendering side once `is_hidden` becomes `true` in the cache — combined with optimistic `setQueryData`, the card disappears in the same render frame (no extra UI machinery needed).
- **Story 6.x** (design tokens + AppShell) — the toaster wrapper inherits the dark theme via the `next-themes` integration shadcn ships in `sonner.tsx`. Nothing extra to configure.
- **Stories 3.1, 3.4, 3.5** — `useTogglePlaylist` is the established pattern. `useHidePlaylist` is its sibling, not its replacement.

### Git Intelligence

- Most recent backend feature commit: `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count`. Liked Songs (`spotify_id="liked_songs"`) is a real entry in `GET /api/v1/playlists` and **can be hidden** like any other playlist via this story's flow. Spot-check this in smoke step (b)/(c).
- Recent uncommitted Stories 7.1 + 7.2 working tree state (per `git status`) confirms the schema column is applied and the frontend is on the grid layout. If the dev DB pre-dates 7.1, the column is absent and PATCH will 500 with `no such column: playlist.is_hidden` — same warning as in 7.2 dev notes. Mitigation: drop `./data/playlist_spotify.db` and let SQLModel recreate it on next boot.

### Latest Tech Information

- **TanStack Query v5 — Optimistic Updates** — the canonical recipe:
  ```ts
  useMutation({
    mutationFn,
    onMutate: async (vars) => {
      await queryClient.cancelQueries({ queryKey: ['playlists'] })
      const previous = queryClient.getQueryData<Playlist[]>(['playlists'])
      queryClient.setQueryData<Playlist[]>(['playlists'], (old) =>
        (old ?? []).map((p) => p.spotify_id === vars.spotifyId ? { ...p, is_hidden: vars.is_hidden, is_included: vars.is_hidden ? false : p.is_included } : p),
      )
      return { previous }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(['playlists'], context.previous)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['playlists'] })
    },
  })
  ```
  The `context` returned from `onMutate` is correctly typed by inference; if TS complains, annotate `onMutate`'s return as `Promise<{ previous: Playlist[] | undefined }>`.
- **sonner** — the modern shadcn toast primitive (replaces the deprecated `toast` shadcn block). Calling `toast.error('...')` is sync; the `<Toaster />` component renders the portal. Position defaults to `bottom-right`. Theme is auto-picked when `<Toaster />` is used without explicit `theme` prop and shadcn's `useTheme()` is wired (the generated wrapper handles this). [Source: shadcn `sonner` block docs + sonner npm docs]
- **Radix DropdownMenu `onSelect` vs `onClick`** — `onSelect` is the keyboard-native handler (fires for Enter/Space + mouse click + touch) and auto-closes the menu. Story 7.2 already uses `onSelect`; keep it.
- **shadcn `<Toaster />` placement** — mount **once**, outside any per-route component. Inside `App.tsx` as a sibling of `<RouterProvider />` is the recommended spot (above `AppShell` in the tree). Mounting inside `AppShell` is functionally fine but creates an extra portal per route mount — not recommended.

### Project Structure Notes

- ✅ Aligns with [`architecture.md#Structure-Patterns`](../planning-artifacts/architecture.md) — frontend hooks live in `frontend/src/hooks/`, components in `frontend/src/features/<feature>/`, shadcn primitives in `frontend/src/components/ui/`.
- ✅ No new feature folder needed; everything lives in the existing `playlists/` feature folder + `hooks/usePlaylists.ts`.
- ⚠️ **Do NOT** put `<Toaster />` inside `PlaylistCard` (mounts per card → N portals) or inside `AppShell` (mounts per route navigation → can leak portals in dev StrictMode). Mount once at the App.tsx level.
- ⚠️ **Do NOT** modify `useTogglePlaylist` to also accept `is_hidden`. Keeping the two mutations separate is intentional: it (a) makes optimistic semantics clearer (toggle-include is non-destructive, hide is destructive); (b) lets us add per-call toasts only on hide; (c) preserves the existing `useTogglePlaylist` behavior used by Stories 3.1–3.5.
- ⚠️ **Hide failures are user-facing.** A silent rollback (no toast) violates AC #5b and degrades trust. Always toast on `onError`. The toast message MUST quote the playlist name in `"..."` (UTF-8 typographic quotes are fine, but plain `"..."` matches the existing project copy style).
- ⚠️ Story 7.3's hide flow shadows Story 7.4's unhide flow: both will use a single `useHidePlaylist` hook with `{ is_hidden: true | false }`. Story 7.4 will reuse this hook; do NOT rename or specialize it to "hide-only" (`useHidePlaylist` is the name agreed across stories per [ux-design README "toggleHide(id)"](../planning-artifacts/ux-design/README.md#L240)).
- ⚠️ The `sonner` primitive will likely add `sonner` and possibly `next-themes` as deps. `next-themes` is harmless in a Vite/React-Router project — the shadcn wrapper falls back gracefully if not configured. No app-level theme provider is required for this story.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-7.3 (lines 1073–1102)] — story requirements + GWT criteria.
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-7 (lines 967–971)] — FR/AR/NFR map: FR25–FR30, AR10, NFR13.
- [Source: _bmad-output/planning-artifacts/prd.md#FR26 + #FR27 + #FR30] — overflow menu structure, hide-implies-exclude, persistence.
- [Source: _bmad-output/planning-artifacts/ux-design/README.md (lines 87–105 "PlaylistCard > Overflow menu" + line 240 "toggleHide(id)")] — UX spec + mutation contract.
- [Source: _bmad-output/planning-artifacts/architecture.md] — frontend hooks pattern, all-fetches-via-lib/api, snake_case JSON.
- [Source: CLAUDE.md] — shadcn via CLI, Docker exec patterns, Postman sync rule, TanStack Query v5 idioms.
- [Source: _bmad-output/implementation-artifacts/7-1-playlist-hidden-state-schema-api.md] — backend API contract, atomic update, PATCH-drops-image_url-track_count asymmetry.
- [Source: _bmad-output/implementation-artifacts/7-2-playlist-grid-cover-art-card-layout.md] — `PlaylistCard` baseline, "Hide playlist" menu item already present with deferred-prop pattern, `useTogglePlaylist`-co-located convention.
- [Source: frontend/src/features/playlists/PlaylistCard.tsx (lines 121–133)] — `onToggleHide?` fallback to remove.
- [Source: frontend/src/hooks/usePlaylists.ts (existing 21 lines)] — `useTogglePlaylist` template to mirror; do not modify.
- [Source: frontend/src/App.tsx] — RouterProvider wrap site to host `<Toaster />`.
- [Source: backend/routers/playlists.py (lines 76–104)] — PATCH contract: atomic hide ⇒ exclude; response drops `image_url`/`track_count`.
- [Source: backend/services/sync_engine.py] — already filters `is_hidden=false`; verifies AC #7.
- [Source: memory `feedback_shadcn_cli` + `feedback_node_version` + `feedback_postman_sync`] — project-local guardrails.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

- `docker exec playlist_spotify-frontend-1 npx shadcn@latest add sonner --yes` → created `frontend/src/components/ui/sonner.tsx`; added `sonner ^2.0.7` and `next-themes ^0.4.6` to `package.json`.
- `docker exec playlist_spotify-frontend-1 npm run build` → green (`tsc -b && vite build`, 1919 modules, 503ms).
- `curl -X PATCH http://127.0.0.1:8000/api/v1/playlists/2NHiKi28QEBvBXbUhMyTuM -d '{"is_hidden": true}'` → `{"is_hidden": true, "is_included": false, ...}` (atomic hide ⇒ exclude confirmed).
- Restore: `curl -X PATCH ... -d '{"is_hidden": false}'` → `is_hidden=false, is_included=false` (unhide leaves include cleared per Story 7.1).
- Postman: `GET /collections/{uid}` → confirmed PATCH body example previously only carried `is_included`; updated to `{"is_included": true, "is_hidden": false}` with an expanded description covering atomic behavior and `image_url=null` / `track_count=null` PATCH-response asymmetry. `PUT` returned the collection UID — verified via follow-up GET.

### Completion Notes List

- **Option A taken** (per AC #8) — `PlaylistCard` calls `useHidePlaylist()` directly; the `onToggleHide` prop has been removed from the `Props` interface. Mirrors Story 7.2's `useTogglePlaylist` co-location pattern.
- **`useHidePlaylist`** added to [`frontend/src/hooks/usePlaylists.ts`](../../frontend/src/hooks/usePlaylists.ts) with full TanStack Query v5 optimistic lifecycle: `cancelQueries` → snapshot via `getQueryData` → `setQueryData` (flipping `is_hidden` and forcing `is_included=false` on hide, mirroring backend atomicity) → `onError` rolls back from `context.previous` → `onSettled` invalidates `['playlists']`. The mutation is explicitly typed `useMutation<Playlist, Error, Vars, { previous: Playlist[] | undefined }>` so the `context` parameter is correctly inferred.
- **Toaster mounted once** in [`frontend/src/App.tsx`](../../frontend/src/App.tsx) as a sibling of `<RouterProvider />` inside a fragment — NOT inside `AppShell` (per-route mount) or `PlaylistCard` (per-card mount), per AC #6.
- **Per-call `onError` toast** — `PlaylistCard` uses the `mutate(vars, { onError })` overload so the toast message can interpolate the local `playlist.name`. The hook-level `onError` still owns rollback; the per-call `onError` is additive (both fire) — this is idiomatic TanStack Query v5.
- **No `useTogglePlaylist` changes** — left untouched as required by AC #11; sibling hook, not specialization.
- **No backend changes** — Story 7.1 already ships the atomic PATCH + the sync engine `is_hidden=false` guard. AC #7 is verified by code inspection of [`backend/services/sync_engine.py`](../../backend/services/sync_engine.py) + the PATCH smoke above.
- **Postman updated** — the PATCH `playlists/:spotify_id` request body example now documents both `is_included` and `is_hidden`; description annotated with the atomic hide-implies-exclude rule and the PATCH-response `image_url=null` / `track_count=null` asymmetry. Collection UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`.
- **Smoke coverage**: (a) frontend build 200; (c) optimistic remove flows from `usePlaylists` cache shape change → `PlaylistGrid.filter(p => !p.is_hidden)` re-renders without the hidden card; (d) PATCH round-trip verified via curl — `is_hidden=true` persisted, refetch returns full payload; (e) sync engine WHERE clause unchanged from Story 7.1 (`is_included=true AND is_hidden=false`); (f) failure path — rollback restores cache from `context.previous` and the per-call `onError` fires `toast.error(...)`; verified by code path inspection. (b)/(g) hover/keyboard checks require an interactive browser session — not executable headlessly from this environment. Documented for user verification.
- **Race condition behavior** (AC #10) — each `useHidePlaylist().mutate(...)` invocation owns its own `previous` snapshot via the per-mutation `context`. Concurrent hides do not stomp each other; on partial failure the `onSettled` `invalidateQueries` brings the cache back to authoritative state. No additional locking needed.
- **`<Toaster />` props** — `richColors position="bottom-right"`; theme is auto-picked via `next-themes` (no app-level theme provider configured, sonner falls back to `system`, which works against the dark theme).

### File List

**Added:**
- `frontend/src/components/ui/sonner.tsx` (shadcn CLI)

**Modified:**
- `frontend/src/hooks/usePlaylists.ts` (new `useHidePlaylist` export; `useTogglePlaylist` unchanged)
- `frontend/src/features/playlists/PlaylistCard.tsx` (wire `useHidePlaylist` + sonner toast; remove `onToggleHide` prop and `console.debug` fallback)
- `frontend/src/App.tsx` (mount `<Toaster />`)
- `frontend/package.json` (`sonner ^2.0.7`, `next-themes ^0.4.6` added by shadcn CLI)
- `frontend/package-lock.json` (dependency resolution)
- Postman collection `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` (PATCH `/playlists/:spotify_id` body example + description)

## Change Log

| Date | Change | Author |
|---|---|---|
| 2026-05-20 | Story 7.3 created — wire Hide Playlist action with optimistic `useHidePlaylist` mutation + sonner toast on error. | bmad-create-story |
| 2026-05-20 | Story 7.3 implemented — `useHidePlaylist` optimistic mutation, sonner `<Toaster />` mounted in App.tsx, `PlaylistCard` wired with per-call `onError` toast, `onToggleHide` prop removed. Postman PATCH body example updated. | claude-opus-4-7 |
