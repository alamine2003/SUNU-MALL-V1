"""Charge de lecture pendant la vérification du navigateur, base d'audit seule."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tools.audit_settings')
import django
django.setup()
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import monotonic
from collections import Counter
import httpx
from apps.users.models import User
from rest_framework_simplejwt.tokens import AccessToken

users = list(User.objects.filter(email__endswith='@example.test')[:30])
barrier = Barrier(len(users))

def work(user):
    token = str(AccessToken.for_user(user))
    codes = Counter()
    with httpx.Client(timeout=15) as client:
        barrier.wait()
        until = monotonic() + 25
        while monotonic() < until:
            response = client.get('http://localhost:8000/api/catalog/products/', headers={'Authorization': f'Bearer {token}'})
            codes[response.status_code] += 1
    return codes

with ThreadPoolExecutor(max_workers=len(users)) as pool:
    print(dict(sum(pool.map(work, users), Counter())), flush=True)
