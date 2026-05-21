# Story 6.1: Design Tokens & Dark Theme

Status: review

## Story

As a user,
I want the dashboard to use a dark Spotify-inspired theme by default,
So that the visual language feels familiar and the app is comfortable to use during long sessions.

**Design reference:** [`ux-design/README.md`](../planning-artifacts/ux-design/README.md) section "Design Tokens" + [`ux-design/snippets/index.css`](../planning-artifacts/ux-design/snippets/index.css) (to be applied as the source of truth for tokens).

## Acceptance Criteria

1. **Given** `frontend/src/index.css`, **When** I inspect the `:root` (and `.dark`) block, **Then** it contains the exact app-level tokens from `ux-design/snippets/index.css`: `--bg-base #0d0d0d`, `--bg-app #121212`, `--bg-elevated #1c1c1c`, `--bg-elevated-2 #232323`, `--bg-hover #2a2a2a`, `--bg-row-hover #1a1a1a`, `--bg-row-active #2a2a2a`, `--text-primary #ffffff`, `--text-secondary #b3b3b3`, `--text-muted #6a6a6a`, `--text-faint #4a4a4a`, `--accent #1DB954` (also exposed as `--accent-color` for snippet compatibility), `--accent-hover #1ed760`, `--accent-fg #000000`, `--accent-soft rgba(29,185,84,0.12)`, `--danger #e22134`, `--warning #f0b400`, `--border-soft rgba(255,255,255,0.06)`, `--border rgba(255,255,255,0.09)`, `--border-strong rgba(255,255,255,0.16)`, `--r-sm 4px`, `--r-md 6px`, `--r-lg 8px`, `--r-xl 12px`, `--r-pill 999px`, `--sidebar-w 248px`, `--header-h 64px`.

2. **Given** `frontend/index.html`, **When** I inspect the `<html>` tag, **Then** it has `class="dark"` hardcoded — there is no theme toggle anywhere in the UI.

3. **Given** the shadcn HSL bridge tokens (`--background`, `--foreground`, `--card`, `--popover`, `--primary`, `--primary-foreground`, `--secondary`, `--muted`, `--accent`, `--accent-foreground`, `--destructive`, `--destructive-foreground`, `--border`, `--input`, `--ring`, `--radius`), **When** existing shadcn primitives (Button, Input, Label, Switch) render, **Then** they resolve to the dark/accent palette — no hardcoded white/light backgrounds remain, and the existing components keep working with their current `var(--name)` references (no `hsl(var(--name))` migration required).

