# Sprint Change Proposal — Pagination serveur + scroll infini sur les tracks d'une playlist

**Date:** 2026-05-26
**Author:** kevin aubel
**Epic impacté:** Epic 9 — Playlist Detail Page
**Scope classification:** Moderate (ajout d'une story, modifications backend + frontend, aucune refonte d'architecture)

---

## Section 1 — Issue Summary

**Problème.** Chargement perçu lent sur une playlist à ~500 titres. La page bloque plusieurs secondes avant d'afficher la première ligne.

**Cause identifiée.** `GET /api/v1/playlists/{spotify_id}/tracks` (Story 9.1, [backend/routers/playlists.py:90](backend/routers/playlists.py#L90)) renvoie la **totalité** des tracks en une seule réponse, après avoir enchaîné côté `services/spotify.py` les pages Spotify de 100 items (5 appels HTTP séquentiels pour 500 tracks). Côté frontend, [usePlaylistTracks.ts](frontend/src/hooks/usePlaylistTracks.ts) fetch tout d'un coup via un `useQuery` simple.

**Confusion à clarifier.** Story 9.6 (`@tanstack/react-virtual`) virtualise le **rendu DOM** : c'est du gain au scroll, pas au chargement initial. Le bottleneck réseau n'est pas adressé.

**Évidence.** UX dégradée mesurée par l'utilisateur sur sa playlist "Liked Songs" (~500 tracks). Le LCP est dominé par l'attente des 5 round-trips Spotify avant le premier render.

---

## Section 2 — Impact Analysis

### Epic Impact
- **Epic 9** : ajout d'une story 9.8 en fin d'epic. Pas de remise en cause des stories existantes.

### Story Impact
- **Story 9.1** (`Playlist Tracks API Endpoint`, status `review`) : son AC actuel ("paginated server-side, full list returned to client") devient un **comportement legacy à rendre paginable**. Pas de réécriture, mais le endpoint évolue pour accepter `?limit&offset` (rétro-compatible : si omis, comportement actuel préservé OU on bascule franchement sur pagination obligatoire — décision dans Story 9.8).
- **Story 9.6** (`Virtualization for Large Playlists`, status `review`) : **non régressée**. Le virtualizer continue de fonctionner sur la liste reçue, qu'elle soit complète ou chargée par pages. La fusion des pages produit un array unique consommé par `TrackListTable` à l'identique.
- **Story 9.5** (filtre côté client) : compatible **uniquement** sur les tracks déjà chargées. Note explicite à ajouter en AC de 9.8 (le filtre ne descend pas côté serveur — accepté comme limitation MVP).
- **Stories 9.2, 9.3, 9.4, 9.7** : aucune modification.

### Artifact Conflicts
- **PRD** : non impacté. La pagination est un détail d'implémentation sous FR46 / NFR16 (performance perçue).
- **Architecture** : pas de doc d'architecture formelle à modifier (le projet n'en a pas de séparée).
- **UX** : aucune. Le scroll infini est un comportement courant — pas de wireframe à produire.

### Technical Impact
- **Backend** : `GET /playlists/{spotify_id}/tracks` accepte `limit` (default 50) et `offset` (default 0). Retour enrichi avec `{items, next_offset, total}` ou conserve l'array et expose `X-Next-Offset` en header (décision technique laissée à la story).
- **Frontend** : `usePlaylistTracks` migre de `useQuery` vers `useInfiniteQuery` (TanStack Query v5). Sentinelle `IntersectionObserver` en bas de `TrackListTable` déclenche `fetchNextPage()`. Aplatissement des pages dans `tracks = data.pages.flatMap(p => p.items)`.
- **Compatibilité avec virtualisation 9.6** : le virtualizer travaille sur l'array aplati. Quand `fetchNextPage` ajoute des items, `count` augmente et `useVirtualizer` recalcule automatiquement (déjà testé dans 9.6 AC #8 pour le blacklist).
- **Tests** : `test_story_9_8.py` couvre `limit`, `offset`, edge cases (offset > total, limit > 100, liked songs synthetic).
- **Postman** : collection à mettre à jour (cf. [feedback_postman_sync](file:///home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md)).

---

## Section 3 — Recommended Approach

**Path:** Direct Adjustment — ajouter Story 9.8 à Epic 9.

**Rationale.** Le périmètre est cleanement additif : nouvelle story, pas de rollback, pas de refonte. Les stories 9.1 à 9.7 livrent une fondation fonctionnelle (la page marche déjà). 9.8 améliore la perf perçue sans casser le contrat existant.

**Effort estimé.** ~2-3h dev (backend : 30 min ; frontend `useInfiniteQuery` + sentinel : 1h ; tests : 1h ; Postman : 15 min).

**Risk assessment.**
- Risque bas — pattern `useInfiniteQuery` standard, déjà supporté par TanStack Query v5.
- Risque modéré sur l'interaction avec le filtre Story 9.5 (filtre client uniquement sur pages chargées). Documenté comme limitation acceptée en AC.

**Timeline impact.** Aucun — Epic 9 reste "in-progress" jusqu'à 9.8 done. Pas de blocage pour démarrer Epic 10 (s'il existe).

---

## Section 4 — Detailed Change Proposals

### 4.1 Ajout dans `epics.md` (après Story 9.7, avant la fin de Epic 9)

```markdown
### Story 9.8: Paginated Tracks API + Infinite Scroll

As a user with large playlists (200+ tracks),
I want the playlist detail page to load the first batch of tracks quickly and stream the rest as I scroll,
So that I see content within ~500 ms instead of waiting for the whole playlist to be fetched from Spotify.

**Acceptance criteria:**

**Given** the backend endpoint `GET /api/v1/playlists/{spotify_id}/tracks`,
**When** the client provides `?limit=50&offset=0`,
**Then** the response returns at most `limit` tracks starting at `offset`, plus a `next_offset` field (null when the end is reached) and a `total` field.

**Given** the same endpoint,
**When** no `limit` is provided,
**Then** the default is `limit=50` and `offset=0` (NOT the full list — breaking change vs. Story 9.1, accepted).

**Given** the synthetic "Liked Songs" playlist (`spotify_id == "liked"`),
**When** paginated requests are made,
**Then** the same pagination semantics apply via `current_user_saved_tracks(limit, offset)`.

**Given** the frontend hook `usePlaylistTracks`,
**When** the playlist detail page mounts,
**Then** the hook uses `useInfiniteQuery` (TanStack Query v5) with `initialPageParam: 0`, `getNextPageParam: (lastPage) => lastPage.next_offset`.

**Given** `TrackListTable`,
**When** the user scrolls within 300 px of the bottom of the list,
**Then** an `IntersectionObserver` sentinel triggers `fetchNextPage()` if `hasNextPage && !isFetchingNextPage`.

**Given** the Story 9.6 virtualizer,
**When** a new page is appended to the flattened `tracks` array,
**Then** the virtualizer's `count` updates automatically and rows render seamlessly (no re-mount, no scroll jump).

**Given** the Story 9.5 filter input,
**When** the user filters,
**Then** the filter applies ONLY to currently-loaded pages (documented limitation — full-playlist search is out of scope for MVP).

**Given** the backend test suite,
**When** the dev runs `pytest tests/test_story_9_8.py -v`,
**Then** ≥4 tests cover: nominal pagination, `offset > total`, `limit > 100` (clamped or rejected), and Liked Songs pagination. Total baseline ≥134.

**Given** the Postman collection,
**When** Story 9.8 ships,
**Then** the `GET /playlists/{id}/tracks` example reflects the new query params and paginated response shape.

**Implementation hints:**
- Backend: `get_playlist_tracks_full` → `get_playlist_tracks_page(spotify_id, limit, offset)`. Use spotipy's native `offset`/`limit` params on `playlist_items` and `current_user_saved_tracks` (no client-side aggregation across pages). Return `{items, next_offset, total}`.
- Clamp `limit` to `[1, 100]` server-side (Spotify's own cap).
- Frontend: `useInfiniteQuery` keyed on `['playlist-tracks', spotifyId]`. Flatten in the consumer: `const tracks = data?.pages.flatMap(p => p.items) ?? []`.
- Sentinel: 1 px `<div ref={sentinelRef} />` rendered after the virtualizer's spacer. `IntersectionObserver` with `rootMargin: '300px'`.
- Loading state: when `isFetchingNextPage`, show a 3-row skeleton at the bottom of the virtualized list.
- `staleTime: 30_000` preserved.
- Backward compat note: Story 9.1 callers (none in production yet — only the frontend touches this endpoint) are updated in the same PR.
```

### 4.2 Mise à jour de `sprint-status.yaml`

Ajouter dans `development_status` (sous `epic-9-retrospective: optional`) :

```yaml
  9-8-paginated-tracks-infinite-scroll: backlog
```

Et bumper `last_updated: 2026-05-26  # Story 9.8 added via correct-course (pagination)`.

### 4.3 Note dans Story 9.1 (file 9-1-playlist-tracks-api.md)

Ajouter une mention en bas du fichier :

```markdown
## Spec Change Log
- 2026-05-26: AC "full list returned to client" superseded by Story 9.8 (paginated server-side AND paginated to client). Endpoint contract evolves to `?limit&offset` with `{items, next_offset, total}` response shape. See `sprint-change-proposal-2026-05-26-playlist-tracks-pagination.md`.
```

### 4.4 Note dans Story 9.6 (file 9-6-virtualization-large-playlists.md)

Ajouter une mention :

```markdown
## Spec Change Log
- 2026-05-26: Confirmed compatible with Story 9.8 (paginated fetch). Virtualizer's `count` reactivity handles appended pages without modification (already validated by AC #8 pattern). No changes required to TrackListTable virtualization branch.
```

---

## Section 5 — Implementation Handoff

**Change scope:** **Moderate**

**Recipients & deliverables:**
1. **Developer agent** (Amelia / `bmad-dev-story`) — implémente Story 9.8 après création du fichier story par `bmad-create-story`
2. **User (kevin aubel)** — exécute `/bmad-create-story` pour matérialiser 9.8 en fichier prêt-dev, puis `/bmad-dev-story`

**Success criteria:**
- Première ligne visible en < 500 ms sur une playlist de 500 tracks (test manuel)
- Aucune régression sur Stories 9.1–9.7 (tests existants verts)
- ≥4 nouveaux tests dans `test_story_9_8.py`
- Collection Postman synchronisée

---

## Approval

- [ ] kevin aubel — review et approbation de cette proposition

Une fois approuvée :
1. Appliquer les 3 modifications d'artefacts (epics.md, sprint-status.yaml, notes dans 9-1 et 9-6)
2. Lancer `/bmad-create-story` qui va auto-découvrir 9.8 en backlog et la matérialiser
