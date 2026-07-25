import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CheckCircle2, Heart, ImageOff, PackageX, ShoppingCart, TriangleAlert } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";
import * as shoppingApi from "@/api/shopping";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { EmptyState } from "@/components/ui/EmptyState";
import { QuantityStepper } from "@/components/marketplace/QuantityStepper";
import { useAuthStore } from "@/store/authStore";
import { useRecentlyViewedStore } from "@/store/recentlyViewedStore";
import { cn, formatPrice } from "@/lib/utils";

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const addRecentlyViewed = useRecentlyViewedStore((s) => s.addProduct);
  const [selectedVariant, setSelectedVariant] = useState<string | null>(null);
  const [activeImage, setActiveImage] = useState(0);
  const [quantity, setQuantity] = useState(1);
  const [adding, setAdding] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const { data: product, loading } = useAsync(() => catalogApi.getProduct(id!), [id]);

  useEffect(() => {
    if (product) addRecentlyViewed(product.id);
  }, [product, addRecentlyViewed]);

  if (loading)
    return (
      <div className="mx-auto max-w-7xl px-4 py-6">
        <Spinner label="Chargement du produit…" />
      </div>
    );
  if (!product)
    return (
      <div className="mx-auto max-w-7xl px-4 py-8">
        <EmptyState icon={PackageX} title="Produit introuvable" description="Ce produit n'existe pas ou a été retiré de la vente." />
      </div>
    );

  const variant = product.variants.find((v) => v.id === selectedVariant) ?? product.variants[0];
  const images = product.images;
  const image = images[activeImage]?.url ?? images[0]?.url;
  const isAvailable = variant?.is_available ?? false;

  async function handleAddToCart() {
    if (!user) {
      navigate(`/login?next=/product/${id}`);
      return;
    }
    if (!variant) return;
    setAdding(true);
    setFeedback(null);
    try {
      await shoppingApi.addCartItem(variant.id, quantity);
      setFeedback({ type: "success", text: "Ajouté au panier !" });
    } catch {
      setFeedback({ type: "error", text: "Impossible d'ajouter au panier." });
    } finally {
      setAdding(false);
    }
  }

  async function handleAddToWishlist() {
    if (!user) {
      navigate(`/login?next=/product/${id}`);
      return;
    }
    try {
      await shoppingApi.addWishlistItem(product!.id);
      setFeedback({ type: "success", text: "Ajouté à la wishlist !" });
    } catch {
      setFeedback({ type: "error", text: "Impossible d'ajouter à la wishlist." });
    }
  }

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-8">
      <Breadcrumbs items={[{ label: product.store_name }, { label: product.name }]} />

      <div className="grid gap-8 md:grid-cols-2">
        <div className="flex flex-col gap-3">
          <div className="relative grid aspect-square place-items-center overflow-hidden rounded-2xl bg-muted">
            {image ? (
              <img src={image} alt={product.name} className="h-full w-full object-cover" />
            ) : (
              <ImageOff className="h-12 w-12 text-muted-foreground" />
            )}
            {!isAvailable && variant && (
              <span className="absolute left-3 top-3 rounded-md bg-gray-700 px-2.5 py-1 text-xs font-bold text-white shadow">
                Rupture de stock
              </span>
            )}
          </div>
          {images.length > 1 && (
            <div className="flex gap-2">
              {images.map((img, i) => (
                <button
                  key={img.id}
                  onClick={() => setActiveImage(i)}
                  className={cn(
                    "focus-ring h-16 w-16 shrink-0 overflow-hidden rounded-lg border-2 bg-muted transition-colors",
                    i === activeImage ? "border-orange" : "border-transparent hover:border-border",
                  )}
                >
                  {img.url ? (
                    <img src={img.url} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <div className="grid h-full w-full place-items-center">
                      <ImageOff className="h-4 w-4 text-muted-foreground" />
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-4">
          <p className="text-sm font-semibold text-muted-foreground">{product.store_name}</p>
          <h1 className="font-display text-2xl font-extrabold leading-tight text-gray-900 md:text-3xl">{product.name}</h1>
          <p className="font-display text-3xl font-extrabold text-orange">{formatPrice(variant?.price ?? product.base_price)}</p>
          <p className="text-sm leading-relaxed text-ink/80">{product.description || "Aucune description fournie."}</p>

          {product.variants.length > 1 && (
            <div>
              <p className="mb-2 text-sm font-semibold text-ink">Variante</p>
              <div className="flex flex-wrap gap-2">
                {product.variants.map((v) => (
                  <button
                    key={v.id}
                    onClick={() => setSelectedVariant(v.id)}
                    className={cn(
                      "focus-ring rounded-lg border px-3 py-1.5 text-sm font-semibold transition-colors",
                      variant?.id === v.id ? "border-orange bg-accent text-orange" : "border-border text-ink hover:border-orange/50",
                    )}
                  >
                    {v.sku}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div>
            <p className="mb-2 text-sm font-semibold text-ink">Quantité</p>
            <QuantityStepper value={quantity} onChange={setQuantity} max={variant?.quantity ?? 99} disabled={!isAvailable} />
          </div>

          <div className="mt-2 flex gap-3">
            <Button onClick={handleAddToCart} loading={adding} disabled={!variant || !isAvailable} className="flex-1">
              <ShoppingCart className="h-4 w-4" />
              {isAvailable ? "Ajouter au panier" : "Indisponible"}
            </Button>
            <Button variant="secondary" onClick={handleAddToWishlist} aria-label="Ajouter à la wishlist">
              <Heart className="h-4 w-4" />
            </Button>
          </div>

          {feedback && (
            <div
              className={cn(
                "flex items-center gap-2 rounded-lg border px-3.5 py-2.5 text-sm font-medium",
                feedback.type === "success" ? "border-green-200 bg-green-50 text-green-700" : "border-danger/30 bg-red-50 text-danger",
              )}
            >
              {feedback.type === "success" ? <CheckCircle2 className="h-4 w-4 shrink-0" /> : <TriangleAlert className="h-4 w-4 shrink-0" />}
              {feedback.text}
            </div>
          )}
          {!variant && (
            <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-red-50 px-3.5 py-2.5 text-sm text-danger">
              <TriangleAlert className="h-4 w-4 shrink-0" />
              Ce produit n'a pas encore de variante disponible.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
