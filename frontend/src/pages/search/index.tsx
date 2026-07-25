import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search as SearchIcon } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";
import { ProductCard } from "@/components/marketplace/ProductCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { Input } from "@/components/ui/Input";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination } from "@/components/ui/Pagination";

const PAGE_SIZE = 20;

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q") ?? "";
  const [page, setPage] = useState(1);

  const {
    data: result,
    loading,
    error,
    refetch,
  } = useAsync(() => catalogApi.searchProducts({ search: query || undefined, page }), [query, page]);

  const products = result?.results ?? [];
  const totalPages = result ? Math.max(1, Math.ceil(result.count / PAGE_SIZE)) : 1;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-8">
      <div>
        <h1 className="mb-4 flex items-center gap-2 font-display text-2xl font-bold text-gray-900">
          <SearchIcon className="h-6 w-6 text-orange" />
          Résultats de recherche
        </h1>
        <Input
          icon={SearchIcon}
          defaultValue={query}
          placeholder="Rechercher un produit…"
          onChange={(e) => {
            setPage(1);
            setSearchParams(e.target.value ? { q: e.target.value } : {});
          }}
        />
      </div>

      {loading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      ) : error ? (
        <ErrorState fullPage onRetry={refetch} />
      ) : products.length > 0 ? (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} className="mt-2" />
        </>
      ) : (
        <EmptyState
          icon={SearchIcon}
          title={query ? `Aucun résultat pour « ${query} »` : "Aucun produit pour le moment"}
          description="Essayez un autre mot-clé ou parcourez nos catégories."
        />
      )}
    </div>
  );
}
