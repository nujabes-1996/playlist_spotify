---
stepsCompleted:
  - step-01-document-discovery
  - step-02-prd-analysis
  - step-03-epic-coverage-validation
  - step-04-ux-alignment
  - step-05-epic-quality-review
  - step-06-final-assessment
filesIncluded:
  prd: _bmad-output/planning-artifacts/prd.md
  architecture: _bmad-output/planning-artifacts/architecture.md
  epics: _bmad-output/planning-artifacts/epics.md
  ux: _bmad-output/planning-artifacts/ux-design/ (sharded)
date: 2026-05-20
---

# Implementation Readiness Assessment Report

**Date:** 2026-05-20
**Project:** playlist_spotify

## Step 1 — Document Discovery

### Document Inventory

| Type | Format | Path |
|------|--------|------|
| PRD | Whole | `_bmad-output/planning-artifacts/prd.md` |
| Architecture | Whole | `_bmad-output/planning-artifacts/architecture.md` |
| Epics & Stories | Whole | `_bmad-output/planning-artifacts/epics.md` |
| UX Design | Sharded | `_bmad-output/planning-artifacts/ux-design/` (index.md, README.md, prototype/, snippets/) |

### Additional Files (non-required)
- `claude-design-prompt.md`
- `sprint-change-proposal-2026-05-20.md`

### Issues
- No duplicate (whole + sharded) versions detected.
- No required document missing.

**Status:** ✅ Document inventory clean — proceeding to PRD analysis.

## Step 2 — PRD Analysis

### Functional Requirements (43 total — MVP: FR1–FR36, Phase 2: FR37–FR43)

**Authentication & Spotify Connection**
- **FR1:** User can authenticate with Spotify via OAuth2 from the dashboard
- **FR2:** User can re-authenticate with Spotify when the token expires or is revoked
- **FR3:** The system automatically refreshes expired Spotify access tokens without user intervention

**Sync Engine**
- **FR4:** Harvest all tracks from user-selected source playlists via Spotify API
- **FR5:** Deduplicate tracks across playlists, retaining most recent `added_at`
- **FR6:** Sort harvested tracks by `added_at` desc
- **FR7:** Select top N tracks based on configured playlist size
- **FR8:** Create target dynamic playlist on Spotify if it does not exist
- **FR9:** Replace target dynamic playlist contents on each sync

**Playlist Selection**
- **FR10:** View all user-created Spotify playlists
- **FR11:** Include/exclude individual playlists from harvest
- **FR12:** Include/exclude prefs persisted across sessions
- **FR13:** Playlist list reflects added/removed playlists from Spotify library

**Scheduler**
- **FR14:** Automatic syncs on user-configured recurring schedule
- **FR15:** Configure sync recurrence (interval or cron expression)
- **FR16:** Scheduler persists & resumes after restart
- **FR17:** Manual sync trigger at any time

**Configuration**
- **FR18:** Configure Spotify API credentials (Client ID, Client Secret)
- **FR19:** Configure dynamic playlist size
- **FR20:** All configuration persisted across restarts

**Observability & Logs**
- **FR21:** View real-time sync progress during active sync
- **FR22:** View sync log entries (timestamp, status, delta, error cause)
- **FR23:** Visible failure indicator when last sync failed
- **FR24:** Access full sync log history

**Playlist Grid & Hiding**
- **FR25:** Display playlists as a grid of square cover-image cards (name + track count)
- **FR26:** Hide a playlist via per-card overflow menu
- **FR27:** Hiding ⇒ exclusion from sync
- **FR28:** Hidden playlists accessible in collapsible section with count
- **FR29:** Unhide restores card to main grid (include defaults to excluded — must re-toggle)
- **FR30:** Hidden state persisted

**Recently Added Page**
- **FR31:** Navigate to "Recently Added" page showing current dynamic playlist contents
- **FR32:** Track list view with columns: #, title+artist+thumbnail, album, date added, duration
- **FR33:** Per-row overflow menu with Hide/Blacklist
- **FR34:** Blacklisting persistently excludes a track from future syncs
- **FR35:** Next sync removes blacklisted track from Spotify playlist
- **FR36:** Blacklist state persisted

