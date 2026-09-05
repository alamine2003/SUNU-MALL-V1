from django.test import TestCase
from django.utils import timezone

from apps.analytics.models import SalesStatistic
from apps.catalog.models import Product, ProductVariant, Store
from apps.orders.models import Order, OrderItem
from apps.users.models import User


class SalesStatisticTests(TestCase):
    def setUp(self):
        self.merchant = User.objects.create_user(
            username="stats-merchant@example.com",
            email="stats-merchant@example.com",
            password="testpass123",
        )
        self.customer = User.objects.create_user(
            username="stats-customer@example.com",
            email="stats-customer@example.com",
            password="testpass123",
        )
        self.store = Store.objects.create(owner=self.merchant, name="Stats store")
        product = Product.objects.create(store=self.store, name="Stats product", base_price=1000)
        self.variant = ProductVariant.objects.create(product=product, sku="STATS-1", price=1000)

    def _order(self, status, amount):
        order = Order.objects.create(
            customer=self.customer,
            store=self.store,
            total_amount=amount,
            status=status,
        )
        OrderItem.objects.create(
            order=order,
            product_variant=self.variant,
            quantity=1,
            unit_price=amount,
        )
        return order

    def test_only_paid_orders_are_counted(self):
        self._order(Order.Status.PENDING, 900)
        self._order(Order.Status.PAID, 1000)
        self._order(Order.Status.DELIVERED, 2000)
        self._order(Order.Status.CANCELLED, 500)

        stat = SalesStatistic.compute_for_store(self.store, timezone.now().date())

        self.assertEqual(stat.total_orders, 2)
        self.assertEqual(stat.total_sales, 3000)


class SummaryRegressionTests(TestCase):
    setUp = SalesStatisticTests.setUp
    _order = SalesStatisticTests._order

    def test_summary_and_daily_totals_agree_for_paid_and_unpaid_orders(self):
        from decimal import Decimal
        from rest_framework.test import APIClient
        for state, amount in [(Order.Status.PENDING, 10000), (Order.Status.CANCELLED, 500),
                              (Order.Status.PAID, 1000), (Order.Status.DELIVERED, 3000)]:
            self._order(state, amount)
        client = APIClient()
        client.force_authenticate(self.merchant)
        response = client.get("/api/analytics/store-summary/", {"store": str(self.store.pk)})
        daily = SalesStatistic.compute_for_store(self.store, timezone.now().date())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data["revenue_30d"]), daily.total_sales)
        self.assertEqual(response.data["orders_30d"], daily.total_orders)
        self.assertEqual(daily.total_sales, 4000)
        self.assertEqual(Decimal(response.data["avg_order_value_30d"]), 2000)
        self.assertEqual(response.data["delivered_rate"], 50)
