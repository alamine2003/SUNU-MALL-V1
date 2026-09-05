"""Charge HTTP reproductible : python -m tools.marketplace_load --output /results/baseline.json.

Exige config.settings=tools.audit_settings et une base sunu_load_* jetable.
Les comptes clients sont provisionnés hors mesure ; le parcours vendeur
utilise l'API et un lien de vérification créé comme dans l'email de test.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from threading import Barrier, Event, Lock, Thread
from time import perf_counter
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tools.audit_settings')
import django
django.setup()
from django.conf import settings
from django.db import connection, close_old_connections
from django.db.models import Sum
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
import httpx
from rest_framework_simplejwt.tokens import RefreshToken
from apps.auth.utils import email_verification_token
from apps.users.models import User, Role, UserRole
from apps.catalog.models import Inventory
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment

assert settings.DATABASES['default']['NAME'].startswith('sunu_load_')
parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://sunu-load-api:8000/api')
parser.add_argument('--output', required=True)
parser.add_argument('--clients', default='30,60,120')
args = parser.parse_args()
run_id = uuid.uuid4().hex[:10]
records = []
lock = Lock()
client = httpx.Client(timeout=40, limits=httpx.Limits(max_connections=400, max_keepalive_connections=400))


def call(method, path, token=None, payload=None, expected=(200,), phase='setup'):
    start = perf_counter()
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    try:
        response = client.request(method, args.url + path, headers=headers, json=payload)
        row = {'phase': phase, 'endpoint': path.split('?')[0], 'method': method,
               'status': response.status_code, 'ms': round((perf_counter()-start)*1000, 3),
               'sql_count': int(response.headers.get('X-Audit-Sql-Count', 0)),
               'sql_ms': float(response.headers.get('X-Audit-Sql-Ms', 0)),
               'slowest_sql_ms': float(response.headers.get('X-Audit-Slowest-Sql-Ms', 0))}
        with lock:
            records.append(row)
        if response.status_code not in expected:
            raise RuntimeError(f'{method} {path}: HTTP {response.status_code}')
        return response.json() if response.content else None
    except httpx.HTTPError as exc:
        with lock:
            records.append({'phase': phase, 'endpoint': path, 'method': method, 'status': 'timeout',
                            'ms': round((perf_counter()-start)*1000, 3), 'sql_count': 0, 'sql_ms': 0,
                            'slowest_sql_ms': 0})
        raise RuntimeError(type(exc).__name__) from exc


def fixture_user(index, role='client'):
    user = User.objects.create_user(username=f'{run_id}-{index}', email=f'{run_id}-{index}@example.test', is_verified=True)
    UserRole.objects.create(user=user, role=Role.objects.get(name=role))
    return str(RefreshToken.for_user(user).access_token), user


def seller(index, admin, category_ids):
    email = f'{run_id}-seller-{index}@example.test'
    password = uuid.uuid4().hex + '!Aa9'
    result = call('POST', '/auth/register/', payload={'email': email, 'password': password, 'role_name': 'merchant'}, expected=(201,))
    user = User.objects.get(pk=result['user']['id'])
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    call('GET', f'/auth/verify-email/?uid={uid}&token={email_verification_token.make_token(user)}')
    token = call('POST', '/auth/login/', payload={'email': email, 'password': password})['access']
    store = call('POST', '/catalog/stores/', token, {'name': f'Audit {run_id} {index}', 'city': 'Dakar'}, (201,))
    call('POST', f'/catalog/stores/{store["id"]}/approve/', admin)
    call('PATCH', f'/catalog/stores/{store["id"]}/settings/', token,
         {'min_order_amount': '0', 'business_hours': {'monday': {'open': '08:00', 'close': '20:00'}}})
    products = []
    for i in range(6):
        product = call('POST', '/catalog/products/', token,
                       {'store': store['id'], 'category': category_ids[i % len(category_ids)],
                        'name': f'Audit article {i}', 'base_price': '1000', 'status': 'draft'}, (201,))
        variant = call('POST', '/catalog/variants/', token,
                       {'product': product['id'], 'sku': f'{run_id}-{index}-{i}', 'price': '1000',
                        'initial_quantity': 2000 if i < 5 else 5}, (201,))
        call('PATCH', f'/catalog/products/{product["id"]}/', token, {'status': 'active'})
        products.append((product['id'], variant['id']))
    return store['id'], products


admin, _ = fixture_user('admin', 'admin')
categories = [call('POST', '/catalog/categories/', admin, {'name': f'Audit {run_id} {i}'}, (201,))['id'] for i in range(3)]
stores = [seller(i, admin, categories) for i in range(2)]
clients = []
for i in range(max(int(n) for n in args.clients.split(','))):
    token, user = fixture_user(i)
    address = call('POST', '/orders/addresses/', token,
                   {'label': 'Test', 'street': 'Rue test', 'city': 'Dakar', 'country': 'SN'}, (201,))
    clients.append((token, user.pk, address['id']))


def checkout(token, address, store, items, phase, expected=(201,)):
    return call('POST', '/orders/checkout/', token,
                {'checkout_key': str(uuid.uuid4()), 'store': store, 'address': address, 'delivery_type': 'pickup', 'payment_method': 'wave',
                 'items': [{'product_variant': variant, 'quantity': qty} for variant, qty in items]}, expected, phase)


def shopper(index, phase, barrier):
    token, _, address = clients[index]
    barrier.wait(timeout=30)
    for shop_index in ([0, 1] if index % 3 == 0 else [index % 2]):
        store, products = stores[shop_index]
        call('GET', f'/catalog/stores/{store}/', token, phase=phase)
        call('GET', '/catalog/categories/', token, phase=phase)
        call('GET', f'/catalog/products/?store={store}&search=Audit', token, phase=phase)
        for product, variant in products[:2]:
            call('GET', f'/catalog/products/{product}/', token, phase=phase)
            cart = call('POST', '/shopping/cart/items/', token, {'product_variant': variant, 'quantity': 1}, (201,), phase)
            item = next(line for line in cart['items'] if line['product_variant'] == variant)
            call('PATCH', f'/shopping/cart/items/{item["id"]}/', token, {'quantity': 2}, phase=phase)
        order = checkout(token, address, store, [(v, 2) for _, v in products[:2]], phase)
        payment_id = order['payment']['id']
        call('POST', f'/payments/{payment_id}/sandbox-confirm/', token, {'outcome': 'success'}, phase=phase)
        call('GET', '/orders/', token, phase=phase)
        call('GET', f'/orders/{order["id"]}/', token, phase=phase)


def batch(n, phase, work):
    barrier = Barrier(n)
    started = perf_counter()
    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(work, i, phase, barrier) for i in range(n)]
        errors = []
        for future in futures:
            try:
                future.result()
            except Exception as exc:
                errors.append(str(exc))
    return {'clients': n, 'seconds': round(perf_counter()-started, 3), 'errors': Counter(errors)}


stop = Event()
pg_samples = []

def monitor():
    try:
        while not stop.wait(.2):
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*), count(*) FILTER (WHERE state='active'), count(*) FILTER (WHERE wait_event_type='Lock') FROM pg_stat_activity WHERE datname=current_database()")
                pg_samples.append(cursor.fetchone())
    finally:
        close_old_connections()


thread = Thread(target=monitor, daemon=True)
thread.start()
def resources():
    values = dict(line.split() for line in Path('/sys/fs/cgroup/cpu.stat').read_text().splitlines())
    return {'cpu_usage_usec': int(values['usage_usec']),
            'cpu_throttled_usec': int(values['throttled_usec']),
            'memory_current_bytes': int(Path('/sys/fs/cgroup/memory.current').read_text()),
            'memory_peak_bytes': int(Path('/sys/fs/cgroup/memory.peak').read_text())}

start_resources = resources()
stages = {}
for count in map(int, args.clients.split(',')):
    stages[f'clients_{count}'] = batch(count, f'clients_{count}', shopper)
    print(json.dumps({f'clients_{count}': stages[f'clients_{count}']}), flush=True)


def race(index, phase, barrier):
    token, _, address = clients[index]
    store, products = stores[0]
    barrier.wait(timeout=30)
    result = checkout(token, address, store, [(products[-1][1], 1)], phase, (201, 400))
    if isinstance(result, dict) and 'payment' in result:
        call('POST', f'/payments/{result["payment"]["id"]}/sandbox-confirm/', token, {'outcome': 'success'}, phase=phase)


stages['last_units_30'] = batch(30, 'last_units_30', race)
stop.set()
thread.join(timeout=2)
variant_id = stores[0][1][-1][1]
inventory = Inventory.objects.get(variant_id=variant_id)
sold = OrderItem.objects.filter(product_variant_id=variant_id, order__status__in=Order.SALES_STATUSES).aggregate(total=Sum('quantity'))['total'] or 0
race_checks = {'initial': 5, 'remaining': inventory.quantity, 'reserved': inventory.reserved_quantity, 'sold': sold,
               'consistent': inventory.quantity >= 0 and inventory.reserved_quantity >= 0 and sold + inventory.quantity == 5,
               'orders': Order.objects.filter(items__product_variant_id=variant_id).count(),
               'payments': Payment.objects.filter(order__items__product_variant_id=variant_id).count()}


def percentile(values, percent):
    ordered = sorted(values)
    return ordered[min(len(ordered)-1, int((len(ordered)-1)*percent))] if ordered else 0


def summary(rows):
    return {'requests': len(rows), 'status': dict(Counter(str(r['status']) for r in rows)),
            'p50_ms': percentile([r['ms'] for r in rows], .5), 'p95_ms': percentile([r['ms'] for r in rows], .95),
            'p99_ms': percentile([r['ms'] for r in rows], .99), 'max_ms': max([r['ms'] for r in rows], default=0),
            'sql_count_max': max([r['sql_count'] for r in rows], default=0),
            'sql_ms_p95': percentile([r['sql_ms'] for r in rows], .95),
            'slowest_sql_ms': max([r['slowest_sql_ms'] for r in rows], default=0)}


for phase, stage in stages.items():
    stage.update(summary([r for r in records if r['phase'] == phase]))
    stage['requests_per_second'] = round(stage['requests']/stage['seconds'], 2)
endpoint_groups = defaultdict(list)
import re
for row in records:
    if row['phase'] != 'setup':
        endpoint_groups[row['method']+' '+re.sub(r'[0-9a-f]{8}-[0-9a-f-]{27,}', ':id', row['endpoint'])].append(row)
report = {'run_id': run_id, 'stages': stages, 'last_units': race_checks,
          'pg_max_connections': max((s[0] for s in pg_samples), default=0),
          'pg_max_active': max((s[1] for s in pg_samples), default=0),
          'pg_max_lock_waiters': max((s[2] for s in pg_samples), default=0),
          'resources_before': start_resources, 'resources_after': resources(),
          'endpoints': {key: summary(rows) for key, rows in endpoint_groups.items()}}
Path(args.output).write_text(json.dumps(report, indent=2))
print(json.dumps({'last_units': race_checks, 'output': args.output}), flush=True)
client.close()
