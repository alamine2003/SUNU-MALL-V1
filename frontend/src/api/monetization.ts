import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import type { Invoice, Notification, Paginated, SponsoredProduct, Subscription, SubscriptionPlan } from "@/types";

export async function listNotifications() {
  const data = await apiGet<Paginated<Notification>>("/monetization/notifications/");
  return data.results;
}

export function markNotificationRead(id: string) {
  return apiPost<Notification>(`/monetization/notifications/${id}/read/`);
}

export function markAllNotificationsRead() {
  return apiPost<void>("/monetization/notifications/read-all/");
}

export async function listSubscriptionPlans() {
  const data = await apiGet<Paginated<SubscriptionPlan>>("/monetization/subscription-plans/");
  return data.results;
}

export async function listSubscriptions() {
  const data = await apiGet<Paginated<Subscription>>("/monetization/subscriptions/");
  return data.results;
}

export function subscribe(planId: string) {
  return apiPost<Subscription>("/monetization/subscriptions/", { plan: planId });
}

export function cancelSubscription(id: string) {
  return apiPost<Subscription>(`/monetization/subscriptions/${id}/cancel/`);
}

export async function listInvoices() {
  const data = await apiGet<Paginated<Invoice>>("/monetization/invoices/");
  return data.results;
}

export async function listMySponsoredProducts() {
  const data = await apiGet<Paginated<SponsoredProduct>>("/monetization/sponsored-products/");
  return data.results;
}

export function createSponsoredProduct(payload: {
  product: string;
  store: string;
  daily_budget: number;
  starts_at: string;
  ends_at: string;
}) {
  return apiPost<SponsoredProduct>("/monetization/sponsored-products/", { ...payload, status: "active" });
}

export function stopSponsoredProduct(id: string) {
  return apiPatch<SponsoredProduct>(`/monetization/sponsored-products/${id}/`, { status: "inactive" });
}

export function deleteSponsoredProduct(id: string) {
  return apiDelete<void>(`/monetization/sponsored-products/${id}/`);
}
