import { useEffect } from "react";
import { Radio } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as ordersApi from "@/api/orders";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDate, formatPrice } from "@/lib/utils";

const STATUS_VARIANT: Record<string, "default" | "success" | "warning" | "danger"> = {
  delivered: "success",
  paid: "success",
  processing: "warning",
  shipped: "warning",
  pending: "default",
  cancelled: "danger",
};

export default function LiveSalesPage() {
  const { data: orders, loading, refetch } = useAsync(() => ordersApi.listOrders(), []);

  useEffect(() => {
    const interval = setInterval(refetch, 15000);
    return () => clearInterval(interval);
  }, [refetch]);

  if (loading) return <Spinner label="Chargement des ventes…" />;

  const recent = [...(orders ?? [])].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  return (
    <div>
      <div className="relative mb-6 overflow-hidden rounded-2xl">
        <img src="/live-shopping.jpg" alt="Vendeur en direct présentant ses produits" className="h-40 w-full object-cover sm:h-52" />
        <div className="absolute inset-0 bg-gradient-to-r from-navy/85 via-navy/40 to-transparent" />
        <div className="absolute inset-0 flex flex-col justify-center px-6">
          <h1 className="flex items-center gap-2 font-display text-2xl font-bold text-white">
            <Radio className="h-5 w-5 animate-pulse-dot text-orange" /> Ventes en direct
          </h1>
          <p className="mt-1 max-w-sm text-sm text-white/70">Suivez vos commandes en temps réel pendant vos sessions de live shopping.</p>
        </div>
      </div>
      {recent.length === 0 ? (
        <EmptyState icon={Radio} title="Aucune vente pour le moment" description="Les nouvelles commandes apparaîtront ici en temps réel." />
      ) : (
        <div className="flex flex-col gap-3">
          {recent.map((order) => (
            <Card key={order.id} className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-ink">{order.store_name}</p>
                <p className="text-xs text-muted-foreground">{formatDate(order.created_at)}</p>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant={STATUS_VARIANT[order.status] ?? "default"}>{order.status}</Badge>
                <span className="font-bold text-ink">{formatPrice(order.total_amount)}</span>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
