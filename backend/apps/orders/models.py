"""
Commandes et livraison.
"""
import uuid
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from apps.users.models import User
from apps.catalog.models import ProductVariant, Store


class DeliveryZone(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    boundary_geojson = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def contains(self, lat, lng):
        """Teste un point [lat, lng] dans un GeoJSON Polygon/MultiPolygon."""
        try:
            point_lat, point_lng = float(lat), float(lng)
        except (TypeError, ValueError):
            return False
        geometry = self.boundary_geojson
        if isinstance(geometry, dict) and geometry.get("type") == "Feature":
            geometry = geometry.get("geometry")
        if not isinstance(geometry, dict):
            return False

        def in_ring(ring):
            if not isinstance(ring, list) or len(ring) < 4:
                return False
            inside = False
            for first, second in zip(ring, ring[1:] + ring[:1]):
                try:
                    first_lng, first_lat = float(first[0]), float(first[1])
                    second_lng, second_lat = float(second[0]), float(second[1])
                except (IndexError, TypeError, ValueError):
                    return False
                cross = (point_lng - first_lng) * (second_lat - first_lat) - (point_lat - first_lat) * (second_lng - first_lng)
                if abs(cross) < 1e-12 and min(first_lng, second_lng) <= point_lng <= max(first_lng, second_lng) and min(first_lat, second_lat) <= point_lat <= max(first_lat, second_lat):
                    return True
                if (first_lat > point_lat) != (second_lat > point_lat):
                    intersection_lng = (second_lng - first_lng) * (point_lat - first_lat) / (second_lat - first_lat) + first_lng
                    if point_lng < intersection_lng:
                        inside = not inside
            return inside

        def in_polygon(polygon):
            return bool(polygon) and in_ring(polygon[0]) and not any(in_ring(hole) for hole in polygon[1:])

        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates")
        if geometry_type == "Polygon":
            return in_polygon(coordinates)
        if geometry_type == "MultiPolygon":
            return any(in_polygon(polygon) for polygon in coordinates or [])
        return False

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
        tracking = DeliveryTracking.objects.filter(delivery__driver=self).first()
        if not tracking:
            return None
        return {
            "latitude": tracking.latitude,
            "longitude": tracking.longitude,
            "recorded_at": tracking.recorded_at,
        }

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
    order = models.OneToOneField('Order', on_delete=models.PROTECT, related_name='delivery')
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @transaction.atomic
    def assign_driver(self, driver):
        order = Order.objects.select_for_update().get(pk=self.order_id)
        delivery = Delivery.objects.select_for_update().get(pk=self.pk)
        if order.status not in {Order.Status.PAID, Order.Status.PROCESSING}:
            raise ValidationError("Seule une commande payée peut être affectée.")
        if delivery.status not in {self.Status.PENDING, self.Status.ASSIGNED}:
            raise ValidationError("Cette livraison ne peut plus être réaffectée.")
        if driver.availability_status != Driver.AvailabilityStatus.AVAILABLE:
            raise ValidationError("Ce livreur n'est pas disponible.")
        delivery.driver = driver
        delivery.status = self.Status.ASSIGNED
        delivery.save(update_fields=['driver', 'status', 'updated_at'])
        self.refresh_from_db()
        transaction.on_commit(self._notify_driver_assigned)

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

    def cancel(self):
        """Annule la course (appelé quand le client annule sa commande) et prévient le livreur s'il en avait déjà un."""
        had_driver = self.driver_id is not None
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status"])
        if had_driver:
            self._notify_driver_cancelled()

    def _notify_driver_cancelled(self):
        from apps.monetization.models import Notification

        subject = "Course annulée"
        message = (
            f"Bonjour {self.driver.user.first_name},\n\n"
            f"La commande {str(self.order.id)[:8]} qui vous avait été affectée vient d'être annulée "
            "par le client. Vous n'avez plus besoin d'intervenir sur cette livraison.\n\n"
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
        if self.latitude is not None and self.longitude is not None and lat is not None and lng is not None:
            from .pricing import haversine_km
            return haversine_km(self.latitude, self.longitude, lat, lng)
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

    class StockStatus(models.TextChoices):
        NONE = 'none', 'Aucune réservation'
        RESERVED = 'reserved', 'Réservé'
        COMMITTED = 'committed', 'Déduit'
        RELEASED = 'released', 'Libéré'

    # Périmètre commun aux chiffres de vente (journalier et résumé).
    SALES_STATUSES = (Status.PAID, Status.PROCESSING, Status.SHIPPED, Status.DELIVERED)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name='orders')
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, related_name='orders')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    stock_status = models.CharField(max_length=20, choices=StockStatus.choices, default=StockStatus.NONE)
    checkout_key = models.UUIDField(null=True, blank=True, editable=False)
    checkout_fingerprint = models.CharField(max_length=64, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

        constraints = [
            models.UniqueConstraint(fields=['customer', 'checkout_key'], name='unique_customer_checkout_key'),
        ]

    def can_be_cancelled(self):
        return self.status in [self.Status.PENDING, self.Status.PAID]

    def recalculate_total(self):
        self.total_amount = sum(item.subtotal() for item in self.items.all()) + self.delivery_fee
        self.save(update_fields=["total_amount", "updated_at"])

    def change_status(self, new_status):
        allowed_transitions = {
            self.Status.PENDING: {self.Status.PAID, self.Status.CANCELLED},
            self.Status.PAID: {self.Status.PROCESSING, self.Status.SHIPPED, self.Status.DELIVERED, self.Status.CANCELLED},
            self.Status.PROCESSING: {self.Status.SHIPPED, self.Status.DELIVERED, self.Status.CANCELLED},
            self.Status.SHIPPED: {self.Status.DELIVERED, self.Status.CANCELLED},
            self.Status.DELIVERED: set(),
            self.Status.CANCELLED: set(),
        }
        with transaction.atomic():
            locked = type(self).objects.select_for_update().get(pk=self.pk)
            if new_status == locked.status:
                return locked
            if new_status not in allowed_transitions.get(locked.status, set()):
                raise ValidationError(f"Transition de commande invalide : {locked.status} → {new_status}.")
            old_status = locked.status
            locked.status = new_status
            locked.save(update_fields=["status", "updated_at"])
            OrderHistory.objects.create(
                order=locked,
                previous_status=old_status,
                new_status=new_status,
                changed_by=locked.customer,
            )
            from apps.analytics.models import SalesStatistic
            SalesStatistic.compute_for_store(locked.store, locked.created_at.date())
            self.refresh_from_db()
            return self

    def commit_reserved_stock(self):
        """Déduit le stock une fois, ou refuse si une réservation libérée est perdue.

        Un succès tardif peut suivre une expiration. Dans ce cas le stock
        doit encore être disponible pour toutes les lignes, sans prendre
        les réservations d'autres commandes. Les commandes historiques
        sans réservation suivent cette même vérification.
        """
        from apps.catalog.models import Inventory

        with transaction.atomic():
            order = type(self).objects.select_for_update().get(pk=self.pk)
            if order.stock_status == self.StockStatus.COMMITTED:
                return True
            stocks = []
            for item in order.items.order_by("product_variant_id"):
                inventory = Inventory.objects.select_for_update().get(variant_id=item.product_variant_id)
                if order.stock_status == self.StockStatus.RESERVED:
                    if inventory.reserved_quantity < item.quantity or inventory.quantity < item.quantity:
                        raise ValidationError("Le stock réservé de la commande est incohérent.")
                elif inventory.available() < item.quantity:
                    return False
                stocks.append((item, inventory))
            # Rien n'est écrit avant d'avoir vérifié toutes les lignes.
            for item, inventory in stocks:
                inventory.quantity -= item.quantity
                if order.stock_status == self.StockStatus.RESERVED:
                    inventory.reserved_quantity -= item.quantity
                inventory.save(update_fields=["quantity", "reserved_quantity", "updated_at"])
            order.stock_status = self.StockStatus.COMMITTED
            order.save(update_fields=["stock_status", "updated_at"])
            self.refresh_from_db()
            return True

    def release_stock(self):
        """Libère une réservation ou remet en stock une vente annulée."""
        from apps.catalog.models import Inventory

        with transaction.atomic():
            order = type(self).objects.select_for_update().get(pk=self.pk)
            if order.stock_status not in {self.StockStatus.RESERVED, self.StockStatus.COMMITTED}:
                return False
            for item in order.items.order_by("product_variant_id"):
                inventory = Inventory.objects.select_for_update().get(variant_id=item.product_variant_id)
                if order.stock_status == self.StockStatus.RESERVED:
                    if inventory.reserved_quantity < item.quantity:
                        raise ValidationError("La réservation de stock de la commande est incohérente.")
                    inventory.reserved_quantity -= item.quantity
                else:
                    inventory.quantity += item.quantity
                inventory.save(update_fields=["quantity", "reserved_quantity", "updated_at"])
            order.stock_status = self.StockStatus.RELEASED
            order.save(update_fields=["stock_status", "updated_at"])
            self.refresh_from_db()
            return True

    def notify_merchant_cancelled(self):
        from apps.monetization.models import Notification

        subject = f"Commande annulée — {self.store.name}"
        message = (
            f"Bonjour,\n\n"
            f"La commande n°{str(self.id)[:8]} ({self.total_amount} FCFA) vient d'être annulée par le client.\n\n"
            "Consultez votre tableau de bord pour plus de détails."
        )
        notification = Notification.objects.create(
            user=self.store.owner,
            channel=Notification.Channel.EMAIL,
            subject=subject,
            message=message,
            metadata={"order_id": str(self.id)},
        )
        notification.send()

    def __str__(self):
        return f"Order {self.id} - {self.customer.email}"


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name='order_item_positive_quantity'),
            models.UniqueConstraint(fields=['order', 'product_variant'], name='order_variant_unique'),
        ]

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
