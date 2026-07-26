import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronRight, ClipboardList } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as ordersApi from "@/api/orders";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination } from "@/components/ui/Pagination";
import { formatDate, formatPrice } from "@/lib/utils";

const PAGE_SIZE = 20;

const STATUS_VARIANT: Record<string, "default" | "success" | "warning" | "danger"> = {
  delivered: "success",
  paid: "success",
  processing: "warning",
  shipped: "warning",
  pending: "default",
  cancelled: "danger",
};

export default function AdminOrdersPage() {
  const [page, setPage] = useState(1);
  const { data: result, loading, error, refetch } = useAsync(() => ordersApi.listOrdersPaginated({ page }), [page]);

  const orders = result?.results ?? [];
  const totalPages = result ? Math.max(1, Math.ceil(result.count / PAGE_SIZE)) : 1;

  return (
    <div>
      <h1 className="mb-6 flex items-center gap-2 font-display text-2xl font-bold text-gray-900">
        <ClipboardList className="h-6 w-6 text-orange" /> Commandes
      </h1>

      {loading ? (
        <Spinner label="Chargement des commandes…" />
      ) : error ? (
        <ErrorState fullPage onRetry={refetch} />
      ) : orders.length === 0 ? (
        <EmptyState icon={ClipboardList} title="Aucune commande pour le moment" />
      ) : (
        <>
          <div className="flex flex-col gap-3">
            {orders.map((order) => (
              <Link key={order.id} to={`/admin-order-detail?order=${order.id}`}>
                <Card variant="interactive" className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-ink">{order.store_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {order.customer_name} — {formatDate(order.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={STATUS_VARIANT[order.status] ?? "default"}>{order.status}</Badge>
                    <p className="font-bold text-ink">{formatPrice(order.total_amount)}</p>
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
