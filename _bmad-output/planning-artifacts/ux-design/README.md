# Handoff: playlist_spotify dark redesign

## Overview

Visual redesign of **playlist_spotify**, a personal web app that aggregates the user's most-recently-added Spotify tracks across selected source playlists into a single rolling "Recent Adds" Spotify playlist. The web dashboard lets the user pick which playlists feed the harvest, trigger syncs, watch logs, and manage what's in the resulting playlist.

This handoff covers the **visual layer only** — dark theme, sidebar shell, playlist grid, dense track list, settings form, logs stream. Data fetching and backend wiring are out of scope; the developer wires real data on top.

## About the Design Files

The files in this bundle (in `prototype/`) are **design references built in HTML + inline JSX via Babel**. They are interactive mockups showing intended look, layout, hover states, and behavior. They are **not** production code to ship as-is.

The task is to **recreate these designs inside the existing target codebase**:

- **Stack**: React + Vite + Tailwind + shadcn/ui (already installed)
- **State**: TanStack Query v5 (already installed)
- **Routing**: react-router-dom (add if missing)
- **Icons**: lucide-react (already in shadcn ecosystem)
- **Path alias**: `@/` → `frontend/src/`

Reuse the existing shadcn primitives (`Button`, `Input`, `DropdownMenu`, `Accordion`, `Tooltip`, etc.). The TSX snippets in `snippets/` are drop-in starting points written against shadcn — they import from `@/components/ui/*`.

## Fidelity

**High-fidelity.** Colors, spacing, typography, hover states, and interactions are all final. Implement pixel-close to the prototype. The HTML prototype is the source of truth — if the README and prototype disagree, the prototype wins.

## Implementation order (recommended)

