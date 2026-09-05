"""
Tests pour la propriété des produits (permissions) et l'upload d'images.

Les tests d'upload utilisent un stockage fichier local temporaire plutôt que
MinIO : ils vérifient le comportement de l'application (permissions,
création de l'objet ProductImage), pas la disponibilité d'une vraie
infrastructure S3 — ce qui les rend exécutables tel quel en CI.
"""
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User, Role, UserRole
from apps.catalog.models import Product, ProductVariant, Store

# 1x1 PNG transparent minimal, valide pour Pillow.
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

_TMP_MEDIA_ROOT = tempfile.mkdtemp(prefix="sunu-mall-test-media-")


@override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}, MEDIA_ROOT=_TMP_MEDIA_ROOT)
class CatalogOwnershipTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()
        Role.objects.get_or_create(name=Role.RoleName.MERCHANT)

        self.owner = self._make_merchant("owner@example.com")
        self.other = self._make_merchant("other@example.com")

        self.store = Store.objects.create(owner=self.owner, name="Ma boutique", status=Store.Status.ACTIVE)
        self.product = Product.objects.create(store=self.store, name="Produit", base_price=1000)

    def _make_merchant(self, email):
        user = User.objects.create_user(username=email, email=email, password="testpass123", is_verified=True)
        role = Role.objects.get(name=Role.RoleName.MERCHANT)
        UserRole.objects.create(user=user, role=role)
        return user

    def test_owner_can_upload_image(self):
        self.client.force_authenticate(self.owner)
        image = SimpleUploadedFile("photo.png", TINY_PNG, content_type="image/png")
        response = self.client.post(f"/api/catalog/products/{self.product.id}/images/", {"image": image}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.product.images.count(), 1)
        self.assertTrue(response.data["url"])

    def test_non_owner_cannot_upload_image(self):
        # Le produit est en statut "draft" : un autre commerçant ne le voit même
        # pas dans son queryset (404), ce qui est plus sûr qu'un 403 révélant
        # son existence.
        self.client.force_authenticate(self.other)
        image = SimpleUploadedFile("photo.png", TINY_PNG, content_type="image/png")
        response = self.client.post(f"/api/catalog/products/{self.product.id}/images/", {"image": image}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.product.images.count(), 0)

    def test_non_owner_cannot_upload_image_to_active_product(self):
        # Même un produit actif (donc visible publiquement) reste protégé en écriture.
        self.product.status = Product.Status.ACTIVE
        self.product.save()
        self.client.force_authenticate(self.other)
        image = SimpleUploadedFile("photo.png", TINY_PNG, content_type="image/png")
        response = self.client.post(f"/api/catalog/products/{self.product.id}/images/", {"image": image}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.product.images.count(), 0)

    def test_anyone_can_view_an_active_product_without_auth(self):
        # Régression : la vérification de propriété ne doit jamais bloquer la
        # simple lecture d'un produit, même pour un visiteur non connecté.
        self.product.status = Product.Status.ACTIVE
        self.product.save()
        response = self.client.get(f"/api/catalog/products/{self.product.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_another_authenticated_user_can_view_an_active_product(self):
        self.product.status = Product.Status.ACTIVE
        self.product.save()
        self.client.force_authenticate(self.other)
        response = self.client.get(f"/api/catalog/products/{self.product.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_owner_cannot_create_product_in_others_store(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(
            "/api/catalog/products/",
            {"store": str(self.store.id), "name": "Intrus", "base_price": "500"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_variant_creation_creates_inventory_with_requested_quantity(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/catalog/variants/",
            {"product": str(self.product.id), "sku": "SKU-1", "price": "1000", "initial_quantity": 42},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        variant = ProductVariant.objects.get(sku="SKU-1")
        self.assertTrue(hasattr(variant, "inventory"))
        self.assertEqual(variant.inventory.quantity, 42)
        self.assertTrue(variant.is_available())

    def test_upload_rejects_a_non_image_file(self):
        self.client.force_authenticate(self.owner)
        invalid = SimpleUploadedFile("payload.txt", b"not an image", content_type="image/png")
        response = self.client.post(
            f"/api/catalog/products/{self.product.id}/images/",
            {"image": invalid}, format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.product.images.count(), 0)


class CatalogRegressionTests(TestCase):
    setUp = CatalogOwnershipTests.setUp
    _make_merchant = CatalogOwnershipTests._make_merchant

    def test_merchant_cannot_activate_suspended_store(self):
        self.store.status = Store.Status.SUSPENDED
        self.store.save(update_fields=["status"])
        self.client.force_authenticate(self.owner)
        response = self.client.patch(f"/api/catalog/stores/{self.store.pk}/", {"status": "active"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.store.refresh_from_db()
        self.assertEqual(self.store.status, Store.Status.SUSPENDED)
        self.assertEqual(self.client.post(f"/api/catalog/stores/{self.store.pk}/approve/").status_code, 403)

    def test_merchant_cannot_create_already_approved_store(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post("/api/catalog/stores/", {"name": "Sans contrôle", "status": "active"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Store.objects.filter(name="Sans contrôle").exists())

    def test_admin_can_still_approve_store(self):
        admin = self._make_merchant("admin-catalog@example.com")
        role, _ = Role.objects.get_or_create(name=Role.RoleName.ADMIN)
        UserRole.objects.create(user=admin, role=role)
        self.client.force_authenticate(admin)
        response = self.client.post(f"/api/catalog/stores/{self.store.pk}/approve/")
        self.assertEqual(response.status_code, 200)
        self.store.refresh_from_db()
        self.assertEqual(self.store.status, Store.Status.ACTIVE)

    def test_product_and_variant_cannot_move_to_another_merchant(self):
        other_store = Store.objects.create(owner=self.other, name="Autre boutique")
        other_product = Product.objects.create(store=other_store, name="Autre produit", base_price=1000)
        variant = ProductVariant.objects.create(product=self.product, sku="IMMUTABLE", price=1000)
        self.client.force_authenticate(self.owner)
        response = self.client.patch(f"/api/catalog/products/{self.product.pk}/", {"store": str(other_store.pk)}, format="json")
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(f"/api/catalog/variants/{variant.pk}/", {"product": str(other_product.pk)}, format="json")
        self.assertEqual(response.status_code, 400)
        self.product.refresh_from_db()
        variant.refresh_from_db()
        self.assertEqual(self.product.store_id, self.store.pk)
        self.assertEqual(variant.product_id, self.product.pk)

    def test_delete_archives_product_and_preserves_sold_variant(self):
        from apps.catalog.models import Inventory
        from apps.orders.models import Order, OrderItem
        variant = ProductVariant.objects.create(product=self.product, sku="ARCHIVE", price=1000)
        Inventory.objects.create(variant=variant, quantity=4)
        order = Order.objects.create(customer=self.other, store=self.store, total_amount=1000, status="paid")
        item = OrderItem.objects.create(order=order, product_variant=variant, quantity=1, unit_price=1000)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.delete(f"/api/catalog/products/{self.product.pk}/").status_code, 204)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, Product.Status.INACTIVE)
        self.assertTrue(OrderItem.objects.filter(pk=item.pk).exists())
        self.assertTrue(Inventory.objects.filter(variant=variant).exists())
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f"/api/catalog/products/{self.product.pk}/").status_code, 404)
