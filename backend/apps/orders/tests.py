"""
Tests pour le cycle de vie livreur/livraison : affectation, transitions de
statut, et répercussion sur le statut de la commande.
"""
from django.test import TestCase, TransactionTestCase
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User, Role, UserRole
from apps.catalog.models import Inventory, Product, ProductVariant, Store
from apps.orders.models import Delivery, DeliveryTracking, DeliveryZone, Driver, Order
from apps.payments.models import Payment


class DeliveryLifecycleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        for role_name in (Role.RoleName.MERCHANT, Role.RoleName.DRIVER, Role.RoleName.CLIENT):
            Role.objects.get_or_create(name=role_name)

        self.merchant = self._make_user("merchant@example.com", Role.RoleName.MERCHANT)
        self.other_merchant = self._make_user("other-merchant@example.com", Role.RoleName.MERCHANT)
        self.driver_user = self._make_user("driver@example.com", Role.RoleName.DRIVER)
        self.customer = self._make_user("client@example.com", Role.RoleName.CLIENT)

        self.store = Store.objects.create(owner=self.merchant, name="Boutique")
        self.driver = Driver.objects.create(user=self.driver_user, availability_status=Driver.AvailabilityStatus.AVAILABLE)
        self.order = Order.objects.create(
            customer=self.customer, store=self.store, total_amount=5000, status=Order.Status.PAID
        )
        self.delivery = Delivery.objects.create(order=self.order)

    def _make_user(self, email, role_name):
        user = User.objects.create_user(username=email, email=email, password="testpass123", is_verified=True)
        role = Role.objects.get(name=role_name)
        UserRole.objects.create(user=user, role=role)
        return user

    def test_owner_merchant_can_assign_driver(self):
        self.client.force_authenticate(self.merchant)
        response = self.client.post(f"/api/orders/deliveries/{self.delivery.id}/assign/", {"driver": str(self.driver.id)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.driver_id, self.driver.id)
        self.assertEqual(self.delivery.status, Delivery.Status.ASSIGNED)

    def test_other_merchant_cannot_assign_driver(self):
        self.client.force_authenticate(self.other_merchant)
        response = self.client.post(f"/api/orders/deliveries/{self.delivery.id}/assign/", {"driver": str(self.driver.id)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_full_status_transition_updates_order(self):
        self.delivery.assign_driver(self.driver)
        self.client.force_authenticate(self.driver_user)

        response = self.client.post(f"/api/orders/deliveries/{self.delivery.id}/status/", {"status": "picked_up"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "picked_up")

        response = self.client.post(f"/api/orders/deliveries/{self.delivery.id}/status/", {"status": "delivered"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.DELIVERED)

    def test_invalid_status_transition_is_rejected(self):
        # La livraison est encore "pending" : passer directement à "delivered" est invalide.
        self.delivery.assign_driver(self.driver)
        self.client.force_authenticate(self.driver_user)
        response = self.client.post(f"/api/orders/deliveries/{self.delivery.id}/status/", {"status": "delivered"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unassigned_driver_cannot_update_status(self):
        other_driver_user = self._make_user("driver2@example.com", Role.RoleName.DRIVER)
        Driver.objects.create(user=other_driver_user)
        self.delivery.assign_driver(self.driver)

        self.client.force_authenticate(other_driver_user)
        response = self.client.post(f"/api/orders/deliveries/{self.delivery.id}/status/", {"status": "picked_up"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_me_creates_profile_lazily(self):
        new_driver_user = self._make_user("newdriver@example.com", Role.RoleName.DRIVER)
        self.client.force_authenticate(new_driver_user)
        response = self.client.get("/api/orders/drivers/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Driver.objects.filter(user=new_driver_user).exists())

    def test_order_cannot_be_modified_directly(self):
        self.client.force_authenticate(self.customer)
        response = self.client.patch(
            f"/api/orders/{self.order.id}/",
            {"address": None, "store": str(self.store.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class CheckoutStockTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        for role_name in (Role.RoleName.MERCHANT, Role.RoleName.CLIENT):
            Role.objects.get_or_create(name=role_name)
        self.merchant = self._make_user("stock-merchant@example.com", Role.RoleName.MERCHANT)
        self.customer = self._make_user("stock-client@example.com", Role.RoleName.CLIENT)
        self.store = Store.objects.create(
            owner=self.merchant, name="Boutique active", status=Store.Status.ACTIVE
        )
        self.product = Product.objects.create(
            store=self.store, name="Produit stock", base_price=1000, status=Product.Status.ACTIVE
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="STOCK-1", price=1000
        )
        self.inventory = Inventory.objects.create(variant=self.variant, quantity=2)

    def _make_user(self, email, role_name):
        user = User.objects.create_user(username=email, email=email, password="testpass123", is_verified=True)
        UserRole.objects.create(user=user, role=Role.objects.get(name=role_name))
        return user

    def test_checkout_reserves_then_commits_stock_after_payment(self):
        self.client.force_authenticate(self.customer)
        from apps.orders.models import Address
        address = Address.objects.create(user=self.customer, label="Maison", city="Dakar")
        response = self.client.post("/api/orders/checkout/", {
            "store": str(self.store.id),
            "address": str(address.id),
            "delivery_type": "standard",
            "payment_method": "wave",
            "items": [{"product_variant": str(self.variant.id), "quantity": 1}],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 2)
        self.assertEqual(self.inventory.reserved_quantity, 1)

        payment = Payment.objects.get(order_id=response.data["id"])
        self.client.post(
            f"/api/payments/{payment.id}/sandbox-confirm/", {"outcome": "success"}, format="json"
        )
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 1)
        self.assertEqual(self.inventory.reserved_quantity, 0)

    def test_checkout_rejects_more_than_available_stock(self):
        self.client.force_authenticate(self.customer)
        from apps.orders.models import Address
        address = Address.objects.create(user=self.customer, label="Maison", city="Dakar")
        response = self.client.post("/api/orders/checkout/", {
            "store": str(self.store.id),
            "address": str(address.id),
            "payment_method": "wave",
            "items": [{"product_variant": str(self.variant.id), "quantity": 3}],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.filter(customer=self.customer).exists())


class DeliveryGeometryTests(TestCase):
    def test_polygon_contains_inside_outside_and_boundary_points(self):
        zone = DeliveryZone.objects.create(
            name="Centre",
            boundary_geojson={
                "type": "Polygon",
                "coordinates": [[
                    [-18.1, 14.7], [-18.0, 14.7], [-18.0, 14.8],
                    [-18.1, 14.8], [-18.1, 14.7],
                ]],
            },
        )

        self.assertTrue(zone.contains(14.75, -18.05))
        self.assertTrue(zone.contains(14.7, -18.05))
        self.assertFalse(zone.contains(14.9, -18.05))
        self.assertFalse(zone.contains("invalid", -18.05))

    def test_driver_current_position_uses_latest_tracking(self):
        user = User.objects.create_user(
            username="position-driver@example.com",
            email="position-driver@example.com",
            password="testpass123",
        )
        merchant = User.objects.create_user(
            username="position-merchant@example.com",
            email="position-merchant@example.com",
            password="testpass123",
        )
        customer = User.objects.create_user(
            username="position-customer@example.com",
            email="position-customer@example.com",
            password="testpass123",
        )
        driver = Driver.objects.create(user=user, vehicle_type="moto")
        store = Store.objects.create(owner=merchant, name="Position store")
        order = Order.objects.create(customer=customer, store=store, total_amount=1000)
        delivery = Delivery.objects.create(order=order, driver=driver)
        DeliveryTracking.objects.create(
            delivery=delivery, latitude=14.7, longitude=-17.45
        )

        position = driver.current_position()

        self.assertEqual(position["latitude"], Decimal("14.7"))
        self.assertEqual(position["longitude"], Decimal("-17.45"))


class StockRegressionTests(TestCase):
    """Paiement tardif, annulation et réservation partagée entre commandes."""

    setUp = CheckoutStockTests.setUp
    _make_user = CheckoutStockTests._make_user

    def checkout(self, items=None):
        from apps.orders.models import Address
        self.client.force_authenticate(self.customer)
        address = Address.objects.create(user=self.customer, label="Maison", city="Dakar")
        response = self.client.post("/api/orders/checkout/", {
            "store": str(self.store.pk), "address": str(address.pk), "payment_method": "wave",
            "items": items or [{"product_variant": str(self.variant.pk), "quantity": 1}],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return Payment.objects.get(order_id=response.data["id"])

    def confirm(self, payment, outcome="success"):
        response = self.client.post(
            f"/api/payments/{payment.pk}/sandbox-confirm/", {"outcome": outcome}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        payment.refresh_from_db()
        return payment

    def test_expired_payment_reclaims_stock_once(self):
        from datetime import timedelta
        from django.core.management import call_command
        from django.utils import timezone
        payment = self.checkout()
        payment.expires_at = timezone.now() - timedelta(minutes=1)
        payment.save(update_fields=["expires_at"])
        call_command("expire_pending_payments")
        self.confirm(payment)
        self.confirm(payment)
        self.inventory.refresh_from_db()
        order = Order.objects.get(pk=payment.order_id)
        self.assertEqual((order.status, order.stock_status), (Order.Status.PAID, Order.StockStatus.COMMITTED))
        self.assertEqual((self.inventory.quantity, self.inventory.reserved_quantity), (1, 0))
        self.assertFalse(payment.refunds.exists())

    def test_late_payment_does_not_take_another_orders_reservation(self):
        payment = self.checkout()
        self.confirm(payment, "failed")
        other = self.checkout([{"product_variant": str(self.variant.pk), "quantity": 2}])
        self.confirm(payment)
        self.confirm(payment)
        self.inventory.refresh_from_db()
        self.assertEqual((self.inventory.quantity, self.inventory.reserved_quantity), (2, 2))
        self.assertEqual(Order.objects.get(pk=payment.order_id).status, Order.Status.CANCELLED)
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertEqual(payment.refunds.count(), 1)
        self.assertEqual(payment.refunds.get().amount, payment.amount)
        self.confirm(other)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 0)

    def test_cancel_then_signed_webhook_records_payment_and_refund(self):
        import hashlib
        import hmac
        import json
        from django.test import override_settings
        payment = self.checkout()
        payment.provider_ref = "annulation-webhook"
        payment.save(update_fields=["provider_ref"])
        self.assertEqual(self.client.post(f"/api/orders/{payment.order_id}/cancel/").status_code, 200)
        body = json.dumps({"order_id": payment.provider_ref, "transaction_status": "completed",
                           "amount": str(payment.amount), "currency": "XOF"}).encode()
        signature = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
        with override_settings(NABOOPAY_WEBHOOK_SECRET="test-secret"):
            for _ in range(2):
                response = self.client.post("/api/payments/webhooks/naboopay/", body,
                                            content_type="application/json", HTTP_X_SIGNATURE=signature)
                self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        order = Order.objects.get(pk=payment.order_id)
        self.inventory.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(order.delivery.status, Delivery.Status.CANCELLED)
        self.assertEqual(payment.refunds.count(), 1)
        self.assertEqual((self.inventory.quantity, self.inventory.reserved_quantity), (2, 0))

    def test_cancelling_paid_order_restocks_and_requests_one_refund(self):
        payment = self.checkout()
        self.confirm(payment)
        response = self.client.post(f"/api/orders/{payment.order_id}/cancel/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post(f"/api/orders/{payment.order_id}/cancel/").status_code, 400)
        self.inventory.refresh_from_db()
        self.assertEqual((self.inventory.quantity, self.inventory.reserved_quantity), (2, 0))
        self.assertEqual(payment.refunds.count(), 1)




class ConcurrentCheckoutTests(TransactionTestCase):
    setUp = CheckoutStockTests.setUp
    _make_user = CheckoutStockTests._make_user

    def test_opposite_item_orders_do_not_deadlock(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier, local
        from time import sleep
        from unittest.mock import patch
        from django.db import close_old_connections, connection
        from rest_framework.test import APIRequestFactory, force_authenticate
        from apps.orders.models import Address
        from apps.orders.views import OrderViewSet
        if connection.vendor != "postgresql":
            self.skipTest("Ce test exige les verrous PostgreSQL.")
        second_product = Product.objects.create(store=self.store, name="Second", base_price=1000, status="active")
        second = ProductVariant.objects.create(product=second_product, sku="SECOND", price=1000)
        Inventory.objects.create(variant=second, quantity=2)
        address = Address.objects.create(user=self.customer, label="Maison", city="Dakar")
        barrier = Barrier(2)
        state = local()
        original = Inventory.reserve

        def reserve(inventory, quantity):
            result = original(inventory, quantity)
            state.calls = getattr(state, "calls", 0) + 1
            if state.calls == 1:
                # Laisse l'autre panier commencer pendant que le premier
                # conserve son verrou, sans imposer deux verrous distincts.
                sleep(0.1)
            return result

        def checkout(ids):
            close_old_connections()
            try:
                user = User.objects.get(pk=self.customer.pk)
                request = APIRequestFactory().post("/api/orders/checkout/", {
                    "store": str(self.store.pk), "address": str(address.pk), "payment_method": "wave",
                    "items": [{"product_variant": str(pk), "quantity": 1} for pk in ids],
                }, format="json")
                force_authenticate(request, user=user)
                barrier.wait(timeout=5)
                return OrderViewSet.as_view({"post": "checkout"})(request).status_code
            finally:
                connection.close()

        with patch.object(Inventory, "reserve", reserve), ThreadPoolExecutor(max_workers=2) as pool:
            tasks = [pool.submit(checkout, ids) for ids in [(self.variant.pk, second.pk), (second.pk, self.variant.pk)]]
            self.assertEqual([task.result(timeout=15) for task in tasks], [201, 201])
        self.assertEqual(Order.objects.count(), 2)
        self.assertEqual(list(Inventory.objects.values_list("reserved_quantity", flat=True)), [2, 2])
