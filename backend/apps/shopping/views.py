from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Cart, CartItem, Wishlist
from .serializers import CartSerializer, WishlistSerializer
from apps.catalog.models import Product, ProductVariant


class CartViewSet(viewsets.ViewSet):
    """
    Panier de l'utilisateur connecté (un seul panier par utilisateur : pas de
    notion de liste ni de pk, toutes les actions opèrent sur le panier de
    request.user, créé à la volée s'il n'existe pas encore).
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_cart(self, user):
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart

    def list(self, request):
        return Response(CartSerializer(self._get_cart(request.user)).data)

    @action(detail=False, methods=["post"], url_path="items")
    def add_item(self, request):
        cart = self._get_cart(request.user)
        variant = get_object_or_404(ProductVariant, pk=request.data.get("product_variant"))
        quantity = int(request.data.get("quantity", 1))
        cart.add_item(variant, qty=quantity)
        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["patch", "delete"], url_path=r"items/(?P<item_id>[^/.]+)")
    def item_detail(self, request, item_id=None):
        cart = self._get_cart(request.user)
        item = get_object_or_404(CartItem, pk=item_id, cart=cart)
        if request.method == "DELETE":
            item.delete()
        else:
            quantity = request.data.get("quantity")
            if quantity is not None:
                item.quantity = int(quantity)
                item.save()
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=["post"], url_path="clear")
    def clear(self, request):
        cart = self._get_cart(request.user)
        cart.clear()
        return Response(CartSerializer(cart).data)


class WishlistViewSet(viewsets.ViewSet):
    """Liste de souhaits de l'utilisateur connecté (même principe que CartViewSet)."""
    permission_classes = [permissions.IsAuthenticated]

    def _get_wishlist(self, user):
        wishlist, _ = Wishlist.objects.get_or_create(user=user)
        return wishlist

    def list(self, request):
        return Response(WishlistSerializer(self._get_wishlist(request.user)).data)

    @action(detail=False, methods=["post"], url_path="items")
    def add_item(self, request):
        wishlist = self._get_wishlist(request.user)
        product = get_object_or_404(Product, pk=request.data.get("product"))
        wishlist.add_product(product)
        return Response(WishlistSerializer(wishlist).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["delete"], url_path=r"items/(?P<product_id>[^/.]+)")
    def remove_item(self, request, product_id=None):
        wishlist = self._get_wishlist(request.user)
        product = get_object_or_404(Product, pk=product_id)
        wishlist.remove_product(product)
        return Response(WishlistSerializer(wishlist).data)
