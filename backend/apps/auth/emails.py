"""Résolution des adresses, y compris celles enregistrées avant normalisation."""
from apps.users.models import User


def utilisateur_par_email(email):
    email = email.strip()
    candidats = list(User.objects.filter(email__iexact=email)[:2])
    if len(candidats) == 1:
        return candidats[0]
    # Ne jamais fusionner ni choisir arbitrairement deux anciens comptes
    # dont les adresses ne diffèrent que par la casse.
    if candidats:
        return User.objects.filter(email=email).first()
    return None


def email_de_connexion(email):
    user = utilisateur_par_email(email)
    return user.email if user else email.strip()
