# playlist_spotify — Claude Code Instructions

## Lancer le projet

Le projet tourne entièrement via Docker Compose :

```bash
docker-compose up          # démarre frontend (5173) + backend (8000)
docker-compose up -d       # mode détaché
docker-compose logs -f     # voir les logs en temps réel
```

**Commandes utiles :**
```bash
# Tests backend (toujours via Docker)
docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v

# Build TypeScript frontend
docker exec playlist_spotify-frontend-1 npm run build

# Ajouter un composant shadcn/ui (TOUJOURS via CLI, jamais à la main)
docker exec playlist_spotify-frontend-1 npx shadcn@latest add <component>
# ou sur hôte avec Node 22 actif :
cd frontend && npx shadcn@latest add <component>
```

## Règles de développement

### Backend
- Business logic dans `services/`, jamais dans `routers/`
- Tous les appels spotipy passent par `services/spotify.py`
- Champs JSON en snake_case partout (pas de camelCase)
- Réponses sans wrapper : array direct, pas `{"data": [...]}`

### Frontend
- TanStack Query v5 : `isPending` (pas `isLoading`), callbacks mutation dans `mutate()` ou `useMutation`
- Tous les fetch via `lib/api.ts`, jamais de `fetch()` direct dans les composants
- Alias `@/` = `frontend/src/`
- Composants shadcn : toujours via CLI (`npx shadcn@latest add <name>`)

### Tests
- Tests backend : `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`
- Pattern fixtures établi dans `test_story_2_4.py` / `test_story_3_1.py` (session + client + dependency_overrides)
- Mock des services Spotify : `patch("routers.<module>.spotify_service.<function>", ...)`

## Postman — Mise à jour obligatoire

**À chaque story qui ajoute ou modifie des routes API, mettre à jour la collection Postman.**

- Collection UID : `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`
- API Key : dans `.mcp.json` (env `POSTMAN_API_KEY`)
- Méthode : utiliser le MCP Postman (`postman` server dans `.mcp.json`) ou l'API REST directement

**Procédure :**
1. `GET https://api.getpostman.com/collections/{uid}` — récupérer la collection actuelle
2. Ajouter/modifier les requêtes dans le bon dossier
3. `PUT https://api.getpostman.com/collections/{uid}` — pousser la mise à jour
4. Vérifier avec un GET que les nouvelles routes apparaissent

Cela s'applique même si seule la shape d'une réponse change (nouveau champ, description améliorée, exemple de réponse).

## MCP Postman

Le serveur MCP Postman est configuré dans `.mcp.json`. Il est activé via `enabledMcpjsonServers` dans `.claude/settings.local.json`.

Si les outils MCP Postman ne sont pas disponibles dans la session, utiliser l'API REST directement via curl/Python avec la clé dans `.mcp.json`.
