---
workflowType: 'ux-design'
date: '2026-05-20'
author: 'kevin (via Claude Design handoff)'
inputDocuments: ['_bmad-output/planning-artifacts/prd.md']
status: 'approved'
---

# UX Design — playlist_spotify

Ce dossier est la **source de vérité UX** pour le projet. Il a été produit par Claude Design à partir du brief `_bmad-output/planning-artifacts/claude-design-prompt.md` et intégré en tant qu'artefact BMad le 2026-05-20 via le workflow `bmad-correct-course` (cf. `sprint-change-proposal-2026-05-20.md`).

## Contenu

- **[README.md](./README.md)** — spec UX complète : 5 écrans, tokens CSS, composants, interactions, state management
- **`prototype/`** — prototype HTML/JSX interactif (référence visuelle de vérité)
- **`snippets/`** — fichiers TSX drop-in production-ready :
  - `index.css` — design tokens
  - `AppShell.tsx`, `PlaylistCard.tsx`, `TrackRow.tsx`, `HiddenPlaylistsAccordion.tsx` — composants
  - `shadcn-add.sh` — script d'installation des composants shadcn manquants

## Override projet — SSE Logs

⚠️ Le snippet `useEffect` de la section **Logs route** dans le README ouvre l'`EventSource` en permanence au mount de la route :

```tsx
useEffect(() => {
  const es = new EventSource('/api/logs/stream');
  // ...
}, []);
```

**Pour ce projet, conserver la sémantique FR21 du PRD** : l'`EventSource` est ouvert **uniquement pendant un sync actif** (déclenchement manuel ou émission scheduler), pas en permanence. Voir Story 5.3 dans `epics.md`.

## Décisions de variants ("Tweaks")

Conformément au README section "Variants" :
- Accent : `#1DB954` (Spotify green)
- Grid density : Comfy (`minmax(190px, 1fr)`, 18px gap)
- Sidebar width : 248px
- Hidden section : collapsed par défaut

Le panneau Tweaks du prototype **n'est pas embarqué** en prod.
