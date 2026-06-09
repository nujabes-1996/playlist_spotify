---
date: 2026-05-25
mode: batch
scope: extended
trigger: Nouvelle feature — Page détail playlist (clic carte → liste tracks style Recently Added)
status: draft-pending-approval
---

# Sprint Change Proposal — Epic 9 : Playlist Detail Page

## Section 1 · Issue Summary

### Problem statement

L'utilisateur veut pouvoir **cliquer sur une carte playlist du Dashboard** pour ouvrir une page dédiée listant **tous les titres** de cette playlist, avec **le même style visuel** que la page Recently Added (hero + table TrackRow style Spotify desktop).

### Contexte de découverte

- Tous les Epics 1→8 sont en `review` dans `sprint-status.yaml`. L'app a une UI Spotify desktop-like complète (sidebar, grid playlists, page Recently Added).
- L'utilisateur souhaite étendre l'application avec une nouvelle dimension de navigation : drill-down par playlist.
- Demande explicite en mode **extended** → Epic complet plutôt que story isolée.

### Evidence

- Dashboard actuel : grid de cartes playlists (Epic 7) — actuellement aucun handler `onClick` navigation.
- Page Recently Added (Epic 8) : pattern hero + table TrackRow déjà éprouvé et performant (NFR14 < 1s pour 200 tracks).
- Les composants `RecentlyAddedHero.tsx` et `RecentlyAddedTable.tsx` (dans `frontend/src/features/recently-added/`) sont fortement réutilisables.

---

## Section 2 · Impact Analysis

### Epic Impact

| Epic | Status | Impact |
|------|--------|--------|
| Epic 7 (Playlist Grid) | review | **Modif mineure** : ajouter `onClick` navigation sur `PlaylistCard` (sans casser le menu overflow Hide existant). |
| Epic 8 (Recently Added) | review | **Refacto opportuniste** : extraire les composants `RecentlyAddedHero` + `RecentlyAddedTable` vers `features/tracks/` partagé pour réutilisation. |
| **Epic 9 (nouveau)** | — | **Ajout complet** : 6 stories couvrant API, refacto composants, page détail, actions, recherche, performance. |

### Story Impact

- **Aucune story existante n'est invalidée.** Toutes restent en `review`.
- Refacto recommandée (mais non bloquante) : `RecentlyAddedPage` continuera de fonctionner pendant et après l'extraction des composants partagés.

### Artifact Conflicts

| Artifact | Modifications nécessaires |
|----------|---------------------------|
| `prd.md` | Ajouter FR44–FR48, NFR16, AR13, AR14 ; ajouter Journey 7 ; ajouter section « Playlist Detail Page » dans Functional Requirements ; mentionner la route `/playlists/:id` dans UI & Visual Design. |
| `epics.md` | Ajouter Epic 9 dans Epic List + bloc complet Epic 9 avec ses 6 stories ; mettre à jour FR Coverage Map. |
| `architecture.md` | Aucune modif structurelle (réutilise stack existant : FastAPI router + spotipy + TanStack Query + react-router-dom). Note technique optionnelle sur virtualisation. |
| `ux-design/README.md` | Ajouter section « 6 · Playlist Detail route » décrivant hero (cover playlist + nom + owner + N tracks + durée totale) et table (réutilise TrackRow). |
| `sprint-status.yaml` | Ajouter `epic-9: backlog` + 6 stories `9-X-…: backlog` + `epic-9-retrospective: optional`. |

### Technical Impact

