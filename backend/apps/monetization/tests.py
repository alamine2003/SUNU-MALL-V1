from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Product, Store
from apps.monetization.models import SponsoredProduct, Subscription, SubscriptionPlan
from apps.users.models import Role, User, UserRole


class MonetizationSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        merchant_role, _ = Role.objects.get_or_create(name=Role.RoleName.MERCHANT)
        self.merchant = User.objects.create_user(
            username="monetization@example.com", email="monetization@example.com",
            password="testpass123", is_verified=True,
        )
        UserRole.objects.create(user=self.merchant, role=merchant_role)
        self.store = Store.objects.create(
            owner=self.merchant, name="Boutique", status=Store.Status.ACTIVE
        )
        self.other = User.objects.create_user(
            username="other-monetization@example.com", email="other-monetization@example.com",
            password="testpass123", is_verified=True,
        )
        UserRole.objects.create(user=self.other, role=merchant_role)
        self.other_store = Store.objects.create(
            owner=self.other, name="Autre boutique", status=Store.Status.ACTIVE
        )

    def test_merchant_cannot_modify_subscription_fields_directly(self):
        plan = SubscriptionPlan.objects.create(
            name="Premium", price=1000, billing_cycle="monthly", max_products=20
        )
        self.client.force_authenticate(self.merchant)
        create_response = self.client.post(
            f"/api/monetization/subscription-plans/{plan.id}/subscribe/",
            {"payment_method": "wave"}, format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        subscription_id = create_response.data["subscription"]["id"]

        response = self.client.patch(
            f"/api/monetization/subscriptions/{subscription_id}/",
            {"status": "active"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(
            Subscription.objects.get(pk=subscription_id).status,
            Subscription.Status.PENDING,
        )

    def test_subscription_rejects_unsupported_payment_method(self):
        plan = SubscriptionPlan.objects.create(
            name="Premium", price=1000, billing_cycle="monthly", max_products=20
        )
        self.client.force_authenticate(self.merchant)
        response = self.client.post(
            f"/api/monetization/subscription-plans/{plan.id}/subscribe/",
            {"payment_method": "card"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Subscription.objects.filter(subscriber_id=self.merchant.id).exists())

    def test_campaign_cannot_sponsor_a_product_from_another_store(self):
        product = Product.objects.create(
            store=self.other_store, name="Produit externe", base_price=1000,
            status=Product.Status.ACTIVE,
        )
        self.client.force_authenticate(self.merchant)
        response = self.client.post(
            "/api/monetization/sponsored-products/",
            {
                "product": str(product.id), "store": str(self.store.id),
                "daily_budget": "1000", "starts_at": "2026-01-01",
                "ends_at": "2026-01-31", "status": "active",
            }, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(SponsoredProduct.objects.exists())


class SubscriptionResumeTests(TestCase):
    setUp = MonetizationSecurityTests.setUp

    def subscribe(self, plan=None):
        plan = plan or SubscriptionPlan.objects.create(name="Reprise", price=1000, billing_cycle="monthly")
        self.client.force_authenticate(self.merchant)
        response = self.client.post(f"/api/monetization/subscription-plans/{plan.pk}/subscribe/", {"payment_method": "wave"}, format="json")
        return plan, response

    def test_reopening_returns_same_pending_payment(self):
        from apps.payments.models import Payment
        plan, first = self.subscribe()
        self.assertEqual(first.status_code, 201)
        _, resumed = self.subscribe(plan)
        self.assertEqual(resumed.status_code, 200)
        self.assertEqual(resumed.data["payment"]["id"], first.data["payment"]["id"])
        self.assertEqual(Subscription.objects.filter(subscriber_id=self.merchant.pk).count(), 1)
        self.assertEqual(Payment.objects.count(), 1)

    def test_other_plan_requires_cancelling_pending_subscription(self):
        from apps.payments.models import Payment
        _, first = self.subscribe()
        other_plan = SubscriptionPlan.objects.create(name="Autre", price=2000, billing_cycle="monthly")
        _, blocked = self.subscribe(other_plan)
        self.assertEqual(blocked.status_code, 409)
        response = self.client.post(f'/api/monetization/subscriptions/{first.data["subscription"]["id"]}/cancel/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Payment.objects.get(pk=first.data["payment"]["id"]).status, Payment.Status.FAILED)
        _, created = self.subscribe(other_plan)
        self.assertEqual(created.status_code, 201)

    def test_expired_pending_payment_can_be_replaced(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.payments.models import Payment
        plan, first = self.subscribe()
        Payment.objects.filter(pk=first.data["payment"]["id"]).update(expires_at=timezone.now()-timedelta(minutes=1))
        _, resumed = self.subscribe(plan)
        self.assertEqual(resumed.status_code, 201)
        self.assertNotEqual(resumed.data["payment"]["id"], first.data["payment"]["id"])
        self.assertEqual(Subscription.objects.get(pk=first.data["subscription"]["id"]).status, Subscription.Status.CANCELLED)

    def test_payment_creation_failure_does_not_leave_a_blocking_subscription(self):
        from unittest.mock import patch
        with patch("apps.payments.models.Payment.objects.create", side_effect=RuntimeError("échec simulé")):
            with self.assertRaises(RuntimeError):
                self.subscribe()
        self.assertFalse(Subscription.objects.filter(subscriber_id=self.merchant.pk).exists())

    def test_late_success_does_not_reactivate_cancelled_subscription(self):
        from apps.payments.models import Payment
        _, first = self.subscribe()
        self.client.post(f'/api/monetization/subscriptions/{first.data["subscription"]["id"]}/cancel/')
        for _ in range(2):
            response = self.client.post(f'/api/payments/{first.data["payment"]["id"]}/sandbox-confirm/', {"outcome": "success"})
            self.assertEqual(response.status_code, 200)
        subscription = Subscription.objects.get(pk=first.data["subscription"]["id"])
        payment = Payment.objects.get(pk=first.data["payment"]["id"])
        self.assertEqual(subscription.status, Subscription.Status.CANCELLED)
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertEqual(payment.refunds.count(), 1)


class SubscriptionMaintenanceTests(TestCase):
    setUp = MonetizationSecurityTests.setUp

    def test_reminders_are_sent_once_and_do_not_reactivate_cancelled_subscriptions(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.monetization.models import Notification
        from apps.monetization.tasks import maintain_subscriptions
        plan = SubscriptionPlan.objects.create(name='Maintenance', price=1000, billing_cycle='monthly')
        subscription = Subscription.objects.create(plan=plan, subscriber_type='merchant', subscriber_id=self.merchant.pk, status='active', starts_at=timezone.now().date()-timedelta(days=30), ends_at=timezone.now().date()-timedelta(days=1))
        maintain_subscriptions()
        maintain_subscriptions()
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'expired')
        self.assertEqual(Notification.objects.filter(metadata__subscription_id=str(subscription.pk)).count(), 1)
        subscription.status = 'cancelled'
        subscription.save()
        maintain_subscriptions()
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'cancelled')
