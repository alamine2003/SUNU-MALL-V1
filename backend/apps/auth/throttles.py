"""Limite des actions sensibles partagée et atomique entre workers Redis."""
from functools import lru_cache
from hashlib import sha256
from django.conf import settings
from redis import Redis, RedisError
from rest_framework.exceptions import APIException
from rest_framework.throttling import ScopedRateThrottle

# Fenêtre fixe depuis la première tentative. INCR + EXPIRE atomiques,
# contrairement au cycle lecture/modification/écriture du throttle DRF.
COUNTER_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {count, redis.call('TTL', KEYS[1])}
"""


@lru_cache(maxsize=2)
def client(url):
    return Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)


class AtomicScopedRateThrottle(ScopedRateThrottle):
    def allow_request(self, request, view):
        self.scope = getattr(view, self.scope_attr, None)
        if not self.scope:
            return True
        if settings.CACHES['default']['BACKEND'] != 'django.core.cache.backends.redis.RedisCache':
            return super().allow_request(request, view)
        self.rate = self.get_rate()
        if self.rate is None:
            return True
        self.num_requests, self.duration = self.parse_rate(self.rate)
        identity = str(request.user.pk) if request.user.is_authenticated else self.get_ident(request)
        key = 'sunu:throttle:' + sha256(f'{self.scope}:{identity}'.encode()).hexdigest()
        try:
            count, ttl = client(settings.REDIS_URL).eval(COUNTER_SCRIPT, 1, key, self.duration)
        except RedisError as exc:
            error = APIException('Le service est momentanément indisponible.')
            error.status_code = 503
            raise error from exc
        self.retry_after = max(ttl, 1)
        return count <= self.num_requests

    def wait(self):
        if hasattr(self, 'retry_after'):
            return self.retry_after
        return super().wait()