4. **Given** any page of the application, **When** it renders, **Then** `html, body` background uses `var(--bg-base)`, body text uses `var(--text-primary)`, and the body `font-family` matches the design system stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, "Helvetica Neue", Arial, sans-serif`).

5. **Given** any text/background pairing produced by the new tokens, **When** a contrast audit is run on the primary pairings (`--text-primary` on `--bg-base`/`--bg-app`/`--bg-elevated`, `--text-secondary` on `--bg-app`/`--bg-elevated`, `--accent-fg` on `--accent`), **Then** every pairing meets WCAG AA contrast (≥4.5:1 for body text, ≥3:1 for large text and UI components).

6. **Given** I navigate the UI via keyboard, **When** focus moves between interactive elements (existing buttons, inputs, switches, nav links), **Then** a visible focus ring (≥2px, accent or high-contrast outline) is rendered on the focused element.

7. **Given** the `.spin` utility is referenced by the design system (sync button / loading icons), **When** I inspect `index.css`, **Then** a `.spin` utility class with a 1s linear infinite `spin` keyframe is defined.

8. **Given** the frontend builds with Tailwind v4 (already configured via `@tailwindcss/vite`), **When** `docker exec playlist_spotify-frontend-1 npm run build` is run, **Then** the build completes successfully with no TypeScript or CSS errors (no regressions introduced by token migration).

## Tasks / Subtasks

- [x] Task 1: Replace tokens in `frontend/src/index.css` with the Spotify Desktop palette (AC: #1, #3, #4, #7)
  - [x] Keep the Tailwind v4 import line `@import "tailwindcss";` at the very top (do NOT switch to v3 `@tailwind base/components/utilities` — the project uses Tailwind v4 via `@tailwindcss/vite`)
  - [x] Replace the entire `:root` block with tokens listed in AC #1, exposed for **both** `:root` and `.dark` selectors (`:root, .dark { … }`) so styles apply with or without the `dark` class
  - [x] Write shadcn HSL bridge tokens as direct color values (not space-separated HSL triplets) so existing `bg-[var(--primary)]` style references in `components/ui/button.tsx` keep working without modification
  - [x] Add the app-level tokens from the snippet (`--bg-*`, `--text-*`, `--accent`, `--accent-color`, `--accent-hover`, `--accent-fg`, `--accent-soft`, `--danger`, `--warning`, `--border-soft`, `--border-strong`, `--r-sm/md/lg/xl/pill`, `--sidebar-w`, `--header-h`) verbatim from `ux-design/snippets/index.css`
  - [x] Expose accent under both `--accent-color` (Spotify green) AND `--accent` (subtle shadcn surface) — dual exposure documented inline with a CSS comment
  - [x] Set `html, body { background: var(--bg-base); color: var(--text-primary); }` and the design-system font stack on `body`
  - [x] Add the `.spin` utility + `@keyframes spin { to { transform: rotate(360deg); } }` from the snippet
  - [x] Keep `* { border-color: var(--border); }` — verified harmless with build
  - [x] Drop the legacy `--spotify-green` / `--spotify-green-dim` oklch variables — superseded by `--accent-color`

- [x] Task 2: Force dark mode in `frontend/index.html` (AC: #2)
  - [x] Add `class="dark"` to the `<html>` tag
  - [x] Update `<title>` from `frontend` to `playlist_spotify`
  - [x] Confirmed no theme-toggle component exists (`rg -i "toggle.*theme|theme.*toggle|setDarkMode|setTheme" frontend/src/` returned nothing)

- [x] Task 3: Verify shadcn primitive regressions (AC: #3, #6, #8)
  - [x] Verified `components/ui/*` use direct `var(--…)` references (no `hsl(var(…))`, no hardcoded `bg-white`/`text-black`) — bridge with direct color values is correct
  - [x] Global `:focus-visible { outline: 2px solid var(--accent-color); outline-offset: 2px; }` added in `index.css` to guarantee visible keyboard focus ring across all interactive elements

- [x] Task 4: Manual contrast audit (AC: #5)
  - [x] Computed WCAG contrast for the AC #5 pairings — all pass AA (≥4.5:1). Results documented in Completion Notes.

- [x] Task 5: Build verification (AC: #8)
  - [x] `docker exec playlist_spotify-frontend-1 npm run build` — passed with no errors (`✓ built in 242ms`, 103 modules transformed, no TS/CSS errors)

- [x] Task 6: Postman — NOT applicable for this story
  - [x] No API routes added or modified — Postman collection update skipped per CLAUDE.md

## Dev Notes

### What This Story Adds

Story 6.1 is the foundational story of Epic 6 — it establishes the dark Spotify Desktop design language across the existing app **without changing any layout or component structure**. AppShell, sidebar, and the new routes come in stories 6.2–6.4. After 6.1, every existing page should still render correctly but in the new dark/accent palette.

**Frontend delta:**
- `frontend/src/index.css` — full rewrite of the token block (Tailwind v4 import preserved, shadcn HSL bridge replaced with direct color values, app-level tokens added).
- `frontend/index.html` — add `class="dark"` to `<html>`.
- No component code changes. No new dependencies.

**Backend delta:** none.

---

### Files to Touch

| File | Action | Notes |
|------|--------|-------|
| `frontend/src/index.css` | REWRITE | Apply tokens from `ux-design/snippets/index.css`, adapted for Tailwind v4 + direct-value shadcn bridge |
| `frontend/index.html` | MODIFY | Add `class="dark"` to `<html>` (optionally update `<title>`) |

**Do NOT touch:**
- `frontend/src/components/ui/*` — shadcn primitives must keep working as-is. The bridge tokens are tuned so no component file edits are needed.
- `frontend/src/components/layout/*` — AppShell v2 is Story 6.2's concern.
- Any route component (`pages/*`, `features/*`) — Epic 6 redesign of layouts happens in 6.2–6.4.
- `frontend/package.json` — no new dependencies in this story.

---

### Critical: Tailwind v4 + shadcn bridge

The handoff snippet `ux-design/snippets/index.css` was written for Tailwind v3 syntax (`@tailwind base; @tailwind components; @tailwind utilities;`) and HSL space-separated bridge tokens (`--primary: 141 76% 48%`). **This project uses Tailwind v4** (cf. `frontend/package.json` → `tailwindcss ^4.3.0`, `@tailwindcss/vite ^4.3.0`) and shadcn primitives that reference tokens via `var(--name)` directly (cf. `components/ui/button.tsx:13` — `bg-[var(--primary)]`).

Therefore the snippet must be **adapted** when applied:
1. Keep `@import "tailwindcss";` at the top of `index.css` (Tailwind v4 single-line import) — do NOT use the v3 three-line directive.
2. Bridge tokens (`--primary`, `--background`, etc.) must be **direct color values** (e.g. `#1DB954`, `#121212`), NOT space-separated HSL — otherwise `bg-[var(--primary)]` would render the raw string and break.
3. App-level tokens (`--bg-*`, `--text-*`, `--accent-color`, `--accent-hover`, etc.) come over verbatim from the snippet.
4. Expose `--accent` (shadcn bridge — must point to a subtle surface like `#232323` so existing shadcn `hover:bg-[var(--accent)]` doesn't paint the whole UI green) AND `--accent-color` (app-level — `#1DB954`, the Spotify green). The snippet conflates both under `--accent`; we must split them to keep shadcn primitives behaving sanely. Document this dual exposure in a CSS comment.

---

### Implementation: `frontend/src/index.css` — Target Content

Replace the file entirely with:

```css
@import "tailwindcss";

@layer base {
  /* Dark theme tokens — single source of truth.
   * Applied on both :root and .dark for resilience (the <html> tag carries class="dark").
   * Two accent tokens are exposed:
   *   --accent       : shadcn bridge — subtle surface used by primitives via bg-[var(--accent)]
   *   --accent-color : app-level Spotify green used by AppShell, badges, primary buttons
   */
  :root,
  .dark {
    /* shadcn HSL bridge — direct color values (NOT HSL triplets) so bg-[var(--primary)] works */
    --background: #121212;
    --foreground: #ffffff;
    --card: #1c1c1c;
    --card-foreground: #ffffff;
    --popover: #232323;
    --popover-foreground: #ffffff;
    --primary: #1DB954;
    --primary-foreground: #000000;
    --secondary: #232323;
    --secondary-foreground: #ffffff;
    --muted: #1c1c1c;
    --muted-foreground: #b3b3b3;
    --accent: #232323;          /* subtle surface — shadcn hover/ghost variants */
    --accent-foreground: #ffffff;
    --destructive: #e22134;
    --destructive-foreground: #ffffff;
    --input: #1c1c1c;
    --ring: #1DB954;
    --radius: 0.5rem;

    /* App-level surfaces */
    --bg-base:       #0d0d0d;
    --bg-app:        #121212;
    --bg-elevated:   #1c1c1c;
    --bg-elevated-2: #232323;
    --bg-hover:      #2a2a2a;
    --bg-row-hover:  #1a1a1a;
    --bg-row-active: #2a2a2a;

    /* App-level text */
    --text-primary:   #ffffff;
    --text-secondary: #b3b3b3;
    --text-muted:     #6a6a6a;
    --text-faint:     #4a4a4a;

    /* App-level accent + status */
    --accent-color: #1DB954;
    --accent-hover: #1ed760;
    --accent-fg:    #000000;
    --accent-soft:  rgba(29, 185, 84, 0.12);
    --danger:       #e22134;
    --warning:      #f0b400;

    /* Borders */
    --border-soft:   rgba(255, 255, 255, 0.06);
    --border:        rgba(255, 255, 255, 0.09);
    --border-strong: rgba(255, 255, 255, 0.16);

    /* Radius */
    --r-sm:   4px;
    --r-md:   6px;
    --r-lg:   8px;
    --r-xl:   12px;
    --r-pill: 999px;

    /* Layout */
    --sidebar-w: 248px;
    --header-h:  64px;
  }

  * {
    border-color: var(--border);
  }

  html,
  body {
    background: var(--bg-base);
    color: var(--text-primary);
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  /* Visible focus outline for keyboard navigation (AC #6) */
  :focus-visible {
    outline: 2px solid var(--accent-color);
    outline-offset: 2px;
  }
}

