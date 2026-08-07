import { useEffect, useMemo, useState } from "react";
import { BarChart3, Package, ShoppingBag, Star, TrendingUp, Truck, Wallet } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";
import * as analyticsApi from "@/api/analytics";
import { Card } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { TrendChart } from "@/components/ui/TrendChart";
import { DonutChart } from "@/components/ui/DonutChart";
import { formatPrice } from "@/lib/utils";

const TREND_DAYS = 14;

export default function AnalyticsPage() {
  const { data: own, loading: loadingStores } = useAsync(() => catalogApi.listMyStores(), []);
  const [storeId, setStoreId] = useState<string>("");

  useEffect(() => {
    if (!storeId && own && own.length > 0) setStoreId(own[0].id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [own?.length]);

  const { data: salesStats, loading: loadingStats } = useAsync(
    () => (storeId ? analyticsApi.listSalesStatistics(storeId) : Promise.resolve([])),
    [storeId],
  );
  const { data: topProducts, loading: loadingTop } = useAsync(
    () => (storeId ? catalogApi.listBestSellers({ store: storeId }) : Promise.resolve([])),
    [storeId],
  );
  const { data: summary, loading: loadingSummary } = useAsync(
    () => (storeId ? analyticsApi.getStoreSummary(storeId) : Promise.resolve(null)),
    [storeId],
  );

  const stats = useMemo(() => {
    const rows = salesStats ?? [];
    const revenue = rows.reduce((sum, r) => sum + parseFloat(r.total_sales), 0);
    const orderCount = rows.reduce((sum, r) => sum + r.total_orders, 0);
    // Les lignes sont triées -date (les plus récentes d'abord) ; on prend les
    // TREND_DAYS plus récentes puis on les remet dans l'ordre chronologique.
    const revenueByDay = rows
      .slice(0, TREND_DAYS)
      .slice()
      .reverse()
      .map((r) => ({
        label: new Date(r.date).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" }),
        value: parseFloat(r.total_sales),
      }));
    return { revenue, orderCount, revenueByDay };
  }, [salesStats]);

  if (loadingStores) return <Spinner label="Chargement…" />;
  if (!own || own.length === 0) {
    return <EmptyState icon={BarChart3} title="Aucune boutique" description="Créez d'abord votre boutique pour voir ses statistiques." />;
  }

  const loading = loadingStats || loadingTop || loadingSummary;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="flex items-center gap-2 font-display text-2xl font-bold text-gray-900">
          <BarChart3 className="h-6 w-6 text-orange" /> Analytics
        </h1>
        {own.length > 1 && (
          <div className="w-full max-w-xs sm:w-auto">
            <Select value={storeId} onChange={(e) => setStoreId(e.target.value)}>
              {own.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </Select>
          </div>
        )}
      </div>

      {loading ? (
        <Spinner label="Chargement des statistiques…" />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="flex flex-col justify-between rounded-2xl bg-gradient-navy p-5 text-white shadow-navy-glow lg:col-span-1">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/10">
                <Wallet className="h-5 w-5" />
              </span>
              <div className="mt-4">
                <p className="text-xs text-white/60">Chiffre d'affaires (30j)</p>
                <p className="font-display text-2xl font-bold">{formatPrice(summary?.revenue_30d ?? 0)}</p>
              </div>
            </div>
            <Card className="flex items-center gap-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent text-orange">
                <Package className="h-5 w-5" />
              </span>
              <div>
                <p className="text-xs text-muted-foreground">Commandes (30j)</p>
                <p className="text-lg font-semibold text-ink">{summary?.orders_30d ?? 0}</p>
              </div>
            </Card>
            <Card className="flex items-center gap-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent text-orange">
                <ShoppingBag className="h-5 w-5" />
              </span>
              <div>
                <p className="text-xs text-muted-foreground">Panier moyen</p>
                <p className="text-lg font-semibold text-ink">{formatPrice(summary?.avg_order_value_30d ?? 0)}</p>
              </div>
            </Card>
            <Card className="flex items-center gap-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent text-orange">
                <Star className="h-5 w-5" />
              </span>
              <div>
                <p className="text-xs text-muted-foreground">Note moyenne</p>
                <p className="text-lg font-semibold text-ink">
                  {summary?.avg_rating != null ? `${summary.avg_rating} / 5` : "—"}
                </p>
              </div>
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <h2 className="mb-4 flex items-center gap-2 font-semibold text-ink">
                <Wallet className="h-4 w-4 text-orange" /> Chiffre d'affaires ({TREND_DAYS} derniers jours)
              </h2>
              {stats.revenue === 0 ? (
                <EmptyState icon={Wallet} title="Pas encore de ventes" description="L'évolution de votre chiffre d'affaires apparaîtra ici." />
              ) : (
                <TrendChart data={stats.revenueByDay} valueFormatter={formatPrice} />
              )}
            </Card>

            <Card className="flex flex-col items-center justify-center">
              <h2 className="mb-4 flex w-full items-center gap-2 font-semibold text-ink">
                <Truck className="h-4 w-4 text-orange" /> Taux de livraison
              </h2>
              {!summary || summary.orders_30d === 0 ? (
                <EmptyState icon={Truck} title="Pas encore de commandes" description="Le taux de livraison apparaîtra ici." />
              ) : (
                <DonutChart percentage={summary.delivered_rate} label="Livrées" remainderLabel="En cours" />
              )}
            </Card>
          </div>

          <Card>
            <h2 className="mb-4 flex items-center gap-2 font-semibold text-ink">
              <TrendingUp className="h-4 w-4 text-orange" /> Produits les plus vendus
            </h2>
            {!topProducts || topProducts.length === 0 ? (
              <EmptyState icon={TrendingUp} title="Pas encore de ventes" description="Les produits les plus vendus apparaîtront ici." />
            ) : (
              <ul className="flex flex-col gap-2">
                {topProducts.map((product) => (
                  <li key={product.id} className="flex items-center justify-between border-t border-border pt-2 text-sm first:border-t-0 first:pt-0">
                    <span>{product.name}</span>
                    <span className="font-semibold text-ink">{product.sold_quantity ?? 0} vendus</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
