from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from .models import Report, TrafficStatistic, SalesStatistic
from .serializers import ReportSerializer, TrafficStatisticSerializer, SalesStatisticSerializer
from apps.users.models import Role


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    """Rapports générés (ventes, trafic, inventaire) : chacun voit ses propres rapports, l'admin voit tout."""
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.has_role(Role.RoleName.ADMIN):
            return Report.objects.all()
        return Report.objects.filter(generated_by=user)


class TrafficStatisticViewSet(viewsets.ReadOnlyModelViewSet):
    """Statistiques de trafic par boutique : le commerçant voit celles de ses boutiques, l'admin voit tout."""
    serializer_class = TrafficStatisticSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.has_role(Role.RoleName.ADMIN):
            return TrafficStatistic.objects.all()
        return TrafficStatistic.objects.filter(store__owner=user)


class SalesStatisticViewSet(viewsets.ReadOnlyModelViewSet):
    """Statistiques de ventes par boutique : le commerçant voit celles de ses boutiques, l'admin voit tout."""
    serializer_class = SalesStatisticSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["store"]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.has_role(Role.RoleName.ADMIN):
            return SalesStatistic.objects.all()
        return SalesStatistic.objects.filter(store__owner=user)
