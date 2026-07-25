from rest_framework.routers import DefaultRouter
from .views import AddressViewSet, DeliveryViewSet, DriverViewSet, OrderViewSet

router = DefaultRouter()
router.register("addresses", AddressViewSet, basename="address")
router.register("drivers", DriverViewSet, basename="driver")
router.register("deliveries", DeliveryViewSet, basename="delivery")
router.register("", OrderViewSet, basename="order")

urlpatterns = router.urls
