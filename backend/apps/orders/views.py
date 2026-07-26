from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from .models import Address, Delivery, DeliveryTracking, Driver, Order, OrderItem
from .pricing import compute_delivery_fee
from .serializers import (
    AddressSerializer, CheckoutSerializer, DeliveryQuoteSerializer, DeliverySerializer,
    DeliveryTrackingSerializer, DriverSerializer, OrderSerializer,
)
from apps.catalog.models import ProductVariant, Store
from apps.monetization.models import Notification
from apps.payments.models import Payment
from apps.shopping.models import CartItem
from apps.users.models import Role


class AddressViewSet(viewsets.ModelViewSet):
    """Carnet d'adresses de l'utilisateur connecté."""
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OrderViewSet(viewsets.ModelViewSet):
    """
    Un acheteur voit ses propres commandes, un vendeur celles de ses boutiques,
    un livreur celles dont la livraison lui est affectée, l'admin voit tout.
    """

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.has_role(Role.RoleName.ADMIN):
            return Order.objects.all()
        return Order.objects.filter(
            models.Q(customer=user) | models.Q(store__owner=user) | models.Q(delivery__driver__user=user)
        ).distinct()

    @action(detail=False, methods=["post"])
    def quote(self, request):
        """Prévisualise le frais de livraison (même formule que le checkout) avant paiement."""
        serializer = DeliveryQuoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        store = get_object_or_404(Store, pk=data["store"])
        address = get_object_or_404(Address, pk=data["address"], user=request.user)
        fee = compute_delivery_fee(store, address, data["delivery_type"])
        return Response({"delivery_fee": str(fee)})

    @action(detail=False, methods=["post"])
    def checkout(self, request):
        """
        Construit, en une transaction, la commande, ses lignes, sa livraison
        et son paiement en attente à partir du panier validé côté frontend
        (écrans checkout-address / -delivery / -payment), puis retire du
        panier les articles achetés.
        """
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        store = get_object_or_404(Store, pk=data["store"])
        address = get_object_or_404(Address, pk=data["address"], user=request.user)
        delivery_fee = compute_delivery_fee(store, address, data["delivery_type"])

        with transaction.atomic():
            order = Order.objects.create(
                customer=request.user,
                store=store,
                address=address,
                delivery_fee=delivery_fee,
            )

            total = Decimal("0")
            for item in data["items"]:
                variant = get_object_or_404(
                    ProductVariant.objects.select_related("product"),
                    pk=item["product_variant"],
                    product__store=store,
                )
                order_item = OrderItem.objects.create(
                    order=order,
                    product_variant=variant,
                    quantity=item["quantity"],
                    unit_price=variant.price,
                )
                total += order_item.subtotal()

            order.total_amount = total + order.delivery_fee
            order.save(update_fields=["total_amount"])

            Delivery.objects.create(order=order)
            Payment.objects.create(
                order=order,
                amount=order.total_amount,
                method=data["payment_method"],
            )

            variant_ids = [item["product_variant"] for item in data["items"]]
            CartItem.objects.filter(
                cart__user=request.user, product_variant_id__in=variant_ids
            ).delete()

        from apps.analytics.models import SalesStatistic
        SalesStatistic.compute_for_store(store, order.created_at.date())

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Annule une commande encore annulable (client, boutique concernée ou admin)."""
        order = self.get_object()
        user = request.user
        is_allowed = (
            order.customer_id == user.id
            or order.store.owner_id == user.id
            or user.has_role(Role.RoleName.ADMIN)
        )
        if not is_allowed:
            raise PermissionDenied("Vous ne pouvez annuler que vos propres commandes.")
        if not order.can_be_cancelled():
            raise ValidationError(f"Une commande au statut « {order.status} » ne peut plus être annulée.")

        order.change_status(Order.Status.CANCELLED)
        delivery = getattr(order, "delivery", None)
        if delivery and delivery.status in [Delivery.Status.PENDING, Delivery.Status.ASSIGNED]:
            delivery.status = Delivery.Status.CANCELLED
            delivery.save(update_fields=["status"])

        return Response(OrderSerializer(order).data)


class DriverViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lecture des profils livreur : un admin voit tout, un commerçant voit les
    livreurs disponibles (pour affecter une livraison), un livreur ne voit
    que lui-même sauf via l'action `me`.
    """
    serializer_class = DriverSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.has_role(Role.RoleName.ADMIN):
            return Driver.objects.all()
        if user.has_role(Role.RoleName.MERCHANT):
            return Driver.objects.filter(availability_status=Driver.AvailabilityStatus.AVAILABLE)
        return Driver.objects.filter(user=user)

    @action(detail=False, methods=["get", "patch"], url_path="me")
    def me(self, request):
        """Profil livreur de l'utilisateur connecté, créé à la volée s'il n'existe pas encore."""
        if not request.user.has_role(Role.RoleName.DRIVER):
            raise PermissionDenied("Seul un compte livreur possède un profil livreur.")
        driver, _ = Driver.objects.get_or_create(user=request.user)
        if request.method == "PATCH":
            if "vehicle_type" in request.data:
                driver.vehicle_type = request.data["vehicle_type"]
            if "availability_status" in request.data:
                driver.availability_status = request.data["availability_status"]
            if "zone" in request.data:
                driver.zone_id = request.data["zone"]
            driver.save()
        return Response(DriverSerializer(driver).data)


class DeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Livraisons : un livreur voit celles qui lui sont affectées, un commerçant
    celles de ses commandes, l'admin voit tout. La livraison elle-même est
    créée automatiquement par `OrderViewSet.checkout`, pas ici.
    """
    serializer_class = DeliverySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.has_role(Role.RoleName.ADMIN):
            return Delivery.objects.all()
        if user.has_role(Role.RoleName.DRIVER):
            return Delivery.objects.filter(driver__user=user)
        return Delivery.objects.filter(order__store__owner=user)

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        """Le commerçant affecte un livreur affilié disponible à la livraison de sa commande."""
        delivery = get_object_or_404(Delivery, pk=pk)
        user = request.user
        if not user.has_role(Role.RoleName.ADMIN) and delivery.order.store.owner_id != user.id:
            raise PermissionDenied("Vous ne pouvez affecter un livreur qu'à vos propres commandes.")
        driver = get_object_or_404(Driver, pk=request.data.get("driver"))
        delivery.assign_driver(driver)

        subject = "Nouvelle course qui vous a été affectée"
        message = (
            f"Bonjour {driver.user.first_name},\n\n"
            f"Une nouvelle course vous a été affectée (commande {delivery.order.id}).\n"
            "Connectez-vous à votre espace livreur pour voir le détail et démarrer la livraison.\n\n"
            "Merci."
        )
        Notification.objects.create(
            user=driver.user,
            channel=Notification.Channel.PUSH,
            subject=subject,
            message=message,
            status=Notification.Status.PENDING,
            metadata={"delivery_id": str(delivery.id), "order_id": str(delivery.order.id)},
        )
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [driver.user.email], fail_silently=True)
        except Exception:
            pass

        return Response(DeliverySerializer(delivery).data)

    @action(detail=True, methods=["post"], url_path="status")
    def update_status(self, request, pk=None):
        """Le livreur affecté fait progresser le statut de sa course."""
        delivery = get_object_or_404(Delivery, pk=pk)
        user = request.user
        is_assigned_driver = delivery.driver and delivery.driver.user_id == user.id
        if not user.has_role(Role.RoleName.ADMIN) and not is_assigned_driver:
            raise PermissionDenied("Seul le livreur affecté peut mettre à jour cette livraison.")

        new_status = request.data.get("status")
        allowed_transitions = {
            Delivery.Status.ASSIGNED: [Delivery.Status.PICKED_UP],
            Delivery.Status.PICKED_UP: [Delivery.Status.DELIVERED],
        }
        if new_status not in allowed_transitions.get(delivery.status, []):
            raise ValidationError(
                f"Transition invalide de « {delivery.status} » vers « {new_status} »."
            )

        delivery.status = new_status
        if new_status == Delivery.Status.PICKED_UP:
            delivery.picked_up_at = timezone.now()
        elif new_status == Delivery.Status.DELIVERED:
            delivery.delivered_at = timezone.now()
        delivery.save()

        if new_status == Delivery.Status.DELIVERED:
            delivery.order.change_status(Order.Status.DELIVERED)

        return Response(DeliverySerializer(delivery).data)

    @action(detail=True, methods=["post"], url_path="track")
    def track(self, request, pk=None):
        """Le livreur affecté partage sa position GPS courante."""
        delivery = get_object_or_404(Delivery, pk=pk)
        user = request.user
        is_assigned_driver = delivery.driver and delivery.driver.user_id == user.id
        if not user.has_role(Role.RoleName.ADMIN) and not is_assigned_driver:
            raise PermissionDenied("Seul le livreur affecté peut partager sa position.")

        serializer = DeliveryTrackingSerializer(data={**request.data, "delivery": delivery.id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