**Phase 2 (out of MVP scope)**
- **FR37:** Preview next-sync result list before applying
- **FR38:** Auto-exclude collaborative playlists
- **FR39:** Timeline of past sync operations
- **FR40:** Stats (top artists/genres) on dynamic playlist
- **FR41:** Notifications on sync completion/failure
- **FR42:** Multi-select bulk blacklist on Recently Added
- **FR43:** Review & un-blacklist UI

**Total MVP FRs:** 36 · **Total Phase 2 FRs:** 7 · **Grand total:** 43

### Non-Functional Requirements

**Performance**
- NFR-P1: Dashboard initial page load < 3 s on local network
- NFR-P2: Playlist list refresh from Spotify API < 2 s
- NFR-P3: Real-time sync log events delivered to UI within 1 s of backend emission
- NFR-P4: Sync engine processes up to 5,000 tracks within 30 s
- NFR-P5: Playlist grid renders within 1 s for up to 100 playlists (lazy-loaded cover images)
- NFR-P6: Recently Added list renders within 1 s for up to 200 tracks

**Security**
- NFR-S1: Spotify OAuth tokens stored server-side only, never exposed to browser
- NFR-S2: Spotify API credentials stored in local config file w/ restricted FS permissions, not in source
- NFR-S3: Local/personal deployment only — no dashboard auth layer required
- NFR-S4: All Spotify API communication over HTTPS

**Reliability**
- NFR-R1: Scheduler auto-resumes configured schedule after application restart
- NFR-R2: Sync failure leaves existing dynamic playlist intact (no partial corruption)
- NFR-R3: Every sync operation produces a log entry regardless of outcome
- NFR-R4: HTTP 429 rate-limit responses from Spotify handled with retry + exponential backoff

**Total NFRs:** 14 (6 Performance · 4 Security · 4 Reliability)

### Additional Requirements / Constraints

- **Tech stack constraint:** React SPA frontend + FastAPI/Python backend, SQLite persistence, APScheduler, SSE or WebSocket real-time channel
- **Browser support:** latest stable Chrome and Firefox only
- **Layout constraint:** desktop-first responsive — full Spotify-desktop look on wide, usable on smartphone
- **OAuth constraint:** callback handled server-side; tokens never exposed to browser (reinforces NFR-S1)
- **Scheduler constraint:** runs as background process independent of web server process
- **UI source of truth:** `ux-design/README.md` (Claude Design handoff, integrated 2026-05-20) — tokens, components (AppShell, PlaylistCard, TrackRow, HiddenPlaylistsAccordion), hover/interaction states
- **Accessibility:** WCAG AA contrast on text vs background; visible focus rings; overflow menus reachable via keyboard

### PRD Completeness Assessment

- ✅ All FRs clearly numbered (FR1–FR43) and grouped by capability
- ✅ NFRs cover Performance, Security, Reliability (no Usability/Compliance/Scalability gaps for a personal tool)
- ✅ User journeys (6) trace explicit capabilities back to FRs via Journey Requirements Summary table
- ✅ MVP/Phase 2/Phase 3 scope split is explicit
- ✅ UX source of truth correctly delegated to `ux-design/README.md`
- ⚠️ Minor: NFRs not numbered in source PRD — assigned NFR-P/S/R prefixes here for traceability
- ⚠️ Minor: No explicit Usability/Accessibility NFR section — accessibility constraints are only in UI section. Acceptable for a personal tool but worth flagging.

## Step 3 — Epic Coverage Validation

### Epic Inventory (8 epics, 32 stories)

| Epic | Title | FRs / NFRs / ARs covered | Stories |
|------|-------|--------------------------|---------|
| 1 | Project Foundation & Infrastructure | AR1, AR2, AR3, AR4, AR5, AR8, AR9 \| NFR7 | 1.1–1.4 |
| 2 | Spotify Authentication & App Config | FR1, FR2, FR3, FR18, FR19, FR20 \| AR6 \| NFR5, NFR6, NFR8 | 2.1–2.4 |
| 3 | Playlist Management & Manual Sync | FR4–FR13, FR17 \| NFR2, NFR4, NFR10, NFR11, NFR12 | 3.1–3.5 |
| 4 | Scheduler & Automatic Sync | FR14, FR15, FR16 \| NFR9 | 4.1–4.2 |
| 5 | Real-Time Observability | FR21, FR22, FR23, FR24 \| AR7 \| NFR1, NFR3 | 5.1–5.3 |
| 6 | Spotify Desktop UI Foundation | NFR15 \| PRD "UI & Visual Design" | 6.1–6.4 |
| 7 | Playlist Grid & Hide Management | FR25–FR30 \| AR10 \| NFR13 | 7.1–7.5 |
| 8 | Recently Added Page & Track Blacklist | FR31–FR36 \| AR11, AR12 \| NFR14 | 8.1–8.6 |

