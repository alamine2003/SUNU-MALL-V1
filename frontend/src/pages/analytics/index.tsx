import { useMemo } from "react";
import { BarChart3, Package, TrendingUp, Wallet } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as ordersApi from "@/api/orders";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { TrendChart } from "@/components/ui/TrendChart";
import { formatPrice } from "@/lib/utils";

function lastNDays(n: number) {
  const days: { key: string; label: string }[] = [];
  const now = new Date();
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(now.getDate() - i);
    days.push({ key: d.toISOString().slice(0, 10), label: d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" }) });
  }
  return days;
}

export default function AnalyticsPage() {
  const { data: orders, loading } = useAsync(() => ordersApi.listOrders(), []);

  const stats = useMemo(() => {
    if (!orders) return null;
    const revenue = orders.reduce((sum, o) => sum + parseFloat(o.total_amount), 0);
    const productCounts = new Map<string, number>();
    for (const order of orders) {
      for (const item of order.items) {
        productCounts.set(item.product_name, (productCounts.get(item.product_name) ?? 0) + item.quantity);
      }
    }
    const topProducts = Array.from(productCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);

    const days = lastNDays(14).map((d) => ({ ...d, value: 0 }));
    const byKey = new Map(days.map((d) => [d.key, d]));
    for (const order of orders) {
      const bucket = byKey.get(order.created_at.slice(0, 10));
      if (bucket) bucket.value += parseFloat(order.total_amount);
    }

    return { revenue, orderCount: orders.length, topProducts, revenueByDay: days };
  }, [orders]);

  if (loading) return <Spinner label="Chargement des statistiques…" />;
  if (!stats) return null;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="flex items-center gap-2 font-display text-2xl font-bold text-gray-900">
        <BarChart3 className="h-6 w-6 text-orange" /> Analytics
      </h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-accent text-orange">
            <Wallet className="h-5 w-5" />
          </span>
          <div>
            <p className="text-xs text-muted-foreground">Chiffre d'affaires total</p>
            <p className="text-lg font-semibold text-ink">{formatPrice(stats.revenue)}</p>
          </div>
        </Card>
        <Card className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-accent text-orange">
            <Package className="h-5 w-5" />
          </span>
          <div>
            <p className="text-xs text-muted-foreground">Commandes traitées</p>
            <p className="text-lg font-semibold text-ink">{stats.orderCount}</p>
          </div>
        </Card>
      </div>

      <Card>
        <h2 className="mb-4 flex items-center gap-2 font-semibold text-ink">
          <Wallet className="h-4 w-4 text-orange" /> Chiffre d'affaires (14 derniers jours)
        </h2>
        {stats.revenue === 0 ? (
          <EmptyState icon={Wallet} title="Pas encore de ventes" description="L'évolution de votre chiffre d'affaires apparaîtra ici." />
        ) : (
          <TrendChart data={stats.revenueByDay} valueFormatter={formatPrice} />
        )}
      </Card>

      <Card>
        <h2 className="mb-4 flex items-center gap-2 font-semibold text-ink">
          <TrendingUp className="h-4 w-4 text-orange" /> Produits les plus vendus
        </h2>
        {stats.topProducts.length === 0 ? (
          <EmptyState icon={TrendingUp} title="Pas encore de ventes" description="Les produits les plus vendus apparaîtront ici." />
        ) : (
          <ul className="flex flex-col gap-2">
            {stats.topProducts.map(([name, qty]) => (
              <li key={name} className="flex items-center justify-between border-t border-border pt-2 text-sm">
                <span>{name}</span>
                <span className="font-semibold text-ink">{qty} vendus</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
