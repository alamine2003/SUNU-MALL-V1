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


class SubscriptionViewSet(viewsets.ModelViewSet):
    """Un commerçant gère ses propres abonnements ; l'admin voit et gère tout."""
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.has_role(Role.RoleName.ADMIN):
            return Subscription.objects.all()
        return Subscription.objects.filter(subscriber_id=user.id)

    def perform_create(self, serializer):
        user = self.request.user
        if user.has_role(Role.RoleName.ADMIN):
            serializer.save()
        else:
            serializer.save(subscriber_id=user.id, subscriber_type="merchant")

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
