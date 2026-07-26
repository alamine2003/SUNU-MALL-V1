import { useEffect, useMemo, useState } from "react";
import { BarChart3, Package, TrendingUp, Wallet } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";
import * as analyticsApi from "@/api/analytics";
import { Card } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { TrendChart } from "@/components/ui/TrendChart";
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

  const loading = loadingStats || loadingTop;

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
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Card className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-accent text-orange">
                <Wallet className="h-5 w-5" />
              </span>
              <div>
                <p className="text-xs text-muted-foreground">Chiffre d'affaires (30 derniers jours)</p>
                <p className="text-lg font-semibold text-ink">{formatPrice(stats.revenue)}</p>
              </div>
            </Card>
            <Card className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-accent text-orange">
                <Package className="h-5 w-5" />
              </span>
              <div>
                <p className="text-xs text-muted-foreground">Commandes (30 derniers jours)</p>
                <p className="text-lg font-semibold text-ink">{stats.orderCount}</p>
              </div>
            </Card>
          </div>

          <Card>
            <h2 className="mb-4 flex items-center gap-2 font-semibold text-ink">
              <Wallet className="h-4 w-4 text-orange" /> Chiffre d'affaires ({TREND_DAYS} derniers jours)
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
