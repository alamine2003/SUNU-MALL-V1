"""
Paiements, commissions, transactions et remboursements.
"""
import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.utils import timezone
from apps.orders.models import Order
from apps.monetization.models import Invoice, Subscription


def payment_expiry():
    return timezone.now() + timedelta(minutes=30)


class PaymentService:
    @staticmethod
    def process_order_payment(order, amount, method):
        """Crée un paiement cohérent avec le total de la commande."""
        amount = Decimal(amount)
        if amount != order.total_amount:
            raise ValueError("Le montant du paiement ne correspond pas à la commande.")
        if hasattr(order, "payment"):
            raise ValueError("Cette commande possède déjà un paiement.")
        return Payment.objects.create(order=order, amount=amount, method=method)


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
        return rule.percentage if rule else Decimal("0")

    def __str__(self):
        return f"{self.applies_to} - {self.percentage}%"


class Payment(models.Model):
    class Method(models.TextChoices):
        WAVE = "wave", "Wave"
        ORANGE_MONEY = "orange_money", "Orange Money"
        CARD = "card", "Carte bancaire"

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Un paiement règle soit une commande, soit un abonnement — jamais les
    # deux (contrainte ci-dessous) : d'où les deux FK optionnelles plutôt
    # qu'une seule relation polymorphe, plus simple à requêter/valider.
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name='payment', null=True, blank=True)
    subscription = models.OneToOneField(
        Subscription, on_delete=models.PROTECT, related_name='payment', null=True, blank=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField(default=payment_expiry, db_index=True)
    provider_ref = models.CharField(max_length=255, blank=True, db_index=True)
    checkout_url = models.URLField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(order__isnull=False, subscription__isnull=True)
                    | models.Q(order__isnull=True, subscription__isnull=False)
                ),
                name='payment_targets_order_xor_subscription',
            ),
            models.UniqueConstraint(
                fields=["provider_ref"],
                condition=~models.Q(provider_ref=""),
                name="payment_provider_ref_unique_when_present",
            ),
        ]

    def mark_succeeded(self):
        """Confirme le paiement une seule fois, même sur webhook doublonné."""
        from django.db import transaction

        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(pk=self.pk)
            if payment.status == self.Status.SUCCESS:
                self.refresh_from_db()
                return False
            if payment.status == self.Status.REFUNDED:
                return False

            payment.status = self.Status.SUCCESS
            payment.paid_at = timezone.now()
            payment.save(update_fields=["status", "paid_at", "updated_at"])
            if payment.subscription_id:
                payment._activate_subscription()
            else:
                Transaction.create_for_payment(payment)
            self.refresh_from_db()
            return True

    def _activate_subscription(self):
        subscription = Subscription.objects.select_for_update().get(pk=self.subscription_id)
        if subscription.status in {Subscription.Status.CANCELLED, Subscription.Status.EXPIRED}:
            Refund.objects.get_or_create(
                payment=self,
                defaults={"amount": self.amount, "reason": "Paiement reçu après annulation de l'abonnement."},
            )
            return
        subscription.status = Subscription.Status.ACTIVE
        subscription.save(update_fields=["status"])
        today = timezone.now().date()
        invoice = Invoice.objects.create(
            subscription=subscription, amount=self.amount,
            status=Invoice.Status.ISSUED, issued_at=today, due_at=today,
        )
        invoice.mark_paid()
        subscription.notify_activated()

    def mark_failed(self):
        from django.db import transaction

        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(pk=self.pk)
            if payment.status in {self.Status.FAILED, self.Status.SUCCESS, self.Status.REFUNDED}:
                self.refresh_from_db()
                return False
            payment.status = self.Status.FAILED
            payment.save(update_fields=["status", "updated_at"])
            if payment.subscription_id:
                payment.subscription.cancel()
            self.refresh_from_db()
            return True

    def __str__(self):
        return f"Payment {self.id} - {self.order_id or self.subscription_id}"


