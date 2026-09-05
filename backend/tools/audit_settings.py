"""Serveur HTTP instrumenté réservé à une base de charge jetable."""
import os
from config.settings.base import *  # noqa: F401,F403

if not DATABASES['default']['NAME'].startswith('sunu_load_'):
    raise RuntimeError('Les mesures exigent une base sunu_load_* dédiée.')
DEBUG = False
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'sunu-load-api']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
PAYMENT_SANDBOX = True
ANTHROPIC_API_KEY = ''
NABOOPAY_API_KEY = ''
NABOOPAY_WEBHOOK_SECRET = 'audit-local-only'
MIDDLEWARE += ['tools.audit_metrics.MetricsMiddleware']
# Laisser les protections réelles ; seul le débit de provisionnement peut
# être relevé explicitement, jamais implicitement sur le serveur applicatif.
if os.environ.get('AUDIT_PROVISIONING') == '1':
    REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
        key: '100000/hour' for key in REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
    }

if os.environ.get('AUDIT_REDIS') == '1':
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL, "KEY_PREFIX": "sunu-load"}}
