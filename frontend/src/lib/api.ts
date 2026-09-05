/**
 * Client API pour appeler le backend Django/DRF.
 * Injecte automatiquement le token JWT et tente un refresh sur 401.
 */
import { useAuthStore } from "@/store/authStore";

import { API_BASE_URL, browserSessionRequest } from "@/lib/session";
import type { LoginPayload } from "@/store/authStore";

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, data: unknown, message?: string) {
    super(message ?? `Erreur API (${status})`);
    this.status = status;
    this.data = data;
  }
}

let refreshing: Promise<string | null> | null = null;

export function refreshAccessToken(): Promise<string | null> {
  if (refreshing) return refreshing;
  const version = useAuthStore.getState().sessionVersion;
  refreshing = (async () => {
    const res = await browserSessionRequest("refresh");
    if (useAuthStore.getState().sessionVersion !== version) return null;
    if (!res.ok) {
      if (res.status === 401) useAuthStore.setState((state) => ({ user: null, accessToken: null, refreshToken: null, sessionVersion: state.sessionVersion + 1 }));
      return null;
    }
    const data: LoginPayload = await res.json();
    if (useAuthStore.getState().sessionVersion !== version) return null;
    useAuthStore.getState().loginSuccess(data);
    return data.access;
  })().finally(() => { refreshing = null; });
  return refreshing;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  auth?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}, isRetry = false): Promise<T> {
  const { method = "GET", body, auth = true } = options;
  const isFormData = body instanceof FormData;
  const headers: Record<string, string> = {};
  if (!isFormData) headers["Content-Type"] = "application/json";

  if (auth) {
    const token = useAuthStore.getState().accessToken;
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: isFormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && auth && !isRetry) {
    const currentToken = useAuthStore.getState().accessToken;
    const newToken = currentToken && headers.Authorization !== `Bearer ${currentToken}` ? currentToken : await refreshAccessToken();
    if (newToken) {
      return request<T>(path, options, true);
    }
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const contentType = res.headers.get("content-type") ?? "";
  const data = contentType.includes("application/json") ? await res.json() : await res.text();

  if (!res.ok) {
    throw new ApiError(res.status, data);
  }

  return data as T;
}

export const apiGet = <T>(path: string, options?: Omit<RequestOptions, "method" | "body">) =>
  request<T>(path, { ...options, method: "GET" });

export const apiPost = <T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) =>
  request<T>(path, { ...options, method: "POST", body });

export const apiPatch = <T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) =>
  request<T>(path, { ...options, method: "PATCH", body });

export const apiDelete = <T>(path: string, options?: Omit<RequestOptions, "method" | "body">) =>
  request<T>(path, { ...options, method: "DELETE" });
