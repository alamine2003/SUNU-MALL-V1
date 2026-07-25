"""
Paiements, commissions, transactions et remboursements.
"""
import uuid
from django.db import models
from django.utils import timezone
from apps.orders.models import Order


class PaymentService:
    @staticmethod
    def process_order_payment(order, amount, method):
        # Implement payment processing logic here
        pass


class CommissionRule(models.Model):
    id = models.AutoField(primary_key=True)
    applies_to = models.CharField(max_length=100)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def current_rate(applies_to):
        now = timezone.now()
        rule = CommissionRule.objects.filter(
            applies_to=applies_to,
            valid_from__lte=now
        ).filter(
            models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=now)
        ).first()
        return rule.percentage if rule else 0

    def __str__(self):
        return f"{self.applies_to} - {self.percentage}%"


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=100)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    provider_ref = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def mark_succeeded(self):
        self.status = self.Status.SUCCESS
        self.paid_at = timezone.now()
        self.save()
        # Create transactions
        Transaction.create_for_payment(self)

    def mark_failed(self):
        self.status = self.Status.FAILED
        self.save()

    def __str__(self):
        return f"Payment {self.id} - {self.order.id}"


class Transaction(models.Model):
    class Type(models.TextChoices):
        SALE = 'sale', 'Sale'
        COMMISSION = 'commission', 'Commission'
        REFUND = 'refund', 'Refund'

    id = models.AutoField(primary_key=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=50, choices=Type.choices)
    payee_type = models.CharField(max_length=100)
    payee_id = models.UUIDField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, default='completed')
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def create_for_payment(payment):
        # Implement transaction creation logic here
        pass

    def __str__(self):
        return f"Transaction {self.id} - {self.type}"


class Refund(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        COMPLETED = 'completed', 'Completed'

    id = models.AutoField(primary_key=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    refunded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def process(self):
        # Implement refund processing logic here
        pass

    def __str__(self):
        return f"Refund {self.id} - {self.payment.id}"
