import { apiGet, apiPost } from "@/lib/api";
import type { Paginated, Payment } from "@/types";

export function listPayments(params?: { page?: number }) {
  const qs = params?.page ? `?page=${params.page}` : "";
  return apiGet<Paginated<Payment>>(`/payments/${qs}`);
}

export interface InitiatePaymentResult {
  sandbox: boolean;
  provider_ref: string;
  message: string;
}

export function initiatePayment(paymentId: string) {
  return apiPost<InitiatePaymentResult>(`/payments/${paymentId}/initiate/`);
}

export function sandboxConfirmPayment(paymentId: string, outcome: "success" | "failed") {
  return apiPost<Payment>(`/payments/${paymentId}/sandbox-confirm/`, { outcome });
}
