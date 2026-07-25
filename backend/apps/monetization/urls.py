from rest_framework.routers import DefaultRouter
from .views import (
    NotificationViewSet, SubscriptionPlanViewSet, SubscriptionViewSet,
    InvoiceViewSet, SponsoredProductViewSet,
)

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")
router.register("subscription-plans", SubscriptionPlanViewSet, basename="subscription-plan")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("sponsored-products", SponsoredProductViewSet, basename="sponsored-product")

urlpatterns = router.urls
