from rest_framework.routers import DefaultRouter
from .views import ReportViewSet, TrafficStatisticViewSet, SalesStatisticViewSet

router = DefaultRouter()
router.register("reports", ReportViewSet, basename="report")
router.register("traffic", TrafficStatisticViewSet, basename="traffic-statistic")
router.register("sales", SalesStatisticViewSet, basename="sales-statistic")

urlpatterns = router.urls
