"""Douze tentatives simultanées ; à exécuter dans le serveur d'audit jetable."""
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import django
import httpx

django.setup()
from django.conf import settings  # noqa: E402

if not settings.DATABASES['default']['NAME'].startswith('sunu_load_'):
    raise RuntimeError('Base de test dédiée requise.')

barrier = Barrier(12)


def attempt(_):
    barrier.wait()
    return httpx.post('http://localhost:8000/api/auth/login/',
                      json={'email': 'rate-probe@example.test', 'password': 'invalid'},
                      timeout=20).status_code


with ThreadPoolExecutor(max_workers=12) as pool:
    print(json.dumps(dict(Counter(pool.map(attempt, range(12))))))
