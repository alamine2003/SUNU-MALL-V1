from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from ..models import Review
from ..serializers import (
    ReviewSerializer,
)
from apps.users.models import Role


class ReviewViewSet(viewsets.ModelViewSet):
    """
    Avis produits (note 1-5 + commentaire) : lecture publique pour afficher
    les avis sur la fiche produit, écriture réservée à l'auteur de l'avis
    (ou à l'admin) — un même utilisateur ne peut laisser qu'un avis par
    produit (contrainte unique_together côté modèle).
    """
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["product"]

    def get_queryset(self):
        if self.action in ["update", "partial_update", "destroy"]:
            user = self.request.user
            if user.is_authenticated and user.has_role(Role.RoleName.ADMIN):
                return Review.objects.select_related("user")
            return Review.objects.filter(user=user).select_related("user")
        return Review.objects.select_related("user")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
