import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { ProductCard } from "@/components/marketplace/ProductCard";
import { Skeleton } from "@/components/ui/Skeleton";
import type { Product } from "@/types";

interface ProductRailProps {
  title: string;
  viewAllHref?: string;
  products?: Product[] | null;
  loading?: boolean;
  sponsored?: boolean;
  limit?: number;
}

/**
 * Rangée de produits réutilisable (Nouveautés, Meilleures ventes, Sponsorisé,
 * par catégorie…). Se masque elle-même si aucune donnée réelle à afficher —
 * jamais de section vide avec juste un titre.
 */
export function ProductRail({ title, viewAllHref, products, loading, sponsored, limit = 6 }: ProductRailProps) {
  if (!loading && (!products || products.length === 0)) return null;

  return (
    <section className="mx-auto max-w-7xl px-4 py-6">
      <div className="mb-5 flex items-center justify-between">
        <h2 className="font-display text-xl font-bold text-gray-800">{title}</h2>
        {viewAllHref && (
          <Link to={viewAllHref} className="flex items-center gap-1 text-sm font-semibold text-orange transition-all hover:gap-2">
            Voir tout <ChevronRight className="h-4 w-4" />
          </Link>
        )}
      </div>
      {loading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {Array.from({ length: limit }).map((_, i) => (
            <Skeleton key={i} className="aspect-square w-full" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {products?.slice(0, limit).map((product) => (
            <ProductCard key={product.id} product={product} sponsored={sponsored} />
          ))}
        </div>
      )}
    </section>
  );
}
