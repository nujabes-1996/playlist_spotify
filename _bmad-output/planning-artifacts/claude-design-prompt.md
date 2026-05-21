# Claude Design Prompt — playlist_spotify UI Redesign

> Copy/paste the block below to Claude Design alongside the two reference screenshots (Spotify Desktop playlist grid + Spotify Desktop track-list).

---

## Context

I'm redesigning a personal web app called **playlist_spotify**. The tool automatically aggregates my most-recently-added Spotify tracks (across selected playlists) into a single "Recent Adds" Spotify playlist. The web dashboard lets me pick which playlists feed the harvest, trigger syncs, watch logs, and now — manage what's in the resulting playlist.

**Current stack:** React + Vite + Tailwind + shadcn/ui (we already use shadcn — keep using it). TanStack Query v5. FastAPI backend (REST + SSE). Single user, personal tool.

**Current look:** Generic shadcn light defaults. We want to throw that out.

## Design Goal

Adopt a **Spotify Desktop-inspired** visual language. Reference screenshots attached:
1. Playlist grid (square cover-art cards)
2. Track-list view (numbered rows with title/artist/album/date/duration)

Match Spotify Desktop's *feel* (dark theme, sidebar nav, card grid, dense track list, green accent) but do not literally copy the Spotify logo or brand chrome — this is a personal tool, not a Spotify clone.

## Pages to Design

### 1. Global shell

- Persistent **left sidebar** (~240px):
  - App name/logo at top
  - Primary nav items: `Dashboard`, `Recently Added`, `Settings`, `Logs`
  - Active item: green accent + filled icon
  - Bottom of sidebar: small "Connected as <Spotify display name>" + status dot (green=ok / red=token expired)
- **Top header** of main content:
  - Page title (large, bold)
  - Right-aligned: last-sync status badge (✅ / ❌ + relative time), "Sync now" button (primary green)
- **Main content area:** dark background (`#121212`-class), elevated surfaces in `#1e1e1e`-class

### 2. Dashboard — Playlist Grid

Primary view (`/`).

- **Section: "Your playlists"**
  - Responsive grid of square cards, 4–6 per row on desktop, 2 on tablet, 1 on phone
  - Each card:
    - Square Spotify cover image (top, full width of card)
    - Below image: playlist name (truncated to 2 lines), `<n> tracks`
    - Visual state for **included in harvest** (e.g. green ring around card or green checkmark badge top-right)
    - On hover: subtle lift + reveal a circular play-style button bottom-right (visual only) and a `⋯` overflow menu top-right
    - Overflow menu items: `Include in sync` (toggle) · `Hide playlist`
  - Empty state copy if no playlists yet

- **Section: "Hidden playlists (N)"** — below the main grid
  - Collapsible accordion, default collapsed
  - When expanded: same card grid layout, but visually de-emphasized (e.g. lower opacity until hover)
  - Overflow menu shows `Unhide` instead of `Hide`
  - Help text inside accordion: "Hidden playlists are excluded from sync and removed from the main grid. Unhide to bring them back."

### 3. Recently Added page

Route `/recently-added`. Shows the current contents of the dynamic Spotify playlist.

Match the Spotify Desktop track-list reference. Columns:

| # | Title | Album | Date Added | ⏱ Duration | ⋯ |
|---|---|---|---|---|---|

- Sticky header row on scroll
- Row hover: highlight background + reveal `⋯` action menu
- Title column: small album-art thumbnail (40×40) + stacked `Track name` / `Artist name`
- Date Added: relative ("3 days ago") with tooltip showing absolute date
- `⋯` menu items: `Hide from Recent Adds (blacklist)` · `Open in Spotify`
- Top of page: playlist hero block — large cover (current Recent Adds playlist cover), playlist name, total tracks, total duration, primary "Sync now" button

### 4. Settings page

Route `/settings`. Form-style page, two-column layout on desktop:

- **Spotify connection:** Client ID + Secret inputs, "Reconnect Spotify" button, connection status
- **Sync configuration:** Playlist size (number input, default 50), Cron expression (text input with example presets), Target playlist name
- All fields use shadcn `Input`, `Label`, `Button` — dark-themed
- Sticky save bar at bottom when dirty

### 5. Logs page

Route `/logs`. List of sync events (timestamp, status badge, track count delta, expandable error detail). Real-time appended via SSE — newest at top. Compact, monospace-tinted detail blocks.

## Visual System

- **Palette:**
  - bg-base `#121212` · bg-elevated `#1e1e1e` · bg-hover `#2a2a2a`
  - text-primary `#ffffff` · text-secondary `#b3b3b3` · text-muted `#6a6a6a`
  - accent (success/active) `#1DB954` · accent-hover `#1ed760`
  - danger `#e22134`
- **Radius:** 6–8px on cards & inputs, 999px on primary buttons & status badges
- **Shadows:** subtle on card hover only — Spotify avoids heavy shadows
- **Typography:** system sans-serif stack, weights 400/600/700, tight letter-spacing on headings
- **Iconography:** lucide-react (already in shadcn ecosystem)
- **Motion:** 150ms ease on hover/expand; no flashy transitions

## Deliverables I'd like from you

1. A set of **Tailwind theme tokens** (CSS variables) for the dark Spotify-inspired palette, drop-in compatible with shadcn/ui's theming
2. A redesigned **PlaylistCard** component (TSX + Tailwind) matching the Spotify grid card spec
3. A redesigned **TrackRow** component for the Recently Added list
4. The **AppShell layout** (sidebar + header + main slot) as a TSX component
5. The **HiddenPlaylistsAccordion** wrapper
6. Brief notes on shadcn components to add (`dropdown-menu`, `accordion`, `table`, etc.) so I can run `npx shadcn@latest add ...`

## Constraints

- Keep shadcn/ui primitives — don't introduce a new component library
- Tailwind only, no CSS-in-JS
- All file paths in the existing repo use `@/` alias for `frontend/src/`
- Don't worry about backend integration — I'll wire data myself; just give me the visual layer + dummy data

## What to ignore

- Mobile-first concerns (we are desktop-first now; just don't break on phone)
- Light theme (dark only for MVP)
- Auth screens (already done)
- Drag-and-drop reordering
- Playback (we never play audio in-app)
