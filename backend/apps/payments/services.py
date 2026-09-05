"""Transitions de paiement communes au webhook, au sandbox et au scheduler."""
from django.db import transaction
from .models import Refund
from apps.orders.models import Order
from apps.monetization.models import Notification


def complete_payment(payment):
    """Applique une confirmation une seule fois et déclenche la livraison."""
    with transaction.atomic():
        changed = payment.mark_succeeded()
        if not changed or not payment.order_id:
            return payment

        order = Order.objects.select_for_update().get(pk=payment.order_id)
        if order.status == Order.Status.CANCELLED or not order.commit_reserved_stock():
            # L'encaissement est réel même si la commande ne peut plus être
            # honorée : le conserver et demander un remboursement, jamais
            # réactiver une commande annulée ni vendre un stock inexistant.
            if order.status != Order.Status.CANCELLED:
                order.change_status(Order.Status.CANCELLED)
                delivery = getattr(order, "delivery", None)
                if delivery:
                    delivery.cancel()
            Refund.objects.get_or_create(
                payment=payment,
                defaults={"amount": payment.amount, "reason": "Paiement reçu après annulation ou épuisement du stock."},
            )
            return payment
        if order.status != Order.Status.PAID:
            order.change_status(Order.Status.PAID)
            transaction.on_commit(lambda: _send_order_confirmation(order))
            delivery = getattr(order, "delivery", None)
            if delivery:
                delivery.auto_assign()
    return payment


def fail_payment(payment):
    """Échoue le paiement et libère le stock réservé, une seule fois."""
    with transaction.atomic():
        changed = payment.mark_failed()
        if changed and payment.order_id:
            payment.order.release_stock()
    return changed


def _send_order_confirmation(order):
    """
    Confirmation envoyée au client juste après le paiement réussi. Email
    réellement délivré (SMTP déjà configuré) ; le canal SMS existe déjà
    dans le modèle Notification pour quand un fournisseur sera branché,
    mais n'envoie rien de réel pour l'instant (voir Notification._send_sms).
    """
    subject = f"Commande confirmée — {order.store.name}"
    message = (
        f"Bonjour {order.customer.first_name or order.customer.email},\n\n"
        f"Votre commande n°{str(order.id)[:8]} chez {order.store.name} a été payée avec succès.\n"
        f"Montant total : {order.total_amount} FCFA.\n\n"
        "Vous pouvez suivre sa livraison depuis votre espace Sunu Mall.\n\n"
        "Merci de votre confiance !"
    )
    notification = Notification.objects.create(
        user=order.customer,
        channel=Notification.Channel.EMAIL,
        subject=subject,
        message=message,
        metadata={"order_id": str(order.id)},
    )
    notification.send()
