from django.db import transaction, models
from rest_framework.generics import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Cart, CartItem, Wishlist
from .serializers import CartItemInputSerializer, CartSerializer, WishlistSerializer
from apps.catalog.models import Product, ProductVariant


class CartViewSet(viewsets.ViewSet):
    """
    Panier de l'utilisateur connecté (un seul panier par utilisateur : pas de
    notion de liste ni de pk, toutes les actions opèrent sur le panier de
    request.user, créé à la volée s'il n'existe pas encore).
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_cart(self, user, lock=False):
        cart, _ = Cart.objects.get_or_create(user=user)
        if lock:
            cart = Cart.objects.select_for_update().get(pk=cart.pk)
        return cart

    def _data(self, cart):
        cart = Cart.objects.prefetch_related(models.Prefetch(
            'items', queryset=CartItem.objects.select_related('product_variant__product'),
        )).get(pk=cart.pk)
        return CartSerializer(cart).data

    def list(self, request):
        return Response(self._data(self._get_cart(request.user)))

    @action(detail=False, methods=["post"], url_path="items")
    @transaction.atomic
    def add_item(self, request):
        serializer = CartItemInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = self._get_cart(request.user, lock=True)
        variant = get_object_or_404(
            ProductVariant.objects.select_related("product"),
            pk=serializer.validated_data["product_variant"],
            product__status="active",
            product__store__status="active",
        )
        quantity = serializer.validated_data["quantity"]
        inventory = getattr(variant, "inventory", None)
        existing_quantity = cart.items.filter(product_variant=variant).values_list("quantity", flat=True).first() or 0
        if inventory is None or inventory.available() < existing_quantity + quantity:
            raise ValidationError("La quantité demandée dépasse le stock disponible.")
        cart.add_item(variant, qty=quantity)
        return Response(self._data(cart), status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["patch", "delete"], url_path=r"items/(?P<item_id>[^/.]+)")
    @transaction.atomic
    def item_detail(self, request, item_id=None):
        cart = self._get_cart(request.user, lock=True)
        item = get_object_or_404(CartItem, pk=item_id, cart=cart)
        if request.method == "DELETE":
            item.delete()
        else:
            serializer = CartItemInputSerializer(
                data={"quantity": request.data.get("quantity")}, partial=True
            )
            serializer.is_valid(raise_exception=True)
            inventory = getattr(item.product_variant, "inventory", None)
            if inventory is None or inventory.available() < serializer.validated_data["quantity"]:
                raise ValidationError("La quantité demandée dépasse le stock disponible.")
            item.quantity = serializer.validated_data["quantity"]
            item.save(update_fields=["quantity"])
        return Response(self._data(cart))

    @action(detail=False, methods=["post"], url_path="clear")
    @transaction.atomic
    def clear(self, request):
        cart = self._get_cart(request.user, lock=True)
        cart.clear()
        return Response(self._data(cart))


class WishlistViewSet(viewsets.ViewSet):
    """Liste de souhaits de l'utilisateur connecté (même principe que CartViewSet)."""
    permission_classes = [permissions.IsAuthenticated]

    def _get_wishlist(self, user):
        wishlist, _ = Wishlist.objects.get_or_create(user=user)
        return Wishlist.objects.prefetch_related("items__product").get(pk=wishlist.pk)

    def list(self, request):
        return Response(WishlistSerializer(self._get_wishlist(request.user)).data)

    @action(detail=False, methods=["post"], url_path="items")
    def add_item(self, request):
        wishlist = self._get_wishlist(request.user)
        product = get_object_or_404(
            Product, pk=request.data.get("product"), status=Product.Status.ACTIVE,
            store__status="active",
        )
        wishlist.add_product(product)
        return Response(WishlistSerializer(self._get_wishlist(request.user)).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["delete"], url_path=r"items/(?P<product_id>[^/.]+)")
    def remove_item(self, request, product_id=None):
        wishlist = self._get_wishlist(request.user)
        item = get_object_or_404(wishlist.items, product_id=product_id)
        item.delete()
        return Response(WishlistSerializer(self._get_wishlist(request.user)).data)
