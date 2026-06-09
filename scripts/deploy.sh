#!/usr/bin/env bash
# Déploiement / mise à jour de l'app en production.
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE=".env.prod"
COMPOSE_FILE="docker-compose.prod.yml"

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ $ENV_FILE manquant."
  echo "   Copie le modèle puis renseigne DOMAIN :"
  echo "   cp .env.prod.example .env.prod && \$EDITOR .env.prod"
  exit 1
fi

echo "🔨 Build + (re)démarrage des conteneurs…"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build

echo "🧹 Nettoyage des images orphelines…"
docker image prune -f >/dev/null || true

echo "✅ Déployé. Statut :"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
