from rest_framework import viewsets, permissions, filters, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import get_object_or_404
from django.db import models, transaction
from django.utils import timezone
from ..models import Product, ProductImage, ProductVariant, Store
from ..queries import visible_products, product_details
from ..serializers import (
    ProductImageSerializer, ProductSerializer, ProductVariantSerializer,
)
from apps.users.permissions import IsMerchantOrAdmin, IsStoreOwnerOrAdmin
from apps.users.models import Role
from apps.monetization.models import SponsoredProduct
from .helpers import _validate_image_upload, _check_product_limit


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
        # actions qui modifient le catalogue exigent un compte marchand.
        if self.action == "create":
            return [IsMerchantOrAdmin()]
        if self.action in ["update", "partial_update", "destroy", "upload_image", "delete_image"]:
            return [permissions.IsAuthenticated(), IsStoreOwnerOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = product_details(visible_products(self.request.user))

        if self.request.query_params.get("sponsored") == "true":
            today = timezone.now().date()
            sponsored_product_ids = SponsoredProduct.objects.filter(
                status=SponsoredProduct.Status.ACTIVE,
                starts_at__lte=today,
                ends_at__gte=today,
            ).values_list("product_id", flat=True)
            queryset = queryset.filter(id__in=sponsored_product_ids)

        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        store = serializer.validated_data.get("store")
        Store.objects.select_for_update().get(pk=store.pk)
        user = self.request.user
        if not user.has_role(Role.RoleName.ADMIN) and store.owner_id != user.id:
            raise PermissionDenied("Vous ne pouvez ajouter des produits que dans votre propre boutique.")
        if serializer.validated_data.get("status") == Product.Status.ACTIVE:
            _check_product_limit(store)
        serializer.save()

    def perform_destroy(self, instance):
        # Les variantes et anciennes commandes restent traçables. DELETE
        # retire le produit de la vente sans supprimer son historique.
        instance.status = Product.Status.INACTIVE
        instance.save(update_fields=["status", "updated_at"])

    @transaction.atomic
    def perform_update(self, serializer):
        product = serializer.instance
        Store.objects.select_for_update().get(pk=product.store_id)
        new_status = serializer.validated_data.get("status")
        # Ne vérifie que le passage draft/inactive → active : modifier un
        # produit déjà actif (prix, description...) ne doit jamais être
        # bloqué par la limite de son offre.
        if new_status == Product.Status.ACTIVE and product.status != Product.Status.ACTIVE:
            _check_product_limit(product.store, exclude_product_id=product.id)
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
        image_file = _validate_image_upload(image_file)
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
        la marketplace. Public, comme `sponsored`. Avec ?store=<id>,
        restreint le classement aux produits de cette boutique (utilisé
        par l'onglet Analytics du commerçant pour son propre top produits).
        """
        from apps.orders.models import Order, OrderItem

        items = OrderItem.objects.filter(order__status__in=Order.SALES_STATUSES)
        store_id = request.query_params.get("store")
        if store_id:
            store_id = serializers.UUIDField().run_validation(store_id)
            items = items.filter(product_variant__product__store_id=store_id)

        ranking = list(
            items
            .values("product_variant__product_id")
            .annotate(total_qty=models.Sum("quantity"))
            .order_by("-total_qty")[:12]
        )
        qty_by_id = {str(row["product_variant__product_id"]): row["total_qty"] for row in ranking}
        top_product_ids = [row["product_variant__product_id"] for row in ranking]

        # `filter(id__in=...)` ne préserve pas l'ordre de popularité : on le
        # ré-applique nous-mêmes après coup.
        products_by_id = {p.id: p for p in self.get_queryset().filter(id__in=top_product_ids)}
        ordered = [products_by_id[pid] for pid in top_product_ids if pid in products_by_id]
        serializer = self.get_serializer(ordered, many=True)
        data = serializer.data
        for item in data:
            item["sold_quantity"] = qty_by_id.get(item["id"])
        return Response(data)

    @action(detail=True, methods=["get"], permission_classes=[permissions.AllowAny])
    def similar(self, request, pk=None):
        """
        Produits fréquemment achetés dans les mêmes commandes que celui-ci
        (co-achat, à partir des commandes réelles non annulées) — un
        agrégat SQL classique, pas un appel IA générative : instantané et
        gratuit, contrairement à un appel LLM par affichage de page produit.
        Si le co-achat ne donne pas assez de résultats (produit encore peu
        vendu), complète avec d'autres produits actifs de la même catégorie.
        """
        from apps.orders.models import Order, OrderItem

        product = self.get_object()

        order_ids = (
            OrderItem.objects.filter(
                product_variant__product=product,
                order__status__in=Order.SALES_STATUSES,
            )
            .values_list("order_id", flat=True)
        )
        co_purchased_ids = list(
            OrderItem.objects.filter(
                order_id__in=order_ids,
                order__status__in=Order.SALES_STATUSES,
            ).exclude(product_variant__product=product)
            .values("product_variant__product_id")
            .annotate(freq=models.Count("id"))
            .order_by("-freq")
            .values_list("product_variant__product_id", flat=True)[:12]
        )

        products_by_id = {p.id: p for p in self.get_queryset().filter(id__in=co_purchased_ids)}
        ordered = [products_by_id[pid] for pid in co_purchased_ids if pid in products_by_id]

        if len(ordered) < 8 and product.category_id:
            exclude_ids = {product.id, *(p.id for p in ordered)}
            same_category = (
                self.get_queryset()
                .filter(category_id=product.category_id)
                .exclude(id__in=exclude_ids)
                .order_by("-created_at")[: 8 - len(ordered)]
            )
            ordered.extend(same_category)

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
        if self.action == "create":
            return [IsMerchantOrAdmin()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsStoreOwnerOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        return ProductVariant.objects.filter(product__in=visible_products(self.request.user)).select_related('product__store', 'inventory').order_by('-created_at', 'pk')

    def perform_destroy(self, instance):
        raise ValidationError("Désactivez le produit pour préserver son stock et l'historique des commandes.")

    def perform_create(self, serializer):
        product = serializer.validated_data.get("product")
        user = self.request.user
        if not user.has_role(Role.RoleName.ADMIN) and product.store.owner_id != user.id:
            raise PermissionDenied("Vous ne pouvez ajouter des variantes qu'à vos propres produits.")
        serializer.save()
