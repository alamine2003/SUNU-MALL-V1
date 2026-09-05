"""
Permissions personnalisées pour le RBAC de SUNU MALL.
"""
from rest_framework import permissions
from apps.users.models import Role


class IsAdmin(permissions.BasePermission):
    """Permission pour les administrateurs uniquement."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.has_role(Role.RoleName.ADMIN)
        )




class IsMerchantOrAdmin(permissions.BasePermission):
    """Permission pour les comptes qui gèrent le catalogue marchand."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (
                request.user.has_role(Role.RoleName.MERCHANT)
                or request.user.has_role(Role.RoleName.ADMIN)
            )
        )










class IsStoreOwnerOrAdmin(permissions.BasePermission):
    """
    Vérifie si l'utilisateur est le propriétaire de la boutique associée à l'objet ou admin.
    L'objet doit avoir un attribut 'store' ou une méthode get_store().
    """
    def has_object_permission(self, request, view, obj):
        # Admin peut tout faire
        if request.user.has_role(Role.RoleName.ADMIN):
            return True
        
        # Récupérer la boutique
        store = None
        if hasattr(obj, 'store'):
            store = obj.store
        elif hasattr(obj, 'get_store'):
            store = obj.get_store()
        
        if store:
            return store.owner == request.user
        return False
