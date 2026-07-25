import { Link } from "react-router-dom";
import { ChevronRight, PackageSearch } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as ordersApi from "@/api/orders";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { formatDate, formatPrice } from "@/lib/utils";

const STATUS_VARIANT: Record<string, "default" | "success" | "warning" | "danger"> = {
  delivered: "success",
  paid: "success",
  processing: "warning",
  shipped: "warning",
  pending: "default",
  cancelled: "danger",
};

export default function OrdersPage() {
  const { data: orders, loading, error, refetch } = useAsync(() => ordersApi.listOrders(), []);

  if (loading) return <Spinner label="Chargement de vos commandes…" />;

  return (
    <div>
      <h1 className="mb-6 font-display text-2xl font-bold text-gray-900">Mes commandes</h1>
      {error ? (
        <ErrorState fullPage onRetry={refetch} />
      ) : orders?.length === 0 ? (
        <EmptyState
          icon={PackageSearch}
          title="Vous n'avez pas encore passé de commande"
          description="Vos commandes apparaîtront ici une fois validées."
          action={
            <Link to="/search">
              <Button>Découvrir des produits</Button>
            </Link>
          }
        />
      ) : (
        <div className="flex flex-col gap-3">
          {orders?.map((order) => (
            <Link key={order.id} to={`/tracking?order=${order.id}`}>
              <Card variant="interactive" className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-ink">{order.store_name}</p>
                  <p className="text-xs text-muted-foreground">{formatDate(order.created_at)}</p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={STATUS_VARIANT[order.status] ?? "default"}>{order.status}</Badge>
                  <p className="font-bold text-ink">{formatPrice(order.total_amount)}</p>
                  <ChevronRight className="h-5 w-5 shrink-0 text-muted-foreground" />
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