### Coverage Matrix — Functional Requirements

| FR | Summary | Epic / Story | Status |
|----|---------|--------------|--------|
| FR1 | Spotify OAuth login | Epic 2 / 2.2 | ✅ Covered |
| FR2 | Re-auth on token revoke/expire | Epic 2 / 2.3 | ✅ Covered |
| FR3 | Auto-refresh tokens | Epic 2 / 2.3 (AC5) | ✅ Covered |
| FR4 | Harvest tracks from selected playlists | Epic 3 / 3.3 | ✅ Covered |
| FR5 | Deduplicate (keep most recent added_at) | Epic 3 / 3.3 | ✅ Covered |
| FR6 | Sort by added_at desc | Epic 3 / 3.3 | ✅ Covered |
| FR7 | Top N selection | Epic 3 / 3.3 | ✅ Covered |
| FR8 | Create dynamic playlist if absent | Epic 3 / 3.4 | ✅ Covered |
| FR9 | Replace contents on each sync | Epic 3 / 3.4 | ✅ Covered |
| FR10 | View user-created playlists | Epic 3 / 3.1 | ✅ Covered |
| FR11 | Include/exclude toggle | Epic 3 / 3.1 | ✅ Covered |
| FR12 | Preferences persisted | Epic 3 / 3.2 | ✅ Covered |
| FR13 | Reflect added/removed Spotify playlists | Epic 3 / 3.2 | ✅ Covered |
| FR14 | Auto sync on schedule | Epic 4 / 4.1 | ✅ Covered |
| FR15 | Configure recurrence | Epic 4 / 4.2 + Epic 2 / 2.4 | ✅ Covered |
| FR16 | Scheduler persists across restart | Epic 4 / 4.1 | ✅ Covered |
| FR17 | Manual sync trigger | Epic 3 / 3.5 | ✅ Covered |
| FR18 | Configure Spotify credentials | Epic 2 / 2.1, 2.2 | ✅ Covered |
| FR19 | Configure playlist size | Epic 2 / 2.4 | ✅ Covered |
| FR20 | Config persisted | Epic 2 / 2.4 | ✅ Covered |
| FR21 | Real-time sync progress | Epic 5 / 5.3 | ✅ Covered |
| FR22 | Sync log entries (ts, status, delta, error) | Epic 5 / 5.1 | ✅ Covered |
| FR23 | Failure indicator on dashboard | Epic 5 / 5.2 | ✅ Covered |
| FR24 | Full sync log history | Epic 5 / 5.1 | ✅ Covered |
| FR25 | Grid of cover-art cards | Epic 7 / 7.2 | ✅ Covered |
| FR26 | Hide via per-card overflow menu | Epic 7 / 7.3 | ✅ Covered |
| FR27 | Hide ⇒ exclude from sync | Epic 7 / 7.1, 7.3 | ✅ Covered |
| FR28 | Collapsible Hidden section with count | Epic 7 / 7.4 | ✅ Covered |
| FR29 | Unhide restores card (excluded by default) | Epic 7 / 7.1, 7.4 | ✅ Covered |
| FR30 | Hidden state persisted | Epic 7 / 7.1 | ✅ Covered |
| FR31 | Recently Added page | Epic 8 / 8.3 | ✅ Covered |
| FR32 | Track list columns | Epic 8 / 8.3 | ✅ Covered |
| FR33 | Per-row overflow menu (Hide/Blacklist) | Epic 8 / 8.4 | ✅ Covered |
| FR34 | Blacklist excludes from future syncs | Epic 8 / 8.5 | ✅ Covered |
| FR35 | Next sync removes blacklisted track | Epic 8 / 8.5 | ✅ Covered |
| FR36 | Blacklist persisted | Epic 8 / 8.1 | ✅ Covered |
| **FR37** | **Preview next sync** | **NOT IN MVP EPICS** | 🟡 Phase 2 (deferred) |
| **FR38** | **Auto-exclude collab playlists** | **NOT IN MVP EPICS** | 🟡 Phase 2 (deferred) |
| **FR39** | **Sync history timeline** | **NOT IN MVP EPICS** | 🟡 Phase 2 (deferred) |
| **FR40** | **Top artists/genres stats** | **NOT IN MVP EPICS** | 🟡 Phase 2 (deferred) |
| **FR41** | **Notifications on sync events** | **NOT IN MVP EPICS** | 🟡 Phase 2 (deferred) |
| **FR42** | **Multi-select bulk blacklist** | **NOT IN MVP EPICS** | 🟡 Phase 2 (deferred) |
| **FR43** | **Review & un-blacklist UI** | **NOT IN MVP EPICS** | 🟡 Phase 2 (deferred) |

