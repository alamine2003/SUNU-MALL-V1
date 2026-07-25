import { useParams } from "react-router-dom";
import { Mail, PackageSearch, Store as StoreIcon } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";
import { ProductCard } from "@/components/marketplace/ProductCard";
import { Badge } from "@/components/ui/Badge";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Spinner } from "@/components/ui/Spinner";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";

export default function BoutiqueDetailPage() {
  const { slug: storeId } = useParams<{ slug: string }>();

  const { data: store, loading: loadingStore } = useAsync(() => catalogApi.getStore(storeId!), [storeId]);
  const {
    data: products,
    loading: loadingProducts,
    error: productsError,
    refetch: refetchProducts,
  } = useAsync(() => catalogApi.listProducts({ store: storeId }), [storeId]);

  if (loadingStore)
    return (
      <div className="mx-auto max-w-7xl px-4 py-6">
        <Spinner label="Chargement de la boutique…" />
      </div>
    );
  if (!store)
    return (
      <div className="mx-auto max-w-7xl px-4 py-8">
        <EmptyState icon={StoreIcon} title="Boutique introuvable" description="Cette boutique n'existe pas ou a été retirée." />
      </div>
    );

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-8">
      <Breadcrumbs items={[{ label: "Boutiques", to: "/boutiques" }, { label: store.name }]} />

      <div className="navy-panel flex items-center gap-4 rounded-2xl p-6 shadow-navy-glow">
        <span className="grid h-14 w-14 shrink-0 place-items-center rounded-xl bg-white/10 text-lg font-bold">
          {store.name.slice(0, 2).toUpperCase()}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="font-display text-2xl font-bold">{store.name}</h1>
            {store.status !== "active" && (
              <Badge variant={store.status === "suspended" ? "danger" : "warning"}>
                {store.status === "suspended" ? "Suspendue" : "En attente"}
              </Badge>
            )}
          </div>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-white/70">
            <Mail className="h-3.5 w-3.5" /> {store.owner_email}
          </p>
        </div>
      </div>

      <div>
        <h2 className="mb-4 font-display text-lg font-bold text-gray-800">Produits</h2>
        {loadingProducts ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-40 w-full" />
            ))}
          </div>
        ) : productsError ? (
          <ErrorState onRetry={refetchProducts} />
        ) : products?.length === 0 ? (
          <EmptyState icon={PackageSearch} title="Aucun produit dans cette boutique" description="Cette boutique n'a pas encore publié de produit." />
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {products?.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
