import { browserSessionRequest } from "@/lib/session";
import { ApiError, apiGet, apiPost } from "@/lib/api";
import type { AuthUser } from "@/types";

export interface AuthResponse {
  user: AuthUser;
  access: string | null;
  refresh: string | null;
  message?: string;
}

export function login(email: string, password: string) {
  return browserAuth("login", { email, password });
}

export function register(payload: {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone: string;
  role_name?: "client" | "merchant" | "driver";
}) {
  return apiPost<AuthResponse>("/auth/register/", payload, { auth: false });
}

export function resendVerification(email: string) {
  return apiPost<{ message: string }>("/auth/resend-verification/", { email }, { auth: false });
}

export function guestCheckout(payload: { email: string; first_name: string; last_name?: string; phone: string }) {
  return browserAuth("guest-checkout", payload);
}

export function setPassword(password: string) {
  return apiPost<{ message: string }>("/auth/set-password/", { password });
}

export function verifyEmail(uid: string, token: string) {
  return apiGet<{ message: string }>(
    `/auth/verify-email/?uid=${encodeURIComponent(uid)}&token=${encodeURIComponent(token)}`,
    { auth: false },
  );
}

async function browserAuth(path: string, payload: unknown): Promise<AuthResponse> {
  const response = await browserSessionRequest(path, payload);
  const data = await response.json();
  if (!response.ok) throw new ApiError(response.status, data);
  return data;
}
