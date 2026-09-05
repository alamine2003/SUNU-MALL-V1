#!/usr/bin/env bash
# Sauvegarde locale. Pour un point cohérent DB/médias, suspendre les écritures
# applicatives pendant l'opération. Les archives doivent ensuite être externalisées.
set -euo pipefail
umask 077
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="${SUNU_COMPOSE_FILE:-$REPO_DIR/infra/docker-compose.prod.yml}"
BACKUP_DIR="${SUNU_BACKUP_DIR:-$REPO_DIR/backups}"
MEDIA_DIR="$REPO_DIR/infra/volumes/media"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p -- "$BACKUP_DIR"
test -d "$MEDIA_DIR" || { echo "Volume médias absent : $MEDIA_DIR" >&2; exit 1; }
SQL_TMP="$BACKUP_DIR/postgres_$TIMESTAMP.sql.partial"
MEDIA_TMP="$BACKUP_DIR/media_$TIMESTAMP.tar.gz.partial"
trap 'rm -f -- "$SQL_TMP" "$MEDIA_TMP"' EXIT
docker compose -f "$COMPOSE_FILE" exec -T db sh -c 'exec pg_dump --clean --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$SQL_TMP"
tar -czf "$MEDIA_TMP" -C "$MEDIA_DIR" .
mv -- "$SQL_TMP" "$BACKUP_DIR/postgres_$TIMESTAMP.sql"
mv -- "$MEDIA_TMP" "$BACKUP_DIR/media_$TIMESTAMP.tar.gz"
echo "Sauvegarde créée : $BACKUP_DIR ($TIMESTAMP)"
