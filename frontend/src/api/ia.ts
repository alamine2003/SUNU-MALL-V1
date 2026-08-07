import { apiGet, apiPost } from "@/lib/api";
import type { Product } from "@/types";

/** Nom affiché du modèle IA utilisé — pour que commerçants et clients sachent quel modèle génère le contenu. */
export const AI_MODEL_DISPLAY_NAME = "Claude (Anthropic)";

export function generateProductDescription(payload: {
  name: string;
  category?: string | null;
  price: number;
  store: string;
}) {
  return apiPost<{ description: string; model: string }>("/ia/generate-description/", payload);
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export function sendChatMessage(payload: { message: string; history: ChatMessage[] }) {
  return apiPost<{ reply: string; products: Product[] }>("/ia/chat/", payload);
}

/**
 * Recommandations personnalisées pour l'utilisateur connecté, par
 * co-achat à partir de son historique de commandes réel (pas un appel
 * LLM — un agrégat SQL, voir apps/ia/models.py: RecommendationLog).
 */
export function getPersonalizedRecommendations() {
  return apiGet<Product[]>("/ia/recommendations/for-me/");
}
