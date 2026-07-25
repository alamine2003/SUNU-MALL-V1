import { useState } from "react";
import { CheckCircle2, Store as StoreIcon } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";

export default function AdminShopsPage() {
  const { data: stores, loading, refetch } = useAsync(() => catalogApi.listStores(), []);
  const [busy, setBusy] = useState<string | null>(null);

  async function approve(id: string) {
    setBusy(id);
    try {
      await catalogApi.approveStore(id);
      refetch();
    } finally {
      setBusy(null);
    }
  }

  async function reject(id: string) {
    const reason = prompt("Raison du rejet (optionnel)") ?? undefined;
    setBusy(id);
    try {
      await catalogApi.rejectStore(id, reason);
      refetch();
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <Spinner label="Chargement des boutiques…" />;

  const pending = stores?.filter((s) => s.status === "inactive") ?? [];
  const others = stores?.filter((s) => s.status !== "inactive") ?? [];

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="mb-4 flex items-center gap-2 font-display text-2xl font-bold text-gray-900">
          <StoreIcon className="h-6 w-6 text-orange" /> Validation des boutiques
        </h1>
        {pending.length === 0 ? (
          <EmptyState icon={CheckCircle2} title="Aucune demande en attente" description="Toutes les boutiques ont été traitées." />
        ) : (
          <div className="flex flex-col gap-3">
            {pending.map((store) => (
              <Card key={store.id} className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-ink">{store.name}</p>
                  <p className="text-sm text-muted-foreground">{store.owner_email}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" loading={busy === store.id} onClick={() => approve(store.id)}>
                    Approuver
                  </Button>
                  <Button size="sm" variant="danger" loading={busy === store.id} onClick={() => reject(store.id)}>
                    Rejeter
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <div>
        <h2 className="mb-4 font-display text-lg font-bold text-gray-800">Toutes les boutiques</h2>
        {others.length === 0 ? (
          <EmptyState icon={StoreIcon} title="Aucune boutique" />
        ) : (
          <div className="flex flex-col gap-3">
            {others.map((store) => (
              <Card key={store.id} className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-ink">{store.name}</p>
                  <p className="text-sm text-muted-foreground">{store.owner_email}</p>
                </div>
                <Badge variant={store.status === "active" ? "success" : "danger"}>{store.status}</Badge>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
