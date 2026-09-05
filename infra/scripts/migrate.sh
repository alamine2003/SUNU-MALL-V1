#!/usr/bin/env bash
# Appliquer les migrations versionnées ; leur génération reste une étape de développement.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SUNU_COMPOSE_FILE:-$SCRIPT_DIR/../docker-compose.dev.yml}"
docker compose -f "$COMPOSE_FILE" exec -T backend python manage.py migrate --noinput
