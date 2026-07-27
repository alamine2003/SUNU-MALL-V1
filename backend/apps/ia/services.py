"""
Appels au LLM (Anthropic Claude). Synchrones et appelés directement depuis
les vues (apps/ia/views.py) : contrairement à un batch/inférence lourde
locale, un appel API texte de quelques secondes est un appel réseau
classique, du même genre que les passerelles de paiement du projet
(apps/payments/gateways.py) — pas besoin de Celery ici, le client attend
une réponse immédiate.
"""
import logging

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-5"

# Message générique renvoyé au client : le détail technique de l'erreur
# Anthropic (souvent un problème de facturation/quota côté compte) n'a
# rien à faire dans l'interface d'un commerçant ou d'un client — il part
# dans les logs serveur (voir logger.exception ci-dessous) pour qui doit
# vraiment le voir.
GENERIC_ERROR_MESSAGE = "Le service IA est temporairement indisponible. Réessayez dans quelques instants."


class AIServiceError(Exception):
    """Erreur exploitable côté vue (clé absente, appel API en échec...)."""


def _client() -> anthropic.Anthropic:
    if not settings.ANTHROPIC_API_KEY:
        raise AIServiceError("Le service IA n'est pas configuré sur cet environnement.")
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def generate_product_description(name: str, category_name: str | None, price: str, store_name: str) -> str:
    """Rédige une description produit courte à partir des infos déjà saisies par le commerçant."""
    client = _client()
    prompt = (
        "Tu écris des descriptions produit pour une marketplace e-commerce sénégalaise (Sunu Mall), en français.\n\n"
        f"Produit : {name}\n"
        f"Catégorie : {category_name or 'non précisée'}\n"
        f"Prix : {price} FCFA\n"
        f"Boutique : {store_name}\n\n"
        "Écris une description de 2 à 4 phrases : claire, vendeuse, sans emoji, et surtout sans inventer de "
        "caractéristiques techniques précises (dimensions, matériaux, specs) que tu ne connais pas réellement. "
        "Réponds uniquement avec la description, sans titre ni guillemets."
    )
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as exc:
        logger.exception("Échec génération de description produit (Anthropic)")
        raise AIServiceError(GENERIC_ERROR_MESSAGE) from exc
    return message.content[0].text.strip()


SUPPORT_SYSTEM_PROMPT = (
    "Tu es l'assistant client de Sunu Mall, une marketplace e-commerce sénégalaise qui connecte clients, "
    "commerçants et livreurs. Tu aides les visiteurs et clients avec leurs questions sur la commande, la "
    "livraison, les paiements (Wave, Orange Money, carte bancaire) et le fonctionnement général du site.\n\n"
    "Règles :\n"
    "- Réponds en français, de façon courte et directe.\n"
    "- Tu n'as pas accès aux commandes réelles des clients : si la question porte sur le statut précis d'une "
    "commande, invite poliment le client à consulter « Mes commandes » ou « Suivre ma livraison » dans son espace.\n"
    "- Ne promets jamais un délai de livraison ou un remboursement précis que tu ne peux pas garantir.\n"
    "- Si tu ne sais pas répondre, dis-le honnêtement plutôt que d'inventer une réponse."
)


def chat_reply(history: list[dict], user_message: str) -> str:
    """Répond à un message dans le fil de discussion de l'assistant client."""
    client = _client()
    messages = [*history, {"role": "user", "content": user_message}]
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=SUPPORT_SYSTEM_PROMPT,
            messages=messages,
        )
    except anthropic.APIError as exc:
        logger.exception("Échec de réponse de l'assistant client (Anthropic)")
        raise AIServiceError(GENERIC_ERROR_MESSAGE) from exc
    return response.content[0].text.strip()
