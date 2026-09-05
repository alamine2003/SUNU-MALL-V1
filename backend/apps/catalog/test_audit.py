from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, IntegrityError, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from apps.catalog.models import Inventory, Product, ProductVariant, Store
from apps.catalog.tests import TINY_PNG
from apps.catalog.views.helpers import _validate_image_upload
from apps.ia.services import _search_catalog
from apps.users.models import User, Role, UserRole


class CatalogAuditTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username='catalog-audit', email='catalog-audit@example.test')
        UserRole.objects.create(user=self.owner, role=Role.objects.get(name='merchant'))
        self.store = Store.objects.create(owner=self.owner, name='Audit', status=Store.Status.ACTIVE)
        self.products = []
        for i in range(20):
            product = Product.objects.create(store=self.store, name=f'Audit {i}', base_price=1000, status=Product.Status.ACTIVE)
            variant = ProductVariant.objects.create(product=product, sku=f'Audit-{i}', price=1000)
            Inventory.objects.create(variant=variant, quantity=10)
            self.products.append(product)

    def test_suspended_store_is_absent_from_products_variants_and_ai(self):
        self.store.status = Store.Status.SUSPENDED
        self.store.save()
        self.assertEqual(self.client.get('/api/catalog/products/').data['count'], 0)
        self.assertEqual(self.client.get('/api/catalog/variants/').data['count'], 0)
        self.assertEqual(_search_catalog('Audit'), [])
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get('/api/catalog/products/').data['count'], 20)

    def test_product_list_has_bounded_queries(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/api/catalog/products/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 20)
        self.assertLessEqual(len(queries), 5)

    def test_public_store_does_not_disclose_owners_login_email(self):
        response = self.client.get(f'/api/catalog/stores/{self.store.pk}/')
        self.assertIsNone(response.data['owner_email'])
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get(f'/api/catalog/stores/{self.store.pk}/').data['owner_email'], self.owner.email)

    def test_upload_is_reencoded_and_never_saved_as_html(self):
        upload = SimpleUploadedFile('malicious.html', TINY_PNG + b'<script>alert(1)</script>', content_type='text/html')
        image = _validate_image_upload(upload)
        self.assertTrue(image.name.endswith('.png'))
        self.assertEqual(image.content_type, 'image/png')
        self.assertNotIn(b'<script>', image.read())

    def test_invalid_stock_writes_are_rejected_by_database(self):
        inventory = self.products[0].variants.first().inventory
        for values in [{'quantity': -1}, {'reserved_quantity': -1}, {'reserved_quantity': 11}]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Inventory.objects.filter(pk=inventory.pk).update(**values)

    def test_store_deletion_archives_without_destroying_orders_or_stock(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.delete(f'/api/catalog/stores/{self.store.pk}/').status_code, 204)
        self.store.refresh_from_db()
        self.assertEqual(self.store.status, Store.Status.INACTIVE)
        self.assertEqual(self.store.products.count(), 20)

    def test_ai_tool_rejects_invalid_numeric_arguments(self):
        for value in ['not-a-number', 'NaN', 'Infinity', -1]:
            self.assertEqual(_search_catalog('Audit', max_price=value), [])

    def test_malformed_identifiers_return_client_errors(self):
        self.client.force_authenticate(self.owner)
        for path in ['/api/catalog/products/best_sellers/?store=invalid', '/api/catalog/stores/?product_category=invalid', '/api/analytics/store-summary/?store=invalid']:
            self.assertIn(self.client.get(path).status_code, [400, 404])
        self.assertIn(self.client.post('/api/shopping/wishlist/items/', {'product': 'invalid'}).status_code, [400, 404])
