import { useState } from "react";
import { Check, CheckCircle2, Clock, Crown, FlaskConical, TriangleAlert, XCircle } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as monetizationApi from "@/api/monetization";
import * as paymentsApi from "@/api/payments";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { ApiError } from "@/lib/api";
import { cn, formatPrice } from "@/lib/utils";
import { PAYMENT_METHODS } from "@/lib/paymentMethods";
import type { Payment, Subscription, SubscriptionPlan } from "@/types";

const METHODS = PAYMENT_METHODS;

function formatDateOnly(dateStr: string) {
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" }).format(new Date(dateStr));
}

function daysUntil(dateStr: string) {
  const ms = new Date(dateStr).getTime() - new Date().setHours(0, 0, 0, 0);
  return Math.ceil(ms / (1000 * 60 * 60 * 24));
}

export default function SubscriptionsPage() {
  const { data: plans, loading: loadingPlans } = useAsync(() => monetizationApi.listSubscriptionPlans(), []);
  const { data: subscriptions, loading: loadingSubs, refetch } = useAsync(
    () => monetizationApi.listSubscriptions(),
    [],
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Boutique de souscription en cours (modal) : sélection du moyen de
  // paiement, puis confirmation sandbox explicite — même parcours que
  // /checkout-payment pour une commande, plutôt qu'une activation silencieuse.
  const [target, setTarget] = useState<SubscriptionPlan | null>(null);
  const [method, setMethod] = useState<(typeof METHODS)[number]["id"]>("wave");
  const [creating, setCreating] = useState(false);
  const [pendingSubscription, setPendingSubscription] = useState<Subscription | null>(null);
  const [pendingPayment, setPendingPayment] = useState<Payment | null>(null);
  const [confirming, setConfirming] = useState<"success" | "failed" | null>(null);
  const [paymentFailed, setPaymentFailed] = useState(false);
  const [paymentSession, setPaymentSession] = useState<paymentsApi.InitiatePaymentResult | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);

  const awaitingPayment = subscriptions?.filter((s) => s.status === "pending") ?? [];
  const activeSubscription = subscriptions?.find((s) => s.status === "active");

  async function openSubscribeModal(plan: SubscriptionPlan) {
    // Offre gratuite : aucun paiement à choisir, on active directement.
    if (parseFloat(plan.price) <= 0) {
      setBusy(plan.id);
      setError(null);
      setSuccess(null);
      try {
        const { subscription } = await monetizationApi.subscribe(plan.id, "wave");
        announceSuccess(plan.name, subscription.ends_at);
        refetch();
      } catch (err) {
        const data = err instanceof ApiError ? (err.data as { error?: string }) : null;
        setError(data?.error ?? "Impossible de souscrire à cette offre pour le moment.");
      } finally {
        setBusy(null);
      }
      return;
    }

    setTarget(plan);
    setMethod("wave");
    setPendingSubscription(null);
    setPendingPayment(null);
    setPaymentSession(null);
    setPaymentFailed(false);
    setModalError(null);
  }

  function closeModal() {
    setTarget(null);
  }

  async function handleCreateSubscription() {
    if (!target) return;
    setCreating(true);
    setModalError(null);
    try {
      const { subscription, payment } = await monetizationApi.subscribe(target.id, method);
      setPaymentFailed(false);
      setPendingSubscription(subscription);
      setPendingPayment(payment);
      refetch();
      if (payment) {
        await startPayment(payment);
      } else {
        closeModal();
        announceSuccess(target.name, subscription.ends_at);
      }
    } catch (err) {
      const data = err instanceof ApiError ? (err.data as { error?: string }) : null;
      setModalError(data?.error ?? "Impossible de souscrire à cette offre pour le moment.");
    } finally {
      setCreating(false);
    }
  }

  async function startPayment(payment: Payment) {
    setModalError(null);
    setPaymentSession(null);
    try {
      const session = await paymentsApi.initiatePayment(payment.id);
      setPaymentSession(session);
      if (!session.sandbox && session.checkout_url) window.location.assign(session.checkout_url);
    } catch {
      setModalError("Impossible de démarrer le paiement. Vous pouvez réessayer ou annuler l'abonnement en attente.");
    }
  }

  async function handleSandboxOutcome(outcome: "success" | "failed") {
    if (!pendingPayment) return;
    setConfirming(outcome);
    try {
      await paymentsApi.sandboxConfirmPayment(pendingPayment.id, outcome);
      if (outcome === "success") {
        closeModal();
        announceSuccess(target?.name ?? "", pendingSubscription?.ends_at ?? null);
        refetch();
      } else {
        setPaymentFailed(true);
        refetch();
      }
    } catch {
      setModalError("Impossible de confirmer le paiement. Réessayez dans quelques instants.");
    } finally {
      setConfirming(null);
    }
  }

  function announceSuccess(planName: string, endsAt: string | null) {
    setError(null);
    const endsLabel = endsAt ? ` jusqu'au ${formatDateOnly(endsAt)}` : "";
    setSuccess(`Abonnement « ${planName} » activé${endsLabel}. Un e-mail de confirmation vous a été envoyé.`);
  }

  async function cancel(id: string) {
    setBusy(id);
    setError(null);
    setSuccess(null);
    try {
      await monetizationApi.cancelSubscription(id);
      refetch();
    } catch {
      setError("Impossible d'annuler cet abonnement.");
    } finally {
      setBusy(null);
    }
  }

  if (loadingPlans || loadingSubs) return <Spinner label="Chargement des abonnements…" />;

  return (
    <div>
      <h1 className="mb-6 flex items-center gap-2 font-display text-2xl font-bold text-gray-900">
        <Crown className="h-6 w-6 text-orange" /> Abonnements
      </h1>
      {success && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-3.5 py-2.5 text-sm text-green-700">
          <Check className="h-4 w-4 shrink-0" />
          {success}
        </div>
      )}
      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-danger/30 bg-red-50 px-3.5 py-2.5 text-sm text-danger">
          <TriangleAlert className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}
      {awaitingPayment.map((subscription) => {
        const plan = plans?.find((offer) => offer.id === subscription.plan);
        return (
          <Card key={subscription.id} className="mb-4 flex items-center justify-between gap-3">
            <p className="text-sm">Abonnement en attente de paiement : {plan?.name ?? "offre précédente"}</p>
            <div className="flex gap-2">
              {plan && <Button onClick={() => openSubscribeModal(plan)}>Reprendre le paiement</Button>}
              <Button variant="secondary" loading={busy === subscription.id} onClick={() => cancel(subscription.id)}>
                Annuler l'abonnement en attente
              </Button>
            </div>
          </Card>
        );
      })}
      {plans?.length === 0 ? (
        <EmptyState icon={Crown} title="Aucune offre disponible" description="Revenez plus tard, de nouvelles offres seront proposées." />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {plans?.map((plan) => {
          const isActive = activeSubscription?.plan === plan.id;
          const features = Array.isArray(plan.features) ? (plan.features as string[]) : [];
          return (
            <Card key={plan.id} className={isActive ? "border-orange ring-1 ring-orange" : ""}>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="font-display font-bold text-ink">{plan.name}</h3>
                {isActive && <Badge variant="success">Actif</Badge>}
              </div>
              <p className="mb-3 font-display text-2xl font-bold text-orange">
                {formatPrice(plan.price)}
                <span className="text-sm font-normal text-muted-foreground">/{plan.billing_cycle}</span>
              </p>
              <ul className="mb-4 flex flex-col gap-1 text-sm text-muted-foreground">
                {features.map((f, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <Check className="h-4 w-4 text-success" /> {f}
                  </li>
                ))}
              </ul>
              {isActive && activeSubscription!.ends_at && (
                <p
                  className={cn(
                    "mb-3 flex items-center gap-1.5 text-xs font-medium",
                    daysUntil(activeSubscription!.ends_at) <= 3 ? "text-danger" : "text-muted-foreground",
                  )}
                >
                  <Clock className="h-3.5 w-3.5 shrink-0" />
                  Actif jusqu'au {formatDateOnly(activeSubscription!.ends_at)} (il reste{" "}
                  {Math.max(0, daysUntil(activeSubscription!.ends_at))} jour
                  {daysUntil(activeSubscription!.ends_at) > 1 ? "s" : ""})
                </p>
              )}
              {isActive ? (
                <Button variant="secondary" loading={busy === activeSubscription!.id} onClick={() => cancel(activeSubscription!.id)} className="w-full">
                  Annuler
                </Button>
              ) : (
                <Button onClick={() => openSubscribeModal(plan)} loading={busy === plan.id} className="w-full">
                  S'abonner
                </Button>
              )}
            </Card>
          );
          })}
        </div>
      )}

      <Modal open={!!target} onClose={closeModal} title={target ? `S'abonner — ${target.name}` : undefined} size="sm">
        {target && !pendingPayment && (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-muted-foreground">
              {formatPrice(target.price)} / {target.billing_cycle === "yearly" ? "an" : "mois"}
            </p>
            <div className="flex flex-col gap-2">
              {METHODS.map((m) => (
                <button key={m.id} onClick={() => setMethod(m.id)} className="text-left">
                  <Card
                    variant="interactive"
                    className={method === m.id ? "border-orange ring-1 ring-orange" : ""}
                  >
                    <div className="flex items-center gap-3">
                      <span className="grid h-9 w-9 shrink-0 place-items-center overflow-hidden rounded-lg bg-accent text-orange">
                        {m.image ? (
                          <img src={m.image} alt={m.label} className="h-full w-full object-cover" />
                        ) : null}
                      </span>
                      <p className="text-sm font-semibold text-ink">{m.label}</p>
                    </div>
                  </Card>
                </button>
              ))}
            </div>
            {modalError && (
              <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-red-50 px-3.5 py-2.5 text-sm text-danger">
                <TriangleAlert className="h-4 w-4 shrink-0" />
                {modalError}
              </div>
            )}
            <Button onClick={handleCreateSubscription} loading={creating} className="w-full">
              Payer {formatPrice(target.price)}
            </Button>
          </div>
        )}

        {pendingPayment && (
          <div className="flex flex-col gap-4">
            {paymentSession?.sandbox && <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              <FlaskConical className="h-4 w-4 shrink-0" />
              <div>
                <p className="font-semibold">Mode test (sandbox)</p>
                <p>Aucune vraie transaction Wave/Orange Money/carte n'est envoyée.</p>
              </div>
            </div>
            }
            {modalError && <p role="alert" className="text-sm text-danger">{modalError}</p>}
            {!paymentSession && (modalError
              ? <Button onClick={() => startPayment(pendingPayment)}>Réessayer le paiement</Button>
              : <Spinner label="Préparation du paiement…" />)}
            {paymentSession && !paymentSession.sandbox && <p>Redirection vers le paiement sécurisé…</p>}
            <p className="text-sm text-muted-foreground">
              {formatPrice(pendingPayment.amount)} via {METHODS.find((m) => m.id === pendingPayment.method)?.label}
            </p>

            {paymentSession?.sandbox && (paymentFailed ? (
              <div className="flex flex-col items-center gap-3 py-2 text-center">
                <span className="grid h-14 w-14 place-items-center rounded-full bg-red-100">
                  <XCircle className="h-8 w-8 text-danger" />
                </span>
                <p className="text-sm font-medium text-danger">Paiement simulé en échec.</p>
                <Button onClick={handleCreateSubscription} loading={creating}>
                  Réessayer avec un nouveau paiement
                </Button>
              </div>
            ) : (
              <div className="flex gap-3">
                <Button onClick={() => handleSandboxOutcome("success")} loading={confirming === "success"} className="flex-1">
                  <CheckCircle2 className="h-4 w-4" />
                  Simuler paiement réussi
                </Button>
                <Button variant="secondary" onClick={() => handleSandboxOutcome("failed")} loading={confirming === "failed"}>
                  Simuler échec
                </Button>
              </div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
}
