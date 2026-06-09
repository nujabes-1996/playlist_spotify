---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments: ['CONTEXT.md']
workflowType: 'prd'
classification:
  projectType: web_app
  domain: general
  complexity: medium
  projectContext: greenfield
---

# Product Requirements Document - playlist_spotify

**Author:** kevin
**Date:** 2026-04-17

## Executive Summary

A personal web application that automatically maintains a dynamic Spotify playlist aggregating the most recently added tracks across all user-created playlists. Solves the Spotify organizational gap: users curate music by genre/context (playlists) but have no native way to listen by recency (time). The tool bridges these two dimensions — organize however you want, always have a ready-to-play "recent adds" playlist.

**Target user:** Single user (personal tool). Music listener who actively curates multiple Spotify playlists by genre or mood, and wants frictionless access to their recent additions as a unified listening queue.

**Core workflow:** A scheduled background job harvests tracks from selected playlists, deduplicates, sorts by recency, and pushes the top N tracks to a dedicated Spotify playlist. A React web dashboard provides configuration, playlist selection, manual control, and real-time observability.

### What Makes This Special

Spotify's "Liked Songs" conflates everything into one flat list. This tool respects existing playlist organization while adding a temporal view on top. The key insight: the user doesn't want to change how they organize music — they want a new way to *consume* what they've already organized. Full configurability (which playlists to include, playlist size, sync schedule) and complete dashboard control make this a precise personal instrument rather than a blunt automation.

**Project classification:** Web application with background scheduler service · General domain · Medium complexity · Greenfield

## Success Criteria

### User Success

- Dynamic playlist reflects the N most recent tracks from included playlists after each sync
- Full configuration possible from the dashboard — no code editing required
- Sync runs automatically on schedule without manual intervention
- On sync failure, logs are accessible in the dashboard with the failure reason
- User can trigger a manual sync at any time from the dashboard

### Technical Success

- Spotify OAuth token refresh is transparent — no re-auth prompts under normal operation
- Sync failures are caught, logged with cause, and surfaced in the UI
- Scheduler persists and resumes across application restarts
- Spotify API pagination handled correctly for libraries with 5,000+ tracks

### Measurable Outcomes

- Scheduled sync executes as configured with no missed runs under normal operation
- Sync log entries include timestamp, status, track count delta, and error detail on failure
- Dashboard initial load completes in under 3 seconds on a local network connection

## Product Scope

### MVP — Phase 1

**Philosophy:** Personal utility MVP — minimum that makes the tool genuinely usable daily. No multi-user, no deployment complexity. Solo developer, Python + React.

**Capabilities:**
- Spotify OAuth authentication + transparent token refresh
- Background scheduler with user-configured cron recurrence
- Track harvest: deduplicate across playlists, sort by `added_at` descending, select top N
- Create/update target dynamic playlist on Spotify
- **Spotify Desktop-inspired UI** — dark theme, sidebar navigation, card grid layouts
- **Playlist grid view**: square cover-image cards (Spotify desktop look) with include/exclude toggle
- **Hide playlists**: hidden playlists are excluded from sync AND removed from the main grid; managed via a collapsible "Hidden playlists" section
- **Recently Added page**: track-list view (Spotify desktop style) showing the current dynamic playlist contents, with per-track blacklist (hide) action
- Configuration UI: playlist size, Spotify credentials, cron recurrence
- Manual sync trigger
- Real-time sync logs (SSE/WebSocket) with timestamp + error cause
- Responsive layout (desktop-first, smartphone-usable)

**Risk mitigations:**
- OAuth token expiry → server-side refresh with re-auth UI flow for hard failures
- Spotify API rate limits (HTTP 429) → pagination with backoff; cache playlist metadata between syncs

### Phase 2 — Growth

- Preview mode: show resulting track list before applying sync
- Auto-exclusion of collaborative playlists
- Sync history timeline
- Stats: top artists and genres in the dynamic playlist
- Notifications (email or Telegram) on sync completion or failure
- Bulk track actions on Recently Added page (multi-select blacklist)
- Restore blacklisted tracks (review & un-blacklist UI)

### Phase 3 — Vision

- Multiple independent dynamic playlists with distinct rules (genre filter, source subset, etc.)

## User Journeys

### Journey 1 — First Setup (Onboarding)

**Kevin has just cloned the project.**

