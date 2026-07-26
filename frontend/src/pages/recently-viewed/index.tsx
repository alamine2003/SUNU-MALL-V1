import { Link } from "react-router-dom";
import { History } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";
import { ProductCard } from "@/components/marketplace/ProductCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { useRecentlyViewedStore } from "@/store/recentlyViewedStore";
import type { Product } from "@/types";

export default function RecentlyViewedPage() {
  const recentlyViewedIds = useRecentlyViewedStore((s) => s.productIds);
  const { data: products, loading } = useAsync(async () => {
    const settled = await Promise.allSettled(recentlyViewedIds.map((id) => catalogApi.getProduct(id)));
    return settled
      .filter((r): r is PromiseFulfilledResult<Product> => r.status === "fulfilled")
      .map((r) => r.value);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recentlyViewedIds.join(",")]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="mb-6 flex items-center gap-2 font-display text-2xl font-bold text-gray-900">
        <History className="h-6 w-6 text-orange" /> Récemment consultés
      </h1>

      {loading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square w-full" />
          ))}
        </div>
      ) : products?.length ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={History}
          title="Aucun produit consulté récemment"
          description="Les produits que vous consultez apparaîtront ici pour vous permettre d'y revenir facilement."
          action={
            <Link to="/search">
              <Button>Découvrir des produits</Button>
            </Link>
          }
        />
      )}
    </div>
  );
}
