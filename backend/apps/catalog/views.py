from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db import models
from django.utils import timezone
from .models import Category, Product, ProductImage, ProductVariant, Review, Store, StoreSettings
from .serializers import (
    CategorySerializer, ProductImageSerializer, ProductSerializer, ProductVariantSerializer,
    ReviewSerializer, StoreSerializer, StoreSettingsSerializer,
)
from apps.users.permissions import IsAdmin, IsStoreOwnerOrAdmin
from apps.users.models import Role
from apps.monetization.models import Notification, SponsoredProduct
from django.core.mail import send_mail
from django.conf import settings


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
        category.image = image_file
        category.save(update_fields=["image"])
        return Response(CategorySerializer(category).data)


class ProductViewSet(viewsets.ModelViewSet):
    """
    Lecture publique (un acheteur doit pouvoir parcourir le catalogue
    sans être connecté), écriture réservée aux utilisateurs authentifiés
    (à affiner : un vendeur ne devrait modifier que ses propres produits).
    """

    queryset = Product.objects.filter(status=Product.Status.ACTIVE)
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["store", "category", "status"]
    search_fields = ["name", "description"]

    def get_permissions(self):
        # La lecture (list/retrieve/sponsored) reste publique ; seules les
        # actions qui modifient un produit précis exigent d'en être propriétaire.
        if self.action in ["update", "partial_update", "destroy", "upload_image", "delete_image"]:
            return [permissions.IsAuthenticated(), IsStoreOwnerOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.has_role(Role.RoleName.ADMIN):
            queryset = Product.objects.all()
        elif user.is_authenticated:
            queryset = Product.objects.filter(models.Q(status=Product.Status.ACTIVE) | models.Q(store__owner=user))
        else:
            queryset = Product.objects.filter(status=Product.Status.ACTIVE)

        if self.request.query_params.get("sponsored") == "true":
            today = timezone.now().date()
            sponsored_product_ids = SponsoredProduct.objects.filter(
                status=SponsoredProduct.Status.ACTIVE,
                starts_at__lte=today,
                ends_at__gte=today,
            ).values_list("product_id", flat=True)
            queryset = queryset.filter(id__in=sponsored_product_ids)

        return queryset

    def perform_create(self, serializer):
        store = serializer.validated_data.get("store")
        user = self.request.user
        if not user.has_role(Role.RoleName.ADMIN) and store.owner_id != user.id:
            raise PermissionDenied("Vous ne pouvez ajouter des produits que dans votre propre boutique.")
        serializer.save()

    @action(
        detail=True,
        methods=["post"],
        url_path="images",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_image(self, request, pk=None):
        """Upload d'une photo produit (multipart/form-data, champ 'image') vers MinIO."""
        product = self.get_object()
        image_file = request.FILES.get("image")
        if not image_file:
            return Response({"error": "Fichier 'image' requis."}, status=status.HTTP_400_BAD_REQUEST)
        position = product.images.count()
        product_image = ProductImage.objects.create(product=product, image=image_file, position=position)
        return Response(ProductImageSerializer(product_image).data, status=status.HTTP_201_CREATED)

    @upload_image.mapping.delete
    def delete_image(self, request, pk=None):
        product = self.get_object()
        image_id = request.query_params.get("image_id")
        image = get_object_or_404(ProductImage, pk=image_id, product=product)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def sponsored(self, request):
        """
        Produits actuellement mis en avant (campagne de sponsoring active),
        accessible publiquement pour alimenter les carrousels "Sponsorisé"
        de la marketplace (accueil, résultats de recherche, etc.).
        """
        today = timezone.now().date()
        sponsored_product_ids = SponsoredProduct.objects.filter(
            status=SponsoredProduct.Status.ACTIVE,
            starts_at__lte=today,
            ends_at__gte=today,
        ).values_list("product_id", flat=True)
        queryset = self.get_queryset().filter(id__in=sponsored_product_ids)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def best_sellers(self, request):
        """
        Produits les plus vendus (quantité totale commandée sur des
        commandes non annulées), pour un rail "Meilleures ventes" sur
        la marketplace. Public, comme `sponsored`.
        """
        from apps.orders.models import Order, OrderItem

        top_product_ids = list(
            OrderItem.objects.exclude(order__status=Order.Status.CANCELLED)
            .values("product_variant__product_id")
            .annotate(total_qty=models.Sum("quantity"))
            .order_by("-total_qty")
            .values_list("product_variant__product_id", flat=True)[:12]
        )
        # `filter(id__in=...)` ne préserve pas l'ordre de popularité : on le
        # ré-applique nous-mêmes après coup.
        products_by_id = {p.id: p for p in self.get_queryset().filter(id__in=top_product_ids)}
        ordered = [products_by_id[pid] for pid in top_product_ids if pid in products_by_id]
        serializer = self.get_serializer(ordered, many=True)
        return Response(serializer.data)

class ProductVariantViewSet(viewsets.ModelViewSet):
    """
    Variantes d'un produit (SKU, prix, attributs). Lecture publique pour
    permettre au panier de résoudre un product_variant ; écriture réservée
    au propriétaire de la boutique (à affiner avec une permission dédiée
    une fois le flux de gestion produit stabilisé côté frontend).
    """

    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["product"]

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsStoreOwnerOrAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        product = serializer.validated_data.get("product")
        user = self.request.user
        if not user.has_role(Role.RoleName.ADMIN) and product.store.owner_id != user.id:
            raise PermissionDenied("Vous ne pouvez ajouter des variantes qu'à vos propres produits.")
        serializer.save()


class StoreViewSet(viewsets.ModelViewSet):
    """
    Lecture publique des boutiques actives (un client doit pouvoir parcourir
    les boutiques sans être connecté) ; un commerçant voit en plus ses propres
    boutiques quel que soit leur statut ; l'admin voit tout et seul l'admin
    peut approuver/rejeter.
    """
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]

    def get_permissions(self):
        if self.action in ["approve", "reject"]:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.has_role(Role.RoleName.ADMIN):
            return Store.objects.all()
        if user.is_authenticated:
            return Store.objects.filter(models.Q(status=Store.Status.ACTIVE) | models.Q(owner=user))
        return Store.objects.filter(status=Store.Status.ACTIVE)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        store = self.get_object()
        user = self.request.user
        if not user.has_role(Role.RoleName.ADMIN) and store.owner_id != user.id:
            raise PermissionDenied("Vous ne pouvez modifier que votre propre boutique.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.has_role(Role.RoleName.ADMIN) and instance.owner_id != user.id:
            raise PermissionDenied("Vous ne pouvez supprimer que votre propre boutique.")
        instance.delete()

    def _notify_owner(self, store, subject, message):
        Notification.objects.create(
            user=store.owner,
            channel=Notification.Channel.EMAIL,
            subject=subject,
            message=message,
            status=Notification.Status.PENDING,
            metadata={"store_id": str(store.id), "store_status": store.status}
        )
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [store.owner.email],
                fail_silently=True,
            )
        except Exception:
            pass

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        store = self.get_object()
        store.status = Store.Status.ACTIVE
        store.save()
        subject = f"Boutique '{store.name}' approuvée"
        message = (
            f"Bonjour {store.owner.first_name},\n\n"
            f"Votre boutique '{store.name}' a été approuvée et est maintenant active sur SUNU MALL.\n\n"
            "Merci pour votre patience."
        )
        self._notify_owner(store, subject, message)
        serializer = self.get_serializer(store)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        store = self.get_object()
        reason = request.data.get("reason", "Votre boutique n'a pas été validée.")
        store.status = Store.Status.SUSPENDED
        store.save()
        subject = f"Boutique '{store.name}' rejetée"
        message = (
            f"Bonjour {store.owner.first_name},\n\n"
            f"Votre boutique '{store.name}' a été rejetée.\n"
            f"Raison : {reason}\n\n"
            "Merci de corriger les informations et de soumettre à nouveau."
        )
        self._notify_owner(store, subject, message)
        serializer = self.get_serializer(store)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get", "patch"], url_path="settings")
    def settings_endpoint(self, request, pk=None):
        """
        Paramètres de la boutique (horaires, montant minimum de commande),
        créés à la volée s'ils n'existent pas encore. Réservé au
        propriétaire de la boutique (ou à l'admin) — une boutique active
        reste visible en lecture publique via `get_queryset`, mais ses
        paramètres ne doivent être modifiables que par son propriétaire.
        """
        store = self.get_object()
        if not request.user.has_role(Role.RoleName.ADMIN) and store.owner_id != request.user.id:
            raise PermissionDenied("Vous ne pouvez consulter/modifier que les paramètres de votre propre boutique.")
        settings_obj, _ = StoreSettings.objects.get_or_create(store=store)
        if request.method == "PATCH":
            serializer = StoreSettingsSerializer(settings_obj, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(StoreSettingsSerializer(settings_obj).data)


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
                return Review.objects.all()
            return Review.objects.filter(user=user)
        return Review.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