### Coverage Matrix — Non-Functional Requirements

| NFR (PRD) | Epics NFR# | Epic / Story | Status |
|-----------|-----------|--------------|--------|
| NFR-P1 — Dashboard load < 3 s | NFR1 | Epic 5 / 5.1 (AC5) | ✅ Covered |
| NFR-P2 — Playlist refresh < 2 s | NFR2 | Epic 3 / 3.1 (AC6) | ✅ Covered |
| NFR-P3 — SSE < 1 s | NFR3 | Epic 5 / 5.3 (AC3) | ✅ Covered |
| NFR-P4 — 5,000 tracks < 30 s | NFR4 | Epic 3 / 3.3 (AC5) | ✅ Covered |
| NFR-P5 — Grid < 1 s / 100 playlists | NFR13 | Epic 7 / 7.5 | ✅ Covered |
| NFR-P6 — Recently Added < 1 s / 200 tracks | NFR14 | Epic 8 / 8.3, 8.6 | ✅ Covered |
| NFR-S1 — Tokens server-side only | NFR5 | Epic 2 / 2.2 (AC5) | ✅ Covered |
| NFR-S2 — Credentials restricted (FS perms in PRD; SQLite in epics) | NFR6 | Epic 2 / 2.1 | ⚠️ Re-interpreted (see Notes) |
| NFR-S3 — No dashboard auth layer | NFR7 | Epic 1 (implicit — no auth scaffolding) | ✅ Covered |
| NFR-S4 — HTTPS for Spotify API | NFR8 | Epic 2 (spotipy default) | ✅ Covered (implicit) |
| NFR-R1 — Scheduler resume on restart | NFR9 | Epic 4 / 4.1 | ✅ Covered |
| NFR-R2 — Sync failure preserves playlist | NFR10 | Epic 3 / 3.4 (AC4) | ✅ Covered |
| NFR-R3 — Every sync logged | NFR11 | Epic 3 / 3.4 (AC3-4) | ✅ Covered |
| NFR-R4 — HTTP 429 backoff | NFR12 | Epic 3 / 3.4 (AC5) | ✅ Covered |

### Coverage Matrix — Architecture Constraints (ARs)

All 12 ARs (AR1–AR12) are explicitly mapped to a covering epic via the FR Coverage Map block in epics.md and traced in story acceptance criteria. ✅ Full AR coverage.

### Missing FR Coverage

#### Critical Missing FRs
**None.** All 36 MVP FRs are mapped to at least one story with concrete acceptance criteria.

#### Deferred (Phase 2 — out of MVP scope)
FR37–FR43 (7 FRs) are explicitly scoped as Phase 2 in the PRD ("Phase 2 Capabilities" section) and are correctly absent from the MVP epic plan. No action required — flag only to confirm that the PRD's Phase 2 backlog is preserved for future planning.

### Notes / Discrepancies

1. **NFR-S2 wording shift** — PRD says *"Spotify API credentials stored in local config file with restricted filesystem permissions, not in source code"*; epics rephrase as *"in SQLite, never in source code or .env"*. Architecture decision (AR8 — SQLite as single persistence layer) makes this consistent, but the **OS-level filesystem permissions** angle (e.g., `chmod 600` on `data/app.db`) is not surfaced in any story. Minor — worth confirming during architecture review (step 5) whether the data/ bind mount permissions are documented.
2. **NFR-S4 (HTTPS)** — Not explicitly asserted in any story AC; it is implicit via the `spotipy` library (which only targets `api.spotify.com`). Acceptable for a personal tool; no story-level fix needed.
3. **NFR-S3 (no auth layer)** — Covered as the *absence* of auth scaffolding in Epic 1 rather than a positive AC. Acceptable.
4. **Phase 2 FRs (FR37–FR43)** — intentionally deferred; PRD Phase 2 backlog is preserved.

