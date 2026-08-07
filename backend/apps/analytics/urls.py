from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ReportViewSet, TrafficStatisticViewSet, SalesStatisticViewSet, StoreSummaryView

router = DefaultRouter()
router.register("reports", ReportViewSet, basename="report")
router.register("traffic", TrafficStatisticViewSet, basename="traffic-statistic")
router.register("sales", SalesStatisticViewSet, basename="sales-statistic")

urlpatterns = [
    path("store-summary/", StoreSummaryView.as_view(), name="store_summary"),
    *router.urls,
]
