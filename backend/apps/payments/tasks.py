"""Entretien périodique des réservations, via le Celery Beat existant."""
from celery import shared_task
from django.core.management import call_command


@shared_task(ignore_result=True)
def expire_pending_payments():
    call_command('expire_pending_payments')
