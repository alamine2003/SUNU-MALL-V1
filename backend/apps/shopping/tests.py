from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Inventory, Product, ProductVariant, Store
from apps.users.models import Role, User, UserRole


class CartValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        client_role, _ = Role.objects.get_or_create(name=Role.RoleName.CLIENT)
        merchant_role, _ = Role.objects.get_or_create(name=Role.RoleName.MERCHANT)
        self.customer = User.objects.create_user(
            username="cart-client@example.com", email="cart-client@example.com",
            password="testpass123", is_verified=True,
        )
        UserRole.objects.create(user=self.customer, role=client_role)
        merchant = User.objects.create_user(
            username="cart-merchant@example.com", email="cart-merchant@example.com",
            password="testpass123", is_verified=True,
        )
        UserRole.objects.create(user=merchant, role=merchant_role)
        store = Store.objects.create(owner=merchant, name="Boutique", status=Store.Status.ACTIVE)
        product = Product.objects.create(
            store=store, name="Produit", base_price=1000, status=Product.Status.ACTIVE
        )
        self.variant = ProductVariant.objects.create(product=product, sku="CART-1", price=1000)
        Inventory.objects.create(variant=self.variant, quantity=5)

    def test_negative_quantity_returns_validation_error_not_server_error(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            "/api/shopping/cart/items/",
            {"product_variant": str(self.variant.id), "quantity": -1},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_variant_cannot_be_added(self):
        self.variant.product.status = Product.Status.INACTIVE
        self.variant.product.save(update_fields=["status"])
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            "/api/shopping/cart/items/",
            {"product_variant": str(self.variant.id), "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class WishlistRemovalTests(TestCase):
    setUp = CartValidationTests.setUp

    def test_inactive_favorite_can_be_removed(self):
        from apps.shopping.models import Wishlist
        wishlist = Wishlist.objects.create(user=self.customer)
        product = self.variant.product
        wishlist.add_product(product)
        product.status = Product.Status.INACTIVE
        product.save(update_fields=["status"])
        product.store.status = Store.Status.SUSPENDED
        product.store.save(update_fields=["status"])
        self.client.force_authenticate(self.customer)
        response = self.client.delete(f"/api/shopping/wishlist/items/{product.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(wishlist.items.exists())

    def test_removal_never_touches_another_users_favorite(self):
        from apps.shopping.models import Wishlist
        other = User.objects.create_user(username="wishlist-other", email="wishlist-other@example.com")
        wishlist = Wishlist.objects.create(user=other)
        wishlist.add_product(self.variant.product)
        self.client.force_authenticate(self.customer)
        response = self.client.delete(f"/api/shopping/wishlist/items/{self.variant.product_id}/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(wishlist.items.count(), 1)