1. Copy `snippets/index.css` content into `frontend/src/index.css` (replaces shadcn's default `:root` block).
2. Force dark mode: add `class="dark"` to `<html>` in `index.html`; remove any theme toggles.
3. Run `bash snippets/shadcn-add.sh` (or copy the `npx` command into your shell).
4. Create the 4 component files from `snippets/`:
   - `src/components/AppShell.tsx`
   - `src/components/PlaylistCard.tsx`
   - `src/components/TrackRow.tsx`
   - `src/components/HiddenPlaylistsAccordion.tsx`
5. Build the 4 route files (`Dashboard.tsx`, `RecentlyAdded.tsx`, `Settings.tsx`, `Logs.tsx`) — structure described in **Screens** below.
6. Wire React Router in `App.tsx` with `AppShell` as the layout route.
7. Wire TanStack Query hooks on top — keep components dumb / presentational.

## Screens / Views

There are **5 screens** total: 4 routes + 1 sub-section (hidden accordion on Dashboard).

### 1 · AppShell (layout)

Persistent shell wrapping every route.

- **Outer grid**: `display: grid; grid-template-columns: var(--sidebar-w) 1fr; gap: 8px; padding: 8px; height: 100vh; background: var(--bg-base);`
- **Sidebar** (`var(--sidebar-w)` = 248px default, tweakable 200–320):
  - Background `var(--bg-app)` (`#121212`), rounded `8px`, padding `18px 12px 12px`.
  - Brand block (top): 28×28 gradient square mark (linear gradient from accent → cyan, original — NOT the Spotify logo) + wordmark `playlist_spotify` (font-weight 700, size 15px) with the `_` colored in accent.
  - Section label `WORKSPACE` (uppercase, letter-spacing 0.08em, 10px, muted color).
  - Nav items, each: icon (lucide, 17px) + label (13.5px, weight 600). Hover: `bg-hover` + white text. Active: `bg-elevated-2` + white text + 3px accent vertical bar on the left + accent icon color.
  - Nav items in order: `Dashboard` (LayoutDashboard icon), `Recently Added` (Clock), `Settings` (Settings cog), `Logs` (ScrollText).
  - Footer (margin-top: auto, border-top `var(--border-soft)`, padding 12px 10px): 26×26 gradient circle avatar + 3 lines (Connected as / email / status dot + "Token healthy · expires in 47m").

- **Main area**:
  - Rounded `8px`, background `linear-gradient(180deg, var(--bg-elevated) 0%, var(--bg-app) 280px)` so the top of every page has a subtle accent-tinted gradient that fades into the base.
  - `overflow: hidden; display: flex; flex-direction: column;`
  - Sticky topbar inside (see below), then scrollable content.

- **Topbar** (sticky, 64px height, padding `0 32px`, `backdrop-filter: blur(14px)`):
  - Left: two 32×32 circular nav buttons (back / forward, disabled in this MVP) with `lucide-react` `ChevronLeft`/`ChevronRight`.
  - On Dashboard only: search pill (`bg-elevated-2`, rounded-full, 320px wide) with `Search` icon and placeholder "Filter playlists…".
  - Spacer (flex: 1).
  - Right: status badge (rounded-full, `bg-elevated-2`, font-size 12px, weight 600, accent dot + "Last sync · 21 hours ago" — switches to red dot + "Last sync failed" on error).
  - Primary green button "Sync now" with `RotateCw` icon (rounded-full, accent bg, black text, hover lightens + scales 1.03).
  - When `scrollTop > 4`, topbar background becomes solid `rgba(18,18,18,0.92)` with a 1px bottom border (use a `scrolled` state from `onScroll` on the scroll container).

### 2 · Dashboard route (`/`)

Page title `"Your library"` (the H1 inside the page is `"Good evening"` — a friendly greeting, NOT the route title which is shown above the page).

Layout (inside scroll container, padding `8px 32px 40px`):

- **H1** `Good evening` (32px, weight 800, letter-spacing -0.025em).
- **Subtitle** (14px, secondary color): `<n> playlists feeding <accent>Recent Adds</accent> · next sync in 18 min`.
- **Section "Sync target"** — single card row, max 230px wide cards.
- **Section "Your playlists"** (margin-top 36px):
  - Section head: H2 "Your playlists" (22px, weight 800) + uppercase "SHOW ALL" link (12px, secondary, weight 700, letter-spacing 0.04em) on the right.
  - Responsive grid of `PlaylistCard`s.
  - Grid template: `repeat(auto-fill, minmax(190px, 1fr))` with 18px gap (the "Comfy" density tweak). Other tweak options: Compact = `minmax(150px, 1fr)` 14px gap; Spacious = `minmax(230px, 1fr)` 22px gap.
- **Hidden playlists accordion** (see below).
- **Empty state** when no playlists: centered, 60px vertical padding, Sparkles icon (28px), H3 "No playlists yet", muted paragraph "Connect your Spotify account in Settings to start picking source playlists."

#### PlaylistCard

`220px` typical, but fluid (grid `minmax`). Background `var(--bg-elevated)` (`#1c1c1c`), padding 14px, border-radius 8px.

- **Cover** (square, full card width, border-radius 6px, drop-shadow `0 8px 24px rgba(0,0,0,0.5)`, margin-bottom 14px). In the prototype, covers are generated abstract SVG gradients per-playlist. In production, replace with the Spotify-returned `images[0].url` — render with `<img class="h-full w-full object-cover">`.
- **Included badge** (top-left of cover when `included === true`): 22×22 accent circle with checkmark, `box-shadow: 0 2px 6px rgba(0,0,0,0.4)`. Z-index 2.
- **Overflow menu** (top-right of cover, only on hover): 32×32 black circle (`rgba(0,0,0,0.7)`), `MoreHorizontal` icon. Opacity 0 → 1 on `group-hover`. Uses shadcn `DropdownMenu`:
  - "Include in sync" / "Remove from sync" (text toggles based on state — not shown for the sync target card)
  - "Hide playlist" / "Unhide"
  - Separator
  - "Open in Spotify" with `ExternalLink` icon
- **Play FAB** (bottom-right of cover, only on hover): 44×44 accent circle, black `Play` icon (16px). Opacity 0 + `translateY(8px)` → opacity 1 + `translateY(0)` on hover. Hover: brightens + scale 1.06. Cosmetic only — clicking does nothing in this app.
- **Card hover**: background `var(--bg-hover)` (`#2a2a2a`).
- **Card "included" state**: 2px solid accent outline (`outline-offset: -1px`).
- **Card "dimmed" state** (hidden accordion): `opacity: 0.55`, returns to 1 on hover.
- **Title** (h3): 14.5px, weight 700, color white, `line-clamp: 2`, `min-height: 2.6em` so single-line titles still reserve 2 rows of height for grid alignment.
- **Meta line** (12px, secondary color): `"{n} tracks"`. On the sync target card: ` • Sync target` appended in accent + bold.

#### HiddenPlaylistsAccordion

Below the main grid. Uses shadcn `Accordion` (single, collapsible).

- Top border `1px solid var(--border-soft)`, padding-top 24px, margin-top 8px.
- Trigger: `ChevronRight` (16px, rotates 90° when open) + H2 "Hidden playlists ({count})" (22px, weight 800, NO underline on hover).
- Default collapsed.
- When open:
  - Help text (13px, muted, max-width 720px, margin `10px 0 18px`): "Hidden playlists are excluded from sync and removed from the main grid. Unhide to bring them back."
  - Same `PlaylistCard` grid as the main section but every card gets the `dimmed` prop.
  - Cards' overflow menu shows "Unhide" instead of "Hide".
- Hide entirely if `hidden.length === 0`.

### 3 · Recently Added route (`/recently-added`)

Shows the current contents of the rolling Recent Adds playlist.

- **Hero block** — full-bleed across the main area (uses negative horizontal margins to break out of the page's 32px padding):
  - 24px top padding, 28px bottom padding, 32px horizontal padding.
  - Background: `linear-gradient(180deg, color-mix(in oklab, var(--accent-color) 40%, #1a1a1a) 0%, var(--bg-elevated) 100%)`. The accent color tints the top — when accent changes via Tweaks, the hero gradient changes too.
  - Flex row, gap 26px, `align-items: flex-end`.
  - Cover: 232×232px, border-radius 4px, `box-shadow: 0 16px 40px rgba(0,0,0,0.6)`.
  - Meta column:
    - Kicker (12px, weight 700, uppercase, letter-spacing 0.06em, white): "AUTO-SYNCED PLAYLIST"
    - Title: `clamp(40px, 5vw, 72px)`, weight 900, letter-spacing -0.04em, line-height 1, margin `6px 0 14px`.
    - Sub (13px, secondary): `<strong>email</strong> • 20 of 50 tracks • about X hr Y min • updated 21 hours ago from 8 source playlists`.

- **Hero actions row** (padding 20px 32px 4px, gap 16px, subtle gradient overlay top→none, breaks the 32px margin too):
  - Primary "Sync now" button (RotateCw icon, rounded-full, accent).
  - Secondary "Open in Spotify" button (ExternalLink icon, transparent with 1px border).
  - 36×36 icon-only "more" button (MoreHorizontal).

- **Track list** (margin-top 12px, padding `0 8px`):
  - **Sticky header row** (`position: sticky; top: 0`, `background: rgba(18,18,18,0.92)` + `backdrop-filter: blur(12px)`, z-index 5, border-bottom 1px var(--border-soft)):
    - Columns: `36px | minmax(220px, 4fr) | minmax(160px, 3fr) | minmax(140px, 2fr) | 60px | 40px`
    - Labels: `# | TITLE | ALBUM | DATE ADDED | <Clock icon> | ` — uppercase, 11px, weight 600, letter-spacing 0.06em, muted color.
  - **TrackRow** (described next).

#### TrackRow

Same 6-column grid as the header. Padding 8px 16px, border-radius 4px (subtle on hover background), `gap: 14px`, `align-items: center`.

- **Column 1 (index)**: row number in muted color, centered. On row hover: number is replaced by a 12px Play icon in white (use `group-hover` swap with `hidden`/`grid` utilities).
- **Column 2 (title)**: flex row, gap 12px:
  - 40×40 thumbnail (border-radius 3px, object-cover).
  - Stack:
    - Track title: 14.5px, weight 500, white, single-line ellipsis. If `isNew`, append a small accent pill: "NEW" (background `accent / 15%`, accent color, 10px, weight 700, uppercase, letter-spacing 0.06em, padding 2px 6px, border-radius 3px, margin-left 8px).
    - Sub-line: 12.5px, muted color, flex row, gap 5px:
      - Explicit tag (when `explicit`): `<span>E</span>` background `#535353`, color `#d4d4d4`, 8px font, padding 1px 3px, border-radius 2px, weight 700.
      - Has-video indicator (when `hasVideo`): 12px `ExternalLink` icon at 0.7 opacity.
      - Artist link (hover: underline + white).
- **Column 3 (album)**: single-line ellipsis, 13.5px.
- **Column 4 (date added)**: relative string ("3 days ago"). Wrap in shadcn `Tooltip` showing the absolute date ("May 18, 2026") on hover.
- **Column 5 (duration)**: tabular-nums, right-aligned, 13.5px.
- **Column 6 (overflow)**: 32×32 circle button, MoreHorizontal icon, opacity 0 → 1 on row hover. Shadcn `DropdownMenu` with:
  - **When `!track.isBlacklisted`**: "Hide from Recent Adds" (`EyeOff` icon)
  - **When `track.isBlacklisted`**: "Unhide" (`Eye` icon) — fires `DELETE /api/v1/blacklist/{spotify_id}` (Story 9.7).
  - "Open in Spotify" (`ExternalLink` icon)

- **Row hover**: background `var(--bg-row-hover)` = `#1a1a1a`.
- **Row "active"** (currently-playing visual state — purely cosmetic in this app): background `var(--bg-row-active)` = `#2a2a2a`, title color becomes accent.
- **Row "blacklisted"** (Story 9.7 — `track.isBlacklisted === true`): `opacity-50` applied on the title / artist / album / date columns; cover art opacity unchanged so the user can still visually recognize the track. Row hover state still works (background fades in). The grayed visual signals "this track is hidden and will be removed from the dynamic playlist on the next sync" — but stays in the list so the user can review or restore it via the dropdown "Unhide" item.

### 4 · Settings route (`/settings`)

- H1 "Settings" + subtitle.
- **Two-column grid**: `grid-template-columns: 280px 1fr; gap: 56px; max-width: 1100px;` — left col is the section heading + description (sticky-feeling without actually sticking), right col is the form fields.
- **Three blocks** separated by `1px solid var(--border-soft)`:
  1. **Spotify connection** — `connection-card` (40×40 accent-tinted square with Spotify-style wave icon + identity + status dot + "Reconnect" outline button) + Client ID input + Client secret input (type=password). Show password value as `••••••••` initially.
  2. **Sync configuration** — Playlist size (number input, width 120px), Cron expression (text input with `font-family: var(--font-mono)`) + preset pills underneath (e.g. "every hour · 0 \*/1 \* \* \*"), Target playlist name input.
  3. **Danger zone** — destructive "Disconnect Spotify" button (transparent with 40%-opacity danger border, danger text).

- **Form field structure**:
  - Label: 12px, weight 600, secondary color, margin-bottom 6px.
  - Input: full width, background `var(--bg-elevated)`, 1px border `var(--border)`, padding 10px 12px, border-radius 6px, 13.5px. Focus: border-color accent, background `var(--bg-app)`.
  - Hint: 12px, muted color, margin-top 6px.

- **Sticky save bar** (when form is dirty): position sticky, bottom 0, full-width (negative horizontal margins), padding 14px 32px, `bg-[var(--bg-app)]/96 backdrop-blur`, border-top 1px var(--border-soft), z-index 10:
  - Sparkles icon (accent) + "Unsaved changes — review before saving." (13px, secondary)
  - Spacer
  - "Discard" ghost button
  - Primary "Save changes" button

### 5 · Logs route (`/logs`)

Real-time event stream from the harvester, newest at top.

- H1 "Logs" + subtitle "Live event stream from the harvester · newest first".
- **Filter row** (margin-top 16px, gap 8px): secondary outline button "All" (selected), ghost buttons "Errors only" / "Last 24h", spacer, SSE connection indicator (status dot + "SSE connected", 12px muted).
- **Logs container** (border 1px var(--border-soft), border-radius 6px, background var(--bg-elevated), overflow hidden):
  - **Log row** — `grid-template-columns: 160px 110px 1fr 90px 28px; gap: 14px; padding: 12px 16px; border-bottom: 1px var(--border-soft);` (cleared on last child).
    - Timestamp (12px, mono, muted): `2026-05-20 14:02:11`
    - Status pill (one of): `ok` (accent bg/text at 15%/100% opacity), `err` (danger bg/text), `warn` (#f0b400 bg/text). 11px, weight 700, uppercase, letter-spacing 0.06em, padding 3px 10px, rounded-full.
    - Message (white, single-line).
    - Delta (mono, 12.5px, right-aligned): `+3` in accent, `−1` in danger, em dash if both zero.
    - Expand chevron (22×22 button, ChevronRight → ChevronDown on open). Visibility hidden when row has no detail.
  - **Expanded detail** (when open): full-width row, padding `14px 18px 18px 60px`, background `var(--bg-app)`, border-bottom 1px var(--border-soft), `font-family: var(--font-mono)`, 12px, secondary color, `white-space: pre-wrap`. Lines starting with "ERR" render in danger color.
  - Error rows are expanded by default.
  - Row hover: background `var(--bg-row-hover)`.

### 6 · Playlist Detail route (`/playlists/:spotifyId`)

Same hero + table family as Recently Added. Reuses the shared `TrackListHero` and `TrackListTable` components (extracted in Epic 9 Story 9.2).

**Hero differences vs Recently Added:**

- **Kicker:** `PLAYLIST` (au lieu de `AUTO-SYNCED PLAYLIST`).
- **Title:** playlist name (from `GET /api/v1/playlists`).
- **Sub-line:** `<strong>{owner}</strong> • {n} tracks • about Xh Ym` (no "updated from K source playlists" — c'est une vraie playlist, pas l'agrégée).
- **Cover:** Spotify playlist cover image (mosaïque 2×2 ou cover dédiée, fournie par l'API Spotify). Fallback : gradient accent + initiales si pas d'image (cas Titres likés).
- **Background gradient:** identique à Recently Added (`linear-gradient(180deg, color-mix(in oklab, var(--accent-color) 40%, #1a1a1a) 0%, var(--bg-elevated) 100%)`).

**Hero actions row:**

- Primary button: `Open in Spotify` (`ExternalLink` icon, rounded-full, accent) — promu en primary car cette page n'a pas de "Sync now" (la sync est globale, pas par playlist).
- Search input (rounded-full, w 240px, height 36px, bg `var(--bg-elevated-2)`, `Search` icon prefix, placeholder "Filter tracks…") — filtre live sur title + artists, case-insensitive substring.
- **"Hidden only" toggle** (Story 9.7, FR49): 36×36 icon-only button (`EyeOff` icon), placed entre l'input de recherche et le `MoreHorizontal`. État inactif : couleur `var(--text-secondary)`, hover `bg-white/5`. État actif (toggled ON) : background `var(--accent-soft)`, icon color `var(--accent-color)`, l'icône `EyeOff` reste affichée (signal visuel "filter is on"). Quand actif, la table n'affiche que `filtered.filter(t => t.is_blacklisted)`. Compose en AND avec la recherche : la barre de recherche + le toggle peuvent être actifs simultanément. Tooltip au survol : "Show hidden only" (inactif) / "Show all tracks" (actif).
- 36×36 icon-only `MoreHorizontal` button (futur usage : edit playlist / sort options).

**Track table:**

- Identique pixel-perfect au TrackRow de Recently Added (snippets/TrackRow.tsx).
- Overflow menu par ligne :
  - `Hide from Recent Adds` (= blacklist global) **OU** `Unhide` selon l'état `track.isBlacklisted` (Story 9.7).
  - `Open in Spotify`.
- Tracks blacklistées : rendues grisées (`opacity-50` sur les colonnes de texte) au lieu d'être retirées de la liste (Story 9.7).
- Virtualisation activée automatiquement si `tracks.length > 200` (transparent pour l'utilisateur — sticky header conservé).

**Navigation :**

- Entrée : clic sur une carte playlist du Dashboard (Epic 9 Story 9.3 active le `onClick`).
- Retour : bouton `ChevronLeft` du topbar (devient actif quand `history.length > 1` — précédemment désactivé en MVP cf. §1).

## Interactions & Behavior

- **Sidebar nav**: NavLink with `end` on the root. Active state is the only persistent visual; no transition.
- **Topbar `Sync now`**: disables button + spinning icon (`animation: spin 1s linear infinite`) during the API call. On success, update the "Last sync" badge to "just now" (or actual relative time from the response).
- **Playlist card hover**: 200ms ease background swap. Play FAB animates in (200ms ease, opacity + translateY). Overflow button fades in (150ms).
- **Hidden accordion**: chevron rotates 200ms.
- **Track row hover**: background swap (no transition needed, instant). Index ↔ play swap is also instant. Overflow icon fades in.
- **Log row click**: toggles `open` local state on the row. Smooth-ish but no required transition.
- **Settings save bar**: appears whenever any field changes from initial. Discard reverts and hides; Save POSTs then hides.
- **SSE for logs**:
  ```tsx
  useEffect(() => {
    const es = new EventSource('/api/logs/stream');
    es.onmessage = (e) => setLogs(prev => [JSON.parse(e.data), ...prev]);
    es.onerror = () => setSseConnected(false);
    es.onopen = () => setSseConnected(true);
    return () => es.close();
  }, []);
  ```

## State Management

Suggested TanStack Query keys:

| Hook | Query key | Returns |
|---|---|---|
| `usePlaylists()` | `['playlists']` | `Playlist[]` (both visible and hidden) |
| `useRecentTracks()` | `['recent-tracks']` | `Track[]` |
| `useSyncStatus()` | `['sync-status']` | `{ lastSync: string; ok: boolean }` |
| `useSettings()` | `['settings']` | `SettingsForm` |
| `useLogs()` | `['logs']` | initial `LogEntry[]`, then appended via SSE |

Mutations:

| Mutation | Effect | Invalidates |
|---|---|---|
| `toggleInclude(id)` | flips `included` | `['playlists']` |
| `toggleHide(id)` | flips `hidden` (and clears `included` when hiding) | `['playlists']` |
| `triggerSync()` | POST /api/sync | `['sync-status']`, `['recent-tracks']`, `['logs']` |
| `saveSettings(form)` | PATCH /api/settings | `['settings']` |
| `reconnectSpotify()` | OAuth flow | `['settings']`, `['sync-status']` |

Local UI state (per-component, not in Query):
- Settings form `dirty` boolean and field values.
- Log row `open` boolean.
- Accordion `open` state (or use shadcn Accordion built-in).
- Topbar `scrolled` boolean (driven by `onScroll` on the main scroll container).

## Design Tokens

All tokens live in `frontend/src/index.css`. See `snippets/index.css`.

### Surfaces
```
--bg-base       #0d0d0d     (outer letterbox)
--bg-app        #121212     (sidebar)
--bg-elevated   #1c1c1c     (cards, main area top)
--bg-elevated-2 #232323     (active nav, search pill, popovers)
--bg-hover      #2a2a2a     (interactive hover)
--bg-row-hover  #1a1a1a     (track row hover — subtler than --bg-hover)
--bg-row-active #2a2a2a     (track row selected)
```

### Text
```
--text-primary    #ffffff
--text-secondary  #b3b3b3
--text-muted      #6a6a6a
--text-faint      #4a4a4a   (input placeholder)
```

### Accent + status
```
--accent          #1DB954
--accent-hover    #1ed760
--accent-fg       #000000   (text on accent surfaces)
--accent-soft     rgba(29, 185, 84, 0.12)
--danger          #e22134
--warning         #f0b400
```

### Borders
```
--border-soft     rgba(255, 255, 255, 0.06)
--border          rgba(255, 255, 255, 0.09)
--border-strong   rgba(255, 255, 255, 0.16)
```

### Radius
```
--r-sm     4px
--r-md     6px       (cards, inputs)
--r-lg     8px       (main panels, sidebar)
--r-xl     12px
--r-pill   999px     (primary buttons, badges)
```

### Layout
```
--sidebar-w  248px
--header-h   64px
```

### Typography
- Font family: `-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, "Helvetica Neue", Arial, sans-serif`
- Mono: `ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace`
- Weights used: 400, 500, 600, 700, 800, 900
- Letter-spacing on H1/hero: `-0.025em` to `-0.04em`
- Letter-spacing on section labels (uppercase): `+0.06em` to `+0.08em`
- Body size: 14px, line-height 1.45

### Shadows
- Card cover: `0 8px 24px rgba(0,0,0,0.5)`
- Hero cover: `0 16px 40px rgba(0,0,0,0.6)`
- Popover: `0 12px 32px rgba(0,0,0,0.5)`
- Play FAB: `0 8px 14px rgba(0,0,0,0.55)`

### Motion
- Hover transitions: 150–200ms ease
- Spin: 1s linear infinite

## Assets

**Iconography**: All icons in the implementation should come from **lucide-react**:
- `LayoutDashboard`, `Clock`, `Settings`, `ScrollText` — sidebar
- `ChevronLeft`, `ChevronRight`, `ChevronDown` — topbar + accordion
- `RotateCw` — sync
- `Search` — filter input
- `Play`, `Pause` — covers + track rows
- `MoreHorizontal` — overflow menus
- `Check` — included badge
- `Eye`, `EyeOff` — hide / unhide
- `ExternalLink` — open in Spotify + video tag
- `Sparkles` — empty state + save bar
- `Code` — handoff button (dev only)

The prototype uses inline SVG copies of these icons. **In the real implementation, use `lucide-react` directly** — same visual.

**Brand mark**: the sidebar wordmark "playlist_spotify" uses a 28×28 gradient square as a logo (linear gradient from accent → cyan). This is original, not the Spotify logo. Keep it; do not use the real Spotify brand asset.

**Playlist covers**: the prototype generates abstract gradient SVGs because we don't have real album art available. **In production, render the actual `images[0].url` returned by the Spotify Web API** — the card just needs `<img src={p.coverUrl} class="h-full w-full object-cover" />`.

## Variants (Tweaks)

The prototype exposes a Tweaks panel with 4 variants the user explored:
- **Accent color** — Spotify green is the chosen production value (`#1DB954`). Other swatches (`#22d3ee`, `#ec4899`, `#f0b400`) were exploration only — ignore.
- **Grid density** — "Comfy" is the chosen production default (`minmax(190px, 1fr)`, 18px gap). Keep the other modes (`compact` / `spacious`) as a future setting if useful.
- **Sidebar width** — 248px chosen. Keep variable in CSS to allow easy tuning.
- **Hidden expanded by default** — false (collapsed) chosen.

Implement only the chosen values. Don't ship the Tweaks panel.

## Files in this handoff

```
design_handoff_playlist_spotify/
├── README.md                                  ← this file
├── prototype/                                 ← interactive HTML reference
│   ├── playlist_spotify Prototype.html        ← open this in a browser
│   ├── styles.css                             ← all visual styles (canonical)
│   ├── data.js                                ← dummy data
│   ├── app.jsx                                ← main app composition
│   ├── shell.jsx                              ← Sidebar + Topbar + Menu
│   ├── playlist-card.jsx                      ← PlaylistCard, PlaylistGrid, HiddenAccordion
│   ├── track-list.jsx                         ← TrackRow + RecentlyAdded page
│   ├── pages.jsx                              ← Dashboard, Settings, Logs
│   ├── icons.jsx                              ← inline SVG icon set (replaced by lucide in prod)
│   ├── handoff.jsx                            ← dev-only handoff panel (skip)
│   └── tweaks-panel.jsx                       ← dev-only tweaks panel (skip)
└── snippets/                                  ← drop-in production files
    ├── index.css                              ← tokens + dark theme override
    ├── AppShell.tsx
    ├── PlaylistCard.tsx
    ├── TrackRow.tsx
    ├── HiddenPlaylistsAccordion.tsx
    └── shadcn-add.sh                          ← shell script with all `npx shadcn` adds
```

## How to view the prototype

```bash
cd design_handoff_playlist_spotify/prototype
python3 -m http.server 8080
# open http://localhost:8080/playlist_spotify%20Prototype.html
```

Or open the HTML file directly — it loads dependencies from unpkg.

The prototype includes a "Dev handoff" button (bottom-right) that shows the same TSX snippets in `snippets/` — use it for inline reference while implementing.
