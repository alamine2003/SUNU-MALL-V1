import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronRight, CreditCard, RotateCcw } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as paymentsApi from "@/api/payments";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination } from "@/components/ui/Pagination";
import { formatDate, formatPrice } from "@/lib/utils";

const PAGE_SIZE = 20;

const STATUS_VARIANT: Record<string, "default" | "success" | "warning" | "danger"> = {
  success: "success",
  pending: "warning",
  failed: "danger",
  refunded: "default",
};

const METHOD_LABEL: Record<string, string> = {
  wave: "Wave",
  orange_money: "Orange Money",
  card: "Carte bancaire",
};

function RefundsSection() {
  const [page, setPage] = useState(1);
  const { data: result, loading, error, refetch } = useAsync(() => paymentsApi.listRefunds({ page }), [page]);
  const [processingId, setProcessingId] = useState<number | null>(null);

  const refunds = result?.results ?? [];
  const totalPages = result ? Math.max(1, Math.ceil(result.count / PAGE_SIZE)) : 1;

  async function handleProcess(id: number) {
    if (!confirm("Confirmer que l'argent a bien été renvoyé au client ?")) return;
    setProcessingId(id);
    try {
      await paymentsApi.processRefund(id);
      refetch();
    } finally {
      setProcessingId(null);
    }
  }

  if (loading) return <Spinner label="Chargement des remboursements…" />;
  if (error) return <ErrorState onRetry={refetch} />;
  if (refunds.length === 0) return null;

  return (
    <div className="mb-8">
      <h2 className="mb-4 flex items-center gap-2 font-display text-lg font-bold text-gray-900">
        <RotateCcw className="h-5 w-5 text-orange" /> Remboursements
      </h2>
      <div className="flex flex-col gap-3">
        {refunds.map((refund) => (
          <Card key={refund.id} className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-ink">
                {refund.store_name} — Commande n°{refund.order_id.slice(0, 8)}
              </p>
              <p className="text-xs text-muted-foreground">
                {refund.customer_email} · {refund.reason} · {formatDate(refund.created_at)}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={refund.status === "completed" ? "success" : "warning"}>
                {refund.status === "completed" ? "Remboursé" : "En attente"}
              </Badge>
              <p className="font-bold text-ink">{formatPrice(refund.amount)}</p>
              {refund.status !== "completed" && (
                <Button size="sm" loading={processingId === refund.id} onClick={() => handleProcess(refund.id)}>
                  Marquer remboursé
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} className="mt-4" />
    </div>
  );
}

export default function AdminPaymentsPage() {
  const [page, setPage] = useState(1);
  const { data: result, loading, error, refetch } = useAsync(() => paymentsApi.listPayments({ page }), [page]);

  const payments = result?.results ?? [];
  const totalPages = result ? Math.max(1, Math.ceil(result.count / PAGE_SIZE)) : 1;

  return (
    <div>
      <h1 className="mb-6 flex items-center gap-2 font-display text-2xl font-bold text-gray-900">
        <CreditCard className="h-6 w-6 text-orange" /> Paiements
      </h1>

      <RefundsSection />

      {loading ? (
        <Spinner label="Chargement des paiements…" />
      ) : error ? (
        <ErrorState fullPage onRetry={refetch} />
      ) : payments.length === 0 ? (
        <EmptyState icon={CreditCard} title="Aucun paiement pour le moment" />
      ) : (
        <>
          <div className="flex flex-col gap-3">
            {payments.map((payment) => {
              const label = payment.order
                ? `Commande n°${payment.order.slice(0, 8)}`
                : `Abonnement n°${(payment.subscription ?? "").slice(0, 8)}`;
              const content = (
                <Card variant="interactive" className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-ink">{METHOD_LABEL[payment.method] ?? payment.method}</p>
                    <p className="text-xs text-muted-foreground">
                      {label} — {formatDate(payment.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={STATUS_VARIANT[payment.status] ?? "default"}>{payment.status}</Badge>
                    <p className="font-bold text-ink">{formatPrice(payment.amount)}</p>
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                  </div>
                </Card>
              );
              return payment.order ? (
                <Link key={payment.id} to={`/admin-order-detail?order=${payment.order}`}>
                  {content}
                </Link>
              ) : (
                <div key={payment.id}>{content}</div>
              );
            })}
          </div>
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} className="mt-6" />
        </>
      )}
    </div>
  );
}
