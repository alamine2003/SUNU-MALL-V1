"""
Calcule (ou recalcule) les statistiques de vente journalières par boutique
(apps.analytics.models.SalesStatistic), à partir des commandes réelles.

Usage :
    python manage.py compute_sales_stats                 # hier, pour toutes les boutiques
    python manage.py compute_sales_stats --date 2026-07-20
    python manage.py compute_sales_stats --days 30        # recalcule les 30 derniers jours
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.analytics.models import SalesStatistic
from apps.catalog.models import Store


class Command(BaseCommand):
    help = "Calcule les statistiques de vente journalières par boutique à partir des commandes."

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, help="Date à calculer (AAAA-MM-JJ). Défaut : hier.")
        parser.add_argument("--days", type=int, default=1, help="Nombre de jours à recalculer en partant de --date (ou hier).")

    def handle(self, *args, **options):
        if options.get("date"):
            end_date = parse_date(options["date"])
            if not end_date:
                self.stderr.write(self.style.ERROR("Format de date invalide, attendu AAAA-MM-JJ."))
                return
        else:
            end_date = timezone.now().date() - timedelta(days=1)

        days = max(1, options["days"])
        stores = list(Store.objects.all())
        if not stores:
            self.stdout.write("Aucune boutique en base.")
            return

        total_computed = 0
        for offset in range(days):
            date = end_date - timedelta(days=offset)
            for store in stores:
                SalesStatistic.compute_for_store(store, date)
                total_computed += 1

        self.stdout.write(self.style.SUCCESS(
            f"{total_computed} ligne(s) de statistiques calculées pour {len(stores)} boutique(s) sur {days} jour(s)."
        ))
