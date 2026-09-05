from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.payments.models import Payment
from apps.payments.services import fail_payment


class Command(BaseCommand):
    help = "Libère les réservations associées aux paiements en attente expirés."

    def handle(self, *args, **options):
        expired = Payment.objects.filter(
            status=Payment.Status.PENDING,
            expires_at__lte=timezone.now(),
        ).order_by("expires_at")
        count = 0
        for payment in expired.iterator():
            if fail_payment(payment):
                count += 1
        self.stdout.write(self.style.SUCCESS(f"{count} paiement(s) expiré(s) traité(s)."))
