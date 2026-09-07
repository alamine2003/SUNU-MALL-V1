"""
Tests unitaires pour l'application auth.
"""
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User, Role, UserRole
from apps.auth.utils import email_verification_token, send_verification_email
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes


class AuthTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        """
        Configuration initiale des tests.
        """
        self.client = APIClient()
        self.register_url = reverse('auth_register')
        self.login_url = reverse('auth_login')
        self.verify_email_url = reverse('auth_verify_email')
        self.resend_verification_url = reverse('auth_resend_verification')
        self.guest_checkout_url = reverse('auth_guest_checkout')
        self.token_url = reverse('token_obtain_pair')
        self.token_refresh_url = reverse('token_refresh')
        self.token_verify_url = reverse('token_verify')
        self.token_blacklist_url = reverse('token_blacklist')
        
        # Créer les rôles par défaut
        Role.objects.get_or_create(name=Role.RoleName.CLIENT)
        Role.objects.get_or_create(name=Role.RoleName.MERCHANT)
        Role.objects.get_or_create(name=Role.RoleName.DRIVER)
        Role.objects.get_or_create(name=Role.RoleName.ADMIN)

    def create_user_with_role(self, *, email='test@example.com', password='testpassword123',
                              role_name=Role.RoleName.CLIENT, is_verified=False,
                              is_active=True, username='testuser'):
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=is_active,
        )
        user.is_verified = is_verified
        user.save()
        role = Role.objects.get(name=role_name)
        UserRole.objects.create(user=user, role=role)
        return user

    def test_register_user_success(self):
        """
        Teste l'inscription réussie d'un utilisateur.
        """
        data = {
            'email': 'test@example.com',
            'password': 'testpassword123',
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '+221771234567',
            'role_name': 'client'
        }

        with patch('apps.auth.views.send_verification_email') as mocked_send:
            response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIsNone(response.data['access'])
        self.assertIsNone(response.data['refresh'])
        self.assertTrue(response.data['verification_required'])
        self.assertEqual(response.data['user']['email'], data['email'])
        self.assertEqual(response.data['user']['roles'], ['client'])
        mocked_send.assert_called_once()
        
        user = User.objects.get(email=data['email'])
        self.assertFalse(user.is_verified)
        self.assertTrue(user.check_password(data['password']))

    def test_register_user_missing_fields(self):
        """
        Teste l'inscription avec des champs manquants.
        """
        data = {
            'email': 'test@example.com',
            # Mot de passe manquant
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    @override_settings(
        EMAIL_DELIVERY_ENABLED=False,
        EMAIL_VERIFICATION_REQUIRED=False,
    )
    def test_register_auto_verifies_when_email_is_unavailable(self):
        with patch('apps.auth.views.send_verification_email') as mocked_send:
            response = self.client.post(self.register_url, {
                'email': 'email-down@example.com',
                'password': 'testpassword123',
                'first_name': 'Email',
                'last_name': 'Down',
                'phone': '+221771234568',
                'role_name': 'client',
            }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['verification_required'])
        self.assertTrue(User.objects.get(email='email-down@example.com').is_verified)
        mocked_send.assert_not_called()

    @override_settings(
        EMAIL_DELIVERY_ENABLED=False,
        EMAIL_VERIFICATION_REQUIRED=True,
    )
    def test_register_returns_503_when_verification_is_explicitly_required(self):
        response = self.client.post(self.register_url, {
            'email': 'verification-required@example.com',
            'password': 'testpassword123',
            'first_name': 'Email',
            'last_name': 'Required',
            'phone': '+221771234569',
            'role_name': 'client',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(User.objects.filter(email='verification-required@example.com').exists())

    @override_settings(EMAIL_DELIVERY_ENABLED=False)
    def test_resend_returns_503_for_any_email_when_delivery_is_unavailable(self):
        response = self.client.post(
            self.resend_verification_url,
            {'email': 'unknown@example.com'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_register_cannot_assign_an_admin_role(self):
        response = self.client.post(self.register_url, {
            'email': 'attacker@example.com',
            'password': 'testpassword123',
            'first_name': 'Attacker',
            'role_name': 'admin',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email='attacker@example.com').exists())

    def test_login_user_unverified(self):
        """
        Teste la connexion avec un email non vérifié.
        """
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        role = Role.objects.get(name=Role.RoleName.CLIENT)
        UserRole.objects.create(user=user, role=role)
        
        data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)

    def test_login_user_verified(self):
        """
        Teste la connexion avec un email vérifié.
        """
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        user.is_verified = True
        user.save()
        
        role = Role.objects.get(name=Role.RoleName.CLIENT)
        UserRole.objects.create(user=user, role=role)
        
        data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], data['email'])

    def test_login_wrong_password(self):
        """
        Teste la connexion avec un mauvais mot de passe.
        """
        self.create_user_with_role(is_verified=True)

        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_login_nonexistent_user(self):
        """
        Teste la connexion avec un utilisateur inexistant.
        """
        data = {
            'email': 'nonexistent@example.com',
            'password': 'wrongpassword'
        }

        response = self.client.post(self.login_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_login_inactive_user(self):
        """
        Teste la connexion avec un utilisateur inactif.
        """
        self.create_user_with_role(
            is_verified=True,
            is_active=False,
            email='inactive@example.com',
            username='inactiveuser',
        )

        response = self.client.post(self.login_url, {
            'email': 'inactive@example.com',
            'password': 'testpassword123'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_token_obtain_pair_user_unverified(self):
        """
        Teste que l'endpoint SimpleJWT refuse un utilisateur non vérifié.
        """
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )

        response = self.client.post(self.token_url, {
            'email': user.email,
            'password': 'testpassword123'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data['detail'],
            "Veuillez vérifier votre email avant de vous connecter."
        )

    def test_token_obtain_pair_user_verified(self):
        """
        Teste que l'endpoint SimpleJWT fonctionne pour un utilisateur vérifié.
        """
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        user.is_verified = True
        user.save()

        response = self.client.post(self.token_url, {
            'email': user.email,
            'password': 'testpassword123'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_token_refresh_success(self):
        """
        Teste le refresh d'un JWT valide.
        """
        user = self.create_user_with_role(
            is_verified=True,
            email='refresh@example.com',
            username='refreshuser',
        )

        token_response = self.client.post(self.token_url, {
            'email': user.email,
            'password': 'testpassword123'
        }, format='json')

        response = self.client.post(self.token_refresh_url, {
            'refresh': token_response.data['refresh']
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_token_verify_success(self):
        """
        Teste la vérification d'un access token valide.
        """
        user = self.create_user_with_role(
            is_verified=True,
            email='verifytoken@example.com',
            username='verifytokenuser',
        )

        token_response = self.client.post(self.token_url, {
            'email': user.email,
            'password': 'testpassword123'
        }, format='json')

        response = self.client.post(self.token_verify_url, {
            'token': token_response.data['access']
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_token_blacklist_revokes_refresh_token(self):
        """
        Teste la mise en blacklist d'un refresh token.
        """
        user = self.create_user_with_role(
            is_verified=True,
            email='blacklist@example.com',
            username='blacklistuser',
        )

        token_response = self.client.post(self.token_url, {
            'email': user.email,
            'password': 'testpassword123'
        }, format='json')
        refresh_token = token_response.data['refresh']

        blacklist_response = self.client.post(self.token_blacklist_url, {
            'refresh': refresh_token
        }, format='json')
        refresh_response = self.client.post(self.token_refresh_url, {
            'refresh': refresh_token
        }, format='json')

        self.assertEqual(blacklist_response.status_code, status.HTTP_200_OK)
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_verify_email_success(self):
        """
        Teste la vérification d'email réussie.
        """
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
        
        response = self.client.get(self.verify_email_url, {'uid': uid, 'token': token})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        user.refresh_from_db()
        self.assertTrue(user.is_verified)

    def test_verify_email_same_token_reused_after_verified_is_idempotent(self):
        """
        Un second appel avec le même lien, une fois le compte déjà vérifié,
        renvoie un succès (idempotent) plutôt qu'une erreur — sans ça, un
        double déclenchement légitime (React StrictMode en dev, un client
        mail qui pré-visite le lien pour le scanner) affiche à tort un échec
        alors que la vérification a bien eu lieu.
        """
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)

        first_response = self.client.get(self.verify_email_url, {'uid': uid, 'token': token})
        second_response = self.client.get(self.verify_email_url, {'uid': uid, 'token': token})

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertIn('message', second_response.data)

    def test_verify_email_invalid_token(self):
        """
        Teste la vérification d'email avec un token invalide.
        """
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        invalid_token = 'invalidtoken123'
        
        response = self.client.get(self.verify_email_url, {'uid': uid, 'token': invalid_token})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        
        user.refresh_from_db()
        self.assertFalse(user.is_verified)

    def test_verify_email_expired_token(self):
        """
        Teste la vérification d'email avec un token expiré.
        """
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
        current_seconds = email_verification_token._num_seconds(email_verification_token._now())

        with patch.object(
            email_verification_token,
            '_num_seconds',
            return_value=current_seconds + settings.PASSWORD_RESET_TIMEOUT + 1,
        ):
            response = self.client.get(self.verify_email_url, {'uid': uid, 'token': token})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

        user.refresh_from_db()
        self.assertFalse(user.is_verified)

    def test_resend_verification_email(self):
        """
        Teste le renvoi de l'email de vérification.
        """
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        
        data = {'email': 'test@example.com'}
        with patch('apps.auth.views.send_verification_email') as mocked_send:
            response = self.client.post(self.resend_verification_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        mocked_send.assert_called_once_with(user)

    def test_resend_verification_email_already_verified(self):
        """
        Teste le renvoi de l'email pour un utilisateur déjà vérifié.
        """
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        user.is_verified = True
        user.save()
        
        data = {'email': 'test@example.com'}
        response = self.client.post(self.resend_verification_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)

    def test_guest_checkout_cannot_take_over_an_existing_guest_account(self):
        guest = User.objects.create_user(
            username='guest@example.com', email='guest@example.com',
            first_name='Original',
        )
        guest.set_unusable_password()
        guest.save(update_fields=['password'])

        response = self.client.post(self.guest_checkout_url, {
            'email': guest.email,
            'first_name': 'Attacker',
            'phone': '+221770000000',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        guest.refresh_from_db()
        self.assertEqual(guest.first_name, 'Original')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_verification_email_helper(self):
        """
        Teste l'envoi réel de l'email de vérification via le helper existant.
        """
        user = User(
            username='testuser',
            email='test@example.com',
            first_name='Test'
        )

        send_verification_email(user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Vérifiez votre email - SUNU MALL")
        self.assertIn('/verify-email?uid=', mail.outbox[0].body)


class EmailCaseRegressionTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()

    def test_registration_normalizes_email_and_allows_mixed_case_login(self):
        response = self.client.post(reverse("auth_register"), {
            "email": "Alice@Example.com", "password": "testpassword123", "first_name": "Alice",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="alice@example.com")
        user.is_verified = True
        user.save(update_fields=["is_verified"])
        response = self.client.post(reverse("auth_login"), {
            "email": "ALICE@example.com", "password": "testpassword123",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["user"]["id"]), str(user.pk))

    def test_legacy_email_works_for_both_login_endpoints_and_resend(self):
        user = User.objects.create_user(username="legacy", email="Alice@example.com", password="testpassword123")
        with patch("apps.auth.views.send_verification_email") as send:
            response = self.client.post(reverse("auth_resend_verification"), {"email": "alice@example.com"})
        self.assertEqual(response.status_code, 200)
        send.assert_called_once_with(user)
        user.is_verified = True
        user.save(update_fields=["is_verified"])
        for route in ("auth_login", "token_obtain_pair"):
            response = self.client.post(reverse(route), {"email": "alice@example.com", "password": "testpassword123"})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertIn("access", response.data)

    def test_case_variants_cannot_register_or_create_a_guest_over_existing_email(self):
        User.objects.create_user(username="legacy", email="Alice@example.com", password="testpassword123")
        for route in ("auth_register", "auth_guest_checkout"):
            response = self.client.post(reverse(route), {
                "email": "alice@example.com", "password": "testpassword123", "first_name": "Alice", "phone": "771234567",
            }, format="json")
            self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.filter(email__iexact="alice@example.com").count(), 1)

    def test_legacy_case_collision_never_selects_an_arbitrary_account(self):
        from apps.auth.emails import utilisateur_par_email
        first = User.objects.create_user(username="first", email="Alice@example.com")
        second = User.objects.create_user(username="second", email="alice@example.com")
        self.assertEqual(utilisateur_par_email("Alice@example.com"), first)
        self.assertEqual(utilisateur_par_email("alice@example.com"), second)
        self.assertIsNone(utilisateur_par_email("ALICE@example.com"))
