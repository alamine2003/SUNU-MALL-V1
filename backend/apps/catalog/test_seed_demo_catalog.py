from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.catalog.models import Inventory, Product, ProductImage, ProductVariant, Store
from apps.monetization.models import SponsoredProduct


class SeedDemoCatalogTests(TestCase):
    def test_seed_is_complete_and_idempotent(self):
        output = StringIO()

        call_command(
            "seed_demo_catalog",
            asset_base_url="https://example.com/SUNU-MALL-V1",
            stdout=output,
        )
        call_command(
            "seed_demo_catalog",
            asset_base_url="https://example.com/SUNU-MALL-V1",
            stdout=output,
        )

        self.assertEqual(Store.objects.filter(status=Store.Status.ACTIVE).count(), 4)
        self.assertEqual(Product.objects.filter(status=Product.Status.ACTIVE).count(), 16)
        self.assertEqual(ProductVariant.objects.filter(sku__startswith="DEMO-SM-").count(), 16)
        self.assertEqual(Inventory.objects.filter(variant__sku__startswith="DEMO-SM-").count(), 16)
        self.assertEqual(ProductImage.objects.count(), 16)
        self.assertEqual(SponsoredProduct.objects.count(), 4)
        self.assertTrue(
            all(
                image.minio_path.startswith("https://example.com/SUNU-MALL-V1/")
                for image in ProductImage.objects.all()
            )
        )
