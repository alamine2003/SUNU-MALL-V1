from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ChatView, GenerateDescriptionView, RecommendationViewSet

router = DefaultRouter()
router.register("recommendations", RecommendationViewSet, basename="recommendation")

urlpatterns = router.urls + [
    path("generate-description/", GenerateDescriptionView.as_view(), name="ia_generate_description"),
    path("chat/", ChatView.as_view(), name="ia_chat"),
]
