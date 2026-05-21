---
workflowType: 'correct-course'
date: '2026-05-20'
author: 'kevin'
trigger: 'Claude Design handoff intégration'
scope: 'Moderate'
---

# Sprint Change Proposal — Intégration du Handoff Design Claude Design

**Date:** 2026-05-20
**Auteur:** kevin
**Mode:** Batch
**Classification de scope:** Moderate (réorganisation backlog stories 6.1–8.6 + ajout artefact UX officiel, pas de replanification fondamentale)

---

## Section 1 — Issue Summary

### Problème déclencheur
Un livrable de design externe a été produit par Claude Design (`design_handoff_playlist_spotify/`). Il contient :
- Un README de 16 KB décrivant 5 écrans (AppShell, Dashboard, Recently Added, Settings, Logs)
- Un prototype HTML/JSX interactif
- 4 snippets TSX shadcn-compatible drop-in (`AppShell.tsx`, `PlaylistCard.tsx`, `TrackRow.tsx`, `HiddenPlaylistsAccordion.tsx`)
- Un fichier `index.css` avec tous les design tokens
- Un script `shadcn-add.sh` listant les composants shadcn à installer

### Contexte
- Le PRD existant comporte une section "UI & Visual Design" haut niveau (prd.md:189-198)
- Les Epics 6/7/8 cadrent la refonte mais leurs Stories étaient rédigées sans spec UX (epics.md:88 mentionne explicitement *"No UX Design document provided"*)
- Le handoff comble ce manque mais introduit aussi des décisions techniques précises (composants nommés, tokens exacts, ordre d'implémentation) absentes du PRD/Architecture

### Décisions prises avec l'utilisateur (2026-05-20)
1. **Deltas techniques**: Adopter intégralement le handoff **sauf** le SSE always-on (conserver la sémantique FR21 — SSE pendant un sync actif uniquement). Le snippet SSE du README sera ajusté en conséquence.
2. **Emplacement UX**: Déplacer `design_handoff_playlist_spotify/` dans `_bmad-output/planning-artifacts/ux-design/` pour qu'il devienne l'artefact UX BMad officiel (chargeable via le pattern `*ux*.md` du workflow correct-course / IR).
3. **Granularité Stories**: Réécrire les Acceptance Criteria des Stories 6.1 à 8.6 pour absorber les détails concrets du handoff (composants exacts, tokens, comportements de hover, etc.).

---

## Section 2 — Impact Analysis

### Epic Impact

| Epic | Impact | Statut |
|---|---|---|
| Epic 1 (Foundation) | ✅ Aucun — déjà livré, scaffolding compatible | Inchangé |
| Epic 2 (Auth & Config) | ⚠️ Mineur — `/config` → `/settings` redirige (déjà couvert Story 6.3) | Inchangé |
| Epic 3 (Playlists & Sync) | ⚠️ Mineur — API `GET /api/v1/playlists` doit déjà retourner `image_url` (Story 7.1) | Inchangé |
| Epic 4 (Scheduler) | ✅ Aucun | Inchangé |
| Epic 5 (Observability) | ⚠️ Mineur — UI logs alignée handoff (filtres, expand rows, status pills), **mais comportement SSE inchangé** (pendant sync actif uniquement) | AC réécrits |
| **Epic 6 (UI Foundation)** | 🔴 Majeur — tokens CSS exacts, AppShell tel que défini dans `snippets/AppShell.tsx`, composants shadcn additionnels (Accordion, DropdownMenu, Tooltip) | AC réécrits |
| **Epic 7 (Playlist Grid)** | 🔴 Majeur — composants PlaylistCard / HiddenPlaylistsAccordion tels que livrés, états hover/included/dimmed spécifiés | AC réécrits |
| **Epic 8 (Recently Added)** | 🔴 Majeur — TrackRow + hero block + sticky header tels que livrés | AC réécrits |

### Artifact Conflicts

| Artefact | Conflit | Résolution |
|---|---|---|
| `prd.md` section "UI & Visual Design" | Description haut niveau, ne mentionne pas tokens précis ni composants nommés | **Ajouter** un pointeur vers `ux-design/README.md` comme source de vérité, sans réécrire la section (PRD reste lisible à haut niveau) |
| `prd.md` FR21 | "User can view real-time sync progress during an active sync" — conforme au choix utilisateur | Inchangé |
| `architecture.md` | Mentionne déjà React Router, AppShell, shadcn/ui — pas de conflit fondamental | **Ajouter** une sous-section "Design tokens & UI primitives" pointant vers le handoff + lister les nouveaux composants shadcn requis |
| `epics.md` ligne 88 | "No UX Design document provided" | **Remplacer** par référence à `ux-design/README.md` |
| `epics.md` Stories 6.1–8.6 | AC génériques, sans référence aux specs concrètes du handoff | **Réécrire** les AC en conservant la structure Given/When/Then |
| `design_handoff_playlist_spotify/` (emplacement) | Hors structure BMad | **Déplacer** vers `_bmad-output/planning-artifacts/ux-design/` |

### Technical Impact

| Aspect | Action |
|---|---|
| `frontend/package.json` | Ajouter `react-router-dom` (l'architecture mentionne v7 mais le projet ne l'a pas encore installé) |
| Composants shadcn à ajouter | `Accordion`, `DropdownMenu`, `Tooltip`, `Sheet` (cf. `snippets/shadcn-add.sh`) |
| `frontend/src/index.css` | Remplacer le bloc `:root` par celui de `snippets/index.css` |
| `frontend/index.html` | Forcer `class="dark"` sur `<html>` |
| Lucide icons | Liste de 14 icônes spécifiques (LayoutDashboard, Clock, Settings, ScrollText, ChevronLeft/Right/Down, RotateCw, Search, Play, MoreHorizontal, Check, EyeOff, ExternalLink, Sparkles) |
| Snippet SSE du handoff (Logs route) | **À ajuster** : ouvrir l'EventSource uniquement quand un sync est actif (cohérent FR21), pas en permanence comme dans le README |

### Code Impact

- Story 1.4 / Story 6.2 ont déjà créé un `AppShell` minimal. Il sera **remplacé** par celui du handoff (pas étendu — réécriture complète, le composant snippet en est la nouvelle baseline).
- Le composant `PlaylistList` (mentionné epics.md:969) sera supprimé au profit du grid (déjà acté par Story 7.2).

---

## Section 3 — Recommended Approach

### Chemin retenu : Direct Adjustment (réorganisation backlog + enrichissement specs)

**Justification:**
- Le scope macro (Epics 6/7/8) est inchangé — le handoff précise *comment* faire, pas *quoi* faire en plus.
- Pas de remise en cause du PRD/Architecture.
- Aucun travail déjà livré (Stories 1.1–5.3) n'est invalidé.

### Effort estimé
- Application du proposal (déplacement + réécritures): **~30 min** de travail BMad
- Travail dev en aval: identique à l'estimation Epics 6/7/8 d'origine (les AC sont plus précis mais le scope ne change pas)

### Risques
- ⚠️ Le snippet SSE always-on du README pourrait être copié-collé par inadvertance. **Mitigation:** mention explicite dans Story 5.3 (AC) + commentaire dans `ux-design/README.md` lors du déplacement.

### Timeline impact
Nul — la refonte UI était déjà au planning. Le sprint actuel n'est pas en cours sur les Epics 6/7/8.

---

## Section 4 — Detailed Change Proposals

### 4.1 — Déplacement du Handoff (artefact UX)

**Action:** `git mv design_handoff_playlist_spotify _bmad-output/planning-artifacts/ux-design`

**Ajout:** un fichier `_bmad-output/planning-artifacts/ux-design/index.md` (frontmatter BMad + pointeur vers README.md) pour que le pattern `*ux*.md` du workflow le trouve.

```markdown
---
workflowType: 'ux-design'
date: '2026-05-20'
author: 'kevin (via Claude Design handoff)'
inputDocuments: ['_bmad-output/planning-artifacts/prd.md']
---

# UX Design — playlist_spotify

Ce dossier est la source de vérité UX. Voir [README.md](./README.md) pour la spec complète.

**Note SSE:** Le README contient un snippet SSE always-on dans la section Logs.
**Pour le projet, conserver la sémantique FR21**: l'EventSource est ouvert uniquement pendant un sync actif (voir Story 5.3).
```

---

### 4.2 — Mises à jour PRD

**Fichier:** `_bmad-output/planning-artifacts/prd.md`
**Section concernée:** "UI & Visual Design" (lignes 189-198)

**OLD (inchangé, conservé tel quel):** description haut niveau

**NEW (ajout en tête de section):**
```markdown
### UI & Visual Design

> 📐 **Source de vérité UX**: voir [_bmad-output/planning-artifacts/ux-design/README.md](./ux-design/README.md) pour les tokens, composants nommés, écrans, hover states et interactions.

The dashboard adopts a **Spotify Desktop-inspired visual language**:
[... reste inchangé ...]
```

**Rationale:** Garder le PRD lisible à haut niveau et redirige vers le handoff pour les détails d'implémentation.

---

### 4.3 — Mises à jour Architecture

**Fichier:** `_bmad-output/planning-artifacts/architecture.md`
**Action:** Ajouter une nouvelle sous-section après la section "Frontend Stack" (à insérer autour de la ligne 297 où sont déjà mentionnés Router et AppShell).

**NEW:**
```markdown
### Design System & UI Primitives

Source: [ux-design/README.md](./ux-design/README.md)

**Design tokens:** centralisés dans `frontend/src/index.css` (cf. `ux-design/snippets/index.css`). Tokens majeurs: `--bg-base`, `--bg-app`, `--bg-elevated`, `--accent (#1DB954)`, `--sidebar-w (248px)`, `--header-h (64px)`.

**Theme:** dark forcé (`class="dark"` sur `<html>`). Pas de toggle.

**shadcn/ui components requis** (au-delà de Button déjà présent): Accordion, DropdownMenu, Tooltip, Sheet, Input, Label, Separator. Installation via `bash ux-design/snippets/shadcn-add.sh` ou commandes individuelles `npx shadcn@latest add <component>`.

**Composants applicatifs livrés par le handoff (drop-in):**
- `frontend/src/components/AppShell.tsx` — layout grid 2 colonnes (sidebar + main)
- `frontend/src/components/PlaylistCard.tsx` — carte playlist 220px avec hover FAB
- `frontend/src/components/TrackRow.tsx` — ligne table track 6 colonnes
- `frontend/src/components/HiddenPlaylistsAccordion.tsx` — accordion shadcn collapsé par défaut

**Routes (react-router-dom):** `/` Dashboard · `/recently-added` Recently Added · `/settings` (formerly `/config`, redirige) · `/logs`. AppShell est la layout route parent.

**Icônes:** `lucide-react` exclusivement. Liste: LayoutDashboard, Clock, Settings, ScrollText, ChevronLeft, ChevronRight, ChevronDown, RotateCw, Search, Play, MoreHorizontal, Check, Eye, EyeOff, ExternalLink, Sparkles.
```

---

### 4.4 — Mises à jour `epics.md`

#### 4.4.1 — Ligne 88 — UX Design Requirements

**OLD:**
```
### UX Design Requirements

No UX Design document provided — no UX-specific requirements to extract.
```

**NEW:**
```
### UX Design Requirements

UX Design source: [ux-design/README.md](./ux-design/README.md) (Claude Design handoff, 2026-05).

**Composants drop-in fournis:** `AppShell.tsx`, `PlaylistCard.tsx`, `TrackRow.tsx`, `HiddenPlaylistsAccordion.tsx` (cf. `ux-design/snippets/`).
**Tokens CSS:** `ux-design/snippets/index.css` — à coller dans `frontend/src/index.css`.
**Shadcn additions:** `bash ux-design/snippets/shadcn-add.sh`.
**Override projet:** SSE EventSource ouvert uniquement pendant un sync actif (cf. Story 5.3 — le snippet always-on du README est inadapté).
```

#### 4.4.2 — Réécriture des AC des Stories 6.1 à 8.6

Pour ne pas faire exploser ce document, voici la **table de transformation des AC**. Les détails complets seront appliqués directement dans `epics.md` après approbation.

| Story | Changement principal des AC |
|---|---|
| **6.1** Design Tokens & Dark Theme | AC réécrits autour des tokens **exacts** du handoff (`--bg-base #0d0d0d`, `--bg-app #121212`, `--bg-elevated #1c1c1c`, `--accent #1DB954`, etc.). Ajout AC : "`<html>` porte `class='dark'` en dur, aucun toggle". |
| **6.2** AppShell v2 | AC alignés sur `snippets/AppShell.tsx`: grid outer `var(--sidebar-w) 1fr` gap 8px, sidebar avec brand block + WORKSPACE label + footer Connected-as, main area avec gradient top + topbar sticky 64px + bouton Sync Now rounded-full vert + status badge. |
| **6.3** Routes | Inchangé sur les routes mais AC précise les **icônes lucide** par item nav: `LayoutDashboard`, `Clock`, `Settings`, `ScrollText`. |
| **6.4** Desktop-First Responsive | AC inchangés sur la philosophie, mais ajoute que la sidebar utilise `var(--sidebar-w)` (248px par défaut, range 200-320 documenté). |
| **7.1** Hidden State Schema & API | Inchangé (déjà livré côté backend). Précise que la réponse `GET /api/v1/playlists` inclut `image_url` (depuis Spotify API `images[0].url`) et `track_count`. |
| **7.2** Playlist Grid Layout | AC réécrits autour de `PlaylistCard.tsx` du handoff: card 220px bg `var(--bg-elevated)`, cover square avec `border-radius 6px` + `drop-shadow 0 8px 24px rgba(0,0,0,0.5)`, badge "included" check 22×22 accent, **Play FAB** 44×44 sur hover (translateY animation), overflow menu opacity 0→1 sur hover. Grid `repeat(auto-fill, minmax(190px, 1fr))` 18px gap (mode Comfy). |
| **7.3** Hide Action | AC précisent que le menu d'overflow utilise shadcn `DropdownMenu` avec items: "Include in sync" / "Remove from sync" (toggle), "Hide playlist" / "Unhide", séparateur, "Open in Spotify" avec icône `ExternalLink`. |
| **7.4** Hidden Section | AC réécrits autour de `HiddenPlaylistsAccordion.tsx`: shadcn `Accordion` (single, collapsible), border-top 1px `var(--border-soft)`, label "Hidden playlists ({count})" h2 22px weight 800, cards en mode `dimmed` (opacity 0.55). |
| **7.5** Grid Performance | Inchangé (lazy loading) — précise `loading="lazy"` natif. |
| **8.1** Track Blacklist API | Inchangé (déjà rédigé clairement). |
| **8.2** Recently Added API | Inchangé — précise que la shape doit matcher TrackRow `{spotify_id, title, artists, album, image_url, added_at, duration_ms}`. Ajout: champ `explicit: bool` et `has_video: bool` requis pour l'affichage handoff (tags E + icône vidéo). |
| **8.3** Recently Added Page | AC réécrits autour du **hero block** spécifique (gradient accent → bg-elevated, cover 232×232, title clamp(40px, 5vw, 72px)) + **sticky header** grid 6 colonnes (`36px | minmax(220px, 4fr) | minmax(160px, 3fr) | minmax(140px, 2fr) | 60px | 40px`) + **TrackRow** tel que livré. |
| **8.4** Per-Track Blacklist Action | AC précisent l'utilisation de shadcn `DropdownMenu` avec items "Hide from Recent Adds" (icône `EyeOff`) + "Open in Spotify" (icône `ExternalLink`). Action `EyeOff` déclenche `POST /api/v1/blacklist` optimiste. |
| **8.5** Sync Filter Blacklist | Inchangé. |
| **8.6** Performance & Polish | Inchangé. |
| **5.3** Real-Time SSE | **Nouvelle clarification AC** : "L'`EventSource` est ouvert uniquement quand un sync est actif (déclenchement manuel ou notification scheduler), pas au mount permanent de la route `/logs`. Le snippet `useEffect` du handoff README qui ouvre la connexion en permanence est explicitement non-applicable au projet." |

---

### 4.5 — Aucun changement nécessaire sur

- Stories 1.1 à 5.2 (déjà livrées ou non impactées)
- Architecture sections backend (FastAPI, sync engine, scheduler, SQLite)
- PRD sections : Success Criteria, Functional Requirements, NFRs (le NFR15 reste valide)
- `claude-design-prompt.md` (prompt source ayant servi à générer le handoff — gardé pour traçabilité)

---

## Section 5 — Implementation Handoff

### Classification de scope: **Moderate**

### Recipient: bmad-dev (Amelia) après application des changements ici

### Plan d'exécution post-approval

1. **Déplacement** (`git mv`) de `design_handoff_playlist_spotify/` → `_bmad-output/planning-artifacts/ux-design/`
2. **Création** de `_bmad-output/planning-artifacts/ux-design/index.md` (wrapper BMad)
3. **Édition** `prd.md` — ajout référence UX en tête de section "UI & Visual Design"
4. **Édition** `architecture.md` — ajout sous-section "Design System & UI Primitives"
5. **Édition** `epics.md` — remplacement ligne 88 + réécriture AC Stories 5.3, 6.1, 6.2, 6.3, 6.4, 7.2, 7.3, 7.4, 8.2, 8.3, 8.4 (cf. table 4.4.2)
6. **Vérification** : lancer `bmad-check-implementation-readiness` pour confirmer l'alignement PRD ⇄ Arch ⇄ Epics ⇄ UX

### Success Criteria

- ✅ `_bmad-output/planning-artifacts/ux-design/` existe et contient le handoff
- ✅ `epics.md` ligne 88 référence le handoff
- ✅ AC des Stories 6.1–8.6 mentionnent au moins un composant ou token concret du handoff
- ✅ Story 5.3 contient une AC explicite "SSE actif uniquement pendant sync"
- ✅ `bmad-check-implementation-readiness` ne flag pas d'incohérence UX ↔ epics

### Étapes suivantes (au-delà de ce proposal)

1. `/bmad-check-implementation-readiness` (validation cross-doc)
2. `/bmad-sprint-planning` (régénération du sprint plan pour intégrer la précision UX dans la séquence)
3. Cycle d'implémentation: `CS` → `VS` → `DS` → `CR` story par story, dans l'ordre Epic 6 → 7 → 8

---

## Annexe — Liste des fichiers modifiés (récap)

| Fichier | Type d'opération |
|---|---|
| `design_handoff_playlist_spotify/` → `_bmad-output/planning-artifacts/ux-design/` | git mv |
| `_bmad-output/planning-artifacts/ux-design/index.md` | new |
| `_bmad-output/planning-artifacts/prd.md` | edit (1 paragraphe ajouté) |
| `_bmad-output/planning-artifacts/architecture.md` | edit (1 sous-section ajoutée) |
| `_bmad-output/planning-artifacts/epics.md` | edit (1 paragraphe + AC de 12 stories) |
| `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-20.md` | new (ce document) |
