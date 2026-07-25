from django.conf import settings
from django.db import models
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .models import Payment
from .serializers import PaymentSerializer
from .gateways import PaymentGatewayError, get_gateway
from apps.orders.models import Order
from apps.users.models import Role


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
            models.Q(order__customer=user) | models.Q(order__store__owner=user)
        ).distinct()

    def _ensure_customer(self, payment):
        if payment.order.customer_id != self.request.user.id and not self.request.user.has_role(Role.RoleName.ADMIN):
            raise PermissionDenied("Seul le client de la commande peut agir sur ce paiement.")

    @action(detail=True, methods=["post"], url_path="initiate")
    def initiate(self, request, pk=None):
        """Démarre le paiement auprès du fournisseur (ou de la simulation sandbox)."""
        payment = self.get_object()
        self._ensure_customer(payment)
        gateway = get_gateway(payment.method)
        try:
            result = gateway.initiate(payment)
        except (NotImplementedError, PaymentGatewayError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_501_NOT_IMPLEMENTED)
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
        if outcome == "success":
            payment.mark_succeeded()
            payment.order.change_status(Order.Status.PAID)
        else:
            payment.mark_failed()
        return Response(PaymentSerializer(payment).data)
