import { useState } from "react";
import { Search, Store as StoreIcon } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";
import { StoreCard } from "@/components/marketplace/StoreCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Pagination } from "@/components/ui/Pagination";

const PAGE_SIZE = 20;

export default function BoutiquesPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data: result, loading, error, refetch } = useAsync(
    () => catalogApi.listStoresPaginated({ search: search || undefined, page }),
    [search, page],
  );

  const stores = result?.results ?? [];
  const totalPages = result ? Math.max(1, Math.ceil(result.count / PAGE_SIZE)) : 1;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-8">
      <div>
        <h1 className="mb-4 flex items-center gap-2 font-display text-2xl font-bold text-gray-900">
          <StoreIcon className="h-6 w-6 text-orange" />
          Boutiques
        </h1>
        <Input
          icon={Search}
          placeholder="Rechercher une boutique…"
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
          className="max-w-md"
        />
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full rounded-lg" />
          ))}
        </div>
      ) : error ? (
        <ErrorState fullPage onRetry={refetch} />
      ) : stores.length > 0 ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {stores.map((store) => (
              <StoreCard key={store.id} store={store} />
            ))}
          </div>
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} className="mt-2" />
        </>
      ) : (
        <EmptyState
          icon={StoreIcon}
          title={search ? `Aucune boutique pour « ${search} »` : "Aucune boutique active pour le moment"}
          description="Les nouvelles boutiques validées apparaîtront ici."
        />
      )}
    </div>
  );
}
