"""Visibilité et chargement du catalogue utilisés par l'API et l'assistant."""
from django.db.models import Prefetch, Q
from apps.users.models import Role
from .models import Product, ProductVariant, Store


def visible_products(user=None):
    public = Q(status=Product.Status.ACTIVE, store__status=Store.Status.ACTIVE)
    if user is not None and user.is_authenticated:
        if user.has_role(Role.RoleName.ADMIN):
            return Product.objects.all()
        public |= Q(store__owner=user)
    return Product.objects.filter(public)


def product_details(queryset):
    return queryset.select_related('store').prefetch_related(
        'images', Prefetch('variants', queryset=ProductVariant.objects.select_related('inventory')),
    )
