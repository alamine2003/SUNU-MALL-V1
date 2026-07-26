"""
Notifications, produits sponsorisés, abonnements et factures.
"""
import uuid
from django.db import models
from django.utils import timezone
from apps.users.models import User
from apps.catalog.models import Product, Store


class Notification(models.Model):
    class Channel(models.TextChoices):
        EMAIL = 'email', 'Email'
        SMS = 'sms', 'SMS'
        PUSH = 'push', 'Push'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    channel = models.CharField(max_length=50, choices=Channel.choices)
    subject = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @staticmethod
    def send():
        # Implement notification sending logic here
        pass

    def mark_sent(self):
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.save()

    def mark_failed(self):
        self.status = self.Status.FAILED
        self.save()

    def __str__(self):
        return f"Notification for {self.user.email}"


class SponsoredProduct(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        EXPIRED = 'expired', 'Expired'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sponsorships')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='sponsored_products')
    daily_budget = models.DecimalField(max_digits=10, decimal_places=2)
    starts_at = models.DateField()
    ends_at = models.DateField()
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.INACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_active(self):
        today = timezone.now().date()
        return self.status == self.Status.ACTIVE and self.starts_at <= today <= self.ends_at

    def spend_today(self):
        # Implement today's spend calculation
        return 0

    def __str__(self):
        return f"Sponsored {self.product.name}"


class SubscriptionPlan(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(max_length=50)  # monthly, yearly
    features = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        CANCELLED = 'cancelled', 'Cancelled'
        EXPIRED = 'expired', 'Expired'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='subscriptions')
    subscriber_type = models.CharField(max_length=100)
    subscriber_id = models.UUIDField()
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.ACTIVE)
    starts_at = models.DateField()
    ends_at = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_active(self):
        today = timezone.now().date()
        return self.status == self.Status.ACTIVE and self.starts_at <= today <= self.ends_at

    def renew(self):
        # Implement renewal logic
        pass

    def cancel(self):
        self.status = self.Status.CANCELLED
        self.save()

    def __str__(self):
        return f"Subscription {self.id} - {self.plan.name}"


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ISSUED = 'issued', 'Issued'
        PAID = 'paid', 'Paid'
        OVERDUE = 'overdue', 'Overdue'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='invoices')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.DRAFT)
    issued_at = models.DateField(null=True, blank=True)
    due_at = models.DateField(null=True, blank=True)
    paid_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def mark_paid(self):
        self.status = self.Status.PAID
        self.paid_at = timezone.now().date()
        self.save()

    def is_overdue(self):
        if self.status == self.Status.ISSUED and self.due_at and timezone.now().date() > self.due_at:
            return True
        return False

    def __str__(self):
        return f"Invoice {self.id} - {self.subscription.id}"
