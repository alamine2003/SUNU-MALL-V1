import { apiGet, apiPost } from "@/lib/api";
import type { AuthUser } from "@/types";

export interface AuthResponse {
  user: AuthUser;
  access: string | null;
  refresh: string | null;
  message?: string;
}

export function login(email: string, password: string) {
  return apiPost<AuthResponse>("/auth/login/", { email, password }, { auth: false });
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

export function verifyEmail(uid: string, token: string) {
  return apiGet<{ message: string }>(
    `/auth/verify-email/?uid=${encodeURIComponent(uid)}&token=${encodeURIComponent(token)}`,
    { auth: false },
  );
}