He opens the dashboard for the first time. The app detects no Spotify credentials are configured and displays this clearly on the home screen. He enters his `Client ID` and `Client Secret` from the Spotify Developer Dashboard, clicks "Connect Spotify" — redirected to Spotify, grants access, returns authenticated.

He sees his playlist list immediately. He toggles the playlists to include, sets a size of 50 tracks, configures cron to "every 6 hours", clicks "Save" then "Sync Now". Seconds later: ✅ Sync successful — 50 tracks, playlist "Recent Adds" created. He opens Spotify — the playlist is there, ready to play.

**Capabilities revealed:** initial config screen, OAuth flow, settings persistence, immediate post-sync feedback.

---

### Journey 2 — Daily Use (Happy Path)

**Kevin has added 8 tracks across 3 playlists this week.**

He did nothing special — the cron ran automatically each night. He opens Spotify, plays "Recent Adds", finds exactly his recent additions in order. The tool is invisible. That is the success.

**Capabilities revealed:** scheduler reliability, aggregation accuracy, deduplication correctness.

---

### Journey 3 — Failed Sync (Error Recovery)

**The OAuth token expired. The nightly sync failed.**

Kevin opens the dashboard. A red badge shows "Last sync: ❌ Failed". He clicks the log: `401 Unauthorized — token expired, refresh failed`. He clicks "Reconnect Spotify", re-authorizes in 30 seconds, triggers a manual sync. Log shows ✅, playlist is up to date.

**Capabilities revealed:** error visibility, log with precise cause, re-auth flow, one-click manual sync.

---

### Journey 4 — Reconfiguration

**Kevin creates "Jazz Discoveries" and wants it included in the harvest.**

He opens the dashboard, sees the new playlist already listed (refreshed from Spotify API), toggles it on, saves. Next sync includes it. No restart required.

**Capabilities revealed:** dynamic playlist list refresh, preference persistence.

---

### Journey 5 — Curating the Playlist Grid

**Kevin has 47 playlists, but only a dozen feed Recent Adds.**

He opens the dashboard. His included playlists are displayed as a Spotify-style square grid of cover-art cards. The 30+ playlists he never wants to harvest (old, archived, friends-shared) used to clutter the view. He clicks the ⋯ menu on each clutter playlist → "Hide". They vanish from the grid and are simultaneously excluded from the next sync. A collapsible "Hidden playlists (32)" section at the bottom lets him expand, review, and "Unhide" any if needed.

**Capabilities revealed:** card grid layout with cover art, hide-from-grid + auto-exclude, hidden-section accordion, unhide flow.

---

### Journey 6 — Pruning Recently Added

**Kevin opens the Recently Added page and sees a track he doesn't want there.**

A track auto-added from his "Workout" playlist isn't right for the unified queue he wants. He clicks the ⋯ menu on the track row → "Hide from Recent Adds". The track is blacklisted; next sync removes it from the Spotify playlist and it won't ever come back as long as the blacklist is active.

**Capabilities revealed:** track-level list view with per-row actions, blacklist persistence, post-sync clean playlist.

---

### Journey 7 — Exploring a single playlist

**Kevin wants to see exactly what's in his "Rock" playlist before deciding to include it in Recent Adds.**

He clicks the Rock card on the Dashboard. The app navigates to `/playlists/<id>` — same hero+table layout he knows from Recently Added, this time showing all 56 Rock tracks with their date added. He filters by "Metallica" and the table narrows live. He spots a track that doesn't belong, clicks ⋯ → "Hide from Recent Adds" — the track is blacklisted globally and won't appear in his Recent Adds next sync.

**Capabilities revealed:** click-to-detail navigation, reused track table pattern, per-track blacklist from any context.

---

### Journey Requirements Summary

| Capability | Journeys |
|---|---|
| OAuth setup + re-auth flow | 1, 3 |
| Playlist list with toggle + persistence | 1, 4 |
| Configuration form (size, cron, credentials) | 1 |
| Reliable background scheduler | 2 |
| One-click manual sync | 1, 3 |
| Logs with timestamp + error cause | 3 |
| Dynamic playlist list refresh from API | 4 |
| Spotify-style grid with cover images | 5 |
| Hide playlist (visual + sync exclusion) + hidden section | 5 |
| Recently Added track-list page | 6 |
| Per-track blacklist action | 6, 7 |
| Click-to-detail playlist navigation + filter within playlist | 7 |

