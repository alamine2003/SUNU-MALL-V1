import { useState } from "react";
import { CheckCircle2, Store as StoreIcon } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination } from "@/components/ui/Pagination";

const PAGE_SIZE = 20;

export default function AdminShopsPage() {
  const [pendingPage, setPendingPage] = useState(1);
  const [allPage, setAllPage] = useState(1);
  const [busy, setBusy] = useState<string | null>(null);

  const {
    data: pendingResult,
    loading: loadingPending,
    error: pendingError,
    refetch: refetchPending,
  } = useAsync(() => catalogApi.listStoresPaginated({ status: "inactive", page: pendingPage }), [pendingPage]);
  const {
    data: allResult,
    loading: loadingAll,
    error: allError,
    refetch: refetchAll,
  } = useAsync(() => catalogApi.listStoresPaginated({ page: allPage }), [allPage]);

  const pending = pendingResult?.results ?? [];
  const pendingTotalPages = pendingResult ? Math.max(1, Math.ceil(pendingResult.count / PAGE_SIZE)) : 1;
  const all = allResult?.results ?? [];
  const allTotalPages = allResult ? Math.max(1, Math.ceil(allResult.count / PAGE_SIZE)) : 1;

  function refetchBoth() {
    refetchPending();
    refetchAll();
  }

  async function approve(id: string) {
    setBusy(id);
    try {
      await catalogApi.approveStore(id);
      refetchBoth();
    } finally {
      setBusy(null);
    }
  }

  async function reject(id: string) {
    const reason = prompt("Raison du rejet (optionnel)") ?? undefined;
    setBusy(id);
    try {
      await catalogApi.rejectStore(id, reason);
      refetchBoth();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="mb-4 flex items-center gap-2 font-display text-2xl font-bold text-gray-900">
          <StoreIcon className="h-6 w-6 text-orange" /> Validation des boutiques
        </h1>
        {loadingPending ? (
          <Spinner label="Chargement…" />
        ) : pendingError ? (
          <ErrorState onRetry={refetchPending} />
        ) : pending.length === 0 ? (
          <EmptyState icon={CheckCircle2} title="Aucune demande en attente" description="Toutes les boutiques ont été traitées." />
        ) : (
          <>
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
            <Pagination page={pendingPage} totalPages={pendingTotalPages} onPageChange={setPendingPage} className="mt-4" />
          </>
        )}
      </div>

      <div>
        <h2 className="mb-4 font-display text-lg font-bold text-gray-800">Toutes les boutiques</h2>
        {loadingAll ? (
          <Spinner label="Chargement…" />
        ) : allError ? (
          <ErrorState onRetry={refetchAll} />
        ) : all.length === 0 ? (
          <EmptyState icon={StoreIcon} title="Aucune boutique" />
        ) : (
          <>
            <div className="flex flex-col gap-3">
              {all.map((store) => (
                <Card key={store.id} className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-ink">{store.name}</p>
                    <p className="text-sm text-muted-foreground">{store.owner_email}</p>
                  </div>
                  <Badge variant={store.status === "active" ? "success" : store.status === "suspended" ? "danger" : "warning"}>
                    {store.status}
                  </Badge>
                </Card>
              ))}
            </div>
            <Pagination page={allPage} totalPages={allTotalPages} onPageChange={setAllPage} className="mt-4" />
          </>
        )}
      </div>
    </div>
  );
}
