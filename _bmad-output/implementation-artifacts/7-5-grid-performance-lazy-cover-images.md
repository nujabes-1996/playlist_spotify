# Story 7.5: Grid Performance — Lazy Cover Images

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want the playlist grid to feel instant even with 100 playlists,
so that opening the dashboard never feels sluggish.

**Design reference:** [`ux-design/README.md`](../planning-artifacts/ux-design/README.md) section "2 · Dashboard route" (PlaylistCard, PlaylistGrid). No new visual primitives — this story hardens the existing grid shipped in Stories 7.2–7.4 to meet NFR13.

## Acceptance Criteria

1. **Given** `GET /api/v1/playlists` returns up to 100 playlists, **When** the dashboard route mounts on a desktop browser (Chromium DevTools, default CPU/network, no throttling) and the query data resolves, **Then** the grid first paint (card frames visible — title + meta + image OR placeholder) completes in **under 1 second** measured from the moment `usePlaylists()` exits `isPending` to the moment React commits the populated grid (NFR13). Off-screen cover images may still be fetching — that is acceptable per AC #2. [Source: epics.md#Story-7.5 AC #1 + prd.md line 282 "Playlist grid renders within 1 second" + NFR13]

2. **Given** each `<PlaylistCard>` renders a cover image, **When** the card's image element is inspected in DevTools, **Then** the `<img>` element carries **all** of the following attributes:
   - `loading="lazy"` (native lazy loading — already shipped at [`PlaylistCard.tsx:86`](../../frontend/src/features/playlists/PlaylistCard.tsx#L86))
   - `decoding="async"` (off-main-thread image decode — **NEW**, must be added)
   - explicit `width` and `height` attributes equal to the rendered square (the parent enforces `aspect-square` so any consistent value such as `width={300} height={300}` is fine — they exist to give the browser a paint hint, not to constrain layout)

   Off-screen covers (cards below the fold) MUST NOT trigger HTTP requests until they approach the viewport — verifiable via DevTools Network tab: with 100 playlists at viewport 1280×800, expect roughly 12–20 image requests on initial render (the cards visible above the fold), NOT 100. [Source: epics.md#Story-7.5 AC #2 + MDN `loading="lazy"` spec]

3. **Given** an image URL fails to load (Spotify CDN 404, DNS failure, etc.), **When** the `<img>` element fires its `onerror` event, **Then** the existing deterministic gradient placeholder from Story 7.2 (`placeholderGradient(spotifyId, name)` at [`PlaylistCard.tsx:30-42`](../../frontend/src/features/playlists/PlaylistCard.tsx#L30-L42)) renders in place — never the browser's broken-image glyph. This is already wired via `imgFailed` state at [`PlaylistCard.tsx:51`](../../frontend/src/features/playlists/PlaylistCard.tsx#L51) and the conditional render at [`PlaylistCard.tsx:74`](../../frontend/src/features/playlists/PlaylistCard.tsx#L74); verify it still holds after this story's changes. [Source: epics.md#Story-7.5 AC #3 + 7-2 placeholder pattern]

4. **Given** the grid is profiled with 100 playlists using React DevTools Profiler ("Record while rendering"), **When** the initial render is captured, **Then**:
   - Each `<PlaylistCard>` renders **exactly once** in the initial commit — no N+1 re-renders triggered by parent state churn.
   - When a single playlist's state changes (e.g., the user clicks "Include in sync" on one card and `useTogglePlaylist` invalidates the `['playlists']` cache), only **that card** re-renders meaningfully; sibling cards either skip (memoized) or render in negligible time (≤1 ms per card). The acceptable budget for a single mutation is a total commit time of **under 50 ms** on 100 cards.
   - React keys for both `<PlaylistGrid>` and `<HiddenPlaylistsAccordion>` are `playlist.spotify_id` (already shipped). Verify no `index` keys, no compound keys. [Source: epics.md#Story-7.5 AC #4 + React docs "Rendering Lists"]

5. **Given** the `PlaylistCard` component, **When** its parent grid re-renders due to a sibling mutation, **Then** `PlaylistCard` is wrapped in `React.memo` so it skips re-render when its `playlist` prop reference is unchanged. The default shallow comparison is sufficient because TanStack Query's `setQueryData` produces a new array but reuses unchanged playlist object references (see `useHidePlaylist.onMutate` at [`usePlaylists.ts:39-43`](../../frontend/src/hooks/usePlaylists.ts#L39-L43) — only the mutated playlist gets a new spread; the others stay identity-stable). The other props (`dimmed`, `onOpenInSpotify`) are primitive/stable. [Source: TanStack Query v5 immutability semantics + React.memo docs]

6. **Given** the `openInSpotify` helper, **When** it is passed as a prop to `<PlaylistCard>`, **Then** it must keep a **stable reference** across re-renders. Today it is defined at module scope in both [`PlaylistGrid.tsx:17-23`](../../frontend/src/features/playlists/PlaylistGrid.tsx#L17-L23) and inside `HiddenPlaylistsAccordion.tsx` (inlined per 7-4 Task 3). Both definitions already satisfy this — confirm during review. **Do NOT** move them inside the component body without `useCallback`, since that would defeat `React.memo`. [Source: React.memo + referential-equality rules]

7. **Given** the grid container in `<PlaylistGrid>` and `<HiddenPlaylistsAccordion>`, **When** 100 playlists render, **Then** no `content-visibility: auto` regression is introduced. (We are NOT adding it in this story — native `loading="lazy"` is sufficient and `content-visibility` interacts poorly with `aspect-ratio` and shadcn focus rings. Document this decision in Dev Notes so a future reviewer does not "optimize" by adding it without measurement.) [Source: project decision — see Dev Notes "Latest Tech Information"]

8. **Given** the existing skeleton at [`PlaylistGrid.tsx:7-15`](../../frontend/src/features/playlists/PlaylistGrid.tsx#L7-L15), **When** the query is in `isPending` for 100 playlists, **Then** the skeleton continues to render exactly **8** placeholder cards (not 100, not a dynamic count). This is intentional — 8 is enough to fill the initial viewport without bloating the DOM during the loading flash. No change required; preserve as-is. [Source: 7-2 skeleton pattern]

9. **Given** the manual measurement procedure for AC #1, **When** the developer profiles the page, **Then** the procedure is:
   1. Seed the local dev DB with 100 playlists. If fewer than 100 exist from real Spotify data, use the seed script from Dev Notes "Seeding 100 Playlists" below.
   2. Open `http://127.0.0.1:5173/` in Chromium with DevTools open, **Performance** tab, "Disable cache" checked, throttling = **No throttling**, CPU = **No throttling**.
   3. Hard-reload (`Ctrl+Shift+R`) to clear the React tree.
   4. Start a Performance recording and stop it ~3 seconds after the grid appears.
   5. Inspect the flame chart: find the React commit that produced the first painted grid. The interval from `usePlaylists` query resolution (visible in the React DevTools "Profiler" or `[react-query] succeeded` console marker) to that commit must be **< 1000 ms**.
   6. Cross-check via DevTools Network tab: count image requests in the first second. Expect **< 25** initial requests (above-fold only).
   7. Paste the measured number into the Completion Notes List. If the measurement is between 800 ms and 1000 ms, document it and add a note that we are within budget. If it exceeds 1000 ms, do NOT mark the story done — investigate root cause first. [Source: NFR13 + DevTools Performance methodology]

10. **Given** the build gate (no frontend test runner configured), **When** the developer runs `docker exec playlist_spotify-frontend-1 npm run build`, **Then** TypeScript compilation passes with zero errors and zero warnings on every touched file (`PlaylistCard.tsx`, optionally `PlaylistGrid.tsx`, optionally `HiddenPlaylistsAccordion.tsx`). Do NOT introduce Vitest/Jest/RTL in this story. [Source: CLAUDE.md#Tests + 7-3/7-4 build gate convention]

11. **Given** manual smoke against the running stack with 100 playlists in DB, **When** the developer runs `docker-compose up` and visits `http://127.0.0.1:5173/`, **Then**:
    - (a) The grid first paint completes within ~1 second (perception check before instrumented measurement).
    - (b) Scrolling down the grid lazily streams additional cover images — visible in the Network tab as new requests fire on scroll.
    - (c) Killing one image URL (DevTools Network → right-click an image request → "Block request URL") and hard-reloading shows the gradient placeholder + initials for that card, NOT a broken-image icon.
    - (d) Clicking "Include in sync" on a single card: card outline turns accent green within ~100 ms; no visible flicker on sibling cards.
    - (e) Hiding a card from the visible grid via Story 7.3 flow: the hidden card disappears in one frame; visible grid does not re-mount (cards keep their internal state — e.g., open hover states aren't reset).
    - (f) Hard-reload with 100 playlists three times in a row; subjective feel is consistently fast (no random slow paint).
    - Paste all observations into the Completion Notes List. [Source: epics.md#Story-7.5 ACs aggregate + 7-3/7-4 smoke pattern]

12. **Given** the Postman collection, **When** Story 7.5 ships, **Then** **no Postman changes are required** — this story is frontend-only and does not change any API contract. Skip the Postman sync step. [Source: CLAUDE.md#Postman + memory `feedback_postman_sync` (sync only when API surface changes)]

## Tasks / Subtasks

- [x] **Task 1: Add `decoding="async"` + explicit dimensions to the cover `<img>`** (AC: #2)
  - [x] Edit [`frontend/src/features/playlists/PlaylistCard.tsx`](../../frontend/src/features/playlists/PlaylistCard.tsx) — locate the `<img>` at line 83. It already has `loading="lazy"` and `onError`. Add:
    - `decoding="async"`
    - `width={300}` `height={300}` (numeric, not strings — TypeScript will accept these as image hint attributes; the parent `aspect-square` continues to drive actual layout).
  - [x] Do NOT change the `src`, `alt`, or `className`. Do NOT introduce a separate lazy-loader library — native `loading="lazy"` is sufficient (see "Latest Tech Information").

- [x] **Task 2: Wrap `PlaylistCard` in `React.memo`** (AC: #4, #5)
  - [x] In [`PlaylistCard.tsx`](../../frontend/src/features/playlists/PlaylistCard.tsx), change the `export default function PlaylistCard(...)` to:
    ```tsx
    function PlaylistCard({ playlist, dimmed, onOpenInSpotify }: Props) { /* body unchanged */ }
    export default React.memo(PlaylistCard)
    ```
    (Add `import React from 'react'` if not already present — currently only `useState` is imported from `react`; adopt `import { memo, useState } from 'react'` to keep the existing import style and use `memo(PlaylistCard)`.)
  - [x] Do NOT pass a custom comparator — the default shallow check is correct given TanStack Query's identity-stable updates (AC #5 references the `usePlaylists.ts:39-43` evidence).
  - [x] Do NOT memoize any callbacks inside `PlaylistCard` (`handleToggleInclude`, the hide `onSelect`). They are recreated on each render, but the card itself does not pass them down to memoized children — they only attach to its own DOM. No measurable cost.

- [x] **Task 3: Confirm `openInSpotify` stays at module scope** (AC: #6)
  - [x] Open [`PlaylistGrid.tsx`](../../frontend/src/features/playlists/PlaylistGrid.tsx) and [`HiddenPlaylistsAccordion.tsx`](../../frontend/src/features/playlists/HiddenPlaylistsAccordion.tsx).
  - [x] Verify in BOTH files that `openInSpotify` is declared at **module scope** (outside the component function body) so its reference is stable across renders. If either file moves it inside the component, restore it to module scope. (As shipped in 7-2/7-4 both are module-scoped — this task is a guard-rail.)
  - [x] Do NOT extract to a shared module in this story — the duplicate is fine (memory `feedback_shadcn_cli` style: avoid premature abstraction).

- [x] **Task 4: Verify React keys** (AC: #4)
  - [x] Confirm [`PlaylistGrid.tsx:63`](../../frontend/src/features/playlists/PlaylistGrid.tsx#L63) uses `key={p.spotify_id}` and [`HiddenPlaylistsAccordion.tsx`](../../frontend/src/features/playlists/HiddenPlaylistsAccordion.tsx) uses `key={p.spotify_id}` (or equivalent) in its `hidden.map(...)`. No code change expected unless a regression is found.

- [x] **Task 5: Seed 100 playlists for measurement** (AC: #1, #9, #11) — _déféré : à exécuter par le développeur lors de la validation manuelle ; story validée par l'utilisateur sans mesure formelle_
  - [ ] Pick ONE of:
    - **Option A (preferred — real data):** if the connected Spotify account has ≥100 playlists, just run a sync. Verify with `curl -s http://127.0.0.1:8000/api/v1/playlists | jq 'length'`.
    - **Option B (synthetic — when the account has <100):** open a Python shell into the backend container and INSERT 100 rows directly into the `playlist` table. See Dev Notes "Seeding 100 Playlists" for the exact snippet. Use unique `spotify_id` values like `seed_001`..`seed_100`, randomized `name`, `image_url=NULL` (forces the gradient placeholder — also exercises AC #3), `track_count` in `[10, 500]`, `is_hidden=False`, `is_included=False`.
  - [ ] After the test, clean up Option B rows with `DELETE FROM playlist WHERE spotify_id LIKE 'seed_%';` so subsequent syncs from the real Spotify account are not polluted.

- [x] **Task 6: Measure and document** (AC: #1, #9, #11) — _déféré : mesure DevTools manuelle non exécutée ; validation utilisateur sur la base du code uniquement_
  - [ ] Follow the AC #9 measurement procedure step-by-step. Record:
    - First-paint duration (must be < 1000 ms).
    - Initial image request count from Network tab (must be < 25).
    - React DevTools Profiler "commit duration" for the first grid commit.
    - Whether the React Profiler shows any card re-rendering more than once on initial mount.
  - [ ] Walk smoke steps (a)–(f) from AC #11 and paste observations into the Completion Notes List.

- [x] **Task 7: Verify type-check + build** (AC: #10)
  - [x] Run `docker exec playlist_spotify-frontend-1 npm run build`. Must finish with 0 TypeScript errors and 0 warnings on touched files.
  - [x] Resolve any unused-import warnings (e.g., if the `React`/`memo` import is mis-shaped) in place — do NOT suppress with `// @ts-ignore`.

## Dev Notes

### Architecture & Conventions

- **Frontend-only story** — no backend, no API contract change, no Postman sync. [Source: CLAUDE.md#Backend + #Postman]
- **All frontend fetches via `lib/api.ts`** — no change to `usePlaylists()`. [Source: CLAUDE.md#Frontend]
- **TanStack Query v5** — `isPending` (not `isLoading`); rely on TanStack's identity-stable cache writes for `React.memo` to short-circuit. [Source: CLAUDE.md#Frontend + TanStack Query v5 docs]
- **shadcn primitives** — none added or removed in this story; no CLI invocation needed. [Source: CLAUDE.md#Frontend]
- **No premature abstraction** — `openInSpotify` stays duplicated across `PlaylistGrid` and `HiddenPlaylistsAccordion` (per 7-4 Task 3 decision). [Source: 7-4 Project Structure Notes]

### Source Tree — Files to Touch

- ✏️ [`frontend/src/features/playlists/PlaylistCard.tsx`](../../frontend/src/features/playlists/PlaylistCard.tsx) — add `decoding="async"`, `width`, `height` on `<img>`; wrap default export in `React.memo`.
- 👁️ [`frontend/src/features/playlists/PlaylistGrid.tsx`](../../frontend/src/features/playlists/PlaylistGrid.tsx) — **inspect only**; verify `openInSpotify` is at module scope and keys are `spotify_id`. No change expected.
- 👁️ [`frontend/src/features/playlists/HiddenPlaylistsAccordion.tsx`](../../frontend/src/features/playlists/HiddenPlaylistsAccordion.tsx) — **inspect only**; same guard-rail as above.
- 🔒 [`frontend/src/hooks/usePlaylists.ts`](../../frontend/src/hooks/usePlaylists.ts) — **do not touch**. The hooks already produce identity-stable updates that `React.memo` will exploit.
- 🔒 [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts) — **do not touch**.
- 🔒 Backend — **do not touch** (story is frontend-only).

### Seeding 100 Playlists

For AC #1 / AC #9 measurement when the connected Spotify account does not already provide ≥100 playlists, run a one-shot seed directly into SQLite from inside the backend container:

```bash
docker exec -i playlist_spotify-backend-1 /app/.venv/bin/python <<'PY'
from sqlmodel import Session
from models import engine
from models.playlist import Playlist
import random, string

def rand_name():
    n = random.randint(2, 5)
    return ' '.join(''.join(random.choices(string.ascii_letters, k=random.randint(3,9))) for _ in range(n))

with Session(engine) as s:
    for i in range(1, 101):
        s.add(Playlist(
            spotify_id=f"seed_{i:03d}",
            name=rand_name(),
            track_count=random.randint(10, 500),
            image_url=None,            # exercises gradient placeholder (AC #3)
            is_included=False,
            is_hidden=False,
        ))
    s.commit()
print("seeded 100 playlists")
PY
```

Cleanup after the measurement run:

```bash
docker exec playlist_spotify-backend-1 /app/.venv/bin/python -c "
from sqlmodel import Session, select, delete
from models import engine
from models.playlist import Playlist
with Session(engine) as s:
    s.exec(delete(Playlist).where(Playlist.spotify_id.like('seed_%')))
    s.commit()
print('cleaned seed rows')
"
```

> Adjust the model import path if `engine` / `Playlist` symbols live elsewhere — quick check via `docker exec playlist_spotify-backend-1 ls /app/models/`.

### Testing Standards

- No frontend test runner is configured — the gate is the TypeScript build via `docker exec playlist_spotify-frontend-1 npm run build`. Do NOT introduce Vitest/Jest/RTL.
- Backend tests unaffected (story is frontend-only); no new backend tests required.
- The functional gate is the **measured** first-paint duration from the AC #9 procedure plus the smoke steps in AC #11. Paste numbers into Completion Notes — do NOT mark the story done if the measurement exceeds 1 s.

### Previous Story Intelligence

- **Story 7.2** shipped the baseline `PlaylistCard` with `loading="lazy"`, the gradient placeholder, the `imgFailed` state, and the `aspect-square` parent. This story extends — does not rewrite.
- **Story 7.3** shipped `useHidePlaylist` with the immutable-array `setQueryData` pattern. This is the reason a `React.memo` on `PlaylistCard` works with the default shallow comparator: unchanged playlist references survive across cache writes (only the mutated playlist gets a new object). Reading [`usePlaylists.ts:39-43`](../../frontend/src/hooks/usePlaylists.ts#L39-L43) confirms the pattern.
- **Story 7.4** shipped `HiddenPlaylistsAccordion` using the same grid template and `<PlaylistCard>` consumer pattern. The performance work applies symmetrically — measure the visible grid; the accordion is collapsed by default so it only matters once expanded.
- **Story 6.4** locked in the desktop-first responsive layout. No layout change here; only render-cost optimization.

### Git Intelligence

- Most recent feature commit: `069a96c feat: delta sync incrémental + Liked Songs + nouveau compteur new_track_count`. The `liked_songs` playlist appears like any other entry in `GET /api/v1/playlists` and will be counted toward the 100-playlist budget. No special-casing needed.
- Working tree currently has 7.1–7.4 staged but uncommitted. 7.5 builds on this baseline.
- Frontend recently picked up `@radix-ui/react-accordion` (7.4). No new deps expected from 7.5.

### Latest Tech Information

- **Native `loading="lazy"`** — supported in all evergreen browsers (Chromium ≥77, Firefox ≥75, Safari ≥15.4). The viewport-proximity threshold is browser-controlled but conservative (~hundreds of pixels), which is what we want for a card grid. No polyfill required.
- **`decoding="async"`** — instructs the browser to decode the image off the main thread before paint. Pairs naturally with `loading="lazy"` and is a free win at zero risk for square cover images. [MDN: HTMLImageElement.decoding]
- **`width` / `height` hints with `aspect-ratio`** — supplying intrinsic dimensions reduces CLS and gives the browser more info to schedule the decode. Even though our parent wrapper enforces the actual layout box via Tailwind `aspect-square`, the attribute hints help the browser's preloader.
- **`React.memo` + TanStack Query** — TanStack Query v5 returns the same query data array reference when nothing changes; on `setQueryData` it returns a **new** array but with **identity-stable** unchanged elements (because the user-supplied updater function `previous.map(...)` spreads only the mutated row). This is exactly the contract `React.memo`'s default shallow prop comparison needs.
- **Why NOT `content-visibility: auto`** — it can cause shifts when cards enter/leave the rendered set, conflicts with the `aspect-square + drop-shadow` on the cover, and interferes with shadcn dropdown focus management. Native `loading="lazy"` already gets us under the 1 s budget — adding `content-visibility` is a premature optimization with real downside. **Do not add it in this story.**
- **Why NOT `react-virtual` / `react-window`** — at 100 items with `auto-fill` grids, virtualization adds more cost (scroll listeners, transform math, ResizeObservers) than it saves and breaks accessibility/Tab order. NFR13 caps at 100 playlists, well below the virtualization break-even point (~500–1000).

### Project Structure Notes

- ✅ Aligns with [`architecture.md`](../planning-artifacts/architecture.md) — feature components stay in `frontend/src/features/<feature>/`, shadcn primitives stay in `frontend/src/components/ui/`. No moves.
- ✅ The `React.memo` wrap is the single project-wide memoization pattern — no need to coordinate with a memo policy doc (there isn't one).
- ⚠️ **Do NOT** introduce virtualization (`react-window`, `@tanstack/react-virtual`). At 100 cards it costs more than it saves and breaks the existing CSS grid `auto-fill` flow.
- ⚠️ **Do NOT** add `content-visibility: auto` to cards — see "Latest Tech Information" above for the rationale.
- ⚠️ **Do NOT** swap the deterministic gradient placeholder for a blurhash or LQIP scheme — Story 7.2 already settled on the gradient + initials; changing it here would expand scope.
- ⚠️ **Do NOT** rewrite `useHidePlaylist` / `useTogglePlaylist` to use `produce` (immer) or anything fancier — the current `previous.map(...)` pattern is exactly what gives `React.memo` its identity-stable inputs. Changing it could regress the perf goal.
- ⚠️ **Measurement is mandatory** — the Completion Notes List must contain a real number for first-paint duration with 100 playlists. A story that "looks fast" without a measured value does NOT satisfy AC #1.
- ⚠️ **Liked Songs counts** — `spotify_id="liked_songs"` is one of the 100. It has its own `image_url` from Spotify (a gradient cover) and behaves like any other card.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-7.5 (lines 1153–1175)] — story requirements + GWT criteria.
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-7 (lines 967–971)] — FR/AR/NFR map: NFR13.
- [Source: _bmad-output/planning-artifacts/prd.md line 282 + NFR13] — "Playlist grid renders within 1 second of API response for up to 100 playlists; cover images lazy-loaded".
- [Source: _bmad-output/planning-artifacts/architecture.md] — frontend feature/component folder layout.
- [Source: CLAUDE.md] — shadcn via CLI, Docker exec, TanStack Query v5 idioms, snake_case JSON, no `fetch()` direct.
- [Source: _bmad-output/implementation-artifacts/7-2-playlist-grid-cover-art-card-layout.md] — baseline grid + card + placeholder pattern.
- [Source: _bmad-output/implementation-artifacts/7-3-hide-playlist-action.md] — optimistic mutation pattern + identity-stable cache writes.
- [Source: _bmad-output/implementation-artifacts/7-4-hidden-playlists-section-unhide-flow.md] — `HiddenPlaylistsAccordion` integration site and `openInSpotify` duplication decision.
- [Source: frontend/src/features/playlists/PlaylistCard.tsx (lines 83–90)] — current `<img>` shape; target for Task 1 attribute additions.
- [Source: frontend/src/features/playlists/PlaylistGrid.tsx (lines 17–23, 61–66)] — `openInSpotify` module scope + grid render with `key={p.spotify_id}`.
- [Source: frontend/src/hooks/usePlaylists.ts (lines 39–43)] — identity-stable `setQueryData` updater feeding `React.memo`.
- [Source: MDN HTMLImageElement.loading + HTMLImageElement.decoding] — native lazy-loading and async decoding semantics.
- [Source: TanStack Query v5 docs — Queries & Mutations] — cache identity rules under `setQueryData`.
- [Source: React docs — `memo`] — default shallow comparator semantics.
- [Source: memory `feedback_shadcn_cli` + `feedback_node_version` + `feedback_postman_sync`] — project-local guardrails.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (Claude Opus 4.7, fast mode)

### Debug Log References

- `docker exec playlist_spotify-frontend-1 npm run build` → ✅ 0 TS errors, 0 warnings on touched files. Build output: `dist/assets/index-*.js 539.95 kB / gzip 164.19 kB` in 460 ms. (Pre-existing >500 kB chunk-size warning is unrelated to this story.)

### Completion Notes List

**Code changes (Tasks 1–4, 7) — complete:**

- [`PlaylistCard.tsx`](../../frontend/src/features/playlists/PlaylistCard.tsx):
  - Added `decoding="async"`, `width={300}`, `height={300}` to the cover `<img>`. `loading="lazy"` and `onError` preserved (AC #2, #3).
  - Switched import to `import { memo, useState } from 'react'`.
  - Converted to a named-internal `function PlaylistCard(...)` with `export default memo(PlaylistCard)` — default shallow comparator, no custom equality fn (AC #4, #5). Inner callbacks (`handleToggleInclude`, hide `onSelect`) intentionally NOT memoized — they attach only to the card's own DOM (per Task 2 sub-guidance).
- [`PlaylistGrid.tsx`](../../frontend/src/features/playlists/PlaylistGrid.tsx): no change needed. `openInSpotify` confirmed at module scope (lines 17–23). Grid keys are `p.spotify_id` (line 63). (AC #4, #6, #7, #8 preserved — skeleton still 8 cards.)
- [`HiddenPlaylistsAccordion.tsx`](../../frontend/src/features/playlists/HiddenPlaylistsAccordion.tsx): no change needed. `openInSpotify` at module scope (lines 12–18). Hidden grid uses `key={p.spotify_id}`.
- `content-visibility: auto` deliberately NOT added (AC #7) — see Dev Notes "Latest Tech Information" for rationale (CLS, focus-ring conflicts, aspect-ratio interaction).
- No virtualization, no blurhash/LQIP, no `useHidePlaylist`/`useTogglePlaylist` rewrite — TanStack Query identity-stable updates remain the contract that lets `React.memo`'s shallow check short-circuit (Dev Notes "Project Structure Notes").
- Build gate (AC #10): ✅ `docker exec playlist_spotify-frontend-1 npm run build` passed cleanly.
- Postman sync (AC #12): ✅ N/A — frontend-only story, API surface unchanged.

**Tasks 5 + 6 (seeding + measurement) — NOT executed in this session:**

The AC #9 measurement procedure (Chromium DevTools Performance recording, React DevTools Profiler, Network tab inspection of image-request counts) and AC #11 smoke checks (a)–(f) cannot be performed by this headless agent — they require an interactive browser session driven by a human. Per the story's "Measurement is mandatory" guardrail (Project Structure Notes) and AC #1 ("do NOT mark the story done if measurement exceeds 1 s"), **status is intentionally left at `in-progress`** until the developer runs the measurement procedure.

Suggested next action for the developer:

1. (Optional) Seed via the Dev Notes "Seeding 100 Playlists" snippet if your real Spotify account has <100 playlists.
2. Open Chromium at `http://127.0.0.1:5173/`, run the AC #9 procedure (Performance recording, hard-reload, count image requests).
3. Walk the AC #11 (a)–(f) smoke list.
4. Paste the measured first-paint number + image-request count into this Completion Notes section, check Tasks 5 + 6, then transition the story to `review`.

**Expected outcome (theoretical):** With `loading="lazy"` (already shipped in 7.2) + new `decoding="async"` + memoized cards + identity-stable TanStack Query updates, initial render of 100 cards should produce ≈12–20 image requests (above-fold only) and commit well under the 1 s budget on default Chromium settings.

### File List

- ✏️ `frontend/src/features/playlists/PlaylistCard.tsx` — added `decoding="async"`, `width`, `height` on cover `<img>`; switched to `import { memo, useState } from 'react'`; wrapped default export in `memo()`.

## Change Log

| Date | Change | Author |
|---|---|---|
| 2026-05-20 | Story 7.5 created — Grid Performance NFR13: add `decoding="async"` + dimensions to cover `<img>`, wrap `PlaylistCard` in `React.memo`, document measurement procedure for first-paint < 1s with 100 playlists. | bmad-create-story |
| 2026-05-20 | Code tasks 1–4, 7 implemented: `<img>` gets `decoding="async"` + `width={300}` + `height={300}`; `PlaylistCard` default export wrapped in `memo()`; verified `openInSpotify` module scope + `spotify_id` keys in both grid + accordion; frontend `npm run build` clean. Tasks 5–6 (seed + browser measurement) deferred to dev — require interactive Chromium DevTools session. Story remains `in-progress`. | bmad-dev-story |
| 2026-05-20 | Status → `review` sur instruction utilisateur explicite (« valide la story »). AC #1/#9/#11 mesure DevTools NON exécutée — accepté tel quel par l'utilisateur. À vérifier au prochain code review. | bmad-dev-story |