### Coverage Statistics

- Total PRD MVP FRs: **36** — Covered: **36 / 36 (100%)**
- Total PRD Phase 2 FRs: **7** — Deferred (out of MVP scope, not a gap)
- Total NFRs (PRD): **14** — Covered: **14 / 14 (100%)** (2 implicit/re-interpreted)
- Total ARs: **12** — Covered: **12 / 12 (100%)**
- Total epics: **8** · Total stories: **32**

**Verdict:** ✅ **Full MVP FR/NFR/AR coverage in the epic plan.** No traceability gaps blocking implementation.

## Step 4 — UX Alignment Assessment

### UX Document Status

✅ **Found.** Sharded UX design package at `_bmad-output/planning-artifacts/ux-design/`:
- `index.md` — entry point with project overrides (SSE-only-during-sync) and variants chosen
- `README.md` — full spec (5 screens, tokens, components, interactions, state)
- `prototype/` — interactive reference prototype
- `snippets/` — drop-in production-ready TSX: `AppShell.tsx`, `PlaylistCard.tsx`, `TrackRow.tsx`, `HiddenPlaylistsAccordion.tsx`, `index.css` (tokens), `shadcn-add.sh`

Integrated 2026-05-20 via `bmad-correct-course` workflow (cf. `sprint-change-proposal-2026-05-20.md`). Status: `approved`.

### UX ↔ PRD Alignment

| Topic | PRD reference | UX coverage | Status |
|-------|---------------|-------------|--------|
| Dark theme | "UI & Visual Design" section | Tokens in `snippets/index.css`, `class="dark"` hardcoded | ✅ Aligned |
| Spotify-green accent | `#1DB954`-class | `--accent #1DB954` token (matches `1DB954`) | ✅ Aligned |
| Persistent left sidebar | "Layout: persistent left sidebar" | `AppShell.tsx` with `--sidebar-w 248px` grid | ✅ Aligned |
| Playlist grid (cover-art cards) | FR25, "Playlist grid" UI section | `PlaylistCard.tsx` + grid `repeat(auto-fill, minmax(190px, 1fr))` | ✅ Aligned |
| Hidden playlists accordion | FR28 | `HiddenPlaylistsAccordion.tsx` (shadcn Accordion, default collapsed) | ✅ Aligned |
| Recently Added track table | FR31, FR32 — index/title/album/date added/duration | `TrackRow.tsx` 6-column grid with sticky header | ✅ Aligned |
| Per-row overflow menu | FR33 | TrackRow overflow column + DropdownMenu items | ✅ Aligned |
| Hover affordance (Play FAB, overflow) | UI section, "Hover reveals a play/details affordance" | PlaylistCard hover: Play FAB + overflow button | ✅ Aligned |
| AA contrast / focus rings | "Accessibility: AA contrast … focus rings visible" | Story 6.1 AC4-5 enforces AA + ≥2px focus ring | ✅ Aligned |
| Desktop-first responsive | "Desktop-first responsive layout … gracefully degrades to smartphone" | Story 6.4 + UX README "Layout" / "Variants" | ✅ Aligned |
| SSE for sync logs | FR21 — real-time during active sync | UX `useEffect` always-on snippet **overridden by project policy** (sync-active only) in `ux-design/index.md` and Story 5.3 | ✅ Aligned (override documented in 3 places) |

**No UX requirement is missing from the PRD; no PRD UI requirement is missing from the UX spec.**

### UX ↔ Architecture Alignment

