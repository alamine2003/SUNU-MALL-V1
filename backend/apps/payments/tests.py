"""
Tests pour le paiement en mode sandbox : confirmation simulée, sécurité
d'accès (un client ne voit que ses propres paiements).
"""
import hashlib
import hmac
import json
from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User, Role, UserRole
from apps.catalog.models import Store
from apps.orders.models import Order
from apps.payments.models import Payment, Transaction


class PaymentSandboxTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        Role.objects.get_or_create(name=Role.RoleName.CLIENT)
        Role.objects.get_or_create(name=Role.RoleName.MERCHANT)

        self.customer = self._make_user("client@example.com", Role.RoleName.CLIENT)
        self.other_customer = self._make_user("other@example.com", Role.RoleName.CLIENT)
        merchant = self._make_user("merchant@example.com", Role.RoleName.MERCHANT)
        store = Store.objects.create(owner=merchant, name="Boutique")

        self.order = Order.objects.create(customer=self.customer, store=store, total_amount=10000)
        self.payment = Payment.objects.create(order=self.order, amount=10000, method="wave")

    def _make_user(self, email, role_name):
        user = User.objects.create_user(username=email, email=email, password="testpass123", is_verified=True)
        role = Role.objects.get(name=role_name)
        UserRole.objects.create(user=user, role=role)
        return user

    def test_customer_only_sees_own_payments(self):
        self.client.force_authenticate(self.other_customer)
        response = self.client.get("/api/payments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_initiate_returns_sandbox_response_by_default(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(f"/api/payments/{self.payment.id}/initiate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["sandbox"])
        self.payment.refresh_from_db()
        self.assertTrue(self.payment.provider_ref.startswith("SANDBOX-"))

    def test_sandbox_confirm_success_marks_payment_and_order_paid(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(f"/api/payments/{self.payment.id}/sandbox-confirm/", {"outcome": "success"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.SUCCESS)
        self.assertEqual(self.order.status, Order.Status.PAID)

    def test_sandbox_confirm_failure_does_not_advance_order(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(f"/api/payments/{self.payment.id}/sandbox-confirm/", {"outcome": "failed"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.FAILED)
        self.assertEqual(self.order.status, Order.Status.PENDING)

    def test_other_customer_cannot_confirm_payment(self):
        # Le paiement n'appartient pas à son périmètre : absent de son queryset,
        # donc 404 (et non 403, qui révélerait son existence).
        self.client.force_authenticate(self.other_customer)
        response = self.client.post(f"/api/payments/{self.payment.id}/sandbox-confirm/", {"outcome": "success"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

    @override_settings(PAYMENT_SANDBOX=False)
    def test_sandbox_confirm_disabled_outside_sandbox_mode(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(f"/api/payments/{self.payment.id}/sandbox-confirm/", {"outcome": "success"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_order_delete_is_disabled_to_preserve_payment_history(self):
        self.client.force_authenticate(self.customer)
        response = self.client.delete(f"/api/orders/{self.order.id}/")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Order.objects.filter(pk=self.order.id).exists())

    def test_expire_pending_payment_is_idempotent(self):
        self.payment.expires_at = timezone.now() - timedelta(minutes=1)
        self.payment.save(update_fields=["expires_at"])

        call_command("expire_pending_payments")
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.FAILED)

        call_command("expire_pending_payments")
        self.assertEqual(Payment.objects.filter(status=Payment.Status.FAILED).count(), 1)


class NabooPayTests(PaymentSandboxTests):
    @override_settings(
        PAYMENT_SANDBOX=False,
        NABOOPAY_API_KEY="test-api-key",
        NABOOPAY_BASE_URL="https://api.naboopay.test",
        NABOOPAY_WEBHOOK_SECRET="webhook-secret",
    )
    @patch("apps.payments.gateways.httpx.post")
    def test_initiate_creates_and_reuses_naboopay_checkout(self, post):
        import httpx

        post.return_value = httpx.Response(
            201,
            json={"data": {"order_id": "naboo-order-1", "checkout_url": "https://pay.naboo.test/1"}},
        )
        self.client.force_authenticate(self.customer)

        response = self.client.post(f"/api/payments/{self.payment.id}/initiate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["sandbox"])
        self.assertEqual(response.data["checkout_url"], "https://pay.naboo.test/1")
        self.assertEqual(post.call_count, 1)
        sent_payload = post.call_args.kwargs["json"]
        self.assertEqual(sent_payload["selected_payment_method"], "wave")
        self.assertEqual(sent_payload["currency"], "XOF")

        response = self.client.post(f"/api/payments/{self.payment.id}/initiate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(post.call_count, 1)

    @override_settings(NABOOPAY_WEBHOOK_SECRET="webhook-secret")
    def test_naboopay_webhook_confirms_payment_idempotently(self):
        self.payment.provider_ref = "naboo-order-1"
        self.payment.save(update_fields=["provider_ref"])
        payload = {
            "order_id": "naboo-order-1",
            "transaction_status": "completed",
            "amount": 10000,
            "currency": "XOF",
        }
        body = json.dumps(payload, separators=(",", ":")).encode()
        signature = hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest()

        first = self.client.post(
            "/api/payments/webhooks/naboopay/",
            data=body,
            content_type="application/json",
            HTTP_X_SIGNATURE=signature,
        )
        second = self.client.post(
            "/api/payments/webhooks/naboopay/",
            data=body,
            content_type="application/json",
            HTTP_X_SIGNATURE=signature,
        )

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.SUCCESS)
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertEqual(Transaction.objects.filter(payment=self.payment).count(), 1)

    @override_settings(NABOOPAY_WEBHOOK_SECRET="webhook-secret")
    def test_naboopay_webhook_rejects_invalid_signature(self):
        response = self.client.post(
            "/api/payments/webhooks/naboopay/",
            data=b'{"order_id":"naboo-order-1"}',
            content_type="application/json",
            HTTP_X_SIGNATURE="bad-signature",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
