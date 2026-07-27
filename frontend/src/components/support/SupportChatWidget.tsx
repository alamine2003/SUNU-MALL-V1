import { useEffect, useRef, useState } from "react";
import { MessageCircle, Send, TriangleAlert, X } from "lucide-react";
import * as iaApi from "@/api/ia";
import type { ChatMessage } from "@/api/ia";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

const WELCOME_MESSAGE: ChatMessage = {
  role: "assistant",
  content: "Bonjour 👋 Je suis l'assistant Sunu Mall. Une question sur une commande, la livraison ou le paiement ?",
};

export function SupportChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, open]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    const history = messages.filter((m) => m !== WELCOME_MESSAGE);
    const nextMessages = [...messages, { role: "user", content: text } as ChatMessage];
    setMessages(nextMessages);
    setInput("");
    setError(null);
    setSending(true);
    try {
      const { reply } = await iaApi.sendChatMessage({ message: text, history });
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? ((err.data as { error?: string })?.error ?? "L'assistant est indisponible pour le moment.")
          : "Impossible de contacter le serveur.";
      setError(message);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="fixed bottom-5 right-5 z-40 flex flex-col items-end gap-3">
      {open && (
        <div className="flex h-[28rem] w-80 flex-col overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-elevated sm:w-96">
          <div className="flex items-center justify-between bg-gradient-orange px-4 py-3 text-white">
            <p className="font-display font-bold">Assistant Sunu Mall</p>
            <button onClick={() => setOpen(false)} aria-label="Fermer" className="rounded-full p-1 hover:bg-white/20">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
            {messages.map((m, i) => (
              <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                <p
                  className={cn(
                    "max-w-[85%] rounded-2xl px-3.5 py-2 text-sm leading-relaxed",
                    m.role === "user" ? "bg-orange text-white" : "bg-gray-100 text-gray-800",
                  )}
                >
                  {m.content}
                </p>
              </div>
            ))}
            {sending && <p className="text-xs text-muted-foreground">L'assistant écrit…</p>}
            {error && (
              <div className="flex items-start gap-1.5 rounded-lg border border-danger/30 bg-red-50 px-3 py-2 text-xs text-danger">
                <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {error}
              </div>
            )}
          </div>

          <form onSubmit={handleSend} className="flex items-center gap-2 border-t border-gray-100 p-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Écrivez votre message…"
              className="focus-ring flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-orange"
            />
            <button
              type="submit"
              disabled={sending || !input.trim()}
              aria-label="Envoyer"
              className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-orange text-white transition-colors hover:bg-orange-dark disabled:opacity-40"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Fermer l'assistant" : "Ouvrir l'assistant"}
        className="grid h-14 w-14 place-items-center rounded-full bg-gradient-orange text-white shadow-orange transition-transform hover:scale-105"
      >
        {open ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
      </button>
    </div>
  );
}
