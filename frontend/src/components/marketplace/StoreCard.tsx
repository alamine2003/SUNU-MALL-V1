import { Link } from "react-router-dom";
import { ArrowRight, Star, Store as StoreIcon } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import type { Store } from "@/types";
import { cn } from "@/lib/utils";

const BANNER_GRADIENTS = [
  "bg-gradient-navy",
  "bg-gradient-orange",
  "bg-gradient-to-br from-navy via-navy-2 to-orange-dark",
  "bg-gradient-to-br from-orange-dark via-orange to-navy-2",
];

function bannerFor(id: string) {
  const hash = Array.from(id).reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  return BANNER_GRADIENTS[hash % BANNER_GRADIENTS.length];
}

interface StoreCardProps {
  store: Store;
  compact?: boolean;
  layout?: "grid" | "list";
}

export function StoreCard({ store, compact, layout = "grid" }: StoreCardProps) {
  const initials = store.name.slice(0, 2).toUpperCase();

  const ratingBlock = store.rating != null && (
    <p className="flex items-center gap-1 text-xs text-gray-600">
      <Star className="h-3.5 w-3.5 shrink-0 fill-orange text-orange" />
      <span className="font-semibold">{store.rating.toFixed(1)}</span>
      <span className="text-muted-foreground">({store.review_count} avis)</span>
    </p>
  );
  const categoriesBlock = store.category_names.length > 0 && (
    <p className="truncate text-xs text-muted-foreground">{store.category_names.join(" · ")}</p>
  );
  const statusBadge = store.status !== "active" && (
    <Badge variant={store.status === "suspended" ? "danger" : "warning"}>
      {store.status === "suspended" ? "Suspendue" : "En attente"}
    </Badge>
  );

  if (layout === "list") {
    return (
      <Link to={`/boutiques/${store.id}`} className="card-interactive group surface-card flex items-center gap-4 p-3.5">
        {store.logo_url ? (
          <img src={store.logo_url} alt={store.name} className="h-14 w-14 shrink-0 rounded-xl object-cover" />
        ) : (
          <span
            className={cn(
              "grid h-14 w-14 shrink-0 place-items-center rounded-xl text-sm font-bold text-white",
              bannerFor(store.id),
            )}
          >
            {initials || <StoreIcon className="h-5 w-5" />}
          </span>
        )}
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <div className="flex items-center gap-2">
            <p className="truncate font-display text-sm font-bold text-gray-800">{store.name}</p>
            {statusBadge}
          </div>
          {categoriesBlock}
          {ratingBlock}
        </div>
        <p className="flex shrink-0 items-center gap-1 text-xs font-semibold text-orange transition-all group-hover:gap-1.5">
          Visiter <ArrowRight className="h-3 w-3" />
        </p>
      </Link>
    );
  }

  return (
    <Link
      to={`/boutiques/${store.id}`}
      className={cn(
        "card-interactive group surface-card flex shrink-0 flex-col overflow-hidden p-0",
        compact ? "w-40" : "w-full",
      )}
    >
      <div
        className={cn("relative grid h-32 place-items-center bg-cover bg-center", !store.banner_url && bannerFor(store.id))}
        style={store.banner_url ? { backgroundImage: `url(${store.banner_url})` } : undefined}
      >
        {store.banner_url && <div className="absolute inset-0 bg-black/25" />}
        {statusBadge && <div className="absolute left-2 top-2">{statusBadge}</div>}
        {store.logo_url ? (
          <img
            src={store.logo_url}
            alt={store.name}
            className="h-14 w-14 rounded-full border border-white/20 object-cover shadow-sm"
          />
        ) : (
          <span className="grid h-14 w-14 place-items-center rounded-full border border-white/20 bg-white/15 text-base font-bold text-white backdrop-blur-sm">
            {initials || <StoreIcon className="h-6 w-6" />}
          </span>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1 p-3.5">
        <p className="truncate font-display text-sm font-bold text-gray-800">{store.name}</p>
        {categoriesBlock}
        {ratingBlock}
        <p className="mt-auto flex items-center gap-1 pt-1 text-xs font-semibold text-orange transition-all group-hover:gap-1.5">
          Visiter la boutique <ArrowRight className="h-3 w-3" />
        </p>
      </div>
    </Link>
  );
}
