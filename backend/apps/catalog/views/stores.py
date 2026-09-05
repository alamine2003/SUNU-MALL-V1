from rest_framework import viewsets, permissions, filters, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from django.db.models.functions import Coalesce
from ..models import Product, Review, Store, StoreSettings
from ..serializers import (
    StoreSerializer, StoreSettingsSerializer,
)
from apps.users.permissions import IsAdmin, IsMerchantOrAdmin
from apps.users.models import Role
from apps.monetization.models import Notification
from .helpers import _validate_image_upload


class StoreViewSet(viewsets.ModelViewSet):
    """
    Lecture publique des boutiques actives (un client doit pouvoir parcourir
    les boutiques sans être connecté) ; un commerçant voit en plus ses propres
    boutiques quel que soit leur statut ; l'admin voit tout et seul l'admin
    peut approuver/rejeter.
    """
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "owner"]
    search_fields = ["name"]
    ordering_fields = ["created_at", "name", "rating"]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.action == "create":
            return [IsMerchantOrAdmin()]
        if self.action in ["approve", "reject"]:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.has_role(Role.RoleName.ADMIN):
            qs = Store.objects.all()
        elif user.is_authenticated:
            qs = Store.objects.filter(models.Q(status=Store.Status.ACTIVE) | models.Q(owner=user))
        else:
            qs = Store.objects.filter(status=Store.Status.ACTIVE)

        # Sous-requêtes indépendantes (plutôt qu'un simple .annotate(Avg(...))
        # sur le queryset principal) : le filtre product_category ci-dessous
        # joint aussi via `products`, et cumuler les deux joins gonflerait
        # artificiellement la moyenne/le compte d'avis (fan-out de jointure).
        review_qs = Review.objects.filter(product__store=models.OuterRef("pk"))
        rating_subquery = review_qs.values("product__store").annotate(avg=models.Avg("rating")).values("avg")
        count_subquery = review_qs.values("product__store").annotate(cnt=models.Count("id")).values("cnt")
        qs = qs.annotate(
            rating=models.Subquery(rating_subquery[:1], output_field=models.FloatField()),
            review_count=Coalesce(
                models.Subquery(count_subquery[:1], output_field=models.IntegerField()), 0
            ),
        )

        category_id = self.request.query_params.get("product_category")
        if category_id:
            category_id = serializers.IntegerField(min_value=1).run_validation(category_id)
            qs = qs.filter(products__category_id=category_id, products__status=Product.Status.ACTIVE).distinct()

        return qs.select_related('owner', 'category').prefetch_related(
            models.Prefetch('products', queryset=Product.objects.filter(status=Product.Status.ACTIVE, category__isnull=False).select_related('category').only('id', 'store_id', 'category_id', 'category__name'), to_attr='category_products'),
        )

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
        instance.status = Store.Status.INACTIVE
        instance.save(update_fields=["status", "updated_at"])

    @action(
        detail=True,
        methods=["post"],
        url_path="logo",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_logo(self, request, pk=None):
        """Photo de profil de la boutique — réservée au propriétaire (ou à l'admin)."""
        store = self.get_object()
        user = request.user
        if not user.has_role(Role.RoleName.ADMIN) and store.owner_id != user.id:
            raise PermissionDenied("Vous ne pouvez modifier que votre propre boutique.")
        image_file = request.FILES.get("logo")
        if not image_file:
            return Response({"error": "Fichier 'logo' requis."}, status=status.HTTP_400_BAD_REQUEST)
        image_file = _validate_image_upload(image_file)
        store.logo = image_file
        store.save(update_fields=["logo"])
        return Response(StoreSerializer(store).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="banner",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_banner(self, request, pk=None):
        """Photo de couverture de la boutique — réservée au propriétaire (ou à l'admin)."""
        store = self.get_object()
        user = request.user
        if not user.has_role(Role.RoleName.ADMIN) and store.owner_id != user.id:
            raise PermissionDenied("Vous ne pouvez modifier que votre propre boutique.")
        image_file = request.FILES.get("banner")
        if not image_file:
            return Response({"error": "Fichier 'banner' requis."}, status=status.HTTP_400_BAD_REQUEST)
        image_file = _validate_image_upload(image_file)
        store.banner = image_file
        store.save(update_fields=["banner"])
        return Response(StoreSerializer(store).data)

    def _notify_owner(self, store, subject, message):
        notification = Notification.objects.create(
            user=store.owner,
            channel=Notification.Channel.EMAIL,
            subject=subject,
            message=message,
            metadata={"store_id": str(store.id), "store_status": store.status},
        )
        notification.send()

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        store = self.get_object()
        store.status = Store.Status.ACTIVE
        store.rejection_reason = ""
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
        store.rejection_reason = reason
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
