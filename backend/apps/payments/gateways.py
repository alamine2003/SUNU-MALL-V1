"""
Passerelles de paiement (Wave, Orange Money, carte bancaire).

Aucune clé API marchande réelle n'est configurée pour l'instant : tant que
`settings.PAYMENT_SANDBOX` est actif (par défaut), toutes les méthodes de
paiement passent par `SandboxGateway`, qui simule le cycle de vie d'un
paiement réel sans jamais contacter Wave/Orange Money. `WaveGateway` et
`OrangeMoneyGateway` documentent la forme qu'aurait le vrai branchement —
il suffira de fournir les clés (`WAVE_API_KEY`, `ORANGE_MONEY_API_KEY`)
et de désactiver `PAYMENT_SANDBOX` pour les activer, sans toucher au reste
du code (vues, frontend).
"""
from django.conf import settings


class PaymentGatewayError(Exception):
    pass


class BasePaymentGateway:
    def initiate(self, payment) -> dict:
        """Démarre le paiement. Retourne les infos à afficher/utiliser côté client."""
        raise NotImplementedError


class SandboxGateway(BasePaymentGateway):
    """Simulation locale — ne contacte aucun vrai fournisseur de paiement."""

    def initiate(self, payment) -> dict:
        provider_ref = f"SANDBOX-{payment.id.hex[:10].upper()}"
        payment.provider_ref = provider_ref
        payment.save(update_fields=["provider_ref"])
        return {
            "sandbox": True,
            "provider_ref": provider_ref,
            "message": (
                "Mode test : aucune transaction réelle n'est envoyée à "
                f"{payment.method}. Utilisez l'action « sandbox-confirm » "
                "pour simuler le résultat du paiement."
            ),
        }


class WaveGateway(BasePaymentGateway):
    """
    Squelette d'intégration réelle de l'API Wave Checkout.
    À activer en configurant WAVE_API_KEY et en désactivant PAYMENT_SANDBOX.
    """

    def initiate(self, payment) -> dict:
        if not settings.WAVE_API_KEY:
            raise PaymentGatewayError("WAVE_API_KEY n'est pas configurée.")
        # Intégration réelle (non implémentée sans clé de test) :
        #   POST https://api.wave.com/v1/checkout/sessions
        #   Headers: Authorization: Bearer {settings.WAVE_API_KEY}
        #   Body: {"amount": str(payment.amount), "currency": "XOF",
        #          "success_url": ..., "error_url": ..., "client_reference": str(payment.id)}
        #   -> stocker session["id"] dans payment.provider_ref, rediriger vers session["wave_launch_url"]
        raise NotImplementedError("Intégration Wave réelle non implémentée.")


class OrangeMoneyGateway(BasePaymentGateway):
    """Squelette d'intégration réelle de l'API Orange Money Web Payment."""

    def initiate(self, payment) -> dict:
        if not settings.ORANGE_MONEY_API_KEY:
            raise PaymentGatewayError("ORANGE_MONEY_API_KEY n'est pas configurée.")
        raise NotImplementedError("Intégration Orange Money réelle non implémentée.")


def get_gateway(method: str) -> BasePaymentGateway:
    if settings.PAYMENT_SANDBOX:
        return SandboxGateway()
    return {
        "wave": WaveGateway(),
        "orange_money": OrangeMoneyGateway(),
    }.get(method, SandboxGateway())
