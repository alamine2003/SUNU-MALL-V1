from decimal import Decimal
from hashlib import sha256
import json
from django.core.exceptions import ValidationError as ModelValidationError
from django.db import models, transaction
from rest_framework.generics import get_object_or_404
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
from apps.catalog.models import Inventory, Product, ProductVariant, Store
from apps.payments.models import Payment, PaymentService, Refund
from apps.shopping.models import Cart
from apps.users.models import Role, User


class AddressViewSet(viewsets.ModelViewSet):
    """Carnet d'adresses de l'utilisateur connecté."""
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Un acheteur voit ses propres commandes, un vendeur celles de ses boutiques,
    un livreur celles dont la livraison lui est affectée, l'admin voit tout.
    """

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        """Une commande reste traçable ; seule l'annulation est autorisée."""
        return Response(
            {"error": "Une commande ne peut pas être supprimée. Utilisez cancel."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.select_related(
            'customer', 'store', 'address', 'payment', 'delivery__driver__user',
        ).prefetch_related(
            models.Prefetch('items', queryset=OrderItem.objects.select_related('product_variant__product')),
            models.Prefetch('payment__refunds', queryset=Refund.objects.order_by('-created_at')[:1], to_attr='latest_refunds'),
            models.Prefetch('delivery__trackings', queryset=DeliveryTracking.objects.order_by('-recorded_at')[:1], to_attr='latest_trackings'),
        )
        if user.has_role(Role.RoleName.ADMIN):
            return queryset
        return queryset.filter(
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
        checkout_key = data.pop('checkout_key', None)
        fingerprint = sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest() if checkout_key else ''

        with transaction.atomic():
            if checkout_key:
                # Sérialiser les tentatives du même acheteur, y compris avant
                # l'existence de la première commande. Aucun verrou global.
                User.objects.select_for_update(no_key=True).get(pk=request.user.pk)
                previous = Order.objects.filter(customer=request.user, checkout_key=checkout_key).first()
                if previous:
                    if previous.checkout_fingerprint != fingerprint:
                        return Response({'error': 'Cette tentative correspond à un autre panier.'}, status=status.HTTP_409_CONFLICT)
                    return Response(OrderSerializer(previous).data)

            # Le panier précède les stocks dans l'ordre de verrouillage.
            # Un ajout pendant le checkout doit rester dans le panier.
            cart = Cart.objects.select_for_update().filter(user=request.user).first()
            store = get_object_or_404(Store, pk=data["store"], status=Store.Status.ACTIVE)
            address = get_object_or_404(Address, pk=data["address"], user=request.user)
            delivery_fee = compute_delivery_fee(store, address, data["delivery_type"])
            order = Order.objects.create(
                customer=request.user,
                store=store,
                address=address,
                delivery_fee=delivery_fee,
                checkout_key=checkout_key,
                checkout_fingerprint=fingerprint,
            )

            total = Decimal("0")
            # Même ordre pour tous les paniers : A/B et B/A ne doivent pas
            # verrouiller les stocks dans un ordre opposé.
            for item in sorted(data["items"], key=lambda line: line["product_variant"]):
                variant = get_object_or_404(
                    ProductVariant.objects.select_for_update(of=("self",)).select_related("product"),
                    pk=item["product_variant"],
                    product__store=store,
                    product__status=Product.Status.ACTIVE,
                )
                inventory = get_object_or_404(
                    Inventory.objects.select_for_update(), variant=variant
                )
                if not inventory.reserve(item["quantity"]):
                    raise ValidationError(
                        f"Le stock disponible est insuffisant pour « {variant.product.name} »."
                    )
                order_item = OrderItem.objects.create(
                    order=order,
                    product_variant=variant,
                    quantity=item["quantity"],
                    unit_price=variant.price,
                )
                total += order_item.subtotal()

            order.total_amount = total + order.delivery_fee
            if hasattr(store, "settings") and order.total_amount < store.settings.min_order_amount:
                raise ValidationError(
                    f"Le montant minimum de commande est de {store.settings.min_order_amount} FCFA."
                )
            order.stock_status = Order.StockStatus.RESERVED
            order.save(update_fields=["total_amount", "stock_status"])

            Delivery.objects.create(order=order)
            PaymentService.process_order_payment(
                order, order.total_amount, data["payment_method"]
            )

            if cart:
                purchased = {item['product_variant']: item['quantity'] for item in data['items']}
                for line in cart.items.filter(product_variant_id__in=purchased):
                    remaining = line.quantity - purchased[line.product_variant_id]
                    if remaining > 0:
                        line.quantity = remaining
                        line.save(update_fields=['quantity'])
                    else:
                        line.delete()

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

        with transaction.atomic():
            # Même ordre que le webhook : paiement, puis commande et stocks.
            payment = Payment.objects.select_for_update().filter(order_id=order.pk).first()
            order = Order.objects.select_for_update().get(pk=order.pk)
            if not order.can_be_cancelled():
                raise ValidationError(f"Une commande au statut « {order.status} » ne peut plus être annulée.")
            order.release_stock()
            order.change_status(Order.Status.CANCELLED)
            delivery = getattr(order, "delivery", None)
            if delivery and delivery.status in [Delivery.Status.PENDING, Delivery.Status.ASSIGNED]:
                delivery.cancel()
            if payment and payment.status == Payment.Status.SUCCESS:
                Refund.objects.get_or_create(
                    payment=payment,
                    defaults={"amount": payment.amount, "reason": "Commande annulée par le client"},
                )
            transaction.on_commit(order.notify_merchant_cancelled)

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
            serializer = DriverSerializer(driver, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
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
        driver = get_object_or_404(
            Driver,
            pk=request.data.get("driver"),
            availability_status=Driver.AvailabilityStatus.AVAILABLE,
        )
        try:
            delivery.assign_driver(driver)
        except ModelValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(DeliverySerializer(delivery).data)

    @action(detail=True, methods=["post"], url_path="status")
    @transaction.atomic
    def update_status(self, request, pk=None):
        """Le livreur affecté fait progresser le statut de sa course."""
        delivery = get_object_or_404(Delivery, pk=pk)
        user = request.user
        is_assigned_driver = delivery.driver and delivery.driver.user_id == user.id
        if not user.has_role(Role.RoleName.ADMIN) and not is_assigned_driver:
            raise PermissionDenied("Seul le livreur affecté peut mettre à jour cette livraison.")

        order = Order.objects.select_for_update().get(pk=delivery.order_id)
        delivery = Delivery.objects.select_for_update().get(pk=delivery.pk)
        if not user.has_role(Role.RoleName.ADMIN) and (not delivery.driver or delivery.driver.user_id != user.id):
            raise PermissionDenied("La livraison a été réaffectée.")
        if order.status not in Order.SALES_STATUSES or order.status == Order.Status.DELIVERED:
            raise ValidationError("La commande ne peut pas progresser dans cet état.")

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
