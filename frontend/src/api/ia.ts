import { apiPost } from "@/lib/api";

export function generateProductDescription(payload: {
  name: string;
  category?: string | null;
  price: number;
  store: string;
}) {
  return apiPost<{ description: string }>("/ia/generate-description/", payload);
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export function sendChatMessage(payload: { message: string; history: ChatMessage[] }) {
  return apiPost<{ reply: string }>("/ia/chat/", payload);
}
