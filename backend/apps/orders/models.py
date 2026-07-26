"""
Commandes et livraison.
"""
import uuid
from django.db import models
from django.utils import timezone
from apps.users.models import User
from apps.catalog.models import ProductVariant, Store


class DeliveryZone(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    boundary_geojson = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def contains(self, lat, lng):
        # Simplified check, should use proper GeoJSON library
        return True

    def __str__(self):
        return self.name


class Driver(models.Model):
    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        BUSY = 'busy', 'Busy'
        OFFLINE = 'offline', 'Offline'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    zone = models.ForeignKey(DeliveryZone, on_delete=models.SET_NULL, null=True, related_name='drivers')
    vehicle_type = models.CharField(max_length=100)
    availability_status = models.CharField(max_length=50, choices=AvailabilityStatus.choices, default=AvailabilityStatus.OFFLINE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_available(self):
        return self.availability_status == self.AvailabilityStatus.AVAILABLE

    def current_position(self):
        # Should get last known position from DeliveryTracking
        return None

    def __str__(self):
        return f"Driver {self.user.get_full_name()}"


class Delivery(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ASSIGNED = 'assigned', 'Assigned'
        PICKED_UP = 'picked_up', 'Picked Up'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField('Order', on_delete=models.CASCADE, related_name='delivery')
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def assign_driver(self, driver):
        self.driver = driver
        self.status = self.Status.ASSIGNED
        self.save()
        self._notify_driver_assigned()

    def _notify_driver_assigned(self):
        from apps.monetization.models import Notification

        subject = "Nouvelle course qui vous a été affectée"
        message = (
            f"Bonjour {self.driver.user.first_name},\n\n"
            f"Une nouvelle course vous a été affectée (commande {self.order.id}).\n"
            "Connectez-vous à votre espace livreur pour voir le détail et démarrer la livraison.\n\n"
            "Merci."
        )
        notification = Notification.objects.create(
            user=self.driver.user,
            channel=Notification.Channel.EMAIL,
            subject=subject,
            message=message,
            metadata={"delivery_id": str(self.id), "order_id": str(self.order.id)},
        )
        notification.send()

    def auto_assign(self):
        """
        Affecte automatiquement le livreur disponible ayant le moins de
        courses actives (assigned/picked_up) en ce moment — pour ne pas
        dépendre d'une affectation manuelle à chaque commande, ce qui ne
        tient pas à l'échelle (des centaines de commandes). Ne fait rien
        si un livreur est déjà affecté, ou si aucun n'est disponible : la
        course reste alors "pending", affectable à la main en filet de
        secours (menu déroulant déjà existant côté commerçant/admin).
        """
        if self.driver_id is not None:
            return None

        candidate = (
            Driver.objects.filter(availability_status=Driver.AvailabilityStatus.AVAILABLE)
            .annotate(
                active_count=models.Count(
                    "deliveries",
                    filter=models.Q(deliveries__status__in=[self.Status.ASSIGNED, self.Status.PICKED_UP]),
                )
            )
            .order_by("active_count")
            .first()
        )
        if candidate:
            self.assign_driver(candidate)
        return candidate

    def mark_delivered(self):
        self.status = self.Status.DELIVERED
        self.delivered_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Delivery for Order {self.order.id}"


class DeliveryTracking(models.Model):
    id = models.AutoField(primary_key=True)
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name='trackings')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']

    def broadcast(self):
        # Implement websocket/broadcast logic here
        pass

    def __str__(self):
        return f"Tracking {self.delivery.id} at {self.recorded_at}"


class Address(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=255)
    street = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Senegal')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def distance_to(self, lat, lng):
        # Simplified distance calculation
        if self.latitude and self.longitude and lat and lng:
            return ((self.latitude - lat)**2 + (self.longitude - lng)**2)**0.5
        return None

    def __str__(self):
        return f"{self.label} for {self.user.get_full_name()}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        PROCESSING = 'processing', 'Processing'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='orders')
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, related_name='orders')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def can_be_cancelled(self):
        return self.status in [self.Status.PENDING, self.Status.PAID]

    def recalculate_total(self):
        self.total_amount = sum(item.subtotal() for item in self.items.all()) + self.delivery_fee
        self.save()

    def change_status(self, new_status):
        old_status = self.status
        self.status = new_status
        self.save()
        OrderHistory.objects.create(
            order=self,
            previous_status=old_status,
            new_status=new_status,
            changed_by=self.customer
        )
        from apps.analytics.models import SalesStatistic
        SalesStatistic.compute_for_store(self.store, self.created_at.date())

    def __str__(self):
        return f"Order {self.id} - {self.customer.email}"


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def subtotal(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.quantity} x {self.product_variant.product.name}"


class OrderHistory(models.Model):
    id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='history')
    previous_status = models.CharField(max_length=50, blank=True)
    new_status = models.CharField(max_length=50)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='order_changes')
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"Order {self.order.id}: {self.previous_status} → {self.new_status}"
