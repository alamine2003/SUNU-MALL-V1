"""
Routes principales de l'API SUNU MALL.
Chaque app expose ses propres routes dans son fichier urls.py —
on les inclut ici sous un préfixe clair.
"""
from django.contrib import admin
from django.conf import settings
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import (
    SpectacularJSONAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

def health(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/", include("apps.auth.urls")),
    path("api/users/", include("apps.users.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/orders/", include("apps.orders.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/shopping/", include("apps.shopping.urls")),
    path("api/monetization/", include("apps.monetization.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/ia/", include("apps.ia.urls")),
    # Swagger/OpenAPI Documentation
    path("api/schema/", SpectacularJSONAPIView.as_view(), name="schema"),
    path("api/schema.json", SpectacularJSONAPIView.as_view(), name="schema-json"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema-json"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.STORAGES["default"]["BACKEND"] == "django.core.files.storage.FileSystemStorage":
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
