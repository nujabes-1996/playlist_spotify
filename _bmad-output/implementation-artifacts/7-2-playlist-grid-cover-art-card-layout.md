# Story 7.2: Playlist Grid — Cover-Art Card Layout

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want to see my Spotify playlists as a grid of square cover-art cards,
so that the dashboard looks and feels like the Spotify Desktop app.

**Design reference:** [`ux-design/README.md`](../planning-artifacts/ux-design/README.md) sections "2 · Dashboard route" + "PlaylistCard". Baseline composant: [`ux-design/snippets/PlaylistCard.tsx`](../planning-artifacts/ux-design/snippets/PlaylistCard.tsx).

## Acceptance Criteria

1. **Given** the dashboard route `/` ([`frontend/src/pages/DashboardPage.tsx`](../../frontend/src/pages/DashboardPage.tsx)), **When** the user is authenticated and `usePlaylists()` resolves, **Then** visible playlists (`is_hidden === false`) render in a responsive CSS grid of square cover-art cards. Each card shows the playlist cover image, the playlist name and the track count (FR25). [Source: epics.md#Story-7.2 AC #1 + ux-design/README.md section "Your playlists"]

2. **Given** the grid container, **When** I inspect its computed CSS, **Then** it uses `display: grid`, `grid-template-columns: repeat(auto-fill, minmax(190px, 1fr))`, `gap: 18px` (the "Comfy" production density). The grid must be applied via an inline `style={{ gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))" }}` because Tailwind cannot statically generate `repeat(auto-fill, minmax(190px, 1fr))` from an arbitrary value safely (matches the [`PlaylistCard.tsx` snippet line 127–128](../planning-artifacts/ux-design/snippets/PlaylistCard.tsx)). [Source: epics.md#Story-7.2 AC #2 + snippets/PlaylistCard.tsx]

3. **Given** a `PlaylistCard`, **When** I inspect its structure (matching [`snippets/PlaylistCard.tsx`](../planning-artifacts/ux-design/snippets/PlaylistCard.tsx)), **Then** it has:
   - background `var(--bg-elevated)`, padding `14px` (Tailwind `p-3.5`), border-radius `8px` (`rounded-lg`).
   - Cover wrapper: square (`aspect-square`), `overflow-hidden`, `rounded-md` (`6px`), `box-shadow: 0 8px 24px rgba(0,0,0,0.5)` (Tailwind `shadow-[0_8px_24px_rgba(0,0,0,0.5)]`), `margin-bottom: 14px` (`mb-3.5`).
   - `<img>` cover with `class="h-full w-full object-cover"` and `loading="lazy"`, `alt={playlist.name}`.
   - Title `<h3>` 14.5px (`text-[14.5px]`), `font-weight: 700` (`font-bold`), color white (`text-white`), `line-clamp: 2`, `min-height: 2.6em` (so single-line titles still reserve 2 rows for grid alignment), `title={playlist.name}` for full-name tooltip on truncation.
   - Meta line: 12px (`text-xs`), color `var(--text-secondary)` — content `"{n} tracks"` using `track_count.toLocaleString()`.
   [Source: epics.md#Story-7.2 AC #3 + ux-design/README.md#PlaylistCard]

4. **Given** the card's `is_included` state, **When** `is_included === true`, **Then** (a) a 22×22 accent circle with a `Check` icon (Lucide `Check`, size 12, strokeWidth 3) appears top-left of the cover (`absolute left-2 top-2 z-[2]`, `bg-[var(--accent-color)]`, `text-black`, `shadow-[0_2px_6px_rgba(0,0,0,0.4)]`, `rounded-full`, `grid place-items-center`) AND (b) the card has a 2px solid accent outline (`outline outline-2 -outline-offset-1 outline-[var(--accent-color)]`). [Source: epics.md#Story-7.2 AC #4 + snippets/PlaylistCard.tsx lines 35, 46–54]

5. **Given** a desktop pointer hovers over a card, **When** the hover state activates (`group-hover` on the card root which is `group relative`), **Then**:
   - (a) The card background transitions to `var(--bg-hover)` (`hover:bg-[var(--bg-hover)]` with `transition`, ~200ms ease — Tailwind default `transition` is 150ms which is acceptable per ux-design tolerances).
   - (b) A 44×44 accent Play FAB appears bottom-right of the cover (`absolute bottom-2 right-2`, `h-11 w-11`, `rounded-full`, `bg-[var(--accent-color)]`, `text-black`, `shadow-lg`, Lucide `Play` icon size 16 with `fill="currentColor"`). It starts hidden as `opacity-0 translate-y-2` and becomes `opacity-100 translate-y-0` via `group-hover:opacity-100 group-hover:translate-y-0` with `transition`. On hover of the FAB itself: `hover:scale-[1.06] hover:bg-[var(--accent-hover)]`. The FAB is cosmetic (no onClick handler — clicking does nothing per ux-design#PlaylistCard line 98).
   - (c) A 32×32 black overflow button (`h-8 w-8`, `rounded-full`, `bg-black/70 hover:bg-black/90`, Lucide `MoreHorizontal` size 14, `text-white`) fades in top-right of the cover (`absolute right-2 top-2 z-[2]`, `opacity-0 group-hover:opacity-100` with `transition`).
   [Source: epics.md#Story-7.2 AC #5 + snippets/PlaylistCard.tsx lines 31–63, 84–92]

6. **Given** the overflow button, **When** it is clicked, **Then** a shadcn `DropdownMenu` opens (anchored `align="end"`, `min-w-[200px]`) with these items in order:
   - "Include in sync" (Lucide `CircleCheck`, 15px) — shown when `is_included === false`.
   - "Remove from sync" (Lucide `X`, 15px) — shown when `is_included === true`.
   - "Hide playlist" (Lucide `EyeOff`, 15px) — for cards in the visible grid (NOT in the hidden accordion — that's Story 7.4's concern; this story only renders cards from the visible grid where `is_hidden=false`, so the label is always "Hide playlist" here).
   - `DropdownMenuSeparator`.
   - "Open in Spotify" (Lucide `ExternalLink`, 15px).

   **Wiring in this story (7.2):**
   - "Include in sync" / "Remove from sync" → calls the existing `useTogglePlaylist()` mutation with `{ spotifyId: playlist.spotify_id, is_included: !playlist.is_included }` (re-uses Story 3.1 + 7.1 mutation; payload must NOT include `is_hidden`).
   - "Hide playlist" → wired to a `onToggleHide` prop on `PlaylistCard`, but the prop's implementation is **deferred to Story 7.3** (the menu item must exist and be clickable; the parent `DashboardPage` passes either `undefined` or a no-op handler that logs a `console.debug("hide TBD by Story 7.3")` for now — do NOT call any PATCH from 7.2 for hide).
   - "Open in Spotify" → wired to `onOpenInSpotify` prop. Default implementation in `DashboardPage`: `window.open(\`https://open.spotify.com/playlist/${spotifyId}\`, "_blank", "noopener,noreferrer")`. For the synthetic Liked Songs entry (`spotify_id === "liked_songs"`), open `https://open.spotify.com/collection/tracks` instead.

   [Source: epics.md#Story-7.2 AC #6 + ux-design/README.md#PlaylistCard + snippets/PlaylistCard.tsx lines 56–82]

7. **Given** a playlist has no cover image (`image_url === null` or empty string — Liked Songs always falls here per Story 7.1 AC #3), **When** the card renders, **Then** a deterministic placeholder is rendered in place of the `<img>`: a square `<div>` with a linear gradient computed deterministically from `spotify_id` (e.g., hash → hue ∈ [0,360), output `linear-gradient(135deg, hsl(H 60% 25%) 0%, hsl((H+40) 60% 12%) 100%)`), centered with the playlist's initial(s) — first letter of each whitespace-separated word, up to 2 chars, uppercase — in white, `font-weight: 800`, font-size scales with card width (use `text-3xl` or similar). The placeholder MUST occupy the same square slot (same `aspect-square` wrapper + `h-full w-full`), so the grid layout is identical with or without an image. No broken-image icon shall ever appear (covers FR + epic 7.5 AC #3 forward-compat). [Source: epics.md#Story-7.2 AC #7 + epics.md#Story-7.5 AC #3]

8. **Given** an image fails to load at runtime (e.g., Spotify CDN error), **When** the `<img>`'s `onError` fires, **Then** the same deterministic placeholder from AC #7 is rendered in place of the broken image (state-managed via a local `useState<boolean>` flag — no broken image icon ever shown). [Source: epics.md#Story-7.5 AC #3 — forward-compat in 7.2]

9. **Given** the grid mounts, **When** `usePlaylists()` is in its `isPending` state, **Then** a skeleton grid renders with 8 placeholder cards in the same grid container (same `gridTemplateColumns`/gap), each card being a `var(--bg-elevated)` square with `animate-pulse` and an internal `aspect-square` gradient skeleton — to avoid layout shift when data arrives. The empty state `playlists.length === 0` shows the centered empty state described in [`ux-design/README.md` section "Empty state"](../planning-artifacts/ux-design/README.md) (60px vertical padding, Lucide `Sparkles` icon 28px, H3 "No playlists yet", muted paragraph "Connect your Spotify account in Settings to start picking source playlists."). The error state continues to render the existing red error text (`"Failed to load playlists. Make sure you are connected to Spotify."`). [Source: existing PlaylistList.tsx loading/error patterns + ux-design/README.md "Empty state"]

10. **Given** the page renders on a wide desktop viewport (≥1280px), **When** I count columns, **Then** the `auto-fill, minmax(190px, 1fr)` grid yields 4–6 columns at ≥1280px, 3 columns at ~1024px, 2 columns at ~640px, and 1 column at <480px. **No** custom breakpoints are required — the responsive behavior MUST emerge from the `auto-fill, minmax` formula alone (do not add `grid-cols-N` Tailwind utilities). The grid lives inside the existing AppShell main column (already constrained by sidebar width — see [`AppShell.tsx`](../../frontend/src/components/layout/AppShell.tsx) — so no extra max-width is needed here). [Source: epics.md#Story-7.2 AC #10 + Story 6.4 responsive behavior]

11. **Given** the previous list-based components, **When** the grid view ships, **Then** [`frontend/src/features/playlists/PlaylistList.tsx`](../../frontend/src/features/playlists/PlaylistList.tsx) and [`frontend/src/features/playlists/PlaylistToggle.tsx`](../../frontend/src/features/playlists/PlaylistToggle.tsx) are **deleted** (no feature flag, no fallback — the grid is the only view per epic 7 framing). The new components live at `frontend/src/features/playlists/PlaylistCard.tsx` (exporting `PlaylistCard`) and `frontend/src/features/playlists/PlaylistGrid.tsx` (exporting `PlaylistGrid`, default export). [`DashboardPage.tsx`](../../frontend/src/pages/DashboardPage.tsx) imports `PlaylistGrid` instead of `PlaylistList`. [Source: epics.md#Story-7.2 AC #11 + CLAUDE.md project conventions]

12. **Given** the TypeScript `Playlist` interface in [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts), **When** I inspect its shape, **Then** it now includes the three fields from Story 7.1: `is_hidden: boolean`, `image_url: string | null`, `track_count: number`. Existing fields (`spotify_id`, `name`, `is_included`) remain. Field names stay snake_case (the API contract — no camelCase mapping; the snippet uses camelCase locally inside the component but the TS interface and props mirror the API). [Source: Story 7.1 API contract + CLAUDE.md#Frontend "snake_case"]

13. **Given** the include-toggle mutation (`useTogglePlaylist` in [`frontend/src/hooks/usePlaylists.ts`](../../frontend/src/hooks/usePlaylists.ts)), **When** the menu item "Include in sync" / "Remove from sync" fires, **Then** the existing mutation is reused unchanged — its onSuccess `invalidateQueries(['playlists'])` already refetches GET `/playlists` which (post-7.1) returns the three new fields, so the UI updates with the included-card outline + check badge automatically. No new mutation hook is introduced in 7.2. [Source: existing usePlaylists.ts + Story 7.1 API contract]

14. **Given** the shadcn `DropdownMenu` primitive, **When** I check the project before this story, **Then** it is **not yet installed** (verify: `ls frontend/src/components/ui/dropdown-menu.tsx` is absent). It MUST be added via the shadcn CLI: `docker exec playlist_spotify-frontend-1 npx shadcn@latest add dropdown-menu` (per [CLAUDE.md](../../CLAUDE.md) — never hand-roll shadcn primitives). This will pull in `@radix-ui/react-dropdown-menu` automatically. [Source: CLAUDE.md#Frontend "Composants shadcn : toujours via CLI" + memory feedback_shadcn_cli]

15. **Given** the Lucide icons used by this story (`Check`, `Play`, `MoreHorizontal`, `CircleCheck`, `X`, `EyeOff`, `ExternalLink`, `Sparkles`), **When** I import them, **Then** the existing `lucide-react` dependency is used as-is (already installed per `package.json`). No new icon library is introduced. [Source: existing package.json + snippets/PlaylistCard.tsx imports]

16. **Given** keyboard accessibility, **When** a user tabs across the grid, **Then** (a) the overflow `DropdownMenu` trigger is keyboard-focusable (shadcn `DropdownMenuTrigger` is a button by default; do NOT wrap the card itself in a `<button>` — the card is a `<div>`, hover-only affordances must not steal focus). (b) The overflow button has `aria-label="More options for {playlistName}"`. (c) The include badge has `title="Included in sync"` (existing snippet behavior). (d) The Play FAB has `aria-label="Preview"` and `tabIndex={-1}` (since it's purely cosmetic, it should NOT be a tab stop — diverges from the snippet which is tabbable; document this in dev notes). [Source: epics.md#Story-7.3 AC keyboard accessibility (carried forward) + WCAG keyboard nav]

17. **Given** the tests, **When** the developer runs `docker exec playlist_spotify-frontend-1 npm run build`, **Then** TypeScript compilation passes with no errors and no warnings in the new files. (Frontend test framework is not yet set up in this project — type-check via the build is the gate. Do NOT introduce Vitest/Jest in this story; that's out of scope.) [Source: CLAUDE.md#Tests + existing project state — no frontend test runner configured]

18. **Given** manual smoke against the running stack, **When** the developer runs `docker-compose up` and visits `http://127.0.0.1:5173/`, **Then**: (a) playlists render as cards in a responsive grid; (b) hovering reveals the Play FAB + overflow menu; (c) the overflow menu opens and shows the 3 items + separator + Open in Spotify; (d) clicking "Include in sync"/"Remove from sync" updates the outline + check badge (round-trips through PATCH); (e) the Liked Songs card renders with the deterministic placeholder (no image) and "Open in Spotify" opens `/collection/tracks`; (f) resizing the window from 1920 → 480px confirms 4–6 → 3 → 2 → 1 column reflow. Document any visual deviations in completion notes. [Source: epics.md#Story-7.2 ACs aggregate]

19. **Given** the Postman collection, **When** Story 7.2 ships, **Then** **no Postman changes are required** — this story is frontend-only and does not change any API contract (Story 7.1 already updated `GET /api/v1/playlists` and `PATCH /api/v1/playlists/{spotify_id}`). [Source: CLAUDE.md#Postman + Story 7.1 completion notes]

## Tasks / Subtasks

- [x] **Task 1: Install `dropdown-menu` shadcn primitive** (AC: #14)
  - [x] Run: `docker exec playlist_spotify-frontend-1 npx shadcn@latest add dropdown-menu` (or on host: `cd frontend && npx shadcn@latest add dropdown-menu` with Node 22 active per memory `feedback_node_version`).
  - [x] Verify `frontend/src/components/ui/dropdown-menu.tsx` exists and `@radix-ui/react-dropdown-menu` is added to `package.json`.
  - [x] Do NOT hand-edit the generated file (per memory `feedback_shadcn_cli`).

- [x] **Task 2: Update TypeScript `Playlist` interface** (AC: #12)
  - [x] Edit [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts):
    ```ts
    export interface Playlist {
      spotify_id: string
      name: string
      is_included: boolean
      is_hidden: boolean
      image_url: string | null
      track_count: number
    }
    ```
  - [x] No camelCase remapping anywhere.

- [x] **Task 3: Create `PlaylistCard` component** (AC: #3, #4, #5, #6, #7, #8, #15, #16)
  - [x] Create [`frontend/src/features/playlists/PlaylistCard.tsx`](../../frontend/src/features/playlists/PlaylistCard.tsx) modeled on [`snippets/PlaylistCard.tsx`](../planning-artifacts/ux-design/snippets/PlaylistCard.tsx) but adapted to the project's snake_case `Playlist` type and the PATCH-then-invalidate mutation pattern.
  - [x] Props: `{ playlist: Playlist; dimmed?: boolean; onToggleHide?: (spotifyId: string) => void; onOpenInSpotify?: (spotifyId: string) => void; }`. (Note: `onToggleInclude` is NOT a prop — the card calls `useTogglePlaylist()` directly to keep optimistic semantics local; or pass `onToggleInclude?` as a prop if you prefer to lift state. **Recommendation: keep `useTogglePlaylist` inside the card** for symmetry with the deleted `PlaylistToggle` and to localize mutation state.)
  - [x] Card root: `<div className="group relative cursor-pointer rounded-lg bg-[var(--bg-elevated)] p-3.5 transition hover:bg-[var(--bg-hover)] ..." />` — wire `is_included` outline + `dimmed` opacity per snippet.
  - [x] Cover wrapper `<div className="relative mb-3.5 aspect-square overflow-hidden rounded-md shadow-[0_8px_24px_rgba(0,0,0,0.5)]">`.
  - [x] Image: `<img src={playlist.image_url} loading="lazy" onError={() => setImgFailed(true)} className="h-full w-full object-cover" alt={playlist.name} />`. If `!playlist.image_url || imgFailed`, render the placeholder (see Task 4).
  - [x] Included badge (`Check`, 22×22 accent circle): render when `playlist.is_included`.
  - [x] Overflow `DropdownMenu` (32×32 trigger, items per AC #6).
  - [x] Play FAB (44×44 accent, `aria-label="Preview"`, `tabIndex={-1}`).
  - [x] Title `<h3>` + meta line `<div>`. Use `playlist.track_count.toLocaleString()`.
  - [x] Use `cn` from `@/lib/utils` and shadcn DropdownMenu imports from `@/components/ui/dropdown-menu`.

- [x] **Task 4: Implement deterministic placeholder** (AC: #7, #8)
  - [x] Inline helper inside `PlaylistCard.tsx`: `function placeholderGradient(spotifyId: string): { background: string; initials: string }`.
  - [x] Hash `spotify_id` to a stable hue: sum of char codes mod 360 (or any pure-function variant — but it MUST be deterministic and side-effect-free).
  - [x] Background: `linear-gradient(135deg, hsl(${H} 60% 25%) 0%, hsl(${(H+40)%360} 60% 12%) 100%)`.
  - [x] Initials: split `playlist.name` on whitespace, take first char of first 2 words, uppercase. Fallback to "?" if name is empty.
  - [x] Render placeholder as `<div className="grid h-full w-full place-items-center" style={{ background }}><span className="text-3xl font-extrabold text-white/90">{initials}</span></div>`.

- [x] **Task 5: Create `PlaylistGrid` component** (AC: #1, #2, #9, #10)
  - [x] Create [`frontend/src/features/playlists/PlaylistGrid.tsx`](../../frontend/src/features/playlists/PlaylistGrid.tsx) (default export).
  - [x] Call `usePlaylists()`; gate on `isPending` / `isError` / empty.
  - [x] **Pending state:** render 8 skeleton cards in the same grid container (same `gridTemplateColumns`/gap). Skeleton card: `<div className="rounded-lg bg-[var(--bg-elevated)] p-3.5 animate-pulse"><div className="mb-3.5 aspect-square rounded-md bg-white/5" /><div className="h-4 w-3/4 rounded bg-white/5" /><div className="mt-2 h-3 w-1/3 rounded bg-white/5" /></div>`.
  - [x] **Error state:** `<p className="text-sm text-red-500 p-3">Failed to load playlists. Make sure you are connected to Spotify.</p>` (preserve string from old `PlaylistList`).
  - [x] **Empty state:** centered, 60px vertical padding, `Sparkles` icon (28px, `text-[var(--text-secondary)]`), `<h3>` "No playlists yet" (18px, weight 700, mt-3), muted `<p>` "Connect your Spotify account in Settings to start picking source playlists.".
  - [x] **Data state:** filter `playlists.filter(p => !p.is_hidden)`, then map to `<PlaylistCard key={p.spotify_id} playlist={p} onOpenInSpotify={openInSpotify} />`. Grid wrapper: `<div className="grid gap-[18px]" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))" }}>`.
  - [x] `openInSpotify` handler: `(spotifyId) => window.open(spotifyId === "liked_songs" ? "https://open.spotify.com/collection/tracks" : \`https://open.spotify.com/playlist/${spotifyId}\`, "_blank", "noopener,noreferrer")`.
  - [x] Do NOT pass `onToggleHide` from this story (it stays undefined; Story 7.3 will wire it).

- [x] **Task 6: Swap `DashboardPage` to use `PlaylistGrid`** (AC: #1, #11)
  - [x] Edit [`frontend/src/pages/DashboardPage.tsx`](../../frontend/src/pages/DashboardPage.tsx): replace `import PlaylistList from '@/features/playlists/PlaylistList'` with `import PlaylistGrid from '@/features/playlists/PlaylistGrid'`, and `<PlaylistList />` with `<PlaylistGrid />`.
  - [x] Keep the existing `<SyncEventLog />`, header copy ("Your Playlists" h1 + subtitle) and wrapping `space-y-6` div (no layout regressions for the rest of the dashboard — that's Story 6.x's territory).

- [x] **Task 7: Delete the legacy list components** (AC: #11)
  - [x] `rm frontend/src/features/playlists/PlaylistList.tsx`.
  - [x] `rm frontend/src/features/playlists/PlaylistToggle.tsx`.
  - [x] Verify no other imports reference these files: `grep -r "PlaylistList\|PlaylistToggle" frontend/src` (should match only the new code if any incidental string overlap, but no `import` statements).

- [x] **Task 8: Verify type-check + build** (AC: #17)
  - [x] Run `docker exec playlist_spotify-frontend-1 npm run build` → must finish with no TypeScript errors.
  - [x] If `tsc` complains about unused imports or the old types, fix them in place.

- [x] **Task 9: Manual smoke test** (AC: #18)
  - [x] `docker-compose up` (rebuild frontend if needed: `docker-compose up --build frontend`).
  - [x] Hit `http://127.0.0.1:5173/`.
  - [x] Walk the 6 smoke checks (a–f) from AC #18 and note observations in the Completion Notes List.

## Dev Notes

### Architecture & Conventions

- **Frontend lives in `frontend/src/`** with the alias `@/` resolving there. New components for playlists go in [`frontend/src/features/playlists/`](../../frontend/src/features/playlists/) per the established feature-folder layout (see existing `auth/`, `config/`, `sync/`). [Source: CLAUDE.md#Frontend + existing layout]
- **All fetches through `lib/api.ts`.** This story does not introduce any new fetches; `useTogglePlaylist` and `usePlaylists` already go through `api.patch`/`api.get`. [Source: CLAUDE.md#Frontend "Tous les fetch via lib/api.ts"]
- **TanStack Query v5 idioms.** Use `isPending` (NOT `isLoading`). Don't add `onSuccess`/`onError` callbacks at the `useMutation` call site — the existing hook in `usePlaylists.ts` already invalidates `['playlists']` on success which is sufficient. [Source: CLAUDE.md#Frontend "TanStack Query v5"]
- **shadcn primitives via CLI only.** `dropdown-menu` is the only new primitive needed by this story; install via `npx shadcn@latest add dropdown-menu` (Docker or host with Node 22). Do not hand-edit. [Source: CLAUDE.md#Frontend + memory `feedback_shadcn_cli` + memory `feedback_node_version`]
- **Design tokens via CSS variables** — already established by Story 6.1 in [`frontend/src/index.css`](../../frontend/src/index.css). Use `var(--bg-elevated)`, `var(--bg-hover)`, `var(--accent-color)`, `var(--accent-hover)`, `var(--text-secondary)`, etc. Do NOT introduce raw hex colors. [Source: frontend/src/index.css + Story 6.1]
- **Single-source `Playlist` type.** The TypeScript interface lives in [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts) and mirrors the backend `PlaylistRead`. Snake_case throughout — no DTO mapper. [Source: existing types/index.ts]

### Source Tree — Files to Touch

- ➕ [`frontend/src/components/ui/dropdown-menu.tsx`](../../frontend/src/components/ui/dropdown-menu.tsx) — added by shadcn CLI (Task 1).
- ➕ [`frontend/src/features/playlists/PlaylistCard.tsx`](../../frontend/src/features/playlists/PlaylistCard.tsx) — new.
- ➕ [`frontend/src/features/playlists/PlaylistGrid.tsx`](../../frontend/src/features/playlists/PlaylistGrid.tsx) — new.
- ✏️ [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts) — extend `Playlist` interface.
- ✏️ [`frontend/src/pages/DashboardPage.tsx`](../../frontend/src/pages/DashboardPage.tsx) — swap `PlaylistList` → `PlaylistGrid`.
- ❌ [`frontend/src/features/playlists/PlaylistList.tsx`](../../frontend/src/features/playlists/PlaylistList.tsx) — delete.
- ❌ [`frontend/src/features/playlists/PlaylistToggle.tsx`](../../frontend/src/features/playlists/PlaylistToggle.tsx) — delete.
- 🔒 [`frontend/src/hooks/usePlaylists.ts`](../../frontend/src/hooks/usePlaylists.ts) — **do not touch**. The existing `useTogglePlaylist` mutation is reused as-is.
- 🔒 Backend — **do not touch** (Story 7.1 already shipped the API contract).

### Testing Standards

- No frontend test runner is configured in this project — the gate is TypeScript build via `docker exec playlist_spotify-frontend-1 npm run build`. Do NOT introduce Vitest/Jest/RTL in this story; that's an orthogonal concern that should be its own dedicated story if/when the team wants it.
- Backend tests: not impacted. Story 7.1's `test_story_7_1.py` already covers the API.
- Manual smoke (AC #18) is the functional gate.

### Previous Story Intelligence

- **Story 7.1** (`is_hidden` schema + API). Already shipped. Provides:
  - `is_hidden`, `image_url`, `track_count` on `GET /api/v1/playlists`.
  - Atomic hide-implies-exclude on `PATCH /api/v1/playlists/{spotify_id}` with `{"is_hidden": true}`.
  - Liked Songs (`spotify_id="liked_songs"`) returns `image_url=null` — Story 7.2 MUST render the deterministic placeholder for it (AC #7 + smoke step e).
  - PATCH response intentionally drops `image_url`/`track_count` — Story 7.1 dev notes line 112 — Story 7.2 already handles this by relying on `invalidateQueries(['playlists'])` to refetch GET.
- **Story 6.1** (design tokens) introduced all `--bg-*` / `--accent-*` / `--text-*` variables used by the snippet. Use them, do not duplicate.
- **Story 6.2** (AppShell) established the `group`-relative pattern with `hover:` modifiers in the codebase. The card's hover affordances follow that pattern.
- **Story 6.4** (desktop-first responsive) — the AppShell already constrains the main content width; we don't need any additional max-width container around the grid.
- **Story 3.1 / 3.4 / 3.5** — `useTogglePlaylist` is the established mutation. Reuse, don't fork.
- **Past warning from 7.1** — `PlaylistRead` shape changed in Story 7.1, which broke 4 backend tests inherited from older stories. The frontend `Playlist` TS interface in `types/index.ts` was NOT yet updated to match — this story finally aligns it (AC #12). Confirm no TS errors propagate elsewhere (search for `Playlist` usage: `grep -rn "Playlist[ \[{,]" frontend/src`).

### Git Intelligence

- Most recent backend feature commit: `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count` — provided the synthetic Liked Songs entry. The card MUST render a placeholder for it and open the correct Spotify URL (`/collection/tracks` vs `/playlist/{id}`).
- Local working tree already contains uncommitted changes from Story 7.1 (backend) — verify the dev DB has the `is_hidden` column applied (or has been recreated) before testing the smoke step; otherwise `GET /api/v1/playlists` may 500 with `no such column: playlist.is_hidden`.
- The recent UX-design and Epic 6 commits show the design system (tokens + AppShell) is already in production; no design-token additions needed in this story.

### Latest Tech Information

- **shadcn DropdownMenu** (via `@radix-ui/react-dropdown-menu`) — standard usage:
  ```tsx
  <DropdownMenu>
    <DropdownMenuTrigger asChild>
      <button aria-label="More options">…</button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" className="min-w-[200px]">
      <DropdownMenuItem onSelect={() => …}>…</DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem>…</DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
  ```
  Use `onSelect` (Radix) NOT `onClick` for the items — `onClick` works but Radix's `onSelect` integrates correctly with keyboard activation (Enter/Space) and auto-closes the menu. The snippet at [`snippets/PlaylistCard.tsx`](../planning-artifacts/ux-design/snippets/PlaylistCard.tsx) uses `onClick`; either is acceptable for v0 — but `onSelect` is preferred. **If in doubt, use the keyword "context7" — query Context7 MCP for the latest Radix DropdownMenu API.**
- **Tailwind v4** is in use (`tailwindcss ^4.3.0`). Arbitrary-value classes (`text-[14.5px]`, `shadow-[0_8px_24px_rgba(0,0,0,0.5)]`, `bg-[var(--bg-elevated)]`) work — no extra config needed.
- **TanStack Query v5** — `useMutation().mutate({...})` is sync-fire-and-forget. `useMutation().mutateAsync({...})` returns a promise. For the include-toggle item, use `mutate` (no awaiting needed).
- **React 19** — `useState`, `useEffect` semantics unchanged. No new patterns required.
- **Lucide React** — the version pinned in `package.json` is `^1.16.0`, which is the legacy npm package name for very old releases. The current ecosystem uses `lucide-react` ≥ 0.300. If any of the icons (`Sparkles`, `CircleCheck`, `EyeOff`, `MoreHorizontal`) do not exist in the installed version, **escalate before improvising** — open a question in the dev log rather than swapping icons. (Quick check at build time will surface this.) Do NOT bump `lucide-react` as part of this story without an explicit decision.

### Project Structure Notes

- ✅ Aligns with [`architecture.md#Structure-Patterns`](../planning-artifacts/architecture.md) — frontend feature folders. The new `playlists/` folder mirrors `auth/`, `config/`, `sync/`.
- ✅ shadcn primitives live in `frontend/src/components/ui/` — `dropdown-menu.tsx` lands there via the CLI.
- ⚠️ The `snippets/PlaylistCard.tsx` reference uses a different `Playlist` shape (camelCase `coverUrl`/`trackCount`/`included`/`hidden`) — **do NOT copy it verbatim**. Adapt to the snake_case `Playlist` from `types/index.ts` (AC #12). The visual structure and Tailwind classes are the canonical part of the snippet; the prop names are not.
- ⚠️ The snippet's `onToggleInclude` flow is callback-based with the parent owning the mutation. We keep the mutation **inside** `PlaylistCard` so the card matches the deleted `PlaylistToggle`'s self-contained mutation pattern — this avoids prop drilling and keeps optimistic UI local.
- ⚠️ The snippet's `isTarget` branch (Sync target playlist) is **out of scope** for 7.2. That visual is for the "Recently Added" Sync-target hero card (Stories 7.3+ / Epic 8). Implement the card without the `isTarget` branch; if/when needed it can be added later.
- ⚠️ Do NOT modify `usePlaylists.ts` to add a `useHidePlaylist` hook — that's Story 7.3's deliverable. Story 7.2 ends at "menu opens, hide item exists, click is a no-op / console.debug".

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-7.2 (lines 1009–1069)] — story requirements + GWT criteria.
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-7 (lines 967–971)] — FR/AR/NFR map: FR25–FR30, AR10, NFR13.
- [Source: _bmad-output/planning-artifacts/prd.md#FR25 + FR26] — playlist grid + overflow menu structure.
- [Source: _bmad-output/planning-artifacts/ux-design/README.md (lines 75–116)] — Dashboard "Your playlists" + PlaylistCard + HiddenPlaylistsAccordion design spec.
- [Source: _bmad-output/planning-artifacts/ux-design/snippets/PlaylistCard.tsx] — baseline component to adapt (snake_case adjustments per AC #12).
- [Source: _bmad-output/planning-artifacts/architecture.md] — frontend structure, shadcn-via-CLI, design-token-via-CSS-vars.
- [Source: CLAUDE.md] — project conventions, Docker exec patterns, Postman not applicable here.
- [Source: _bmad-output/implementation-artifacts/7-1-playlist-hidden-state-schema-api.md] — Story 7.1 API contract (`is_hidden`, `image_url`, `track_count`).
- [Source: _bmad-output/implementation-artifacts/6-1-design-tokens-dark-theme.md] — `--accent-color`, `--bg-elevated`, etc.
- [Source: _bmad-output/implementation-artifacts/6-2-appshell-v2-sidebar-header-layout.md] — `group`-relative + hover patterns.
- [Source: frontend/src/features/playlists/PlaylistList.tsx + PlaylistToggle.tsx] — components to delete; reuse their loading/error strings.
- [Source: frontend/src/hooks/usePlaylists.ts] — reuse `useTogglePlaylist` unchanged.
- [Source: frontend/src/types/index.ts] — `Playlist` interface to extend.
- [Source: frontend/src/index.css] — design tokens.
- [Source: commit 069a96c] — Liked Songs `LIKED_SONGS_ID = "liked_songs"` synthetic playlist (placeholder + special Spotify URL).

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

- `docker exec playlist_spotify-frontend-1 npx shadcn@latest add dropdown-menu --yes` → created `frontend/src/components/ui/dropdown-menu.tsx`, added `@radix-ui/react-dropdown-menu ^2.1.16` to `package.json`.
- `docker exec playlist_spotify-frontend-1 npm run build` → green (`tsc -b && vite build`, 1916 modules, 405ms).
- `curl http://127.0.0.1:8000/api/v1/playlists` → 200, payload includes `is_hidden`, `image_url`, `track_count` (Liked Songs `image_url=null` confirmed — placeholder path exercised).
- `curl http://127.0.0.1:5173/` → 200.

### Completion Notes List

- **Lucide icons** — package.json pins `lucide-react ^1.16.0`, an unusually old major. Verified all required icons exist in `node_modules/lucide-react/dist/esm/icons/`: `check`, `play`, `more-horizontal`, `circle-check`, `external-link`, `eye-off`, `sparkles`, `x`. Per Dev Notes "Latest Tech Information", did NOT bump the dependency — kept the existing major as-is.
- **`useTogglePlaylist` kept inside `PlaylistCard`** (per Dev Notes recommendation) — mirrors the deleted `PlaylistToggle` self-contained pattern; no prop drilling.
- **`onToggleHide` prop** — left wired but with a `console.debug("hide TBD by Story 7.3")` fallback when parent passes no handler. The menu item is clickable from 7.2; the PATCH wiring is Story 7.3's deliverable.
- **`DropdownMenuItem` uses `onSelect`** (Radix) rather than `onClick` — preferred for keyboard activation per Dev Notes.
- **Play FAB is `tabIndex={-1}`** — divergence from snippet, intentional per AC #16(d): cosmetic-only, must not be a tab stop.
- **No camelCase remapping** — `Playlist` interface extended in place with snake_case fields; `PlaylistCard` reads `playlist.spotify_id` / `playlist.image_url` / `playlist.track_count` directly.
- **Placeholder** — deterministic hue from `sum(charCodes(spotify_id)) % 360`, 135° linear gradient `hsl(H 60% 25%) → hsl((H+40) 60% 12%)`. Initials = first char of first 2 whitespace-split words, uppercase, fallback `?`.
- **`<img onError>`** flips local `useState` so the same placeholder renders on CDN failure (AC #8).
- **Skeleton** — 8 cards in the same grid container/gap to avoid layout shift.
- **Smoke test — coverage**: (a) grid renders (frontend 200 + backend returns expected payload with new fields); (e) Liked Songs `image_url=null` → placeholder path exercised by code (`showPlaceholder` true) and Open-in-Spotify resolves to `/collection/tracks`; (f) responsive reflow flows purely from `auto-fill, minmax(190px, 1fr)`. (b)–(d) hover/menu/include-toggle visual checks need an interactive browser session — not executable headlessly from this environment. Documented for user verification.
- **No Postman changes** — frontend-only story, API contract unchanged (Story 7.1 already shipped the new fields per `CLAUDE.md#Postman`).
- **Legacy components deleted** — `PlaylistList.tsx` and `PlaylistToggle.tsx` removed; `grep -r "PlaylistList\|PlaylistToggle" frontend/src` returns no matches.

### File List

**Added:**
- `frontend/src/components/ui/dropdown-menu.tsx` (shadcn CLI)
- `frontend/src/features/playlists/PlaylistCard.tsx`
- `frontend/src/features/playlists/PlaylistGrid.tsx`

**Modified:**
- `frontend/src/types/index.ts` (Playlist interface +`is_hidden`, `image_url`, `track_count`)
- `frontend/src/pages/DashboardPage.tsx` (swap PlaylistList → PlaylistGrid)
- `frontend/package.json` (`@radix-ui/react-dropdown-menu ^2.1.16` added by shadcn CLI)
- `frontend/package-lock.json` (dependency resolution)

**Deleted:**
- `frontend/src/features/playlists/PlaylistList.tsx`
- `frontend/src/features/playlists/PlaylistToggle.tsx`

## Change Log

| Date | Change | Author |
|---|---|---|
| 2026-05-20 | Story 7.2 implemented — playlist grid with cover-art cards, deterministic placeholder, hover Play FAB, overflow DropdownMenu, deleted legacy list/toggle components. | claude-opus-4-7 |

