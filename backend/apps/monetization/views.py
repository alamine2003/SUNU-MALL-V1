from datetime import timedelta

from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .models import Notification, SponsoredProduct, SubscriptionPlan, Subscription, Invoice
from .serializers import (
    NotificationSerializer, SponsoredProductSerializer,
    SubscriptionPlanSerializer, SubscriptionSerializer, InvoiceSerializer,
)
from apps.users.permissions import IsAdmin
from apps.users.models import Role, User

# Durée d'une période d'abonnement selon le cycle de facturation du plan —
# utilisé pour calculer starts_at/ends_at côté serveur (jamais fourni par le
# client, contrairement à l'ancien comportement qui exigeait ces dates dans
# la requête et échouait systématiquement en pratique).
BILLING_CYCLE_DAYS = {"monthly": 30, "yearly": 365}


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Un utilisateur ne voit que ses propres notifications (créées par le système)."""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    """Offres Standard/Premium/Premium+ : lecture publique, gestion réservée à l'admin."""
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return super().get_permissions()

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, pk=None):
        """
        POST /api/monetization/subscription-plans/{id}/subscribe/
        Crée l'abonnement (en attente) et son paiement associé pour le
        commerçant connecté — les dates et le statut sont calculés côté
        serveur, jamais fournis par le client. Une offre gratuite (price=0)
        est activée immédiatement, sans paiement à confirmer. Pour une offre
        payante, renvoie le paiement existant s'il est encore en attente.
        Le frontend initialise ensuite la session fournisseur ; seule une
        session sandbox peut être confirmée avec sandbox-confirm.
        """
        from apps.payments.models import Payment
        from apps.payments.serializers import PaymentSerializer

        plan = self.get_object()
        user = request.user
        if not user.has_role(Role.RoleName.MERCHANT):
            raise PermissionDenied("Réservé aux comptes commerçants.")

        payment_method = request.data.get("payment_method", "wave")
        if payment_method not in {"wave", "orange_money"}:
            return Response(
                {"error": "Le moyen de paiement doit être « wave » ou « orange_money »."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = timezone.now().date()
        with transaction.atomic():
            # Sérialise les souscriptions du même marchand, même sur deux
            # offres différentes. Aucun appel fournisseur sous ce verrou.
            User.objects.select_for_update().get(pk=user.pk)
            subscriptions = Subscription.objects.filter(
                subscriber_id=user.id, subscriber_type="merchant",
            )
            if subscriptions.filter(status=Subscription.Status.ACTIVE, ends_at__gte=today).exists():
                return Response(
                    {"error": "Vous avez déjà un abonnement actif. Annulez-le avant d'en choisir un autre."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            pending = subscriptions.filter(status=Subscription.Status.PENDING).first()
            if pending:
                payment = Payment.objects.select_for_update().filter(subscription=pending).first()
                pending.refresh_from_db()
                if pending.status != Subscription.Status.PENDING:
                    return Response({"error": "L'abonnement vient de changer. Actualisez la page."}, status=409)
                if payment and payment.status == Payment.Status.PENDING and payment.expires_at <= timezone.now():
                    payment.mark_failed()
                elif payment and payment.status == Payment.Status.PENDING:
                    if pending.plan_id != plan.pk:
                        return Response(
                            {"error": "Reprenez ou annulez votre abonnement en attente avant de choisir une autre offre."},
                            status=status.HTTP_409_CONFLICT,
                        )
                    return Response({
                        "subscription": SubscriptionSerializer(pending).data,
                        "payment": PaymentSerializer(payment).data,
                    })
                else:
                    pending.cancel()

            days = BILLING_CYCLE_DAYS.get(plan.billing_cycle, 30)
            subscription = Subscription.objects.create(
                plan=plan, subscriber_type="merchant", subscriber_id=user.id,
                starts_at=today, ends_at=today + timedelta(days=days),
                status=Subscription.Status.ACTIVE if plan.price <= 0 else Subscription.Status.PENDING,
            )
            payment = None
            if plan.price > 0:
                payment = Payment.objects.create(
                    subscription=subscription, amount=plan.price, method=payment_method,
                )
        return Response(
            {"subscription": SubscriptionSerializer(subscription).data,
             "payment": PaymentSerializer(payment).data if payment else None},
            status=status.HTTP_201_CREATED,
        )


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """Un commerçant gère ses propres abonnements (via l'action `subscribe` du plan, pas en écrivant ici) ; l'admin voit et gère tout."""
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        subscriptions = Subscription.objects.all()
        if not user.has_role(Role.RoleName.ADMIN):
            subscriptions = subscriptions.filter(subscriber_id=user.pk)
        subscriptions.filter(status=Subscription.Status.ACTIVE, ends_at__lt=timezone.now().date()).update(status=Subscription.Status.EXPIRED)
        return subscriptions.select_related('plan')

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        from apps.payments.models import Payment

        subscription = self.get_object()
        with transaction.atomic():
            # Même ordre que la confirmation : paiement, puis abonnement.
            payment = Payment.objects.select_for_update().filter(subscription=subscription).first()
            subscription = Subscription.objects.select_for_update().get(pk=subscription.pk)
            if payment and payment.status == Payment.Status.PENDING:
                payment.mark_failed()
                subscription.refresh_from_db()
            elif subscription.status != Subscription.Status.CANCELLED:
                subscription.cancel()
        return Response(self.get_serializer(subscription).data, status=status.HTTP_200_OK)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """Factures liées aux abonnements du commerçant connecté ; l'admin voit tout."""
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.has_role(Role.RoleName.ADMIN):
            return Invoice.objects.all()
        return Invoice.objects.filter(subscription__subscriber_id=user.id)


class SponsoredProductViewSet(viewsets.ModelViewSet):
    """Un commerçant gère la mise en avant de ses propres produits ; l'admin voit et gère tout."""
    serializer_class = SponsoredProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.has_role(Role.RoleName.ADMIN):
            return SponsoredProduct.objects.all()
        if not user.has_role(Role.RoleName.MERCHANT):
            return SponsoredProduct.objects.none()
        return SponsoredProduct.objects.filter(store__owner=user)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.has_role(Role.RoleName.MERCHANT) and not user.has_role(Role.RoleName.ADMIN):
            raise PermissionDenied("Réservé aux comptes commerçants.")
        store = serializer.validated_data.get("store")
        product = serializer.validated_data.get("product")
        if product.store_id != store.id:
            raise PermissionDenied("Le produit doit appartenir à la boutique sponsorisée.")
        if not user.has_role(Role.RoleName.ADMIN) and store.owner_id != user.id:
            raise PermissionDenied("Vous ne pouvez sponsoriser que les produits de votre propre boutique.")
        serializer.save()
