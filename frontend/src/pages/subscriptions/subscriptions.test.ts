// @vitest-environment jsdom
import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as monetizationApi from "@/api/monetization";
import * as paymentsApi from "@/api/payments";
import type { Payment, Subscription, SubscriptionPlan } from "@/types";
import SubscriptionsPage from "./index";

vi.mock("@/api/monetization");
vi.mock("@/api/payments");

const plan: SubscriptionPlan = {
  id: "plan-1", name: "Premium", price: "5000", billing_cycle: "monthly",
  features: {}, created_at: "2026-09-01",
};
const subscription: Subscription = {
  id: "subscription-1", plan: plan.id, subscriber_type: "merchant", subscriber_id: "merchant-1",
  status: "pending", starts_at: "2026-09-01", ends_at: "2026-10-01",
  created_at: "2026-09-01", updated_at: "2026-09-01",
};
const payment: Payment = {
  id: "payment-1", order: null, subscription: subscription.id, method: "wave", amount: "5000",
  status: "pending", provider_ref: "", refund: null, created_at: "2026-09-01",
};
const sandboxSession = { sandbox: true, provider_ref: "test", checkout_url: null, message: "" };

let container: HTMLDivElement;
let root: Root;

async function renderPage() {
  await act(async () => { root.render(createElement(SubscriptionsPage)); });
}

async function click(label: string) {
  const button = Array.from(container.querySelectorAll("button")).find((element) =>
    element.textContent?.trim().startsWith(label) || element.getAttribute("aria-label") === label,
  );
  expect(button, `Bouton manquant : ${label}`).toBeDefined();
  await act(async () => { button!.click(); });
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  vi.mocked(monetizationApi.listSubscriptionPlans).mockResolvedValue([plan]);
  vi.mocked(monetizationApi.listSubscriptions).mockResolvedValue([subscription]);
  vi.mocked(monetizationApi.subscribe).mockResolvedValue({ subscription, payment });
  vi.mocked(paymentsApi.initiatePayment).mockResolvedValue(sandboxSession);
  vi.mocked(paymentsApi.sandboxConfirmPayment).mockResolvedValue({ ...payment, status: "success" });
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(async () => {
  await act(async () => { root.unmount(); });
  container.remove();
  vi.unstubAllGlobals();
});

describe("Reprise d'un abonnement en attente", () => {
  it("retrouve le paiement après fermeture de la fenêtre et rechargement de la page", async () => {
    await renderPage();
    await click("Reprendre le paiement");
    await click("Payer");
    expect(paymentsApi.initiatePayment).toHaveBeenLastCalledWith(payment.id);
    await click("Fermer");
    await act(async () => { root.unmount(); });
    root = createRoot(container);
    await renderPage();
    await click("Reprendre le paiement");
    await click("Payer");
    expect(monetizationApi.subscribe).toHaveBeenCalledTimes(2);
    expect(paymentsApi.initiatePayment).toHaveBeenLastCalledWith(payment.id);
    expect(container.textContent).toContain("Simuler paiement réussi");
  });

  it("permet d'annuler l'abonnement en attente", async () => {
    vi.mocked(monetizationApi.cancelSubscription).mockResolvedValue({ ...subscription, status: "cancelled" });
    await renderPage();
    vi.mocked(monetizationApi.listSubscriptions).mockResolvedValue([]);
    await click("Annuler l'abonnement en attente");
    expect(monetizationApi.cancelSubscription).toHaveBeenCalledWith(subscription.id);
    expect(container.textContent).not.toContain("Abonnement en attente de paiement");
  });

  it("propose une reprise si l'initialisation du fournisseur échoue", async () => {
    vi.mocked(paymentsApi.initiatePayment).mockRejectedValueOnce(new Error("Indisponible"));
    await renderPage();
    await click("Reprendre le paiement");
    await click("Payer");
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("Impossible de démarrer");
    expect(container.textContent).not.toContain("Simuler paiement réussi");
    await click("Réessayer le paiement");
    expect(paymentsApi.initiatePayment).toHaveBeenCalledTimes(2);
    expect(container.textContent).toContain("Simuler paiement réussi");
  });

  it("n'affiche pas les commandes sandbox pour une session réelle", async () => {
    vi.mocked(paymentsApi.initiatePayment).mockResolvedValue({ ...sandboxSession, sandbox: false });
    await renderPage();
    await click("Reprendre le paiement");
    await click("Payer");
    expect(container.textContent).not.toContain("Simuler paiement réussi");
    expect(paymentsApi.sandboxConfirmPayment).not.toHaveBeenCalled();
  });

  it("crée un nouveau paiement après un échec au lieu de confirmer l'abonnement annulé", async () => {
    await renderPage();
    await click("Reprendre le paiement");
    await click("Payer");
    vi.mocked(monetizationApi.listSubscriptions).mockResolvedValue([{ ...subscription, status: "cancelled" }]);
    await click("Simuler échec");
    const newPayment = { ...payment, id: "payment-2", subscription: "subscription-2" };
    vi.mocked(monetizationApi.subscribe).mockResolvedValue({
      subscription: { ...subscription, id: "subscription-2" }, payment: newPayment,
    });
    await click("Réessayer avec un nouveau paiement");
    expect(paymentsApi.initiatePayment).toHaveBeenLastCalledWith(newPayment.id);
    await click("Simuler paiement réussi");
    expect(paymentsApi.sandboxConfirmPayment).toHaveBeenNthCalledWith(1, payment.id, "failed");
    expect(paymentsApi.sandboxConfirmPayment).toHaveBeenNthCalledWith(2, newPayment.id, "success");
  });
});
