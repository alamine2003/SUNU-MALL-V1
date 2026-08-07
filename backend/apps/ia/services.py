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
# Nom affichable côté interface (commerçant/client) — la marketplace montre
# quel modèle génère le contenu plutôt que de le laisser invisible derrière
# un simple bouton "IA".
MODEL_DISPLAY_NAME = "Claude (Anthropic)"

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
    "livraison, les paiements (Wave, Orange Money, carte bancaire) et le fonctionnement général du site. Tu "
    "aides aussi à trouver des produits du catalogue à partir d'une description en langage naturel (ex : "
    "\"un téléphone à moins de 100 000 FCFA\", \"des chaussures pour homme\").\n\n"
    "Règles :\n"
    "- Réponds en français, de façon courte et directe.\n"
    "- Dès que le client décrit un produit qu'il cherche (même vaguement), utilise l'outil search_catalog "
    "plutôt que de suggérer des produits toi-même : ils doivent toujours venir du catalogue réel. Commente "
    "ensuite les résultats renvoyés (nombre trouvé, fourchette de prix) sans jamais inventer un produit qui "
    "n'y figure pas.\n"
    "- La recherche est une correspondance exacte de mots (pas de synonymes automatiques) : si un premier essai "
    "ne renvoie rien, réessaie une ou deux fois avec un synonyme courant du commerce (ex: téléphone → "
    "smartphone/portable, PC → ordinateur) avant de conclure. Si ça ne donne toujours rien, dis-le honnêtement "
    "et propose d'élargir la recherche (prix, mots-clés) plutôt que d'inventer une alternative.\n"
    "- Tu n'as pas accès aux commandes réelles des clients : si la question porte sur le statut précis d'une "
    "commande, invite poliment le client à consulter « Mes commandes » ou « Suivre ma livraison » dans son espace.\n"
    "- Ne promets jamais un délai de livraison ou un remboursement précis que tu ne peux pas garantir.\n"
    "- Si tu ne sais pas répondre, dis-le honnêtement plutôt que d'inventer une réponse."
)

CATALOG_SEARCH_TOOL = {
    "name": "search_catalog",
    "description": (
        "Recherche des produits actifs du catalogue Sunu Mall par mot-clé, prix maximum et/ou catégorie. "
        "Renvoie une liste de produits réels (nom, prix, boutique) — jamais de produits inventés."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Mots-clés décrivant le produit recherché, ex: téléphone, sac à main, chaussures homme",
            },
            "max_price": {
                "type": "number",
                "description": "Prix maximum en FCFA, uniquement si le client en a mentionné un",
            },
            "category": {
                "type": "string",
                "description": "Nom de catégorie si le client l'a mentionnée explicitement",
            },
        },
        "required": ["query"],
    },
}

# Nombre max d'allers-retours outil autorisés par réponse : un garde-fou
# contre une boucle d'appels d'outil qui s'enchaînerait indéfiniment
# (chaque tour est un appel Anthropic facturé).
MAX_TOOL_ROUNDS = 3


def _search_catalog(query: str = "", max_price: float | None = None, category: str | None = None, limit: int = 6):
    """Interroge le vrai catalogue — jamais le LLM lui-même — pour ancrer ses réponses sur des produits réels."""
    from django.db.models import Q
    from apps.catalog.models import Product

    qs = Product.objects.filter(status=Product.Status.ACTIVE)
    for word in query.split():
        qs = qs.filter(Q(name__icontains=word) | Q(description__icontains=word) | Q(category__name__icontains=word))
    if max_price is not None:
        qs = qs.filter(base_price__lte=max_price)
    if category:
        qs = qs.filter(category__name__icontains=category)
    return list(qs.select_related("store")[:limit])


def chat_reply(history: list[dict], user_message: str) -> tuple[str, list]:
    """
    Répond à un message dans le fil de discussion de l'assistant client. Peut
    s'appuyer sur l'outil search_catalog pour ancrer sa réponse sur de vrais
    produits plutôt que d'en halluciner. Renvoie (texte, produits trouvés).
    """
    client = _client()
    messages = [*history, {"role": "user", "content": user_message}]
    found_products: list = []
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            response = client.messages.create(
                model=MODEL,
                max_tokens=500,
                system=SUPPORT_SYSTEM_PROMPT,
                tools=[CATALOG_SEARCH_TOOL],
                messages=messages,
            )
            if response.stop_reason != "tool_use":
                break

            tool_use = next(block for block in response.content if block.type == "tool_use")
            products = _search_catalog(
                query=tool_use.input.get("query", ""),
                max_price=tool_use.input.get("max_price"),
                category=tool_use.input.get("category"),
            )
            found_products = products
            result_text = (
                "\n".join(f"{p.name} — {p.base_price} FCFA — boutique {p.store.name}" for p in products)
                or "Aucun produit trouvé."
            )
            messages.append({"role": "assistant", "content": response.content})
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": tool_use.id, "content": result_text}
                    ],
                }
            )
        else:
            response = client.messages.create(
                model=MODEL, max_tokens=500, system=SUPPORT_SYSTEM_PROMPT, messages=messages
            )
    except anthropic.APIError as exc:
        logger.exception("Échec de réponse de l'assistant client (Anthropic)")
        raise AIServiceError(GENERIC_ERROR_MESSAGE) from exc

    text = next((block.text for block in response.content if block.type == "text"), "")
    return text.strip(), found_products
