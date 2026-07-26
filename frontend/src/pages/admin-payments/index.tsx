import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronRight, CreditCard } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as paymentsApi from "@/api/payments";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
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

      {loading ? (
        <Spinner label="Chargement des paiements…" />
      ) : error ? (
        <ErrorState fullPage onRetry={refetch} />
      ) : payments.length === 0 ? (
        <EmptyState icon={CreditCard} title="Aucun paiement pour le moment" />
      ) : (
        <>
          <div className="flex flex-col gap-3">
            {payments.map((payment) => (
              <Link key={payment.id} to={`/admin-order-detail?order=${payment.order}`}>
                <Card variant="interactive" className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-ink">{METHOD_LABEL[payment.method] ?? payment.method}</p>
                    <p className="text-xs text-muted-foreground">
                      Commande n°{payment.order.slice(0, 8)} — {formatDate(payment.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={STATUS_VARIANT[payment.status] ?? "default"}>{payment.status}</Badge>
                    <p className="font-bold text-ink">{formatPrice(payment.amount)}</p>
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                  </div>
                </Card>
              </Link>
            ))}
          </div>
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} className="mt-6" />
        </>
      )}
    </div>
  );
}
