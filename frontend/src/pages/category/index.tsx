import { Link } from "react-router-dom";
import { Package, Shirt, Smartphone, Home as HomeIcon, Sparkles, Utensils, Baby, Dumbbell, LayoutGrid, type LucideIcon } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";

const ICONS: LucideIcon[] = [Shirt, Smartphone, HomeIcon, Utensils, Sparkles, Baby, Dumbbell, Package];

const GRADIENTS = [
  "from-orange to-orange-dark",
  "from-navy to-navy-2",
  "from-pink-500 to-rose-600",
  "from-blue-600 to-blue-800",
  "from-emerald-500 to-emerald-700",
  "from-purple-500 to-purple-700",
];

export default function CategoryIndexPage() {
  const { data: categories, loading, error, refetch } = useAsync(() => catalogApi.listCategories(), []);
  const topLevel = categories?.filter((c) => !c.parent) ?? [];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="mb-6 font-display text-2xl font-bold text-gray-900">Toutes les catégories</h1>
      {loading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="aspect-[4/3] w-full rounded-2xl" />
          ))}
        </div>
      ) : error ? (
        <ErrorState fullPage onRetry={refetch} />
      ) : topLevel.length === 0 ? (
        <EmptyState icon={LayoutGrid} title="Aucune catégorie pour le moment" description="Les catégories apparaîtront ici dès qu'elles seront configurées." />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
          {topLevel.map((category, i) => {
            const Icon = ICONS[i % ICONS.length];
            const gradient = GRADIENTS[i % GRADIENTS.length];
            return (
              <Link
                key={category.id}
                to={`/category/${category.id}`}
                className={`group relative flex aspect-[4/3] items-end overflow-hidden rounded-2xl border border-gray-100 p-3 shadow-sm transition-transform duration-300 hover:-translate-y-1 hover:shadow-lg ${
                  category.image_url ? "bg-navy" : `bg-gradient-to-br ${gradient}`
                }`}
              >
                {category.image_url && (
                  <>
                    <img
                      src={category.image_url}
                      alt=""
                      className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />
                  </>
                )}
                <span className="absolute left-3 top-3 grid h-9 w-9 place-items-center rounded-full bg-white/95 text-orange shadow transition-transform duration-300 group-hover:scale-110">
                  <Icon className="h-4 w-4" />
                </span>
                <p className="relative font-display font-bold leading-tight text-white">{category.name}</p>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
