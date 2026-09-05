"""Session web : refresh en cookie HttpOnly, access token uniquement en mémoire.

Les routes JWT JSON restent disponibles pour les clients non navigateur.
Toutes les écritures utilisant des cookies passent le contrôle CSRF Django.
"""
from django.conf import settings
from django.middleware.csrf import get_token, rotate_token
from rest_framework.authentication import SessionAuthentication
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .views import LoginView, GuestCheckoutView
from apps.users.models import User

COOKIE_NAME = 'sunu_refresh'
COOKIE_PATH = '/api/auth/browser/'


def set_refresh_cookie(response, token):
    response.set_cookie(COOKIE_NAME, token, httponly=True,
                        secure=settings.SESSION_COOKIE_SECURE, samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
                        path=COOKIE_PATH, max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()))
    response['Cache-Control'] = 'no-store'


class BrowserSessionMixin:
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        SessionAuthentication().enforce_csrf(request)
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200 and response.data.get('refresh'):
            token = response.data['refresh']
            response.data['refresh'] = None
            rotate_token(request)
            set_refresh_cookie(response, token)
        return response


class BrowserLoginView(BrowserSessionMixin, LoginView):
    pass


class BrowserGuestView(BrowserSessionMixin, GuestCheckoutView):
    pass


class BrowserCsrfView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        response = Response({'csrfToken': get_token(request)})
        response['Cache-Control'] = 'no-store'
        return response


class BrowserRefreshView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth_refresh'

    def get_authenticate_header(self, request):
        return 'Bearer'

    def post(self, request):
        SessionAuthentication().enforce_csrf(request)
        raw = request.COOKIES.get(COOKIE_NAME)
        if not raw:
            raise InvalidToken('Session expirée.')
        serializer = TokenRefreshSerializer(data={'refresh': raw})
        try:
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            token = RefreshToken(data['refresh'])
            user = User.objects.get(pk=token['user_id'], is_active=True)
        except (TokenError, User.DoesNotExist) as exc:
            raise InvalidToken('Session expirée.') from exc
        response = Response({
            'access': data['access'], 'refresh': None,
            'user': {'id': user.pk, 'email': user.email, 'first_name': user.first_name,
                     'last_name': user.last_name, 'phone': user.phone,
                     'roles': list(user.user_roles.values_list('role__name', flat=True)),
                     'is_verified': user.is_verified, 'has_password': user.has_usable_password()},
        })
        set_refresh_cookie(response, data['refresh'])
        return response


class BrowserLogoutView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth_refresh'

    def post(self, request):
        SessionAuthentication().enforce_csrf(request)
        raw = request.COOKIES.get(COOKIE_NAME)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass
        response = Response(status=204)
        response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH, samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE)
        response['Cache-Control'] = 'no-store'
        return response
