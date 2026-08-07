from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from apps.catalog.models import Category, Product, Store
from apps.catalog.serializers import ProductSerializer
from apps.users.models import Role
from .models import RecommendationLog
from .serializers import ChatSerializer, GenerateDescriptionSerializer, RecommendationLogSerializer
from .services import MODEL_DISPLAY_NAME, AIServiceError, chat_reply, generate_product_description

# Nombre de messages précédents renvoyés au modèle : suffisant pour garder le
# fil de la conversation, sans laisser un historique illimité gonfler le coût
# (et la latence) de chaque appel.
MAX_CHAT_HISTORY = 20


class GenerateDescriptionView(GenericAPIView):
    """
    POST /api/ia/generate-description/
    Rédige une description produit à partir du nom/catégorie/prix déjà
    saisis par le commerçant sur /add-product. Réservé aux commerçants,
    et seulement pour leur propre boutique.
    """
    serializer_class = GenerateDescriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "ai"

    def post(self, request):
        if not request.user.has_role(Role.RoleName.MERCHANT):
            raise PermissionDenied("Réservé aux comptes commerçants.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            store = Store.objects.get(pk=data["store"])
        except Store.DoesNotExist:
            return Response({"error": "Boutique introuvable."}, status=status.HTTP_404_NOT_FOUND)
        if store.owner_id != request.user.id:
            raise PermissionDenied("Vous ne pouvez générer une description que pour votre propre boutique.")

        category_name = None
        if data.get("category"):
            category_name = Category.objects.filter(pk=data["category"]).values_list("name", flat=True).first()

        try:
            description = generate_product_description(
                name=data["name"],
                category_name=category_name,
                price=data["price"],
                store_name=store.name,
            )
        except AIServiceError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({"description": description, "model": MODEL_DISPLAY_NAME})


class ChatView(GenericAPIView):
    """
    POST /api/ia/chat/
    Assistant client (support). Public : un visiteur non connecté doit
    pouvoir poser une question avant même d'avoir un compte.
    """
    serializer_class = ChatSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = "ai"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        history = [{"role": m["role"], "content": m["content"]} for m in data["history"][-MAX_CHAT_HISTORY:]]

        try:
            reply, products = chat_reply(history, data["message"])
        except AIServiceError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({"reply": reply, "products": ProductSerializer(products, many=True).data})


class RecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    """Historique des recommandations calculées pour l'utilisateur connecté (voir l'action `for_me`)."""

    serializer_class = RecommendationLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RecommendationLog.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="for-me")
    def for_me(self, request):
        """
        GET /api/ia/recommendations/for-me/
        Calcule (par co-achat, voir RecommendationLog.compute_for_user) et
        renvoie directement les produits recommandés pour l'utilisateur
        connecté — synchrone, un agrégat SQL est déjà instantané, inutile
        de faire attendre un aller-retour Celery pour ça.
        """
        log = RecommendationLog.compute_for_user(request.user)
        product_ids = log.payload.get("recommended_product_ids", [])
        products = Product.objects.filter(id__in=product_ids, status=Product.Status.ACTIVE)
        products_by_id = {str(p.id): p for p in products}
        ordered = [products_by_id[pid] for pid in product_ids if pid in products_by_id]
        return Response(ProductSerializer(ordered, many=True).data)