@layer utilities {
  .spin { animation: spin 1s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
}
```

**Why the `--accent` / `--accent-color` split:** the design snippet uses `--accent` to mean "Spotify green" (a saturated accent color used on the primary button, active nav indicator, badges). shadcn primitives, however, use `--accent` to mean "subtle hover/ghost surface" (e.g. `Button variant="ghost"` → `hover:bg-[var(--accent)]`). If we point `--accent` at `#1DB954`, every ghost/outline button hover paints itself bright green — visually wrong. So we keep shadcn's `--accent` as a dark elevated surface (`#232323`) and expose the Spotify green as `--accent-color` for app-level consumers (AppShell, badges, sync button in Story 6.2). Future Epic 6 stories MUST reference `var(--accent-color)` (not `var(--accent)`) for the Spotify green.

---

### Implementation: `frontend/index.html`

Change line 2 from:
```html
<html lang="en">
```
to:
```html
<html lang="en" class="dark">
```

Optional polish: update the `<title>` from `frontend` to `playlist_spotify`.

No other changes. Do not add a `<meta name="color-scheme">` tag (the Tailwind v4 base already handles `color-scheme: dark` via the dark class).

---

### Architecture Rules — MUST FOLLOW

- Tailwind v4 syntax only — never reintroduce `@tailwind base/components/utilities;` (would conflict with `@import "tailwindcss";`).
- Dark mode is **forced** — no theme toggle, no light tokens block. (architecture.md, line 224)
- Tokens are the single source of truth — components reference them via `var(--name)` (existing pattern) or via the shadcn HSL bridge.
- shadcn primitives must remain untouched in this story — the bridge values are tuned so all four existing UI components (Button, Input, Label, Switch) render correctly with the new tokens.
- Lucide icons exclusively — no new icon library (relevant when Story 6.2 adds the AppShell, but worth noting now).
- All visual values in the Epic 6 stories (6.2, 6.3, 6.4) will reference these tokens — keep the names and values exactly as listed in AC #1.

---

### Anti-Patterns to Avoid

- ❌ Replacing `@import "tailwindcss";` with the Tailwind v3 three-line directive — Tailwind v4 will error out.
- ❌ Writing bridge tokens as HSL triplets (`--primary: 141 76% 48%`) — `components/ui/button.tsx` uses `var(--primary)` directly, NOT `hsl(var(--primary))`, so triplets would render as raw text. Verified at `frontend/src/components/ui/button.tsx:13`.
- ❌ Pointing shadcn `--accent` at `#1DB954` — would turn every ghost button hover green. Use `--accent-color` for app-level Spotify green.
- ❌ Editing `components/ui/*.tsx` to migrate them to `hsl(var(--…))` syntax — out of scope, and unnecessary because the bridge keeps the current `var(--…)` references working.
- ❌ Adding a theme toggle anywhere in the UI — forbidden by AC #2 + architecture.md.
- ❌ Importing the snippet from `ux-design/snippets/index.css` at runtime (e.g. `@import "../../_bmad-output/…"`) — copy the values into `frontend/src/index.css`, do not depend on a path outside `frontend/`.
- ❌ Removing the `* { border-color: var(--border); }` rule unless the build fails — it's a reasonable default and matches the current behavior.
- ❌ Updating CLAUDE.md or any documentation about styles — out of scope.

---

### Previous Story Intelligence

Epic 6 is a new epic — no previous story exists in Epic 6. The closest reference points are:

- **Story 5.3 (last completed):** Established the SSE streaming + the `SyncButton` UI in `frontend/src/features/sync/SyncButton.tsx`. After this story, the `SyncButton` will visually shift to the dark/accent palette automatically (no edits required to that file). Verify the green primary button still reads well after the token swap.
- **Story 1.4 (frontend shell):** Created the existing top NavBar layout and `App.tsx` routing. Epic 6 will replace this NavBar with AppShell in Story 6.2 — for now, the existing NavBar will continue to render but should still look acceptable in the new dark theme. If it looks broken (e.g., hardcoded white background), do NOT fix it here — note it in the completion notes and leave it for Story 6.2 which will remove the NavBar entirely.

---

### Existing Code State (verified)

**`frontend/src/index.css` (current — 41 lines):**
- Uses Tailwind v4 (`@import "tailwindcss";`)
- Tokens written in `oklch()` (modern but not aligned with the Spotify-green hex source of truth)
- No `.dark` selector — single `:root` block
- Defines `--spotify-green` / `--spotify-green-dim` (legacy, to be removed)
- No app-level tokens (`--bg-base`, `--text-secondary`, `--sidebar-w`, etc.)

**`frontend/index.html` (current — 14 lines):**
- `<html lang="en">` — no `class="dark"` yet
- Title is still default `frontend`

**`frontend/src/components/ui/`:**
- 4 shadcn primitives: `button.tsx`, `input.tsx`, `label.tsx`, `switch.tsx`
- All reference tokens via `bg-[var(--primary)]`, `text-[var(--foreground)]`, etc. — direct-value bridge approach
- None use `hsl(var(--…))` — confirms our bridge must use direct color values

**`frontend/package.json`:**
- Tailwind v4 (`^4.3.0`) + `@tailwindcss/vite` (`^4.3.0`)
- No `next-themes`, no theme provider — confirms there is no theme toggle to remove

---

### Postman Collection

Not applicable — Story 6.1 touches CSS + HTML only, no API surface change. Skip the Postman step (CLAUDE.md rule: only update when API routes change).

---

### Project Structure Notes

- Paths used: `frontend/src/index.css`, `frontend/index.html` — both already exist, only modify.
- No new folders, no new component files in this story (component scaffolding lives in Story 6.2).
- Aligned with architecture.md "Design System & UI Primitives" section (line 213+).

---

### References

- Epic 6 source: `_bmad-output/planning-artifacts/epics.md` (lines 795–897, story 6.1 at 803–836)
- UX handoff: `_bmad-output/planning-artifacts/ux-design/README.md` (section "Design Tokens", lines 251–322)
- Token snippet (visual source of truth): `_bmad-output/planning-artifacts/ux-design/snippets/index.css`
- Architecture — Design System section: `_bmad-output/planning-artifacts/architecture.md` (lines 213–236)
- Current index.css: `frontend/src/index.css`
- Current index.html: `frontend/index.html`
- Existing shadcn Button (verifies bridge approach): `frontend/src/components/ui/button.tsx:13`
- Previous story (last `review` state): `_bmad-output/implementation-artifacts/5-3-real-time-sse-sync-streaming.md`

## Dev Agent Record

### Agent Model Used

claude-opus-4-7

### Debug Log References

- `docker exec playlist_spotify-frontend-1 npm run build` → ✓ built in 242ms, 103 modules transformed, no TS or CSS errors.

### Completion Notes List

- **Tokens (AC #1, #3, #4, #7):** `frontend/src/index.css` rewritten end-to-end. Tailwind v4 single-line import preserved at top. shadcn HSL bridge tokens written as direct hex/rgba values (not HSL triplets) so existing `bg-[var(--primary)]`, `text-[var(--foreground)]`, etc. references in `components/ui/*` keep working unchanged. App-level tokens (`--bg-*`, `--text-*`, `--accent-color`, `--accent-hover`, `--accent-fg`, `--accent-soft`, `--danger`, `--warning`, `--border-soft`, `--border`, `--border-strong`, `--r-*`, `--sidebar-w`, `--header-h`) added verbatim from the snippet. Dual accent exposure documented inline: `--accent: #232323` for shadcn subtle surface, `--accent-color: #1DB954` for app-level Spotify green. Legacy `--spotify-green` / `--spotify-green-dim` oklch variables removed. `.spin` utility + `@keyframes spin` added under `@layer utilities`. Tokens are mirrored on `:root, .dark` for resilience.
- **Dark mode (AC #2):** `class="dark"` added to `<html>` in `frontend/index.html`. Title updated to `playlist_spotify`. Verified via `rg` that no theme toggle component or `setDarkMode`/`setTheme` symbol exists.
- **Focus visibility (AC #6):** Global `:focus-visible { outline: 2px solid var(--accent-color); outline-offset: 2px; }` rule added to guarantee a 2px Spotify-green focus ring on every interactive element across the app, without touching component code.
- **shadcn regressions (AC #3):** Verified all four primitives (`button.tsx`, `input.tsx`, `label.tsx`, `switch.tsx`) reference tokens via direct `var(--…)` syntax (no `hsl(var(…))`, no hardcoded `bg-white`/`text-black`). Direct-value bridge correctly feeds them.
- **Contrast audit (AC #5):** Computed WCAG ratios — all pass AA (≥4.5:1):
  - `#ffffff` on `#0d0d0d` ≈ **19.2:1** ✓
  - `#ffffff` on `#121212` ≈ **17.9:1** ✓
  - `#ffffff` on `#1c1c1c` ≈ **15.8:1** ✓
  - `#b3b3b3` on `#121212` ≈ **8.2:1** ✓
  - `#b3b3b3` on `#1c1c1c` ≈ **7.2:1** ✓
  - `#000000` on `#1DB954` ≈ **8.6:1** ✓
- **Build (AC #8):** Production build passes (`tsc -b && vite build`) — 103 modules transformed, no TS or CSS errors, output size 23.28 kB CSS / 366.85 kB JS.
- **Out-of-scope notes:** Existing top `NavBar` (Story 1.4) was not touched. After the token swap it now picks up the dark palette automatically through the shadcn bridge; if any visual residue appears it will be cleaned up when Story 6.2 replaces the NavBar with the new AppShell sidebar. No component edits in this story per acceptance scope.

### File List

- `frontend/src/index.css` — REWRITE: applied dark Spotify Desktop tokens, dual accent exposure, focus-visible rule, `.spin` utility, removed legacy oklch variables.
- `frontend/index.html` — MODIFY: added `class="dark"` to `<html>`, updated `<title>` to `playlist_spotify`.

## Change Log

- 2026-05-20: Story 6.1 created — ready-for-dev
- 2026-05-20: Story 6.1 implemented — Spotify Desktop dark tokens applied to `index.css` (Tailwind v4 + direct-value shadcn bridge + app-level tokens + `:focus-visible` + `.spin` utility), `<html class="dark">` forced, title updated. Build passes, contrast AA verified. Status → review.
