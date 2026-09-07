# =========================================================
# SUNU MALL — Backend (Django + DRF + Celery + app IA)
# Build multi-stage : pas de compilateurs ni de caches pip
# dans l'image finale, juste le code + les libs nécessaires.
# =========================================================

# ---- Stage 1 : build des dépendances ----
FROM python:3.12-slim AS builder

WORKDIR /app

# Dépendances système nécessaires UNIQUEMENT à la compilation
# (psycopg2, Pillow, etc. en ont besoin pour builder leurs wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/

# On choisit le fichier de requirements selon l'environnement.
# base.txt = Django/DRF/Celery/Redis/Postgres (toujours nécessaire)
# ia.txt   = libs IA (souvent lourdes : numpy, torch, transformers...)
# dev.txt  = outils de dev (pytest, flake8...), jamais en prod
ARG REQUIREMENTS_FILE=requirements/base.txt
RUN python -m pip install --no-cache-dir --upgrade 'pip>=26.2,<27' \
    && pip install --no-cache-dir --user -r ${REQUIREMENTS_FILE} \
    && python -c "import drf_spectacular"

# ---- Stage 2 : image finale, légère ----
FROM python:3.12-slim

WORKDIR /app

# Seulement les libs système nécessaires À L'EXÉCUTION (pas à la compilation)
RUN python -m pip install --no-cache-dir --upgrade 'pip>=26.2,<27'
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# On récupère uniquement les packages Python déjà compilés, pas les outils de build
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY . .

EXPOSE 8000

# En dev, ce CMD est écrasé par docker-compose (reload activé). En production,
# les migrations doivent réussir avant l'ouverture du port : le service ne
# peut ainsi jamais paraître sain avec un schéma de base de données absent.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_demo_catalog --if-empty && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2}"]