## Web Application Requirements

### Architecture

- **Frontend:** React SPA — communicates with backend via REST API + real-time channel (SSE or WebSocket)
- **Backend:** Python (FastAPI) — REST API, Spotify OAuth handler, APScheduler, SQLite persistence
- **Real-time:** SSE or WebSocket streams live sync log events to dashboard during active syncs
- **Persistence:** SQLite for config, playlist preferences, and sync history

### Platform Constraints

- Browser target: latest stable Chrome and Firefox only
- Desktop-first responsive layout — full Spotify-desktop look on wide screens, gracefully degrades to a usable smartphone experience
- OAuth callback handled server-side; tokens never exposed to browser
- Scheduler runs as background process independent of web server process

### UI & Visual Design

> 📐 **Source de vérité UX**: voir [`ux-design/README.md`](./ux-design/README.md) (handoff Claude Design, intégré 2026-05-20). Le présent paragraphe reste un résumé haut niveau — pour les tokens exacts, composants nommés (AppShell, PlaylistCard, TrackRow, HiddenPlaylistsAccordion), hover states et interactions, se référer au handoff.

The dashboard adopts a **Spotify Desktop-inspired visual language**:

- **Theme:** Dark mode by default. Primary background near-black (`#121212`-class), elevated surfaces in dark gray, Spotify-green accent (`#1DB954`-class) reserved for primary actions and active states.
- **Layout:** Persistent left sidebar (logo, primary navigation: Dashboard / Recently Added / Settings / Logs); main content area with top header (page title, sync status badge, manual sync button); generous spacing.
- **Playlist grid:** Square cards displaying the Spotify playlist cover image, playlist name, and track count. Hover reveals a play/details affordance and a ⋯ overflow menu (Include toggle, Hide). Active include state is communicated visually (border, badge, or accent ring).
- **Recently Added page:** Track table with columns inspired by Spotify desktop — `#` index, Title (with track cover thumbnail + title/artist), Album, Date Added, Duration, and a ⋯ overflow menu per row (Hide / Blacklist). Row hover highlights; sticky header on scroll.
- **Playlist detail page:** Same layout family as Recently Added (full-bleed hero with playlist cover + name + owner + track count + total duration; sticky-header track table with `#`, Title, Album, Date Added, Duration, ⋯). Includes a search/filter input in the actions row to narrow the visible tracks.
- **Hidden playlists:** Collapsible accordion below the active grid, default-collapsed, labeled with count (e.g. "Hidden playlists (32)"); expanding shows the same card layout with a clear "Unhide" affordance per card.
- **Typography & density:** Sans-serif system stack, tight track-list density on Recently Added, comfortable density on the playlist grid.
- **Accessibility:** AA contrast on text vs background; focus rings visible on keyboard navigation; ⋯ menus reachable via keyboard.

## Functional Requirements

### Authentication & Spotify Connection

- **FR1:** User can authenticate with Spotify via OAuth2 from the dashboard
- **FR2:** User can re-authenticate with Spotify when the token expires or is revoked
- **FR3:** The system automatically refreshes expired Spotify access tokens without user intervention

### Sync Engine

- **FR4:** The system harvests all tracks from user-selected source playlists via the Spotify API
- **FR5:** The system deduplicates tracks appearing in multiple playlists, retaining the most recent `added_at` date
- **FR6:** The system sorts harvested tracks by `added_at` date in descending order
- **FR7:** The system selects the top N tracks based on the configured playlist size
- **FR8:** The system creates the target dynamic playlist on Spotify if it does not exist
- **FR9:** The system replaces the target dynamic playlist contents on each sync

### Playlist Selection

- **FR10:** User can view all their user-created Spotify playlists
- **FR11:** User can include or exclude individual playlists from the harvest
- **FR12:** Playlist include/exclude preferences are persisted across sessions
- **FR13:** The playlist list reflects newly added or removed playlists from the user's Spotify library

### Scheduler

- **FR14:** The system automatically executes syncs on a user-configured recurring schedule
- **FR15:** User can configure the sync recurrence (interval or cron expression)
- **FR16:** The scheduler persists and resumes after application restart
- **FR17:** User can trigger a sync manually at any time

### Configuration

- **FR18:** User can configure Spotify API credentials (Client ID, Client Secret)
- **FR19:** User can configure the dynamic playlist size (number of tracks to retain)
- **FR20:** All configuration is persisted and survives application restarts

