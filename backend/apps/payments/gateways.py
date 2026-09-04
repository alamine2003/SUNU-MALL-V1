"""Passerelle NabooPay pour les encaissements Wave et Orange Money."""

from decimal import Decimal

import httpx
from django.conf import settings


class PaymentGatewayError(Exception):
    """Erreur contrôlée renvoyée quand le fournisseur refuse une demande."""


class BasePaymentGateway:
    def initiate(self, payment) -> dict:
        """Démarre le paiement et retourne les informations de redirection."""
        raise NotImplementedError


class SandboxGateway(BasePaymentGateway):
    """Simulation locale qui ne contacte jamais un fournisseur."""

    def initiate(self, payment) -> dict:
        provider_ref = payment.provider_ref or f"SANDBOX-{payment.id.hex[:10].upper()}"
        payment.provider_ref = provider_ref
        payment.save(update_fields=["provider_ref", "updated_at"])
        return {
            "sandbox": True,
            "provider_ref": provider_ref,
            "checkout_url": None,
            "message": (
                "Mode test : aucune transaction réelle n'est envoyée à "
                f"{payment.method}. Utilisez l'action « sandbox-confirm » "
                "pour simuler le résultat du paiement."
            ),
        }


class NabooPayGateway(BasePaymentGateway):
    """Création d'une transaction NabooPay v2 et récupération du checkout."""

    def initiate(self, payment) -> dict:
        api_key = settings.NABOOPAY_API_KEY
        if not api_key:
            raise PaymentGatewayError("NABOOPAY_API_KEY n'est pas configurée.")

        if payment.method not in {"wave", "orange_money"}:
            raise PaymentGatewayError(
                "Ce moyen de paiement n'est pas disponible avec NabooPay."
            )

        if payment.provider_ref and payment.checkout_url:
            return {
                "sandbox": False,
                "provider_ref": payment.provider_ref,
                "checkout_url": payment.checkout_url,
                "message": "Reprise de la session de paiement en cours.",
            }

        order = payment.order if payment.order_id else None
        customer = order.customer if order else payment.subscription.subscriber_user()
        if customer is None:
            raise PaymentGatewayError("Le client du paiement est introuvable.")
        products = (
            [
                {
                    "name": item.product_variant.product.name,
                    "price": self._xof_amount(item.unit_price),
                    "quantity": item.quantity,
                    "description": item.product_variant.product.description,
                }
                for item in order.items.select_related("product_variant__product").all()
            ]
            if order
            else [
                {
                    "name": payment.subscription.plan.name,
                    "price": self._xof_amount(payment.amount),
                    "quantity": 1,
                    "description": "Abonnement SUNU MALL",
                }
            ]
        )
        target_id = order.id if order else payment.subscription_id
        payload = {
            "method_of_payment": [payment.method],
            "selected_payment_method": payment.method,
            "amount": self._xof_amount(payment.amount),
            "currency": "XOF",
            "customer": {
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "phone": customer.phone,
            },
            "products": products,
            "is_escrow": settings.NABOOPAY_IS_ESCROW,
            "fees_customer_side": settings.NABOOPAY_FEES_CUSTOMER_SIDE,
            "success_url": (
                f"{settings.FRONTEND_URL}/order-confirmed?order={target_id}"
                if order
                else f"{settings.FRONTEND_URL}/subscriptions?payment={payment.id}"
            ),
            "error_url": (
                f"{settings.FRONTEND_URL}/checkout-payment?payment={payment.id}&status=failed"
            ),
        }

        try:
            response = httpx.post(
                f"{settings.NABOOPAY_BASE_URL.rstrip('/')}/api/v2/transactions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
                timeout=settings.NABOOPAY_TIMEOUT,
            )
        except httpx.RequestError as exc:
            raise PaymentGatewayError("NabooPay est momentanément indisponible.") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise PaymentGatewayError("Réponse NabooPay invalide.") from exc

        if response.is_error:
            message = data.get("error", "NabooPay a refusé la transaction.")
            raise PaymentGatewayError(str(message))

        transaction = data.get("data", data)
        provider_ref = transaction.get("order_id") or transaction.get("id")
        checkout_url = (
            transaction.get("checkout_url")
            or transaction.get("payment_url")
            or transaction.get("url")
        )
        if not provider_ref or not checkout_url:
            raise PaymentGatewayError(
                "NabooPay n'a pas renvoyé de référence et de lien de paiement."
            )

        payment.provider_ref = str(provider_ref)
        payment.checkout_url = str(checkout_url)
        payment.save(update_fields=["provider_ref", "checkout_url", "updated_at"])
        return {
            "sandbox": False,
            "provider_ref": payment.provider_ref,
            "checkout_url": payment.checkout_url,
            "message": "Redirection vers NabooPay pour terminer le paiement.",
        }

    @staticmethod
    def _xof_amount(amount: Decimal) -> int:
        normalized = Decimal(amount).quantize(Decimal("1"))
        if normalized != amount:
            raise PaymentGatewayError("Le montant doit être un nombre entier de FCFA.")
        return int(normalized)


def get_gateway(method: str) -> BasePaymentGateway:
    if settings.PAYMENT_SANDBOX:
        return SandboxGateway()
    if method in {"wave", "orange_money"}:
        return NabooPayGateway()
    raise PaymentGatewayError(
        f"Le moyen de paiement « {method} » n'est pas configuré en production."
    )
