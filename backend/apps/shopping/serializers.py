from rest_framework import serializers
from .models import Wishlist, WishlistItem, Cart, CartItem


class WishlistItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_price = serializers.DecimalField(source="product.base_price", max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = WishlistItem
        fields = ["id", "product", "product_name", "product_price", "added_at"]
        read_only_fields = ["id", "added_at"]


class WishlistSerializer(serializers.ModelSerializer):
    items = WishlistItemSerializer(many=True, read_only=True)

    class Meta:
        model = Wishlist
        fields = ["id", "user", "items", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "items", "created_at", "updated_at"]


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product_variant.product.name", read_only=True)
    unit_price = serializers.DecimalField(source="product_variant.price", max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.SerializerMethodField()
    store = serializers.CharField(source="product_variant.product.store_id", read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product_variant", "product_name", "unit_price", "quantity", "subtotal", "added_at", "store"]
        read_only_fields = ["id", "added_at"]

    def get_subtotal(self, obj):
        return obj.subtotal()


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "user", "items", "total_price", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "items", "total_price", "created_at", "updated_at"]

    def get_total_price(self, obj):
        return obj.total_price()
