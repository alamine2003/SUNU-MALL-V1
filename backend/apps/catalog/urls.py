from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, ProductViewSet, ProductVariantViewSet, ReviewViewSet,
    StoreCategoryViewSet, StoreViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("store-categories", StoreCategoryViewSet, basename="store-category")
router.register("products", ProductViewSet, basename="product")
router.register("variants", ProductVariantViewSet, basename="product-variant")
router.register("stores", StoreViewSet, basename="store")
router.register("reviews", ReviewViewSet, basename="review")

urlpatterns = router.urls
