/**
 * Client API minimal pour appeler le backend Django/DRF
 * depuis l'app mobile (côté acheteur).
 */
import Constants from "expo-constants";

const API_BASE_URL = (
  Constants.expoConfig?.extra?.apiUrl ?? "http://localhost:8000/api"
).replace(/\/$/, "");
const REQUEST_TIMEOUT_MS = 10_000;

export async function apiGet<T>(path: string): Promise<T> {
  if (!path.startsWith("/")) {
    throw new Error("Le chemin API doit commencer par '/'.");
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { signal: controller.signal });
  } catch (error) {
    if (
      error &&
      typeof error === "object" &&
      "name" in error &&
      error.name === "AbortError"
    ) {
      throw new Error(`Délai dépassé sur ${path}`);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
  if (!res.ok) {
    throw new Error(`Erreur API (${res.status}) sur ${path}`);
  }
  return res.json();
}
