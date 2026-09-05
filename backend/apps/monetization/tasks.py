"""Entretien des abonnements hors des requêtes de consultation."""
from datetime import timedelta
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from .models import Subscription, Notification


@shared_task(ignore_result=True)
def maintain_subscriptions():
    today = timezone.now().date()
    candidates = Subscription.objects.filter(
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.EXPIRED],
        ends_at__lte=today + timedelta(days=3),
    ).values_list('pk', flat=True)
    for pk in candidates.iterator():
        with transaction.atomic():
            subscription = Subscription.objects.select_for_update().select_related('plan').get(pk=pk)
            if subscription.status not in {Subscription.Status.ACTIVE, Subscription.Status.EXPIRED}:
                continue
            expired = subscription.ends_at < today
            if expired and subscription.status == Subscription.Status.ACTIVE:
                subscription.status = Subscription.Status.EXPIRED
                subscription.save(update_fields=['status'])
            event = 'expired' if expired else 'expiring'
            if Notification.objects.filter(metadata__subscription_id=str(pk), metadata__event=event).exists():
                continue
            user = subscription.subscriber_user()
            if user is None:
                continue
            notification = Notification.objects.create(
                user=user, channel=Notification.Channel.EMAIL,
                subject='Abonnement expiré' if expired else 'Votre abonnement expire bientôt',
                message=f'Votre abonnement « {subscription.plan.name} » arrive à échéance le {subscription.ends_at:%d/%m/%Y}.',
                metadata={'subscription_id': str(pk), 'event': event},
            )
            transaction.on_commit(notification.send)
