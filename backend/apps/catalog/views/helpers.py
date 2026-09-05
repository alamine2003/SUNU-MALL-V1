from rest_framework.exceptions import ValidationError
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from ..models import Product
from apps.monetization.models import Subscription, SubscriptionPlan

MAX_IMAGE_UPLOAD_SIZE = 5 * 1024 * 1024


def _validate_image_upload(image_file):
    """Réencode les pixels et impose le type réel, sans suffixe HTML ni métadonnées."""
    from io import BytesIO
    from uuid import uuid4
    from django.core.files.uploadedfile import SimpleUploadedFile

    if image_file.size > MAX_IMAGE_UPLOAD_SIZE:
        raise ValidationError("L'image ne doit pas dépasser 5 Mo.")
    try:
        image_file.seek(0)
        with Image.open(image_file) as image:
            image.verify()
            image_format = image.format
            if image_format not in {"JPEG", "PNG", "WEBP"} or image.width * image.height > 20_000_000:
                raise ValidationError("Format ou dimensions d'image non supportés.")
        image_file.seek(0)
        with Image.open(image_file) as image:
            output = BytesIO()
            image.save(output, format=image_format)
        extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[image_format]
        return SimpleUploadedFile(f"{uuid4().hex}.{extension}", output.getvalue(), content_type=f"image/{extension if extension != 'jpg' else 'jpeg'}")
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise ValidationError("Le fichier fourni n'est pas une image valide.") from exc
    finally:
        image_file.seek(0)


def _active_product_limit(store):
    """
    Nombre max de produits ACTIFS (publiés) autorisés pour la boutique,
    selon l'abonnement en cours de son propriétaire — None = illimité.
    Sans abonnement actif, la boutique reste sur l'offre la moins chère
    (gratuite par construction : c'est l'offre d'entrée du produit).
    """
    today = timezone.now().date()
    subscription = (
        Subscription.objects.filter(
            subscriber_type="merchant", subscriber_id=store.owner_id,
            status=Subscription.Status.ACTIVE, starts_at__lte=today, ends_at__gte=today,
        )
        .select_related("plan")
        .first()
    )
    if subscription:
        return subscription.plan.max_products
    default_plan = SubscriptionPlan.objects.order_by("price").first()
    return default_plan.max_products if default_plan else None


def _check_product_limit(store, exclude_product_id=None):
    limit = _active_product_limit(store)
    if limit is None:
        return
    active_count = Product.objects.filter(store=store, status=Product.Status.ACTIVE)
    if exclude_product_id:
        active_count = active_count.exclude(id=exclude_product_id)
    if active_count.count() >= limit:
        raise ValidationError(
            f"Limite de {limit} produits actifs atteinte pour votre offre. "
            "Passez à une offre supérieure pour en publier davantage."
        )
