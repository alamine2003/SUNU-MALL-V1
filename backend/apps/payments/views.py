import hashlib
import hmac
import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import models
from django.db import transaction
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Payment, Refund
from .serializers import PaymentSerializer, RefundSerializer
from .gateways import PaymentGatewayError, get_gateway
from apps.monetization.models import Notification
from apps.orders.models import Order
from apps.users.models import Role
from apps.users.permissions import IsAdmin


def _complete_order_payment(payment):
    """Applique une confirmation une seule fois et déclenche la livraison."""
    changed = payment.mark_succeeded()
    if not changed or not payment.order_id:
        return payment

    order = payment.order
    if order.status != Order.Status.PAID:
        order.change_status(Order.Status.PAID)
        _send_order_confirmation(order)
        delivery = getattr(order, "delivery", None)
        if delivery:
            delivery.auto_assign()
    return payment


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


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lecture seule : un paiement n'est jamais modifié directement par
    l'utilisateur, seulement via les actions `initiate` / `sandbox-confirm`
    (ou plus tard un webhook fournisseur authentifié par signature).
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.has_role(Role.RoleName.ADMIN):
            return Payment.objects.all()
        return Payment.objects.filter(
            models.Q(order__customer=user)
            | models.Q(order__store__owner=user)
            | models.Q(subscription__subscriber_id=user.id)
        ).distinct()

    def _ensure_customer(self, payment):
        if self.request.user.has_role(Role.RoleName.ADMIN):
            return
        if payment.order_id is not None:
            owner_id = payment.order.customer_id
            message = "Seul le client de la commande peut agir sur ce paiement."
        else:
            owner_id = payment.subscription.subscriber_id
            message = "Seul l'abonné peut agir sur ce paiement."
        if owner_id != self.request.user.id:
            raise PermissionDenied(message)

    @action(detail=True, methods=["post"], url_path="initiate")
    def initiate(self, request, pk=None):
        """Démarre le paiement auprès du fournisseur (ou de la simulation sandbox)."""
        payment = self.get_object()
        self._ensure_customer(payment)
        if payment.status != Payment.Status.PENDING:
            return Response(
                {"error": "Ce paiement n'est plus en attente."},
                status=status.HTTP_409_CONFLICT,
            )
        gateway = get_gateway(payment.method)
        try:
            result = gateway.initiate(payment)
        except PaymentGatewayError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(result)

    @action(detail=True, methods=["post"], url_path="sandbox-confirm")
    def sandbox_confirm(self, request, pk=None):
        """
        Simule la confirmation (succès ou échec) qu'enverrait normalement le
        fournisseur via webhook. Uniquement disponible quand PAYMENT_SANDBOX
        est actif — jamais en production avec de vraies clés configurées.
        """
        if not settings.PAYMENT_SANDBOX:
            return Response(
                {"error": "Le mode sandbox n'est pas actif sur cet environnement."},
                status=status.HTTP_403_FORBIDDEN,
            )
        payment = self.get_object()
        self._ensure_customer(payment)

        outcome = request.data.get("outcome", "success")
        if outcome not in {"success", "failed"}:
            return Response(
                {"error": "Le résultat doit être « success » ou « failed »."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if outcome == "success":
            _complete_order_payment(payment)
        else:
            payment.mark_failed()
        return Response(PaymentSerializer(payment).data)


class RefundViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Remboursements créés automatiquement quand une commande déjà payée est
    annulée (voir OrderViewSet.cancel). Un client voit les siens ; seul
    l'admin peut les traiter (action `process`) — un remboursement Wave/
    Orange Money/carte n'est pas un appel API instantané ici, un humain
    confirme que l'argent a bien été renvoyé avant de le marquer complété.
    """
    serializer_class = RefundSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Refund.objects.select_related("payment__order__store", "payment__order__customer")
        if user.has_role(Role.RoleName.ADMIN):
            return qs
        return qs.filter(payment__order__customer=user)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsAdmin])
    def process(self, request, pk=None):
        refund = self.get_object()
        if refund.status == Refund.Status.COMPLETED:
            return Response({"error": "Ce remboursement a déjà été traité."}, status=status.HTTP_400_BAD_REQUEST)
        refund.process()
        return Response(RefundSerializer(refund).data)


@method_decorator(csrf_exempt, name="dispatch")
class NabooPayWebhookView(APIView):
    """Reçoit les statuts NabooPay après vérification de leur signature."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        secret = settings.NABOOPAY_WEBHOOK_SECRET
        signature = request.headers.get("X-Signature", "")
        expected = hmac.new(
            secret.encode("utf-8"), request.body, hashlib.sha256
        ).hexdigest()
        if not secret or not signature or not hmac.compare_digest(signature, expected):
            return JsonResponse({"error": "Signature invalide."}, status=401)

        try:
            payload = json.loads(request.body)
        except (TypeError, ValueError):
            return JsonResponse({"error": "Payload JSON invalide."}, status=400)

        provider_ref = str(payload.get("order_id", ""))
        payment_status = payload.get("transaction_status")
        if not provider_ref or payment_status not in {"completed", "failed", "cancelled"}:
            return JsonResponse({"error": "Événement NabooPay invalide."}, status=400)

        payment = Payment.objects.filter(provider_ref=provider_ref).first()
        if payment is None:
            # Accuser réception évite une boucle de retries pour un paiement
            # créé sur un autre environnement ou supprimé avant le webhook.
            return JsonResponse({"status": "ignored"}, status=200)

        amount = payload.get("amount")
        currency = payload.get("currency", "XOF")
        if currency != "XOF" or amount is None:
            return JsonResponse({"error": "Montant ou devise invalide."}, status=400)
        try:
            if payment.amount != Decimal(str(amount)):
                return JsonResponse({"error": "Montant invalide."}, status=400)
        except (InvalidOperation, TypeError, ValueError):
            return JsonResponse({"error": "Montant invalide."}, status=400)

        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(pk=payment.pk)
            if payment_status == "completed":
                _complete_order_payment(payment)
            else:
                payment.mark_failed()

        return JsonResponse({"status": "received"}, status=200)
