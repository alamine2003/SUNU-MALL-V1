import { useState } from "react";
import { Check, Crown } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as monetizationApi from "@/api/monetization";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatPrice } from "@/lib/utils";

export default function SubscriptionsPage() {
  const { data: plans, loading: loadingPlans } = useAsync(() => monetizationApi.listSubscriptionPlans(), []);
  const { data: subscriptions, loading: loadingSubs, refetch } = useAsync(
    () => monetizationApi.listSubscriptions(),
    [],
  );
  const [busy, setBusy] = useState<string | null>(null);

  const activeSubscription = subscriptions?.find((s) => s.status === "active");

  async function subscribe(planId: string) {
    setBusy(planId);
    try {
      await monetizationApi.subscribe(planId);
      refetch();
    } finally {
      setBusy(null);
    }
  }

  async function cancel(id: string) {
    setBusy(id);
    try {
      await monetizationApi.cancelSubscription(id);
      refetch();
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
              {isActive ? (
                <Button variant="secondary" loading={busy === activeSubscription!.id} onClick={() => cancel(activeSubscription!.id)} className="w-full">
                  Annuler
                </Button>
              ) : (
                <Button loading={busy === plan.id} onClick={() => subscribe(plan.id)} className="w-full">
                  S'abonner
                </Button>
              )}
            </Card>
          );
          })}
        </div>
      )}
    </div>
  );
}