- **Backend** : 1 nouveau router `routers/playlist_tracks.py` (ou ajout dans `playlists.py`) + 1 fonction `spotify.get_playlist_tracks(playlist_id)` dans `services/spotify.py` (paginated).
- **Frontend** : 1 nouvelle page `PlaylistDetailPage.tsx`, 1 nouveau hook `usePlaylistTracks.ts`, refacto `features/recently-added/` → `features/tracks/` (composants partagés), nouvelle route `/playlists/:spotifyId`, handler `onClick` sur `PlaylistCard`.
- **Performance** : pour playlists volumineuses (Liked Songs = 535 tracks chez l'utilisateur), introduire `@tanstack/react-virtual` (déjà compatible TanStack v5) ou pagination côté API.
- **Aucun changement de schéma DB.** Aucune migration.
- **Aucun impact** sur scheduler, sync engine, blacklist (la blacklist par track utilise déjà un `spotify_id` global, valable depuis n'importe quelle source).

---

## Section 3 · Recommended Approach

### Path forward : **Direct Adjustment** (ajout d'un Epic 9 + 6 stories)

- Epic 9 ne touche **aucun code existant en production** au-delà de l'ajout d'un `onClick` sur `PlaylistCard` (zéro régression).
- Le refacto composants partagés (Story 9.2) est **isolé et réversible** (renommage + déplacement, pas de changement d'API).
- Pas de rollback nécessaire, pas de réduction de scope MVP.

### Effort estimate

| Story | Effort | Risque |
|-------|--------|--------|
| 9.1 API tracks playlist | S (1-2h) | Bas — pattern `recently_added.py` réutilisable presque tel quel |
| 9.2 Refacto composants partagés | S (1-2h) | Bas — renommages + ré-imports |
| 9.3 Page détail + nav | M (2-4h) | Moyen — route param, état loading, gestion `Titres likés` (cas particulier) |
| 9.4 Actions par track | S (1h) | Bas — réutilise `useBlacklist` existant |
| 9.5 Recherche/filtre | S (1-2h) | Bas — filter local côté frontend |
| 9.6 Virtualisation | M (2-3h) | Moyen — intégration `@tanstack/react-virtual` |

**Total estimé : 1-2 jours de dev.**

### Timeline impact

Aucun. Tous les Epics 1→8 étant en `review`, Epic 9 démarre sans contention.

---

## Section 4 · Detailed Change Proposals

### 4.1 — `prd.md`

#### Ajout : nouvelles FRs

```
### Playlist Detail Page

- **FR44:** User can click a playlist card on the Dashboard to navigate to a dedicated playlist detail page
- **FR45:** The playlist detail page displays all tracks in the playlist using the same hero + track table layout as Recently Added
- **FR46:** Each track row on the playlist detail page exposes the same overflow menu as Recently Added: "Hide / Blacklist" and "Open in Spotify"
- **FR47:** User can filter the displayed tracks within a playlist by title or artist (case-insensitive substring match)
- **FR48:** User can navigate back to the Dashboard from the playlist detail page (browser back + visible back affordance)
```

#### Ajout : NFR

```
- **NFR16:** Playlist detail page initial paint completes within 1.5s for playlists up to 1,000 tracks; uses virtualization for the track table when track count exceeds 200
```

#### Ajout : AR

```
- AR13: New `GET /api/v1/playlists/{spotify_id}/tracks` endpoint reads playlist contents from Spotify (paginated), returning the same track shape as `GET /api/v1/recently-added` for component reuse
- AR14: Hero + track table components extracted from `features/recently-added/` to `features/tracks/` and consumed by both Recently Added and Playlist Detail pages — single source of truth for the Spotify-desktop track list pattern
```

#### Ajout : Journey 7

```
### Journey 7 — Exploring a single playlist

**Kevin wants to see exactly what's in his "Rock" playlist before deciding to include it in Recent Adds.**

He clicks the Rock card on the Dashboard. The app navigates to `/playlists/<id>` — same hero+table layout he knows from Recently Added, this time showing all 56 Rock tracks with their date added. He filters by "Metallica" and the table narrows live. He spots a track that doesn't belong, clicks ⋯ → "Hide from Recent Adds" — the track is blacklisted globally and won't appear in his Recent Adds next sync.

**Capabilities revealed:** click-to-detail navigation, reused track table pattern, per-track blacklist from any context.
```

#### Ajout : section UI & Visual Design

> Insérer juste après la description « Recently Added page » :
>
> - **Playlist detail page:** Same layout family as Recently Added (full-bleed hero with playlist cover + name + owner + track count + total duration; sticky-header track table with `#`, Title, Album, Date Added, Duration, ⋯). Includes a search/filter input in the actions row to narrow the visible tracks.

#### Ajout : Phase 2

> Aucun changement Phase 2 — les capacités planifiées (preview, multi-select bulk blacklist) restent pertinentes et bénéficieront du composant partagé `features/tracks/`.

---

### 4.2 — `epics.md`

#### Ajout dans Epic List

```
### Epic 9: Playlist Detail Page
The user can click any playlist card to open a dedicated detail page reusing the Recently Added hero + track table layout. Tracks can be filtered, blacklisted directly, and virtualized for large playlists.
**FRs covered:** FR44, FR45, FR46, FR47, FR48 | AR13, AR14 | NFR16
```

#### Ajout dans FR Coverage Map

```
FR44: Epic 9 — User can click a playlist card to navigate to detail page
FR45: Epic 9 — Playlist detail page displays all tracks in same layout as Recently Added
FR46: Epic 9 — Per-row overflow menu on playlist detail (blacklist + open in Spotify)
FR47: Epic 9 — User can filter tracks within a playlist by title or artist
FR48: Epic 9 — User can navigate back to Dashboard from playlist detail
NFR16: Epic 9 — Playlist detail page <1.5s for 1,000 tracks; virtualization beyond 200
AR13: Epic 9 — GET /api/v1/playlists/{spotify_id}/tracks endpoint
AR14: Epic 9 — Track table components extracted to features/tracks/ shared module
```

#### Ajout bloc complet Epic 9 (résumé des 6 stories)

```
## Epic 9: Playlist Detail Page

**FRs covered:** FR44, FR45, FR46, FR47, FR48 | AR13, AR14 | NFR16

### Story 9.1: Playlist Tracks API Endpoint
As a developer, I want a paginated endpoint that returns all tracks of a given playlist
in the same shape as /recently-added, so that the frontend can reuse existing components.

### Story 9.2: Shared Track List Components Extraction
As a developer, I want hero + track table components extracted from features/recently-added/
to features/tracks/, so that both Recently Added and Playlist Detail share one source of truth.

### Story 9.3: Playlist Detail Page & Navigation
As a user, I want clicking a playlist card to open a detail page with hero (cover, name,
owner, track count, total duration) and the shared track table.

### Story 9.4: Per-Track Actions on Playlist Detail
As a user, I want the ⋯ overflow menu on each row of the playlist detail (Blacklist + Open
in Spotify), with optimistic UI matching Recently Added behavior.

### Story 9.5: Filter Tracks within Playlist
As a user, I want a search input in the hero actions row to filter the visible tracks
by title or artist, so I can quickly find a track in a large playlist.

### Story 9.6: Virtualization for Large Playlists
As a user, I want the track table to remain smooth for playlists of 500-1000+ tracks
(e.g. Liked Songs), using @tanstack/react-virtual when track count > 200.
```

> Les **acceptance criteria BDD complets** seront rédigés par `bmad-create-story` au moment de générer chaque story file dans `_bmad-output/implementation-artifacts/`.

---

### 4.3 — `sprint-status.yaml`

```yaml
  # Epic 9: Playlist Detail Page
  epic-9: backlog
  9-1-playlist-tracks-api: backlog
  9-2-shared-track-list-components: backlog
  9-3-playlist-detail-page-navigation: backlog
  9-4-per-track-actions-playlist-detail: backlog
  9-5-filter-tracks-within-playlist: backlog
  9-6-virtualization-large-playlists: backlog
  epic-9-retrospective: optional
```

Mettre à jour `last_updated: 2026-05-25  # Epic 9 added via correct-course`.

---

### 4.4 — `architecture.md`

> Aucune modification structurelle requise. Optionnel : ajouter une note brève dans la section « Frontend Patterns » :
>
> - Pour les listes de tracks > 200 lignes, utiliser `@tanstack/react-virtual` (compatible TanStack Query v5, déjà la stack). Pattern : viewport scroll container + `useVirtualizer` sur le tableau.

---

### 4.5 — `ux-design/README.md`

> Ajouter une nouvelle section après « 3 · Recently Added route » :
>
> ```
> ### 6 · Playlist Detail route (`/playlists/:spotifyId`)
>
> Same hero + table family as Recently Added. Differences vs Recently Added:
> - Hero kicker: "PLAYLIST" (au lieu de "AUTO-SYNCED PLAYLIST")
> - Hero title: playlist name (from /api/v1/playlists)
> - Hero sub-line: <strong>{owner}</strong> • {n} tracks • about Xh Ym
> - Hero actions row: "Open in Spotify" (primary cette fois car pas de sync local) + search input (rounded-full, w 240px, icon Search) + ⋯ menu (futur: edit playlist).
> - Table: réutilise TrackRow inchangé. Search filtre en live (case-insensitive sur title + artists).
> ```

---

## Section 5 · Implementation Handoff

### Scope classification

**MODERATE** — nécessite réorganisation du backlog (ajout d'Epic 9 + 6 stories) et un petit refacto Epic 8 (Story 9.2). Aucun replan PM/Architect requis.

### Routing

1. **PO/DEV** (toi) : approuver ce proposal → appliquer les éditions PRD/Epics/UX/sprint-status.
2. **Developer** : pour chaque story 9.1 → 9.6, dans une fenêtre fraîche :
   - `/bmad-create-story` (auto-pick la prochaine story `backlog`)
   - `/bmad-dev-story`
   - `/bmad-code-review`
3. **Recommandation d'ordre d'exécution** : 9.1 → 9.2 → 9.3 → 9.4 → 9.5 → 9.6 (séquentiel — chaque story dépend de la précédente).

### Success criteria

- Clic sur une carte playlist du Dashboard → page détail rendue en <1.5s pour playlists ≤ 1000 tracks.
- Mêmes interactions track-level (blacklist, open in Spotify) disponibles sur Recently Added ET Playlist Detail.
- Zéro régression sur les Epics 1→8 existants (tests pytest + build TS doivent passer).
- Postman collection mise à jour avec la nouvelle route `GET /api/v1/playlists/{spotify_id}/tracks` (cf. CLAUDE.md).

---

## Approval

- [ ] Proposal approuvé par l'utilisateur — appliquer les éditions sur tous les artefacts listés Section 4
- [ ] Demande de révision — feedback ci-dessous