| Topic | UX expectation | Architecture coverage | Status |
|-------|----------------|----------------------|--------|
| Design tokens centralized | `frontend/src/index.css` :root block | Documented in arch "Design System & UI Primitives" — tokens listed | ✅ Aligned |
| Component baselines drop-in | `AppShell.tsx`, `PlaylistCard.tsx`, `TrackRow.tsx`, `HiddenPlaylistsAccordion.tsx` | Documented in arch "Composants applicatifs livrés par le handoff" | ✅ Aligned |
| shadcn additions | Accordion, DropdownMenu, Tooltip, Sheet, Input, Label, Separator | Documented in arch + install script `ux-design/snippets/shadcn-add.sh` | ✅ Aligned |
| Routes | `/`, `/recently-added`, `/settings`, `/logs` (`/config` redirects) | Documented in arch "Routing: React Router v7" | ✅ Aligned |
| lucide-react icons | LayoutDashboard, Clock, Settings, ScrollText, … | Listed in arch under design system section | ✅ Aligned |
| `track_blacklist` table | Backend support for blacklist (FR34) | ⚠️ **NOT in arch's `models/` directory tree** (file architecture.md predates 2026-05-20 sprint change for blacklist) — AR11 covers it conceptually but the `Complete Project Directory Structure` block omits the model | ⚠️ Minor gap (see Notes) |
| `GET /api/v1/recently-added` endpoint | Backend support for FR31 (AR12) | ⚠️ **NOT in arch's `routers/` mapping** for the same reason | ⚠️ Minor gap (see Notes) |
| `is_hidden` column on Playlist | FR27 backend support (AR10) | ⚠️ **NOT in arch's `models/playlist.py` columns description** — still lists `(id, spotify_id, name, is_included)` | ⚠️ Minor gap (see Notes) |
| Recently Added page perf <1s for 200 tracks | NFR-P6 | Arch performance section only mentions <3s page load + 5,000 tracks/30s — NFR-P6 not echoed | ⚠️ Minor — covered in story AC instead |
| Playlist grid perf <1s for 100 playlists | NFR-P5 | Same omission in architecture.md performance summary | ⚠️ Minor — covered in story AC instead |

### Warnings

**W1 — Architecture predates Sprint Change Proposal (2026-05-20).**
`architecture.md` carries `completedAt: '2026-04-17'` and was not fully revised when Epics 6/7/8 were added on 2026-05-20. The Design System & UI Primitives section was updated, but three lower-level sections were not:
- "Complete Project Directory Structure" — `models/playlist.py` should list `is_hidden`; a `models/track_blacklist.py` should appear; `routers/recently_added.py` (or equivalent) should appear.
- "Requirements to Structure Mapping" table — does not include FR25–FR36.
- "Requirements Coverage Validation" table — stops at FR24.

**Impact:** Low. AR10, AR11, AR12 in the epics inventory document the missing pieces, and Stories 7.1 / 8.1 / 8.2 have concrete acceptance criteria that fully specify the implementation. Implementation will not be blocked, but a code-search reader of `architecture.md` alone would miss these structural additions.

**Recommendation:** Update `architecture.md` in a follow-up edit to reflect AR10/AR11/AR12 in the directory tree and FR mapping tables. Non-blocking for implementation start.

**W2 — None.** No critical or high-severity gaps. UX docs are present, complete, and aligned with PRD requirements.

## Step 5 — Epic Quality Review

Reviewing the 8 epics / 32 stories against `create-epics-and-stories` best practices: user value, independence, story sizing, AC quality, and dependency hygiene.

### Epic-Level Assessment

| # | Epic | User Value | Independence | Verdict |
|---|------|-----------|--------------|---------|
| 1 | Project Foundation & Infrastructure | ⚠️ **Technical milestone** — "developer can run docker-compose up" is dev value, not end-user value. Acceptable as Epic-1 enabler per greenfield best practice. | Stands alone (no dependency on later epics) | 🟡 Minor — typical "Epic 1 enabler" pattern; acceptable for greenfield |
| 2 | Spotify Authentication & App Configuration | ✅ User can connect, configure, settings persist | Depends on Epic 1 outputs only | ✅ Pass |
| 3 | Playlist Management & Manual Sync | ✅ User can select playlists, trigger sync, see dynamic playlist | Depends on Epic 1+2 only | ✅ Pass |
| 4 | Scheduler & Automatic Sync | ✅ Playlist stays current automatically | Depends on Epic 3 (`sync_engine.run_sync()`) — backward only | ✅ Pass |
| 5 | Real-Time Observability | ✅ User sees live progress + failure indicator + history | Depends on Epic 3 (sync runs produce logs) — backward only | ✅ Pass |
| 6 | Spotify Desktop UI Foundation | ✅ User experiences dark theme + AppShell — though largely "foundation" work for 7/8, it does deliver visible value (re-skinned dashboard) | Depends on Epic 1 only; introduced as a layer before 7/8 | ✅ Pass |
| 7 | Playlist Grid & Hide Management | ✅ User can hide/unhide playlists via grid | Depends on Epic 6 (AppShell v2 + tokens) and Epic 3 (PATCH endpoint) — backward only | ✅ Pass |
| 8 | Recently Added Page & Track Blacklist | ✅ User can view + blacklist tracks | Depends on Epic 6 (AppShell) + Epic 3 (sync engine for FR35) — backward only | ✅ Pass |

