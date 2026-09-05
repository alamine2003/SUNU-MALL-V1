"""Settings pour le développement local. Importé par défaut via manage.py."""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# DATABASES est hérité de base.py (Postgres, via infra/docker-compose.dev.yml + pgAdmin)
