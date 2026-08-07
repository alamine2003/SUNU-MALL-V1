from datetime import timedelta

from django.utils import timezone
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
from apps.users.models import Role

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
        payante, le paiement renvoyé se confirme ensuite via l'action
        sandbox-confirm déjà utilisée pour les commandes.
        """
        from apps.payments.models import Payment
        from apps.payments.serializers import PaymentSerializer

        plan = self.get_object()
        user = request.user
        if not user.has_role(Role.RoleName.MERCHANT):
            raise PermissionDenied("Réservé aux comptes commerçants.")

        if Subscription.objects.filter(
            subscriber_id=user.id, subscriber_type="merchant", status=Subscription.Status.ACTIVE
        ).exists():
            return Response(
                {"error": "Vous avez déjà un abonnement actif. Annulez-le avant d'en choisir un autre."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = timezone.now().date()
        days = BILLING_CYCLE_DAYS.get(plan.billing_cycle, 30)
        subscription = Subscription.objects.create(
            plan=plan, subscriber_type="merchant", subscriber_id=user.id,
            starts_at=today, ends_at=today + timedelta(days=days),
        )

        if plan.price <= 0:
            subscription.status = Subscription.Status.ACTIVE
            subscription.save(update_fields=["status"])
            return Response(
                {"subscription": SubscriptionSerializer(subscription).data, "payment": None},
                status=status.HTTP_201_CREATED,
            )

        payment = Payment.objects.create(
            subscription=subscription, amount=plan.price,
            method=request.data.get("payment_method", "wave"),
        )
        return Response(
            {"subscription": SubscriptionSerializer(subscription).data, "payment": PaymentSerializer(payment).data},
            status=status.HTTP_201_CREATED,
        )


class SubscriptionViewSet(viewsets.ModelViewSet):
    """Un commerçant gère ses propres abonnements (via l'action `subscribe` du plan, pas en écrivant ici) ; l'admin voit et gère tout."""
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    # Fenêtre du rappel "expire bientôt" avant la date de fin.
    EXPIRING_SOON_DAYS = 3

    def get_queryset(self):
        # Auto-guérison paresseuse : un abonnement actif dont la date de fin
        # est dépassée passe à "expired" dès qu'on le relit (avec e-mail),
        # sans tâche planifiée dédiée (cohérent avec le reste du projet —
        # voir RecommendationLog/SalesStatistic, calculés à la demande).
        today = timezone.now().date()
        for subscription in Subscription.objects.filter(status=Subscription.Status.ACTIVE, ends_at__lt=today):
            subscription.status = Subscription.Status.EXPIRED
            subscription.save(update_fields=["status"])
            subscription.notify_expired()

        # Rappel envoyé une seule fois par abonnement (on vérifie qu'aucune
        # notification "expire bientôt" n'existe déjà pour lui, plutôt que
        # d'ajouter un champ dédié rien que pour ce drapeau).
        soon_cutoff = today + timedelta(days=self.EXPIRING_SOON_DAYS)
        expiring_soon = Subscription.objects.filter(
            status=Subscription.Status.ACTIVE, ends_at__gte=today, ends_at__lte=soon_cutoff
        )
        for subscription in expiring_soon:
            already_notified = Notification.objects.filter(
                metadata__subscription_id=str(subscription.id), subject__icontains="expire bientôt"
            ).exists()
            if not already_notified:
                subscription.notify_expiring_soon((subscription.ends_at - today).days)

        user = self.request.user
        if user.has_role(Role.RoleName.ADMIN):
            return Subscription.objects.all()
        return Subscription.objects.filter(subscriber_id=user.id)

    def perform_create(self, serializer):
        # Réservé à l'admin (cas d'exception : accorder un abonnement
        # manuellement) — un commerçant passe toujours par l'action
        # `subscribe` du plan, qui calcule dates/statut correctement.
        if not self.request.user.has_role(Role.RoleName.ADMIN):
            raise PermissionDenied("Utilisez l'action « subscribe » d'une offre pour vous abonner.")
        serializer.save()

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        subscription = self.get_object()
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
        return SponsoredProduct.objects.filter(store__owner=user)

    def perform_create(self, serializer):
        user = self.request.user
        store = serializer.validated_data.get("store")
        if not user.has_role(Role.RoleName.ADMIN) and store.owner_id != user.id:
            raise PermissionDenied("Vous ne pouvez sponsoriser que les produits de votre propre boutique.")
        serializer.save()
