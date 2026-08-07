import { useState } from "react";
import { LayoutGrid, List, Search, Store as StoreIcon } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";
import { StoreCard } from "@/components/marketplace/StoreCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Pagination } from "@/components/ui/Pagination";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 20;
const RECENT_ORDERING = "-created_at";

const SORT_OPTIONS = [
  { value: "-rating", label: "Plus populaires" },
  { value: RECENT_ORDERING, label: "Plus récentes" },
  { value: "name", label: "Alphabétique" },
];

type Tab = "all" | "new";

export default function BoutiquesPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [tab, setTab] = useState<Tab>("all");
  const [sort, setSort] = useState(SORT_OPTIONS[0].value);
  const [layout, setLayout] = useState<"grid" | "list">("grid");
  const [categoryId, setCategoryId] = useState<number | null>(null);

  const { data: categories } = useAsync(() => catalogApi.listStoreCategoryCounts(), []);

  const { data: result, loading, error, refetch } = useAsync(
    () =>
      catalogApi.listStoresPaginated({
        search: search || undefined,
        page,
        productCategory: categoryId ?? undefined,
        ordering: tab === "new" ? RECENT_ORDERING : sort,
      }),
    [search, page, categoryId, sort, tab],
  );

  const stores = result?.results ?? [];
  const totalPages = result ? Math.max(1, Math.ceil(result.count / PAGE_SIZE)) : 1;

  function resetFilters() {
    setSearch("");
    setCategoryId(null);
    setTab("all");
    setSort(SORT_OPTIONS[0].value);
    setPage(1);
  }

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-8 lg:flex-row lg:items-start">
      <aside className="flex w-full shrink-0 flex-col gap-5 lg:w-64">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-sm font-bold text-ink">Filtres</h2>
          <button onClick={resetFilters} className="text-xs font-semibold text-orange hover:underline">
            Réinitialiser
          </button>
        </div>

        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Rechercher une boutique
          </p>
          <Input
            icon={Search}
            placeholder="Nom de la boutique…"
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
          />
        </div>

        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Catégories</p>
          <ul className="flex flex-col gap-1">
            <li>
              <button
                onClick={() => {
                  setCategoryId(null);
                  setPage(1);
                }}
                className={cn(
                  "flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent",
                  categoryId === null ? "font-semibold text-orange" : "text-ink",
                )}
              >
                <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", categoryId === null ? "bg-orange" : "bg-border")} />
                Toutes les catégories
              </button>
            </li>
            {categories?.map((c) => (
              <li key={c.id}>
                <button
                  onClick={() => {
                    setCategoryId(c.id);
                    setPage(1);
                  }}
                  className={cn(
                    "flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent",
                    categoryId === c.id ? "font-semibold text-orange" : "text-ink",
                  )}
                >
                  <span className="truncate">{c.name}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">{c.store_count}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col gap-5">
        <div>
          <h1 className="font-display text-2xl font-bold text-gray-900">Toutes les boutiques</h1>
          <p className="mt-1 text-sm text-muted-foreground">Découvrez nos boutiques partenaires</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {(
            [
              { key: "all", label: "Toutes les boutiques" },
              { key: "new", label: "Nouvelles boutiques" },
            ] as const
          ).map((t) => (
            <button
              key={t.key}
              onClick={() => {
                setTab(t.key);
                setPage(1);
              }}
              className={cn(
                "rounded-full border px-4 py-1.5 text-sm font-semibold transition-colors",
                tab === t.key
                  ? "border-orange bg-accent text-orange"
                  : "border-border text-muted-foreground hover:border-orange/40",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground">
            {result ? `${result.count} boutique${result.count > 1 ? "s" : ""} trouvée${result.count > 1 ? "s" : ""}` : ""}
          </p>
          <div className="flex items-center gap-2">
            <Select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              disabled={tab === "new"}
              className="w-44"
              aria-label="Trier par"
            >
              {SORT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
            <div className="flex items-center rounded-lg border border-border p-0.5">
              <button
                onClick={() => setLayout("grid")}
                aria-label="Vue grille"
                className={cn("rounded-md p-1.5", layout === "grid" ? "bg-orange text-white" : "text-muted-foreground")}
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
              <button
                onClick={() => setLayout("list")}
                aria-label="Vue liste"
                className={cn("rounded-md p-1.5", layout === "list" ? "bg-orange text-white" : "text-muted-foreground")}
              >
                <List className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        {loading ? (
          <div className={layout === "grid" ? "grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3" : "flex flex-col gap-3"}>
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-32 w-full rounded-lg" />
            ))}
          </div>
        ) : error ? (
          <ErrorState fullPage onRetry={refetch} />
        ) : stores.length > 0 ? (
          <>
            <div className={layout === "grid" ? "grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3" : "flex flex-col gap-3"}>
              {stores.map((store) => (
                <StoreCard key={store.id} store={store} layout={layout} />
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
    </div>
  );
}