**Independence summary:** No forward dependencies. Each epic only references outputs of prior epics.

### Story-Level Quality (sample audit across all 32 stories)

I audited every story for: (a) Given/When/Then ACs, (b) measurable outcomes, (c) absence of forward references, (d) appropriate sizing.

**Format & BDD compliance:** ✅ All 32 stories use the **As a / I want / So that** narrative followed by Given/When/Then ACs.

**AC density (specificity):**
- All stories include between **3 and 9 ACs** with concrete, testable verbs (DB column names, HTTP endpoints, exact CSS values, ms thresholds).
- UI stories (6.1–8.6) reference exact tokens, lucide icons, pixel values, hex codes — extremely precise.
- Backend stories (1.x, 2.x, 3.x) name exact endpoints (`PUT /api/v1/config`), payload shapes, table columns.

**Forward-reference scan (grep equivalent of "depends on Story X.Y" where X.Y > current story):**
- Story 5.3 references "AR7" and the SSE policy override — both are **prior context**, not forward deps.
- Story 7.3 / 7.4 / 8.4 / 8.5 reference Stories 7.1, 7.2, 8.1, 8.2 / 8.3 — all **backward** dependencies (correct order).
- Story 6.4 mentions "AppShell renders" — relies on Story 6.2 (correct sequencing within Epic 6: 6.1 tokens → 6.2 shell → 6.3 routes → 6.4 responsive).
- **No forward dependencies detected.**

**Story sizing:**
- Smallest stories: 4.2 (Dynamic Schedule Reconfig — 4 ACs), 5.2 (Failure Indicator — 4 ACs). Reasonable.
- Largest stories: 6.2 (AppShell v2 — 10 ACs), 7.2 (Playlist Grid — 11 ACs), 8.3 (Track Table — 11 ACs). Larger because they wire many UX baselines, but each AC is atomic. **No story crosses the "Epic disguised as story" line.**
- Story 6.2 and 7.2 contain **some duplicated ACs** (the same hover/menu/grid criteria appear twice within the same story). 🟡 Minor cleanup opportunity.

**Database/entity timing:**
- Story 1.2 creates `config`, `playlist`, `sync_log` upfront. ⚠️ Mild deviation from "create tables only when needed" best practice — but explicit AR8 ("SQLModel.metadata.create_all() on startup") makes this an architectural decision rather than a sloppy lump. Acceptable.
- Story 7.1 adds `is_hidden` column via SQLModel auto-create when Epic 7 begins — correct just-in-time addition.
- Story 8.1 adds `track_blacklist` table when Epic 8 begins — correct just-in-time addition.

### Starter Template Check

Architecture specifies **manual scaffolding** (no starter template). Story 1.1 ("Project Scaffolding & Docker Compose") correctly serves as the initial setup story with Vite React TS frontend + FastAPI/uv backend + Docker Compose. ✅ Compliant.

### Findings by Severity

#### 🔴 Critical Violations
**None.**

#### 🟠 Major Issues
**None.**

#### 🟡 Minor Concerns
1. **Story 6.2 (AppShell v2)** — 3 ACs are duplicated verbatim with slightly different wording (the `NavBar` removal grep AC appears twice; the hover/overflow card AC appears twice). Recommendation: dedupe before dev pickup. Non-blocking.
2. **Story 7.2 (Playlist Grid)** — Same duplication pattern: hover affordance ACs and "list component removed" AC appear twice. Recommendation: dedupe. Non-blocking.
3. **Story 8.3 (Track Table)** — Same pattern: empty-state, perf, and skeleton ACs are duplicated. Recommendation: dedupe. Non-blocking.
4. **Epic 1 ("Project Foundation")** — Technical epic by design (greenfield enabler). Title remains technical rather than user-facing. Acceptable per BMad greenfield convention but worth flagging.
5. **Story 1.2 (Database Models)** — Creates all base tables upfront rather than per-feature. Justified by AR8 (auto-create-all on startup), but conflicts with the strict "create when needed" rule in the quality checklist. Accept as an explicit architectural choice.
6. **Architecture document staleness** (already flagged in Step 4 W1) — directory tree and FR mapping table don't reflect AR10/AR11/AR12. Non-blocking; epic ACs carry the missing detail.

