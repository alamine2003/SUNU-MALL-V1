from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from redis import ConnectionError
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from .throttles import AtomicScopedRateThrottle


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': 'redis://localhost:6379/15'}})
class SensitiveThrottleTests(SimpleTestCase):
    def setUp(self):
        self.request = Request(APIRequestFactory().post('/api/auth/login/'))
        self.view = type('Login', (), {'throttle_scope': 'auth_login'})()

    @patch('apps.auth.throttles.client')
    def test_exact_limit_and_retry_after(self, client):
        throttle = AtomicScopedRateThrottle()
        client.return_value.eval.side_effect = [[10, 53], [11, 52]]
        self.assertTrue(throttle.allow_request(self.request, self.view))
        self.assertFalse(throttle.allow_request(self.request, self.view))
        self.assertEqual(throttle.wait(), 52)

    @patch('apps.auth.throttles.client')
    def test_redis_outage_fails_closed(self, client):
        client.return_value.eval.side_effect = ConnectionError('private connection details')
        with self.assertRaises(APIException) as caught:
            AtomicScopedRateThrottle().allow_request(self.request, self.view)
        self.assertEqual(caught.exception.status_code, 503)
        self.assertNotIn('private', str(caught.exception))
