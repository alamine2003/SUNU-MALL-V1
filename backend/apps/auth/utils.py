"""
Utilitaires pour l'authentification : génération de tokens, envoi d'emails, etc.
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.conf import settings
from apps.users.models import User


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Générateur de tokens pour la vérification d'email (hérite de PasswordResetTokenGenerator).
    """
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_verified}"


email_verification_token = EmailVerificationTokenGenerator()


def send_verification_email(user: User):
    """
    Envoie un email de vérification à l'utilisateur.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    
    # TODO: Remplacer par la vraie URL du frontend
    verification_url = f"{settings.FRONTEND_URL or 'http://localhost:3000'}/verify-email?uid={uid}&token={token}"
    
    subject = "Vérifiez votre email - SUNU MALL"
    message = render_to_string('emails/verification_email.txt', {
        'user': user,
        'verification_url': verification_url,
    })
    html_message = render_to_string('emails/verification_email.html', {
        'user': user,
        'verification_url': verification_url,
    })
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )
