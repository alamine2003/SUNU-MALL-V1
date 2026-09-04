from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import NabooPayWebhookView, PaymentViewSet, RefundViewSet

router = DefaultRouter()
# IMPORTANT : "refunds" doit être enregistré avant le préfixe vide "" —
# sinon la route détail attrape-tout de PaymentViewSet (`^(?P<pk>...)/$`)
# intercepterait /payments/refunds/ avant d'atteindre RefundViewSet.
router.register("refunds", RefundViewSet, basename="refund")
router.register("", PaymentViewSet, basename="payment")

urlpatterns = [
    path("webhooks/naboopay/", NabooPayWebhookView.as_view(), name="naboopay-webhook"),
    *router.urls,
]
