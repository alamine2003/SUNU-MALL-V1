from rest_framework import serializers
from .models import Category, Inventory, Product, ProductImage, ProductVariant, Review, Store, StoreSettings


class CategorySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "parent", "name", "image_url", "created_at", "updated_at"]
        read_only_fields = ["id", "image_url", "created_at", "updated_at"]

    def get_image_url(self, obj):
        return obj.image.url if obj.image else None


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "url", "position", "created_at"]

    def get_url(self, obj):
        return obj.get_signed_url() or None


class StoreSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)

    class Meta:
        model = Store
        fields = [
            "id", "owner", "owner_email", "category", "name",
            "status", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at", "owner_email"]


class StoreSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreSettings
        fields = ["id", "store", "business_hours", "min_order_amount", "created_at", "updated_at"]
        read_only_fields = ["id", "store", "created_at", "updated_at"]


class ProductVariantSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()
    initial_quantity = serializers.IntegerField(write_only=True, required=False, default=100, min_value=0)

    class Meta:
        model = ProductVariant
        fields = [
            "id", "product", "sku", "attributes", "price",
            "is_available", "quantity", "initial_quantity",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_available", "quantity", "created_at", "updated_at"]

    def get_is_available(self, obj):
        return obj.is_available()

    def get_quantity(self, obj):
        return obj.inventory.available() if hasattr(obj, "inventory") else 0

    def create(self, validated_data):
        initial_quantity = validated_data.pop("initial_quantity", 100)
        variant = super().create(validated_data)
        Inventory.objects.create(variant=variant, quantity=initial_quantity)
        return variant


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "product", "user", "user_name", "rating", "comment", "created_at"]
        read_only_fields = ["id", "user", "user_name", "created_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.method == "POST":
            product = attrs.get("product")
            if product and Review.objects.filter(product=product, user=request.user).exists():
                raise serializers.ValidationError("Vous avez déjà laissé un avis pour ce produit.")
        return attrs


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "store", "store_name", "category", "brand", "name", "description",
            "base_price", "status", "images", "variants",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