class Transaction(models.Model):
    class Type(models.TextChoices):
        SALE = 'sale', 'Sale'
        COMMISSION = 'commission', 'Commission'
        REFUND = 'refund', 'Refund'

    id = models.AutoField(primary_key=True)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='transactions')
    type = models.CharField(max_length=50, choices=Type.choices)
    payee_type = models.CharField(max_length=100)
    # Null pour la part plateforme (COMMISSION) : ce n'est pas un utilisateur,
    # il n'y a donc pas d'UUID réel à renseigner.
    payee_id = models.UUIDField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, default='completed')
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def create_for_payment(payment):
        """
        Ventile un paiement de commande réussi entre le commerçant (part
        vente) et la plateforme (commission), selon le taux configuré dans
        CommissionRule (0% si aucune règle "order" n'est active). Ne
        s'applique qu'aux paiements de commande — un paiement d'abonnement
        est déjà entièrement un revenu plateforme, tracé via Invoice.
        """
        if payment.order_id is None:
            return
        if payment.transactions.exclude(type=Transaction.Type.REFUND).exists():
            return

        rate = CommissionRule.current_rate("order")
        commission_amount = (payment.amount * rate / Decimal("100")).quantize(Decimal("0.01"))
        seller_amount = payment.amount - commission_amount

        Transaction.objects.create(
            payment=payment, type=Transaction.Type.SALE,
            payee_type="merchant", payee_id=payment.order.store.owner_id,
            amount=seller_amount,
        )
        if commission_amount > 0:
            Transaction.objects.create(
                payment=payment, type=Transaction.Type.COMMISSION,
                payee_type="platform", payee_id=None,
                amount=commission_amount,
            )

    def __str__(self):
        return f"Transaction {self.id} - {self.type}"


class Refund(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        COMPLETED = 'completed', 'Completed'

    id = models.AutoField(primary_key=True)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    refunded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def process(self):
        """
        Marque le remboursement traité : passe le paiement à "refunded",
        contre-passe chaque transaction déjà enregistrée (vente + commission)
        par une transaction REFUND de signe opposé, puis prévient le client.
        Appelé par un admin (voir RefundViewSet.process) — un remboursement
        Wave/Orange Money/carte n'est pas un appel API instantané ici, un
        humain confirme que l'argent a bien été renvoyé avant ce statut.
        """
        from django.db import transaction

        with transaction.atomic():
            refund = Refund.objects.select_for_update().select_related("payment").get(pk=self.pk)
            if refund.status == self.Status.COMPLETED:
                return False
            if refund.status not in {self.Status.PENDING, self.Status.APPROVED}:
                raise ValueError("Seul un remboursement en attente peut être traité.")

            payment = Payment.objects.select_for_update().get(pk=refund.payment_id)
            if payment.status != Payment.Status.SUCCESS:
                raise ValueError("Seul un paiement confirmé peut être remboursé.")
            if refund.amount != payment.amount:
                raise ValueError("Seul le remboursement intégral est actuellement supporté.")

            refund.status = self.Status.COMPLETED
            refund.refunded_at = timezone.now()
            refund.save(update_fields=["status", "refunded_at", "updated_at"])

            payment.status = Payment.Status.REFUNDED
            payment.save(update_fields=["status", "updated_at"])

            for original in payment.transactions.exclude(type=Transaction.Type.REFUND):
                Transaction.objects.create(
                    payment=payment, type=Transaction.Type.REFUND,
                    payee_type=original.payee_type, payee_id=original.payee_id,
                    amount=-original.amount,
                )

            self.refresh_from_db()
            transaction.on_commit(self._notify_customer)
            return True

    def _notify_customer(self):
        from apps.monetization.models import Notification

        order = self.payment.order
        if not order:
            return
        subject = f"Remboursement traité — {order.store.name}"
        message = (
            f"Bonjour {order.customer.first_name or order.customer.email},\n\n"
            f"Le remboursement de {self.amount} FCFA pour votre commande n°{str(order.id)[:8]} "
            "a bien été traité.\n\nMerci de votre compréhension."
        )
        notification = Notification.objects.create(
            user=order.customer, channel=Notification.Channel.EMAIL,
            subject=subject, message=message,
            metadata={"refund_id": str(self.id), "order_id": str(order.id)},
        )
        notification.send()

    def __str__(self):
        return f"Refund {self.id} - {self.payment.id}"
