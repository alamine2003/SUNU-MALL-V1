"""Settings pour la production. À utiliser via DJANGO_SETTINGS_MODULE=config.settings.prod"""
from decouple import config, Csv
from django.core.exceptions import ImproperlyConfigured
from .base import *  # noqa: F401,F403

DEBUG = False

if SECRET_KEY.startswith(("change-moi", "remplacez-par")) or len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY doit être défini en production.")

ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="", cast=Csv())
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS doit contenir au moins un hôte.")

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=Csv())
if not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured("CORS_ALLOWED_ORIGINS doit être défini en production.")
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default=",".join(CORS_ALLOWED_ORIGINS),
    cast=Csv(),
)

if not FRONTEND_URL.startswith("https://"):
    raise ImproperlyConfigured("FRONTEND_URL doit utiliser HTTPS en production.")

_uses_default_storage_credentials = (
    AWS_ACCESS_KEY_ID == "minioadmin" and AWS_SECRET_ACCESS_KEY == "minioadmin"
)
if _uses_default_storage_credentials:
    # Le déploiement de démonstration Railway ne fournit pas encore de service
    # S3/MinIO. Django doit néanmoins pouvoir démarrer et servir les médias du
    # conteneur. Une configuration S3 réelle reprend automatiquement la main
    # dès que les deux identifiants sont fournis.
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"
elif AWS_ACCESS_KEY_ID == "minioadmin" or AWS_SECRET_ACCESS_KEY == "minioadmin":
    raise ImproperlyConfigured(
        "MINIO_ACCESS_KEY et MINIO_SECRET_KEY doivent être configurés ensemble."
    )

if not PAYMENT_SANDBOX:
    if not NABOOPAY_API_KEY or not NABOOPAY_WEBHOOK_SECRET:
        raise ImproperlyConfigured(
            "NABOOPAY_API_KEY et NABOOPAY_WEBHOOK_SECRET sont obligatoires hors sandbox."
        )
    if not NABOOPAY_BASE_URL.startswith("https://"):
        raise ImproperlyConfigured("NABOOPAY_BASE_URL doit utiliser HTTPS hors sandbox.")

# Les compteurs de débit doivent être partagés entre tous les workers.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL, "KEY_PREFIX": "sunu-mall"}}
if EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
    raise ImproperlyConfigured("Configurer un backend email réel : les liens de vérification ne doivent pas être journalisés en production.")

# Le déploiement hébergé actuel sépare GitHub Pages et Railway. Un proxy
# same-site peut explicitement revenir à Lax, comme le Compose fourni.
AUTH_REFRESH_COOKIE_SAMESITE = config("AUTH_REFRESH_COOKIE_SAMESITE", default="None")
CSRF_COOKIE_SAMESITE = AUTH_REFRESH_COOKIE_SAMESITE
if AUTH_REFRESH_COOKIE_SAMESITE not in {"Lax", "Strict", "None"}:
    raise ImproperlyConfigured("AUTH_REFRESH_COOKIE_SAMESITE doit valoir Lax, Strict ou None.")

# Adapter au nombre de proxies fiables placés devant Django.
REST_FRAMEWORK["NUM_PROXIES"] = config("TRUSTED_PROXY_COUNT", default=1, cast=int)