### Best Practices Compliance Checklist (per epic)

| Epic | User value | Independent | Sized | No fwd deps | DB timing | Clear ACs | FR trace |
|------|-----------|------------|-------|-------------|-----------|-----------|----------|
| 1 | 🟡 dev value | ✅ | ✅ | ✅ | 🟡 lump | ✅ | ✅ |
| 2 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 6 | ✅ | ✅ | 🟡 duplication | ✅ | ✅ | ✅ | ✅ |
| 7 | ✅ | ✅ | 🟡 duplication | ✅ | ✅ | ✅ | ✅ |
| 8 | ✅ | ✅ | 🟡 duplication | ✅ | ✅ | ✅ | ✅ |

### Recommendations

1. **Dedupe ACs in Stories 6.2, 7.2, 8.3** before dev pickup (cosmetic — does not change behavior). Estimated effort: 10 min total.
2. **Update `architecture.md`** post-implementation start to reflect AR10/AR11/AR12 in directory tree + FR mapping (optional, non-blocking).
3. **Accept Epic 1 + Story 1.2 as architectural exceptions** to the "every epic must deliver end-user value" / "tables when needed" rules. These are explicit, conscious choices grounded in AR1, AR8, and greenfield scaffolding convention.

## Summary and Recommendations

### Overall Readiness Status

# ✅ READY FOR IMPLEMENTATION

The PRD, Architecture, UX, and Epics + Stories artifacts together form a coherent, traceable, and implementation-ready plan. Coverage is complete, dependencies flow only backward, and acceptance criteria are concrete enough for an AI dev agent to pick up any story without ambiguity. Several MVP stories (1.1 through 5.3) are already implemented per `git log`, confirming the plan has been actionable in practice.

### Findings Snapshot

| Severity | Count | Description |
|----------|-------|-------------|
| 🔴 Critical | **0** | No blockers. |
| 🟠 Major | **0** | No high-impact gaps. |
| 🟡 Minor | **6** | Doc-staleness + AC duplication + architectural-exception flags — all non-blocking. |
| 🟢 Notes | n/a | Strong design-system handoff, clean traceability, well-sequenced epics. |

### Critical Issues Requiring Immediate Action

**None.** No critical or major issues were identified.

### Recommended Next Steps

1. **Cosmetic: dedupe duplicated ACs in Stories 6.2, 7.2, 8.3** (~10 min, before story pickup) — the duplications won't break anything but clutter dev attention.
2. **Optional: refresh `architecture.md`** to integrate AR10/AR11/AR12 into:
   - "Complete Project Directory Structure" — add `models/track_blacklist.py`, update `models/playlist.py` columns to include `is_hidden`, add route for `recently-added`.
   - "Requirements to Structure Mapping" — extend table to cover FR25–FR36.
   - "Requirements Coverage Validation" — extend to FR36.
   - Non-blocking. Improves new-reader onboarding.
3. **Confirm NFR-S2 interpretation** — PRD says credentials in "local config file with restricted filesystem permissions"; current implementation stores them in SQLite (`data/app.db`). Consider documenting host-side `chmod` guidance for the `data/` bind mount in the README, or accept SQLite as sufficient given the local-only deployment posture (NFR-S3).
4. **Proceed to Sprint Planning** — implementation can continue from the current state. Per `git log`, Stories 1.x–5.3 + delta sync are already shipped. Next sprint candidates: Epic 6 (UI foundation), then Epics 7 + 8 (grid + Recently Added).

### Phase 2 Backlog Preserved

PRD Phase 2 capabilities (FR37–FR43) are intentionally **not** in the MVP epic plan. Document them in a separate Phase 2 epic backlog when MVP closes — do not let them silently drop.

### Final Note

This assessment identified **6 minor issues across 3 categories** (doc staleness, AC duplication, accepted architectural exceptions). None are blocking. The plan is ready for implementation and, in fact, is already partially executed with no observable derailment from the design.

**Assessor:** Claude (Implementation Readiness skill)
**Date:** 2026-05-20
**Project:** playlist_spotify





