import { apiPost } from "@/lib/api";
import type { Payment } from "@/types";

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
