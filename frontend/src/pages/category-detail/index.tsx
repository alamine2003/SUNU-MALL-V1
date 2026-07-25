import { useParams } from "react-router-dom";
import { PackageSearch } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";
import { ProductCard } from "@/components/marketplace/ProductCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";

export default function CategoryDetailPage() {
  const { slug: categoryId } = useParams<{ slug: string }>();

  const { data: category } = useAsync(async () => {
    const categories = await catalogApi.listCategories();
    return categories.find((c) => c.id === categoryId) ?? null;
  }, [categoryId]);

  const {
    data: products,
    loading,
    error,
    refetch,
  } = useAsync(() => catalogApi.listProducts({ category: categoryId }), [categoryId]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <Breadcrumbs items={[{ label: "Catégories", to: "/category" }, { label: category?.name ?? "Catégorie" }]} className="mb-3" />
      <h1 className="mb-6 font-display text-2xl font-bold text-gray-900">{category?.name ?? "Catégorie"}</h1>
      {loading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      ) : error ? (
        <ErrorState fullPage onRetry={refetch} />
      ) : products?.length === 0 ? (
        <EmptyState icon={PackageSearch} title="Aucun produit dans cette catégorie" description="Revenez plus tard, de nouveaux produits arrivent régulièrement." />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {products?.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </div>
  );
}
