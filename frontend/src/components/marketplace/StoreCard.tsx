import { Link } from "react-router-dom";
import { ArrowRight, Store as StoreIcon } from "lucide-react";
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

export function StoreCard({ store, compact }: { store: Store; compact?: boolean }) {
  const initials = store.name.slice(0, 2).toUpperCase();

  return (
    <Link
      to={`/boutiques/${store.id}`}
      className={cn(
        "card-interactive group surface-card flex shrink-0 flex-col overflow-hidden p-0",
        compact ? "w-40" : "w-full",
      )}
    >
      <div className={cn("relative grid h-20 place-items-center", bannerFor(store.id))}>
        {store.status !== "active" && (
          <Badge variant={store.status === "suspended" ? "danger" : "warning"} className="absolute left-2 top-2">
            {store.status === "suspended" ? "Suspendue" : "En attente"}
          </Badge>
        )}
        <span className="grid h-11 w-11 place-items-center rounded-full border border-white/20 bg-white/15 text-sm font-bold text-white backdrop-blur-sm">
          {initials || <StoreIcon className="h-5 w-5" />}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-0.5 p-3.5">
        <p className="truncate font-display text-sm font-bold text-gray-800">{store.name}</p>
        <p className="mt-0.5 flex items-center gap-1 text-xs font-semibold text-orange transition-all group-hover:gap-1.5">
          Visiter la boutique <ArrowRight className="h-3 w-3" />
        </p>
      </div>
    </Link>
  );
}
