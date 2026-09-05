"""
Listes de souhaits et paniers.
"""
import uuid
from django.core.exceptions import ValidationError
from django.db import models
from apps.users.models import User
from apps.catalog.models import Product, ProductVariant


class Wishlist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def add_product(self, product):
        WishlistItem.objects.get_or_create(wishlist=self, product=product)


    def __str__(self):
        return f"Wishlist for {self.user.email}"


class WishlistItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlist_items')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['wishlist', 'product']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.product.name} in wishlist"


class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def total_price(self):
        return sum(item.subtotal() for item in self.items.all())

    def add_item(self, variant, qty=1):
        if not isinstance(qty, int) or qty <= 0:
            raise ValidationError("La quantité doit être un entier positif.")
        item, created = CartItem.objects.get_or_create(cart=self, product_variant=variant)
        if not created:
            item.quantity += qty
        else:
            item.quantity = qty
        item.save()

    def clear(self):
        self.items.all().delete()

    def __str__(self):
        return f"Cart for {self.user.email}"


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['cart', 'product_variant']
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0), name='cart_item_positive_quantity')]
        ordering = ['-added_at']

    def subtotal(self):
        return self.quantity * self.product_variant.price

    def __str__(self):
        return f"{self.quantity} x {self.product_variant.product.name}"
