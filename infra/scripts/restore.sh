#!/usr/bin/env bash
# Restauration destructive réservée à une fenêtre de maintenance.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="${SUNU_COMPOSE_FILE:-$REPO_DIR/infra/docker-compose.prod.yml}"
BACKUP_DIR="${SUNU_BACKUP_DIR:-$REPO_DIR/backups}"
TIMESTAMP="${1:-}"
[[ "$TIMESTAMP" =~ ^[0-9]{8}_[0-9]{6}$ ]] || { echo "Usage : $0 YYYYMMDD_HHMMSS --confirm-restore" >&2; exit 1; }
[[ "${2:-}" == --confirm-restore ]] || { echo "Arrêter les écritures et MinIO, puis ajouter --confirm-restore pour remplacer les données." >&2; exit 1; }
SQL_FILE="$BACKUP_DIR/postgres_$TIMESTAMP.sql"
MEDIA_FILE="$BACKUP_DIR/media_$TIMESTAMP.tar.gz"
test -s "$SQL_FILE" && test -s "$MEDIA_FILE"
# Vérifier l'archive avant toute modification de la base.
tar -tzf "$MEDIA_FILE" | awk '/^\// || /(^|\/)\.\.(\/|$)/ { bad=1 } END { exit bad }'
tar -tvzf "$MEDIA_FILE" | awk '/^[lh]/ { bad=1 } END { exit bad }'
MEDIA_DIR="$REPO_DIR/infra/volumes/media"
STAGED_DIR="$(mktemp -d "$REPO_DIR/infra/volumes/restore.XXXXXX")"
trap 'rm -rf -- "$STAGED_DIR"' EXIT
tar -xzf "$MEDIA_FILE" -C "$STAGED_DIR"
# Une erreur SQL annule la restauration, contrairement à un DROP déjà validé.
docker compose -f "$COMPOSE_FILE" exec -T db sh -c 'exec psql --set ON_ERROR_STOP=1 --single-transaction -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$SQL_FILE"
# Conserver les anciens médias pour permettre une reprise manuelle.
if [ -d "$MEDIA_DIR" ]; then
    mv -- "$MEDIA_DIR" "$MEDIA_DIR.before-restore-$(date +%s)"
fi
mv -- "$STAGED_DIR" "$MEDIA_DIR"
echo "Restauration terminée. Relancer MinIO et l'application après contrôle."
