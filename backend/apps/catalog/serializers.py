from datetime import datetime
from decimal import Decimal

from rest_framework import serializers
from .models import Category, Inventory, Product, ProductImage, ProductVariant, Review, Store, StoreCategory, StoreSettings


class CategorySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "parent", "name", "image_url", "created_at", "updated_at"]
        read_only_fields = ["id", "image_url", "created_at", "updated_at"]

    def get_image_url(self, obj):
        return obj.image.url if obj.image else None


class StoreCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreCategory
        fields = ["id", "name"]
        read_only_fields = ["id"]


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "url", "position", "created_at"]

    def get_url(self, obj):
        return obj.get_signed_url() or None


class StoreSerializer(serializers.ModelSerializer):
    owner_email = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()
    category_detail = StoreCategorySerializer(source='category', read_only=True)
    # Alimentés par l'annotation Subquery de StoreViewSet.get_queryset (moyenne
    # des notes / nombre d'avis réels sur les produits de la boutique) —
    # absents (None) si la vue qui a produit l'instance ne les a pas annotés.
    rating = serializers.FloatField(read_only=True, default=None)
    review_count = serializers.IntegerField(read_only=True, default=0)
    category_names = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = [
            "id", "owner", "owner_email", "category", "category_detail", "name",
            "phone", "description", "address", "city", "rejection_reason",
            "logo_url", "banner_url", "status", "latitude", "longitude", "rating", "review_count",
            "category_names", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "owner", "created_at", "updated_at", "owner_email",
            "logo_url", "banner_url", "category_detail", "rejection_reason",
        ]

    def get_owner_email(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and (request.user.pk == obj.owner_id or request.user.has_role('admin')):
            return obj.owner.email
        return None

    def validate_status(self, value):
        expected = self.instance.status if self.instance else Store.Status.INACTIVE
        if value != expected:
            raise serializers.ValidationError("Utilisez les actions administratives d'approbation ou de rejet.")
        return value

    def get_logo_url(self, obj):
        return obj.logo.url if obj.logo else None

    def get_banner_url(self, obj):
        return obj.banner.url if obj.banner else None

    def get_category_names(self, obj):
        if hasattr(obj, 'category_products'):
            return sorted({product.category.name for product in obj.category_products})
        # .order_by() vide avant .distinct() : sans ça, le tri par défaut de
        # Product (Meta.ordering = ['-created_at']) s'invite dans le SQL et
        # empêche la déduplication (chaque produit garde sa propre ligne).
        return list(
            obj.products.filter(status=Product.Status.ACTIVE, category__isnull=False)
            .order_by()
            .values_list("category__name", flat=True)
            .distinct()
        )


class StoreSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreSettings
        fields = ["id", "store", "business_hours", "min_order_amount", "created_at", "updated_at"]
        read_only_fields = ["id", "store", "created_at", "updated_at"]

    def validate_min_order_amount(self, value):
        if value < Decimal("0"):
            raise serializers.ValidationError("Le montant minimum ne peut pas être négatif.")
        return value

    def validate_business_hours(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Les horaires doivent être un objet JSON.")
        allowed_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        if set(value) - allowed_days:
            raise serializers.ValidationError("Jour(s) non reconnu(s) dans les horaires.")
        for day, hours in value.items():
            if not isinstance(hours, dict):
                raise serializers.ValidationError({day: "Les horaires du jour doivent être un objet."})
            if hours.get("closed", False):
                continue
            try:
                opening = datetime.strptime(str(hours["open"]), "%H:%M").time()
                closing = datetime.strptime(str(hours["close"]), "%H:%M").time()
            except (KeyError, TypeError, ValueError) as exc:
                raise serializers.ValidationError({day: "Utilisez le format HH:MM pour open et close."}) from exc
            if opening >= closing:
                raise serializers.ValidationError({day: "L'heure de fermeture doit suivre l'ouverture."})
        return value


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

    def validate_product(self, value):
        if self.instance and value.pk != self.instance.product_id:
            raise serializers.ValidationError("Le produit d'une variante ne peut pas être changé.")
        return value

    def get_is_available(self, obj):
        return obj.is_available()

    def get_quantity(self, obj):
        return obj.inventory.available() if hasattr(obj, "inventory") else 0

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le prix doit être strictement positif.")
        return value

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

    def validate_product(self, product):
        from .queries import visible_products
        if self.instance and product.pk != self.instance.product_id:
            raise serializers.ValidationError("Le produit d'un avis ne peut pas être changé.")
        if not visible_products().filter(pk=product.pk).exists():
            raise serializers.ValidationError("Ce produit n'est pas disponible.")
        return product

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

    def validate_store(self, value):
        if self.instance and value.pk != self.instance.store_id:
            raise serializers.ValidationError("La boutique d'un produit ne peut pas être changée.")
        return value

    def validate_base_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le prix doit être strictement positif.")
        return value
