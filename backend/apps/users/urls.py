from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, RoleViewSet, PermissionViewSet,
    UserRoleViewSet, RolePermissionViewSet
)

router = DefaultRouter()
# IMPORTANT : UserViewSet est enregistré au préfixe vide (""), qui génère une
# route détail attrape-tout `^(?P<pk>[^/.]+)/$`. Si on l'enregistre en premier,
# cette route intercepte /users/roles/, /users/permissions/, /users/user-roles/
# etc. avant qu'elles n'atteignent leur propre ViewSet (404 systématique).
# Les préfixes nommés doivent donc être enregistrés AVANT le préfixe vide.
router.register("roles", RoleViewSet, basename="role")
router.register("permissions", PermissionViewSet, basename="permission")
router.register("user-roles", UserRoleViewSet, basename="userrole")
router.register("role-permissions", RolePermissionViewSet, basename="rolepermission")
router.register("", UserViewSet, basename="user")

urlpatterns = router.urls
