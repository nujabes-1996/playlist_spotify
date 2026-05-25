#!/usr/bin/env bash
# Vide la BDD pour relancer un sync depuis zéro.
# Conserve : config.client_id, config.client_secret, config.spotify_token_json,
#            config.playlist_size, config.cron_expr.
# Reset    : playlist, sync_log, track_blacklist, apscheduler_jobs,
#            config.dynamic_playlist_id, config.last_sync_at.
#
# Usage : ./scripts/reset_db.sh

set -euo pipefail

CONTAINER="playlist_spotify-backend-1"
DB_PATH="/data/app.db"

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  echo "❌ Container ${CONTAINER} is not running. Start it with: docker-compose up -d"
  exit 1
fi

echo "📦 Backing up DB to /data/app.db.bak inside the container..."
docker exec "${CONTAINER}" cp "${DB_PATH}" "${DB_PATH}.bak"

echo "🧹 Wiping playlists, sync logs, blacklist, scheduler jobs..."
docker exec "${CONTAINER}" /app/.venv/bin/python - <<'PY'
import sqlite3

conn = sqlite3.connect("/data/app.db")
cur = conn.cursor()

# Tables vidées intégralement.
for table in ("playlist", "sync_log", "track_blacklist", "apscheduler_jobs"):
    cur.execute(f"DELETE FROM {table}")
    print(f"  - {table}: {cur.rowcount} rows deleted")

# Config : on garde client_id/secret/token/playlist_size/cron_expr,
# on remet à zéro l'état lié au playlist dynamique.
cur.execute("""
    UPDATE config
    SET dynamic_playlist_id = NULL,
        last_sync_at = NULL
""")
print(f"  - config: {cur.rowcount} row(s) reset (token preserved)")

conn.commit()
conn.close()
print("✅ Database reset complete.")
PY

echo ""
echo "🎵 Spotify token preserved. Relance un sync via l'UI ou:"
echo "   curl -X POST http://localhost:8000/api/v1/sync"
