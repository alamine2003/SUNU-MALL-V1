from rest_framework.routers import DefaultRouter
from .views import CartViewSet, WishlistViewSet

router = DefaultRouter()
router.register("cart", CartViewSet, basename="cart")
router.register("wishlist", WishlistViewSet, basename="wishlist")

urlpatterns = router.urls