### Observability & Logs

- **FR21:** User can view real-time sync progress during an active sync
- **FR22:** User can view sync log entries including timestamp, status (success/failure), track count delta, and error cause
- **FR23:** The dashboard surfaces a visible failure indicator when the last sync failed
- **FR24:** User can access the full sync log history

### Playlist Grid & Hiding

- **FR25:** The dashboard displays user playlists as a grid of square cards showing the Spotify cover image, playlist name, and track count
- **FR26:** User can hide a playlist from the main grid via a per-card overflow menu
- **FR27:** Hiding a playlist also excludes it from the next and subsequent syncs (hidden ⇒ excluded)
- **FR28:** Hidden playlists are accessible in a collapsible "Hidden playlists" section showing a count and the same card layout
- **FR29:** User can unhide a playlist from the hidden section, which restores it to the main grid (include/exclude state defaults to excluded; user must explicitly toggle include again)
- **FR30:** Hidden state is persisted across sessions

### Recently Added Page

- **FR31:** User can navigate to a dedicated "Recently Added" page showing the current contents of the dynamic Spotify playlist
- **FR32:** Tracks are displayed in a list view with columns: index, title + artist + cover thumbnail, album, date added, duration
- **FR33:** Each row exposes an overflow menu with a "Hide / Blacklist" action. Blacklisted tracks remain visible in track lists with a dimmed/grayed visual treatment and a reversible "Unhide" action (delivered by Story 9.7).
- **FR34:** Blacklisting a track persistently excludes it from all future syncs
- **FR35:** The next sync after a track is blacklisted removes that track from the dynamic Spotify playlist
- **FR36:** Blacklist state is persisted across sessions

### Playlist Detail Page

- **FR44:** User can click a playlist card on the Dashboard to navigate to a dedicated playlist detail page
- **FR45:** The playlist detail page displays all tracks in the playlist using the same hero + track table layout as Recently Added
- **FR46:** Each track row on the playlist detail page exposes the same overflow menu as Recently Added: "Hide / Blacklist" and "Open in Spotify"
- **FR47:** User can filter the displayed tracks within a playlist by title or artist (case-insensitive substring match)
- **FR48:** User can navigate back to the Dashboard from the playlist detail page (browser back + visible back affordance)
- **FR49:** On the Playlist Detail page, the user can toggle a "Hidden only" filter to display only blacklisted tracks. The filter composes with the search filter (FR47) using logical AND.

### Phase 2 Capabilities

- **FR37:** User can preview the track list resulting from the next sync before applying it
- **FR38:** The system can automatically exclude collaborative playlists from the harvest
- **FR39:** User can view a timeline of past sync operations
- **FR40:** User can view aggregated stats on the dynamic playlist (top artists, top genres)
- **FR41:** User can configure notifications for sync completion or failure events
- **FR42:** User can multi-select tracks on the Recently Added page for bulk blacklist
- **FR43:** ~~User can review and un-blacklist previously hidden tracks~~ — **PROMOTED to MVP** in Story 9.7 (grayed-row treatment + "Unhide" overflow action + "Hidden only" filter on Playlist Detail).

## Non-Functional Requirements

### Performance

- Dashboard initial page load: under 3 seconds on local network
- Playlist list refresh from Spotify API: under 2 seconds
- Real-time sync log events delivered to UI: within 1 second of backend emission
- Sync engine processes up to 5,000 tracks within 30 seconds
- Playlist grid renders within 1 second of API response for up to 100 playlists; cover images lazy-loaded
- Recently Added track list renders within 1 second for up to 200 tracks
- **NFR16:** Playlist detail page initial paint completes within 1.5 seconds for playlists up to 1,000 tracks; uses virtualization for the track table when track count exceeds 200

### Security

- Spotify OAuth tokens stored server-side only; never returned to browser or exposed in API responses
- Spotify API credentials stored in local config file with restricted filesystem permissions, not in source code
- Application intended for local/personal deployment only; no dashboard authentication layer required
- All Spotify API communication over HTTPS

### Reliability

- Scheduler resumes configured schedule automatically after application restart
- Sync failure leaves existing dynamic playlist intact — previous contents preserved on error
- Every sync operation produces a log entry regardless of outcome
- HTTP 429 rate limit responses from Spotify API handled with retry and exponential backoff
