from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import FormParser, MultiPartParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from ..models import Category, Product, Store, StoreCategory
from ..serializers import (
    CategorySerializer, StoreCategorySerializer,
)
from apps.users.permissions import IsAdmin
from .helpers import _validate_image_upload


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = []

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "upload_image"]:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return super().get_permissions()

    @action(detail=False, methods=["get"], url_path="store-counts")
    def store_counts(self, request):
        """
        GET /api/catalog/categories/store-counts/
        Nombre de boutiques actives ayant au moins un produit actif dans
        chaque catégorie — pour le filtre par catégorie de la page
        boutiques. N'affiche que les catégories réellement représentées
        (aucune catégorie vide inventée).
        """
        categories = (
            Category.objects.annotate(
                store_count=models.Count(
                    "products__store",
                    filter=models.Q(products__status=Product.Status.ACTIVE, products__store__status=Store.Status.ACTIVE),
                    distinct=True,
                )
            )
            .filter(store_count__gt=0)
            .order_by("name")
        )
        return Response([{"id": c.id, "name": c.name, "store_count": c.store_count} for c in categories])

    @action(
        detail=True,
        methods=["post"],
        url_path="image",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_image(self, request, pk=None):
        """Visuel de la tuile de catégorie (accueil, page catégories). Admin uniquement."""
        category = self.get_object()
        image_file = request.FILES.get("image")
        if not image_file:
            return Response({"error": "Fichier 'image' requis."}, status=status.HTTP_400_BAD_REQUEST)
        image_file = _validate_image_upload(image_file)
        category.image = image_file
        category.save(update_fields=["image"])
        return Response(CategorySerializer(category).data)



class StoreCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Catégories de boutique (Électronique, Mode, ...) — lecture publique, pour le formulaire de création de boutique."""
    queryset = StoreCategory.objects.all().order_by("name")
    serializer_class = StoreCategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
