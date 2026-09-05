from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from apps.users.models import User, Role, UserRole
from .browser import COOKIE_NAME


class BrowserSessionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.user = User.objects.create_user(username='session', email='session@example.test', password='Secure-Test-Password-47!', is_verified=True)
        UserRole.objects.create(user=self.user, role=Role.objects.get(name='client'))

    def csrf(self):
        return self.client.get('/api/auth/browser/csrf/').data['csrfToken']

    def login(self):
        return self.client.post('/api/auth/browser/login/', {'email': self.user.email, 'password': 'Secure-Test-Password-47!'}, format='json', HTTP_X_CSRFTOKEN=self.csrf())

    def test_login_cookie_is_httponly_and_refresh_is_not_exposed(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['refresh'])
        self.assertTrue(response.cookies[COOKIE_NAME]['httponly'])
        self.assertEqual(response.cookies[COOKIE_NAME]['samesite'], 'Lax')
        self.assertEqual(response.cookies[COOKIE_NAME]['path'], '/api/auth/browser/')
        self.assertTrue(response.data['access'])

    def test_cookie_endpoints_require_csrf_and_reject_foreign_origin(self):
        self.assertEqual(self.client.post('/api/auth/browser/login/', {}).status_code, 403)
        self.login()
        self.assertEqual(self.client.post('/api/auth/browser/refresh/').status_code, 403)
        self.assertEqual(self.client.post('/api/auth/browser/logout/').status_code, 403)
        self.assertEqual(self.client.post('/api/auth/browser/refresh/', HTTP_X_CSRFTOKEN=self.csrf(), HTTP_ORIGIN='https://evil.example').status_code, 403)

    def test_refresh_rotates_cookie_and_logout_revokes_it(self):
        self.login()
        original = self.client.cookies[COOKIE_NAME].value
        response = self.client.post('/api/auth/browser/refresh/', HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['refresh'])
        self.assertNotEqual(original, response.cookies[COOKIE_NAME].value)
        response = self.client.post('/api/auth/browser/logout/', HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.post('/api/auth/browser/refresh/', HTTP_X_CSRFTOKEN=self.csrf()).status_code, 401)

    def test_guest_password_endpoint_cannot_reset_an_existing_password(self):
        self.client.force_authenticate(self.user)
        response = self.client.post('/api/auth/set-password/', {'password': 'AnotherStrongPassword47!'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Secure-Test-Password-47!'))
