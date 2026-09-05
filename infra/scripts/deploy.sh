#!/usr/bin/env bash
# Déployer le code présent dans ce checkout, après tests et sauvegarde.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SUNU_COMPOSE_FILE:-$SCRIPT_DIR/../docker-compose.prod.yml}"
# Construire avant de toucher aux services actuellement disponibles.
docker compose -f "$COMPOSE_FILE" build
docker compose -f "$COMPOSE_FILE" up -d db redis minio
docker compose -f "$COMPOSE_FILE" run --rm backend python manage.py check
docker compose -f "$COMPOSE_FILE" run --rm backend python manage.py check --deploy --tag security --fail-level WARNING
docker compose -f "$COMPOSE_FILE" run --rm backend python manage.py migrate --noinput
docker compose -f "$COMPOSE_FILE" up -d
echo "Services démarrés. Vérifier leur santé et le parcours de paiement avant de clore la livraison."
