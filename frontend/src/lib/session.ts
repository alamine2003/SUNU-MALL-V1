/** Transport des seules routes de session web, protégé par CSRF. */
export const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000/api").replace(/\/+$/, "");

export async function browserSessionRequest(path: string, body?: unknown) {
  const csrf = await fetch(`${API_BASE_URL}/auth/browser/csrf/`, { credentials: "include" });
  if (!csrf.ok) throw new Error("Impossible de préparer la session.");
  const { csrfToken } = await csrf.json();
  return fetch(`${API_BASE_URL}/auth/browser/${path}/`, {
    method: "POST", credentials: "include",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
