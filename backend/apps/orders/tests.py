"""
Tests pour le cycle de vie livreur/livraison : affectation, transitions de
statut, et répercussion sur le statut de la commande.
"""
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User, Role, UserRole
from apps.catalog.models import Store
from apps.orders.models import Delivery, Driver, Order


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
        self.order = Order.objects.create(customer=self.customer, store=self.store, total_amount=5000)
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
