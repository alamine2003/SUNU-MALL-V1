from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.orders.tests import CheckoutStockTests
from apps.orders.models import Order
from apps.payments.services import complete_payment
from apps.analytics.models import SalesStatistic
from apps.shopping.models import Cart
from apps.shopping.views import CartViewSet


class ConcurrentAuditTests(TransactionTestCase):
    setUp = CheckoutStockTests.setUp
    _make_user = CheckoutStockTests._make_user

    def run_parallel(self, fn, count=2):
        barrier = Barrier(count)
        def worker(i):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                barrier.wait(timeout=10)
                return fn(i)
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=count) as pool:
            return list(pool.map(worker, range(count)))

    def test_concurrent_cart_additions_are_not_lost(self):
        self.inventory.quantity = 20
        self.inventory.save()
        def add(i):
            request = APIRequestFactory().post('/api/shopping/cart/items/', {'product_variant': str(self.variant.pk), 'quantity': 1}, format='json')
            force_authenticate(request, self.customer)
            return CartViewSet.as_view({'post': 'add_item'})(request).status_code
        self.assertEqual(self.run_parallel(add, 8), [201] * 8)
        self.assertEqual(Cart.objects.get(user=self.customer).items.get().quantity, 8)

    def test_checkout_preserves_a_concurrent_cart_addition(self):
        from apps.orders.models import Address
        from apps.orders.views import OrderViewSet
        from apps.shopping.models import CartItem
        self.inventory.quantity = 20
        self.inventory.save()
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(cart=cart, product_variant=self.variant, quantity=2)
        address = Address.objects.create(user=self.customer, city='Dakar')
        def request(i):
            if i == 0:
                payload = {'store': str(self.store.pk), 'address': str(address.pk), 'delivery_type': 'pickup',
                           'payment_method': 'wave', 'items': [{'product_variant': str(self.variant.pk), 'quantity': 1}]}
                view = OrderViewSet.as_view({'post': 'checkout'})
            else:
                payload = {'product_variant': str(self.variant.pk), 'quantity': 1}
                view = CartViewSet.as_view({'post': 'add_item'})
            req = APIRequestFactory().post('/test/', payload, format='json')
            force_authenticate(req, self.customer)
            return view(req).status_code
        self.assertEqual(self.run_parallel(request), [201, 201])
        self.assertEqual(cart.items.get().quantity, 2)

    def test_concurrent_payments_keep_daily_statistics_exact(self):
        from apps.payments.models import Payment
        orders = [Order.objects.create(customer=self.customer, store=self.store, total_amount=1000) for _ in range(8)]
        payments = [Payment.objects.create(order=order, amount=1000, method='wave') for order in orders]
        self.run_parallel(lambda i: complete_payment(payments[i]), 8)
        stat = SalesStatistic.objects.get(store=self.store)
        self.assertEqual(stat.total_orders, 8)
        self.assertEqual(stat.total_sales, 8000)

    def test_two_initiations_create_only_one_provider_transaction(self):
        from time import sleep
        from types import SimpleNamespace
        from unittest.mock import patch
        from django.test import override_settings
        from apps.payments.models import Payment
        from apps.payments.views import PaymentViewSet
        order = Order.objects.create(customer=self.customer, store=self.store, total_amount=1000)
        payment = Payment.objects.create(order=order, amount=1000, method='wave')
        def provider(*args, **kwargs):
            sleep(.1)
            return SimpleNamespace(is_error=False, json=lambda: {'order_id': 'single-provider-session', 'checkout_url': 'https://pay.example.test/session'})
        def initiate(i):
            request = APIRequestFactory().post('/initiate/')
            force_authenticate(request, self.customer)
            return PaymentViewSet.as_view({'post': 'initiate'})(request, pk=payment.pk).status_code
        with override_settings(PAYMENT_SANDBOX=False, NABOOPAY_API_KEY='local-mocked-key'), patch('apps.payments.gateways.httpx.post', side_effect=provider) as send:
            self.assertEqual(self.run_parallel(initiate), [200, 200])
            self.assertEqual(send.call_count, 1)

    def test_unpaid_order_cannot_be_assigned_to_a_driver(self):
        from django.core.exceptions import ValidationError
        from apps.orders.models import Delivery, Driver
        order = Order.objects.create(customer=self.customer, store=self.store, total_amount=1000)
        delivery = Delivery.objects.create(order=order)
        driver = Driver.objects.create(user=self.customer, availability_status=Driver.AvailabilityStatus.AVAILABLE)
        with self.assertRaises(ValidationError):
            delivery.assign_driver(driver)
        delivery.refresh_from_db()
        self.assertIsNone(delivery.driver_id)
        self.assertEqual(delivery.status, Delivery.Status.PENDING)

    def test_concurrent_checkout_retries_create_one_order_and_payment(self):
        from uuid import uuid4
        from apps.orders.models import Address
        from apps.orders.views import OrderViewSet
        from apps.payments.models import Payment
        address = Address.objects.create(user=self.customer, city='Dakar')
        payload = {'checkout_key': str(uuid4()), 'store': str(self.store.pk), 'address': str(address.pk),
                   'delivery_type': 'pickup', 'payment_method': 'wave',
                   'items': [{'product_variant': str(self.variant.pk), 'quantity': 1}]}
        def checkout(i):
            request = APIRequestFactory().post('/checkout/', payload, format='json')
            force_authenticate(request, self.customer)
            response = OrderViewSet.as_view({'post': 'checkout'})(request)
            return response.status_code, response.data['id']
        results = self.run_parallel(checkout, 8)
        self.assertEqual(sorted(status for status, _ in results), [200] * 7 + [201])
        self.assertEqual(len({order_id for _, order_id in results}), 1)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 1)
        payload['items'][0]['quantity'] = 2
        request = APIRequestFactory().post('/checkout/', payload, format='json')
        force_authenticate(request, self.customer)
        self.assertEqual(OrderViewSet.as_view({'post': 'checkout'})(request).status_code, 409)
