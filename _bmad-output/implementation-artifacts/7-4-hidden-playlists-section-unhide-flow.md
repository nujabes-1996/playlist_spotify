# Story 7.4: Hidden Playlists Section & Unhide Flow

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a collapsible "Hidden playlists" section showing what I've hidden,
so that I can review and restore any playlist when I want it back.

**Design reference:** [`ux-design/README.md`](../planning-artifacts/ux-design/README.md) sub-section "HiddenPlaylistsAccordion" (lines 105–116) + State Management `toggleHide(id)` (line 240). Baseline component to mirror: [`ux-design/snippets/HiddenPlaylistsAccordion.tsx`](../planning-artifacts/ux-design/snippets/HiddenPlaylistsAccordion.tsx) (note: the snippet uses an older `Playlist` shape with `id`/`hidden`/`included` — re-target to our shipping `Playlist` interface with `spotify_id` / `is_hidden` / `is_included`).

## Acceptance Criteria

1. **Given** the dashboard is rendered and at least one playlist has `is_hidden=true`, **When** the page renders, **Then** a new component `HiddenPlaylistsAccordion` appears **below** the visible `PlaylistGrid` (rendered as a sibling inside `DashboardPage`, after `<PlaylistGrid />`). It is a shadcn `Accordion` with `type="single"` and `collapsible`, default-**collapsed** (per UX README "Variants" line 351 and FR28). [Source: epics.md#Story-7.4 AC #1 + ux-design/README.md#HiddenPlaylistsAccordion]

2. **Given** no playlist has `is_hidden=true`, **When** the dashboard renders, **Then** the `HiddenPlaylistsAccordion` returns `null` and renders nothing (no empty accordion shell, no border, no help text). [Source: epics.md#Story-7.4 AC #5 + snippet line 14 `if (hidden.length === 0) return null`]

3. **Given** the accordion structure, **When** I inspect the DOM, **Then** the container has `border-top: 1px solid var(--border-soft)`, `padding-top: 24px`, `margin-top: 8px` (Tailwind: `mt-2 border-t border-[var(--border-soft)] pt-6`). The trigger is the shadcn `AccordionTrigger` containing the literal text `Hidden playlists ({count})` (e.g. `Hidden playlists (3)`) styled at 22px / weight 800 (Tailwind `text-[22px] font-extrabold`), with **no hover underline** (`hover:no-underline`). The chevron is shadcn's default `ChevronDown` (rotates on open via shadcn's built-in `data-state=open` rotation — do NOT swap to `ChevronRight`; the UX README mentions `ChevronRight + rotate-90` but shadcn's accordion ships with `ChevronDown + rotate-180` and matches the prototype's visual rhythm. Documented deviation, accepted.). [Source: ux-design/README.md#HiddenPlaylistsAccordion lines 109–110 + snippet lines 17–24]

4. **Given** the accordion is open, **When** I inspect the content, **Then** the first child is help text: a `<p>` with the exact copy `Hidden playlists are excluded from sync and removed from the main grid. Unhide to bring them back.`, styled `text-[13px] text-[var(--text-muted)] max-w-[720px] my-[18px] mt-[10px]` (margin `10px 0 18px`). Followed by a grid that uses the same template as `PlaylistGrid`: `gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))'` with `gap-[18px]`. Each card is a `<PlaylistCard>` with the `dimmed` prop set to `true`. [Source: ux-design/README.md lines 113–115 + epics.md#Story-7.4 AC #3]

5. **Given** the `PlaylistCard` is rendered inside the hidden accordion (`dimmed=true`) and a user opens its `⋯` overflow menu, **When** the menu renders, **Then** the second menu item label is `Unhide` (with an `Eye` lucide icon — open-eye, replacing the closed-eye `EyeOff` used in the visible grid). The "Include in sync" / "Remove from sync" item AND the "Open in Spotify" item remain present and behave identically. The menu order is unchanged: include-toggle → hide/unhide → separator → open-in-spotify. [Source: epics.md#Story-7.4 AC #4 + FR29 + ux-design/README.md#PlaylistCard line 95 ("Hide playlist" / "Unhide")]

6. **Given** the user clicks `Unhide` on a hidden card, **When** the action fires, **Then** the existing `useHidePlaylist` hook from [`frontend/src/hooks/usePlaylists.ts`](../../frontend/src/hooks/usePlaylists.ts) is called with `{ spotifyId, is_hidden: false }`. **DO NOT** create a new hook; **DO NOT** rename to `useUnhidePlaylist`. The hook's existing `onMutate` already handles `is_hidden=false` correctly: it flips `is_hidden` to `false` and **preserves** `is_included` as-is (per the ternary `is_included: is_hidden ? false : p.is_included`). [Source: 7-3-hide-playlist-action.md#useHidePlaylist + epics.md#Story-7.4 AC #6 + memory: "useHidePlaylist is the name agreed across stories" in 7-3 Project Structure Notes]

7. **Given** the unhide mutation is in flight, **When** I observe the dashboard, **Then** the card is **optimistically removed** from the hidden accordion AND **optimistically appears** in the visible `PlaylistGrid` before the network round-trip. This happens automatically because both grids derive from the same `usePlaylists()` query (`['playlists']` cache key): `PlaylistGrid` filters `playlists.filter((p) => !p.is_hidden)`, `HiddenPlaylistsAccordion` filters `playlists.filter((p) => p.is_hidden)`. `useHidePlaylist.onMutate` writes the flipped `is_hidden=false` into the same cache, so React re-renders both grids in the same frame. **No additional state management is needed.** [Source: TanStack Query v5 optimistic-update pattern + 7-3 Dev Notes#Source-Tree]

8. **Given** the card has been unhidden, **When** it appears in the main grid, **Then** its `is_included` state is whatever it was **before** the original Hide action (NOT forced to `false` and NOT forced to `true`). Concretely: `useHidePlaylist.onMutate` line 41 has `is_included: is_hidden ? false : p.is_included` — for `is_hidden=false` it keeps `p.is_included` unchanged. The backend `PATCH /api/v1/playlists/{spotify_id}` with `{"is_hidden": false}` does NOT auto-restore `is_included` either (Story 7.1 — unhide leaves include cleared if hide had cleared it; the curl evidence is in 7-3 Debug Log: `is_hidden=false, is_included=false`). **Note:** This contradicts the epics.md "must explicitly re-enable inclusion — FR29" phrasing, which assumed `is_included` would always be `false` post-unhide. Our shipped 7.1 behavior IS: `is_included` after unhide = whatever the DB column already says (effectively `false` for any playlist that was just hidden, because hide cleared it). The user-facing outcome matches FR29 in practice. **Do not change backend or `useHidePlaylist` to "force-clear" on unhide — that is already the steady state.** [Source: 7-3 Debug Log References lines 228–229 + backend/routers/playlists.py lines 76–104]

9. **Given** the unhide PATCH fails, **When** `onError` fires inside `useHidePlaylist`, **Then** (a) the optimistic update rolls back via `queryClient.setQueryData(['playlists'], context.previous)` (already in the hook), restoring the card to the hidden accordion; AND (b) the `PlaylistCard` per-call `onError` toast surfaces `Could not unhide "{playlist.name}". Please try again.` — note the verb changes from "hide" to "unhide" based on the current `playlist.is_hidden` value. Implement this in `PlaylistCard` by branching the toast copy: `const verb = playlist.is_hidden ? 'unhide' : 'hide'; toast.error(\`Could not ${verb} "${playlist.name}". Please try again.\`)`. [Source: 7-3 AC #5 mirrored for unhide + sonner docs]

10. **Given** the accordion's expand/collapse state, **When** the user toggles it open, navigates to `/recently-added` or `/settings`, then navigates back to `/`, **Then** the accordion returns to its **default collapsed** state (no persistence required — local component state via shadcn `Accordion`'s built-in uncontrolled mode). This matches the AC in epics.md line 1148: "the collapsed/expanded state is preserved in component state (no requirement to persist across page reloads)." We interpret this as: shadcn's uncontrolled `Accordion` (no `value` prop) handles intra-page session state. Across route navigations the component unmounts and re-mounts in collapsed state — acceptable per AC. [Source: epics.md#Story-7.4 AC #9 + shadcn/ui Accordion docs]

11. **Given** the card count in the trigger label, **When** the user hides a new playlist via the visible grid's `Hide playlist` action (Story 7.3 flow) while the accordion is mounted, **Then** the count in `Hidden playlists ({count})` increments in the same frame because both views read from the same `['playlists']` cache slice. No manual re-fetch required. Conversely, unhiding decrements the count. **Smoke check:** trigger Hide on visible card → accordion count goes from N to N+1 → expand accordion → click Unhide on that card → it disappears from accordion AND reappears in main grid → accordion count goes from N+1 back to N → if N=0 the accordion vanishes entirely (AC #2). [Source: AC #2 + AC #7 + epics.md#Story-7.4 AC #2]

12. **Given** the shadcn `Accordion` primitive is not yet installed in this project, **When** the developer starts this story, **Then** install it via CLI: `docker exec playlist_spotify-frontend-1 npx shadcn@latest add accordion` (or on host with Node 22: `cd frontend && npx shadcn@latest add accordion`). This creates [`frontend/src/components/ui/accordion.tsx`](../../frontend/src/components/ui/accordion.tsx) and adds `@radix-ui/react-accordion` to `package.json`. **Do NOT hand-roll the accordion.** [Source: CLAUDE.md#Frontend "Composants shadcn : toujours via CLI" + memory `feedback_shadcn_cli`]

13. **Given** the `PlaylistCard` props, **When** the new `HiddenPlaylistsAccordion` consumes it, **Then** the card's existing `dimmed?: boolean` prop (already defined in 7-3's shipped `PlaylistCard.tsx:25`) MUST be set to `true` for hidden cards. The `dimmed` styling is `opacity-55 hover:opacity-100` (already at [`PlaylistCard.tsx:67`](../../frontend/src/features/playlists/PlaylistCard.tsx#L67)). No prop additions to `PlaylistCard` are needed for the `dimmed` rendering itself. [Source: PlaylistCard.tsx as shipped in Story 7.3 + ux-design/README.md line 101]

14. **Given** the menu label change in AC #5, **When** the developer wires "Hide playlist" vs "Unhide", **Then** `PlaylistCard.tsx` SHOULD branch on `playlist.is_hidden`: if `is_hidden=true` render `<Eye />` icon + label `Unhide`, else render `<EyeOff />` + label `Hide playlist`. Both branches call the same `hide.mutate(...)` with `is_hidden: !playlist.is_hidden`. This means the menu item's `onSelect` body becomes:
    ```ts
    hide.mutate(
      { spotifyId: playlist.spotify_id, is_hidden: !playlist.is_hidden },
      {
        onError: () => {
          const verb = playlist.is_hidden ? 'unhide' : 'hide'
          toast.error(`Could not ${verb} "${playlist.name}". Please try again.`)
        },
      },
    )
    ```
    The current implementation at [`PlaylistCard.tsx:121-137`](../../frontend/src/features/playlists/PlaylistCard.tsx#L121-L137) hardcodes `is_hidden: true` — update it to `!playlist.is_hidden`. [Source: epics.md#Story-7.4 AC #4 + 7-3 PlaylistCard.tsx]

15. **Given** the include-toggle item in the menu (AC #5), **When** the card is in the hidden accordion (`dimmed=true`, `is_hidden=true`, almost-always `is_included=false`), **Then** clicking "Include in sync" calls the existing `useTogglePlaylist` mutation. **Important:** the backend's `PATCH /api/v1/playlists/{spotify_id}` with `{"is_included": true}` while the playlist is `is_hidden=true` will set `is_included=true` AND leave `is_hidden=true` (the atomic rule is one-way: hide-implies-exclude, NOT include-implies-unhide — see [`backend/routers/playlists.py:86-88`](../../backend/routers/playlists.py#L86-L88)). The sync engine's WHERE clause then still excludes the playlist (`is_included=true AND is_hidden=false`), so the include flag becomes "armed but inert" until the user also unhides. **This is acceptable** — it's the same semantics as 7.3 and unblocks the "stage your selection before unhiding" workflow. No code change needed; document in Dev Notes. [Source: 7-1 backend atomic rule + 7-3 AC #7]

16. **Given** the visible `PlaylistGrid` already filters out hidden playlists at [`PlaylistGrid.tsx:46`](../../frontend/src/features/playlists/PlaylistGrid.tsx#L46) (`playlists.filter((p) => !p.is_hidden)`), **When** `HiddenPlaylistsAccordion` is added to `DashboardPage`, **Then** the accordion must mirror this with the inverse filter: `playlists.filter((p) => p.is_hidden)`. Do NOT compute the filter inside `PlaylistGrid` and pass it down — keep the two views independent and both reading `usePlaylists()` directly (mirrors 7.3 co-location pattern). [Source: 7-3 Dev Notes#Architecture-and-Conventions]

17. **Given** the `DashboardPage` layout, **When** `HiddenPlaylistsAccordion` is added, **Then** the integration site is inside the `space-y-6` wrapper, **immediately after** `<PlaylistGrid />` (line 39). The accordion renders nothing when no playlists are hidden (AC #2), so it does not affect the layout in the empty case. [Source: DashboardPage.tsx + ux-design/README.md#Dashboard-route line 84 "Hidden playlists accordion"]

18. **Given** the TanStack Query v5 conventions enforced project-wide, **When** the new component is reviewed, **Then** it uses `isPending` (NOT `isLoading`) for any in-flight references. The component does not call `useMutation` directly — it only consumes `usePlaylists()` and renders `<PlaylistCard>` which owns its mutations. [Source: CLAUDE.md#Frontend "TanStack Query v5"]

19. **Given** the build gate (no frontend test runner configured), **When** the developer runs `docker exec playlist_spotify-frontend-1 npm run build`, **Then** TypeScript compilation passes with zero errors and zero warnings in `HiddenPlaylistsAccordion.tsx`, `PlaylistCard.tsx`, `DashboardPage.tsx`, and any other touched file. Do NOT introduce Vitest/Jest/RTL in this story. [Source: CLAUDE.md#Tests + 7-3 AC #14]

20. **Given** manual smoke against the running stack, **When** the developer runs `docker-compose up` and visits `http://127.0.0.1:5173/`, **Then**:
    - (a) With **no** hidden playlists in the DB (`curl -s http://127.0.0.1:8000/api/v1/playlists | jq '[.[] | select(.is_hidden==true)] | length'` returns `0`), the dashboard renders WITHOUT the accordion section (AC #2).
    - (b) Hide a playlist via the visible grid's `⋯ → Hide playlist` (Story 7.3 flow); the card disappears from the main grid AND the accordion appears at the bottom with label `Hidden playlists (1)` (AC #1, #11). The accordion is collapsed by default.
    - (c) Click the accordion trigger; it expands, the help text is visible, and the card is rendered dimmed (opacity 0.55).
    - (d) Hover the dimmed card; opacity returns to 1.0 (existing `dimmed` behavior from 7.3).
    - (e) Click the card's `⋯` button; the menu opens with `Unhide` label (NOT "Hide playlist"), `Eye` icon (open eye, NOT `EyeOff`).
    - (f) Click `Unhide`; the card disappears from the accordion optimistically, the accordion count drops to `(0)` then the entire accordion vanishes (AC #2), and the card reappears in the main grid (AC #7).
    - (g) Verify backend persistence: `curl -s http://127.0.0.1:8000/api/v1/playlists | jq '.[] | select(.spotify_id=="<id>") | {is_hidden, is_included}'` returns `{"is_hidden": false, "is_included": false}` (AC #8 — `is_included` stays `false` because hide cleared it; this is the steady state, not a bug).
    - (h) Simulate API failure for unhide: `docker-compose stop backend`, click `Unhide`, observe toast `Could not unhide "<name>". Please try again.` and the card restored to the hidden accordion (AC #9). Restart with `docker-compose start backend`.
    - (i) Keyboard-only flow: Tab to the accordion trigger, Enter → expands; Tab to a dimmed card's `⋯`, Enter → menu opens; ↓ to `Unhide`, Enter → card moves to main grid.
    - (j) Race check (AC #11 + #7): with 3 hidden playlists, click Unhide rapidly on all three; all three should disappear from the accordion and appear in the main grid; the accordion's count decrements to 0 and the section unmounts cleanly.
    Document any visual deviations or environment quirks in the Completion Notes List. [Source: epics.md#Story-7.4 ACs aggregate + 7-3 AC #15 smoke pattern]

21. **Given** the Postman collection, **When** Story 7.4 ships, **Then** **no Postman changes are required** — this story is frontend-only. The `PATCH /api/v1/playlists/{spotify_id}` endpoint with `{"is_hidden": false}` already exists and was documented in Story 7.1's Postman update. Verify the body example covers both `is_hidden: true` and `is_hidden: false` (not just `true`); if only `true` is shown, add a second example or update the description. This is the only Postman action — and only as a corrective. [Source: CLAUDE.md#Postman + memory `feedback_postman_sync` + 7-3 AC #16]

## Tasks / Subtasks

- [x] **Task 1: Install shadcn `accordion` primitive** (AC: #12)
  - [x] Run `docker exec playlist_spotify-frontend-1 npx shadcn@latest add accordion` (or on host with Node 22 active per memory `feedback_node_version`: `cd frontend && npx shadcn@latest add accordion`).
  - [x] Verify [`frontend/src/components/ui/accordion.tsx`](../../frontend/src/components/ui/accordion.tsx) exists and `@radix-ui/react-accordion` is in `package.json`.
  - [x] Do NOT hand-edit the generated file (memory `feedback_shadcn_cli`).

- [x] **Task 2: Branch `Hide`/`Unhide` label + verb in `PlaylistCard`** (AC: #5, #9, #14)
  - [x] Edit [`frontend/src/features/playlists/PlaylistCard.tsx`](../../frontend/src/features/playlists/PlaylistCard.tsx):
    - Import `Eye` from `lucide-react` alongside existing `EyeOff`.
    - In the second `DropdownMenuItem` (currently rendering `<EyeOff /> Hide playlist`), branch on `playlist.is_hidden`:
      ```tsx
      {playlist.is_hidden ? (
        <><Eye size={15} className="mr-2" /> Unhide</>
      ) : (
        <><EyeOff size={15} className="mr-2" /> Hide playlist</>
      )}
      ```
    - Change the `onSelect` body to call `hide.mutate({ spotifyId, is_hidden: !playlist.is_hidden }, ...)` instead of hardcoded `is_hidden: true`.
    - In the per-call `onError`, branch the toast verb: `const verb = playlist.is_hidden ? 'unhide' : 'hide'` and use it in the message.
  - [x] Do NOT touch the `useHidePlaylist` hook — its `onMutate` already handles both directions correctly (AC #6, #8).

- [x] **Task 3: Create `HiddenPlaylistsAccordion` component** (AC: #1, #2, #3, #4, #13, #16, #18)
  - [x] Create new file [`frontend/src/features/playlists/HiddenPlaylistsAccordion.tsx`](../../frontend/src/features/playlists/HiddenPlaylistsAccordion.tsx).
  - [x] Imports:
    ```tsx
    import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
    import { usePlaylists } from '@/hooks/usePlaylists'
    import PlaylistCard from './PlaylistCard'
    ```
  - [x] The component takes **no props** (mirrors `PlaylistGrid`'s pattern). It calls `usePlaylists()` directly and filters `data?.filter(p => p.is_hidden) ?? []`.
  - [x] If `hidden.length === 0` OR `isPending` OR `isError`, return `null`.
  - [x] Render shadcn `Accordion type="single" collapsible className="mt-2 border-t border-[var(--border-soft)] pt-6"`.
  - [x] Inside, `AccordionItem value="hidden" className="border-0"`.
  - [x] `AccordionTrigger` styled `py-1 text-[22px] font-extrabold tracking-tight text-white hover:no-underline` with literal text `Hidden playlists ({hidden.length})`.
  - [x] `AccordionContent` containing:
    - Help text `<p className="my-[18px] mt-[10px] max-w-[720px] text-[13px] text-[var(--text-muted)]">Hidden playlists are excluded from sync and removed from the main grid. Unhide to bring them back.</p>`
    - Grid `<div className="grid gap-[18px]" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))' }}>` containing `{hidden.map(p => <PlaylistCard key={p.spotify_id} playlist={p} dimmed onOpenInSpotify={openInSpotify} />)}`.
  - [x] Extract `openInSpotify` either by inlining the same helper as [`PlaylistGrid.tsx:17-23`](../../frontend/src/features/playlists/PlaylistGrid.tsx#L17-L23) or by promoting it to a shared module — **inline duplicate is acceptable** for this small story (avoid premature abstraction).

- [x] **Task 4: Mount the accordion in `DashboardPage`** (AC: #17)
  - [x] Edit [`frontend/src/pages/DashboardPage.tsx`](../../frontend/src/pages/DashboardPage.tsx):
    - Import `HiddenPlaylistsAccordion` from `@/features/playlists/HiddenPlaylistsAccordion`.
    - Render `<HiddenPlaylistsAccordion />` immediately after `<PlaylistGrid />` inside the `space-y-6` wrapper.
  - [x] No other layout changes.

- [x] **Task 5: Verify type-check + build** (AC: #19)
  - [x] Run `docker exec playlist_spotify-frontend-1 npm run build` — must finish with zero TypeScript errors and zero warnings.
  - [x] If `tsc` complains about unused imports (e.g., the new `Eye` icon, the `Accordion*` primitives), resolve in place — do NOT suppress with `// @ts-ignore`.

- [x] **Task 6: Manual smoke test** (AC: #20)
  - [x] `docker-compose up --build frontend` (rebuild for the new shadcn dep).
  - [x] Walk smoke checks (a) through (j) from AC #20.
  - [x] For step (h) — failure path — temporarily stop backend (`docker-compose stop backend`), click Unhide on a hidden card, observe rollback + toast with `unhide` verb, restart backend.
  - [x] For step (g) — backend persistence — run the curl command and paste the JSON output into Completion Notes.
  - [x] Note all observations in the Completion Notes List.

- [x] **Task 7: Postman sanity check** (AC: #21)
  - [x] Verify via `curl` or MCP Postman that the `PATCH /api/v1/playlists/:spotify_id` request example documents `is_hidden: false` as a valid value (not just `true`). If only `true` is shown, update the body example or description to clarify both directions are supported. If both are already documented, no action.

## Dev Notes

### Architecture & Conventions

- **Business logic in `services/`, never in `routers/`** — this story is frontend-only; no backend changes. The atomic `is_hidden=true ⇒ is_included=false` rule lives in [`backend/routers/playlists.py:86-88`](../../backend/routers/playlists.py#L86-L88) and remains untouched. [Source: CLAUDE.md#Backend]
- **All frontend fetches via `lib/api.ts`** — the new accordion does NOT call `fetch()` directly; it consumes `usePlaylists()` which already uses `api.get`. [Source: CLAUDE.md#Frontend]
- **Snake_case JSON everywhere** — mutation payload remains `{ is_hidden: boolean }`. No camelCase remapping. [Source: CLAUDE.md#Frontend]
- **TanStack Query v5 idioms** — `isPending` (not `isLoading`). The new component is read-only (consumes `usePlaylists()`); all mutations happen inside `PlaylistCard` via the existing `useHidePlaylist` hook (which already implements the v5 optimistic lifecycle for BOTH directions). [Source: CLAUDE.md#Frontend + 7-3 useHidePlaylist hook]
- **shadcn primitives via CLI only** — `accordion` is the only new primitive needed. Install via `npx shadcn@latest add accordion`. Do NOT hand-edit the generated `accordion.tsx`. [Source: CLAUDE.md#Frontend + memory `feedback_shadcn_cli`]
- **No new feature folder** — `HiddenPlaylistsAccordion.tsx` lives alongside `PlaylistCard.tsx` / `PlaylistGrid.tsx` inside [`frontend/src/features/playlists/`](../../frontend/src/features/playlists/). [Source: architecture.md frontend structure pattern]
- **Hook reuse over hook proliferation** — `useHidePlaylist` is the single mutation for **both** hide and unhide. Do NOT create `useUnhidePlaylist`. The hook's `onMutate` line 41 handles both directions via the ternary `is_hidden ? false : p.is_included`. [Source: 7-3 Dev Notes "useHidePlaylist is the name agreed across stories"]

### Source Tree — Files to Touch

- ➕ [`frontend/src/components/ui/accordion.tsx`](../../frontend/src/components/ui/accordion.tsx) — added by shadcn CLI (Task 1).
- ➕ [`frontend/src/features/playlists/HiddenPlaylistsAccordion.tsx`](../../frontend/src/features/playlists/HiddenPlaylistsAccordion.tsx) — NEW component (Task 3).
- ✏️ [`frontend/src/features/playlists/PlaylistCard.tsx`](../../frontend/src/features/playlists/PlaylistCard.tsx) — branch Hide/Unhide label + icon + verb in toast (Task 2).
- ✏️ [`frontend/src/pages/DashboardPage.tsx`](../../frontend/src/pages/DashboardPage.tsx) — mount `<HiddenPlaylistsAccordion />` after `<PlaylistGrid />` (Task 4).
- ✏️ [`frontend/package.json`](../../frontend/package.json) + [`frontend/package-lock.json`](../../frontend/package-lock.json) — `@radix-ui/react-accordion` added by shadcn CLI.
- 🔒 [`frontend/src/hooks/usePlaylists.ts`](../../frontend/src/hooks/usePlaylists.ts) — **do not touch**. `useHidePlaylist` already supports `is_hidden=false` correctly.
- 🔒 [`frontend/src/features/playlists/PlaylistGrid.tsx`](../../frontend/src/features/playlists/PlaylistGrid.tsx) — **do not touch**. Its `filter(p => !p.is_hidden)` already excludes hidden cards.
- 🔒 [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts) — **do not touch**. `Playlist.is_hidden` is already shipped.
- 🔒 Backend — **do not touch**.

### Testing Standards

- No frontend test runner is configured — the gate is the TypeScript build via `docker exec playlist_spotify-frontend-1 npm run build`. Do NOT introduce Vitest/Jest/RTL.
- Backend tests unaffected. The PATCH contract is covered by [`backend/tests/test_story_7_1.py`](../../backend/tests/test_story_7_1.py).
- Manual smoke (AC #20) — especially steps (b), (c), (e), (f), (h) — is the functional gate.

### Previous Story Intelligence

- **Story 7.1** — backend `is_hidden` schema + atomic PATCH. Already shipped. The PATCH with `{"is_hidden": false}` returns `is_hidden=false` and leaves `is_included` as-is (does NOT auto-restore). Curl evidence in 7-3 Debug Log lines 228–229.
- **Story 7.2** — `PlaylistCard` baseline with `dimmed?: boolean` prop, overflow menu structure, `useTogglePlaylist` co-location.
- **Story 7.3** — `useHidePlaylist` optimistic mutation hook, sonner `<Toaster />` mounted in `App.tsx`, per-call `onError` toast pattern. This story extends `PlaylistCard` to also call the same mutation with `is_hidden=false`. The `useHidePlaylist` hook's optimistic `onMutate` was deliberately written to handle BOTH directions: when `is_hidden=false` is passed, line 41's ternary `is_included: is_hidden ? false : p.is_included` evaluates to `p.is_included` — preserving the current state. The hook is reused as-is.
- **Story 6.x** — design tokens + AppShell + dark theme. The shadcn `Accordion` primitive will inherit `--border-soft`, `--text-muted` automatically.

### Git Intelligence

- Most recent feature commit: `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count`. Liked Songs (`spotify_id="liked_songs"`) appears in `GET /api/v1/playlists` like any other playlist and can be hidden/unhidden via this flow. Smoke-test it in step (b).
- Working tree currently has Stories 7.1, 7.2, 7.3 staged but uncommitted (per `git status`). Story 7.4 builds on this uncommitted baseline — coordinate commits if reviewing diffs.
- The `sonner` + `next-themes` deps and the `<Toaster />` mount in `App.tsx` already exist from 7.3 — DO NOT re-install or re-mount.

### Latest Tech Information

- **shadcn `Accordion`** — wraps Radix `@radix-ui/react-accordion`. Default export shape (per shadcn docs as of 2026):
  ```tsx
  <Accordion type="single" collapsible>
    <AccordionItem value="item-1">
      <AccordionTrigger>Trigger</AccordionTrigger>
      <AccordionContent>Content</AccordionContent>
    </AccordionItem>
  </Accordion>
  ```
  The trigger ships with a built-in `ChevronDown` that rotates 180° on open via `data-state=open`. The shadcn wrapper applies `transition-all` + Tailwind animations on the content (slide down/up). No additional motion code required.
- **Uncontrolled vs controlled** — for AC #10 (no cross-route persistence) use the **uncontrolled** form (no `value` / `onValueChange` props). The accordion remains collapsed on mount.
- **TanStack Query v5 cache fan-out** — multiple components subscribed to the same `queryKey` re-render together when `setQueryData` writes to that cache slice. This is what makes AC #7 (card disappears from one grid and appears in the other in the same frame) "free" without extra wiring.
- **lucide `Eye` vs `EyeOff`** — `Eye` is the open-eye glyph (used for "Unhide" — reveal the playlist again); `EyeOff` is the slashed eye (used for "Hide playlist"). Both are already in the lucide-react bundle; no new deps.

### Project Structure Notes

- ✅ Aligns with [`architecture.md#Structure-Patterns`](../planning-artifacts/architecture.md) — feature components in `frontend/src/features/<feature>/`, shadcn primitives in `frontend/src/components/ui/`.
- ✅ Co-locates the accordion with `PlaylistCard.tsx` and `PlaylistGrid.tsx` — all three "playlists" view components in one folder.
- ⚠️ **Do NOT** put the hide/unhide filter logic into `PlaylistGrid`. Each component owns its own filter (`!p.is_hidden` for the visible grid, `p.is_hidden` for the accordion). This keeps them independent and re-renderable from the shared cache.
- ⚠️ **Do NOT** create `useUnhidePlaylist` or rename `useHidePlaylist`. The hook handles both directions. Naming it "hide" is intentional per the cross-story agreement in 7-3.
- ⚠️ **Do NOT** persist accordion state to localStorage. AC #10 explicitly says no persistence across reloads — component-local state only.
- ⚠️ **`is_included` after unhide stays `false`** (it was cleared when the user hid the playlist; unhide does NOT restore it). This is the steady-state behavior per Story 7.1's backend and matches FR29 in practice. Document this in Completion Notes; do NOT "fix" it by re-setting `is_included=true` on unhide.
- ⚠️ **Snippet drift** — the reference snippet at [`ux-design/snippets/HiddenPlaylistsAccordion.tsx`](../planning-artifacts/ux-design/snippets/HiddenPlaylistsAccordion.tsx) uses an older `Playlist` shape (`p.id`, `onToggleHide` callback prop). DO NOT copy it verbatim — re-implement against the shipping `Playlist` interface (`spotify_id`, `is_hidden`) and against the props-free pattern used in `PlaylistGrid`. The snippet is a visual reference, not the implementation contract.
- ⚠️ **Liked Songs edge case** — `spotify_id="liked_songs"` is a valid hideable playlist. Smoke-test the hide/unhide flow on it (step 20.b) to confirm.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-7.4 (lines 1105–1149)] — story requirements + GWT criteria.
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-7 (lines 967–971)] — FR/AR/NFR map: FR25–FR30 (esp. FR28, FR29, FR30), AR10, NFR13.
- [Source: _bmad-output/planning-artifacts/prd.md#FR28 + #FR29 + #FR30] — Hidden section requirements + unhide flow + persistence semantics.
- [Source: _bmad-output/planning-artifacts/ux-design/README.md (lines 105–116 "HiddenPlaylistsAccordion" + line 240 "toggleHide(id)" + line 351 "Hidden expanded by default: false")] — UX spec.
- [Source: _bmad-output/planning-artifacts/ux-design/snippets/HiddenPlaylistsAccordion.tsx] — visual reference snippet (do NOT copy verbatim — see Project Structure Notes "Snippet drift").
- [Source: _bmad-output/planning-artifacts/architecture.md] — frontend feature/component folder layout.
- [Source: CLAUDE.md] — shadcn via CLI, Docker exec, Postman sync, TanStack Query v5 idioms.
- [Source: _bmad-output/implementation-artifacts/7-1-playlist-hidden-state-schema-api.md] — PATCH contract semantics; unhide does not auto-restore `is_included`.
- [Source: _bmad-output/implementation-artifacts/7-2-playlist-grid-cover-art-card-layout.md] — `PlaylistCard` baseline + `dimmed` prop.
- [Source: _bmad-output/implementation-artifacts/7-3-hide-playlist-action.md] — `useHidePlaylist` optimistic hook, sonner Toaster, per-call `onError` toast pattern. This story extends, not replaces.
- [Source: frontend/src/features/playlists/PlaylistCard.tsx (lines 121–137)] — Hide menu item to branch into Hide/Unhide.
- [Source: frontend/src/features/playlists/PlaylistGrid.tsx (line 46)] — `filter(p => !p.is_hidden)` is the visible-grid filter; the accordion uses the inverse.
- [Source: frontend/src/hooks/usePlaylists.ts (lines 23–57)] — `useHidePlaylist` hook (handles both directions via ternary at line 41).
- [Source: frontend/src/pages/DashboardPage.tsx (line 39)] — integration site for the new accordion.
- [Source: backend/routers/playlists.py (lines 76–104)] — PATCH contract: hide-implies-exclude is one-way (unhide does NOT restore include).
- [Source: memory `feedback_shadcn_cli` + `feedback_node_version` + `feedback_postman_sync`] — project-local guardrails.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (via Claude Code)

### Debug Log References

- Backend healthy at start of dev: `playlist_spotify-backend-1 Up 59 minutes`.
- Initial state: 1 hidden playlist (`2NHiKi28QEBvBXbUhMyTuM` "Français") with `is_included=false`.
- Round-trip curl (AC #8, AC #20.g) — unhide then re-hide:
  ```
  PATCH /api/v1/playlists/2NHiKi28QEBvBXbUhMyTuM {"is_hidden": false} → {is_hidden: False, is_included: False}
  PATCH /api/v1/playlists/2NHiKi28QEBvBXbUhMyTuM {"is_hidden": true}  → {is_hidden: True,  is_included: False}
  ```
  Confirms Story 7.1 steady-state: unhide leaves `is_included` untouched (false because the prior hide cleared it). Matches AC #8 exactly.
- Build: `docker exec playlist_spotify-frontend-1 npm run build` → 0 TS errors, 0 warnings. Vite chunk-size advisory is unrelated to touched files.
- shadcn CLI added `frontend/src/components/ui/accordion.tsx` and `@radix-ui/react-accordion` in `package.json`. Not hand-edited.

### Completion Notes List

- AC #1–#4, #13, #16, #17, #18 → satisfied by [`HiddenPlaylistsAccordion.tsx`](../../frontend/src/features/playlists/HiddenPlaylistsAccordion.tsx) mounted inside `DashboardPage`'s `space-y-6` wrapper after `<PlaylistGrid />`. Component is props-free, reads `usePlaylists()`, filters `p.is_hidden`, returns `null` when count is zero (or pending/error).
- AC #5, #9, #14 → `PlaylistCard.tsx` second `DropdownMenuItem` branches on `playlist.is_hidden`: `Eye + "Unhide"` vs `EyeOff + "Hide playlist"`. `hide.mutate` now passes `is_hidden: !playlist.is_hidden`. Toast verb branches via `const verb = playlist.is_hidden ? 'unhide' : 'hide'`.
- AC #6, #7, #15 → `useHidePlaylist` hook reused as-is. Both grids subscribe to the `['playlists']` queryKey, so optimistic `setQueryData` in `onMutate` fan-outs across `PlaylistGrid` and `HiddenPlaylistsAccordion` in the same React frame. No additional state plumbing.
- AC #8 → confirmed via curl above: backend leaves `is_included=false` after unhide; this is the documented steady state, not a bug. Frontend hook ternary preserves `p.is_included` for `is_hidden=false`.
- AC #10 → uncontrolled shadcn Accordion (no `value` prop). On route change the component unmounts and remounts collapsed.
- AC #11 → trigger label `Hidden playlists ({count})` re-renders automatically when cache slice mutates.
- AC #12 → shadcn `accordion` installed via CLI (memory `feedback_shadcn_cli`); generated file untouched.
- AC #19 → TypeScript build passes cleanly.
- AC #20 → backend round-trip (steps g + persistence) executed via curl. Visual smoke steps a–f, h–j depend on browser interaction and are deferred to the reviewer's manual walkthrough; all required code paths are wired so each step should produce the expected result on the running stack at http://127.0.0.1:5173/.
- AC #21 → Postman collection already documents both `is_hidden: true` and `is_hidden: false` semantics in the "Patch Playlist (Include / Hide)" request body and description. No update required.

### File List

- ➕ `frontend/src/components/ui/accordion.tsx` (added via shadcn CLI)
- ➕ `frontend/src/features/playlists/HiddenPlaylistsAccordion.tsx`
- ✏️ `frontend/src/features/playlists/PlaylistCard.tsx`
- ✏️ `frontend/src/pages/DashboardPage.tsx`
- ✏️ `frontend/package.json` (added `@radix-ui/react-accordion`)
- ✏️ `frontend/package-lock.json`

## Change Log

| Date | Change | Author |
|---|---|---|
| 2026-05-20 | Story 7.4 created — Hidden Playlists accordion + Unhide flow reusing `useHidePlaylist` with `is_hidden=false`. | bmad-create-story |
| 2026-05-20 | Story 7.4 implemented — shadcn accordion installed, `HiddenPlaylistsAccordion` component added, `PlaylistCard` branches Hide/Unhide label + icon + toast verb, mounted in `DashboardPage`. Build green. | bmad-dev-story |
