import { Fragment } from "react";
import { Link } from "react-router-dom";
import { ChevronRight, Home } from "lucide-react";
import { cn } from "@/lib/utils";

export interface BreadcrumbItem {
  label: string;
  to?: string;
}

export function Breadcrumbs({ items, className }: { items: BreadcrumbItem[]; className?: string }) {
  return (
    <nav aria-label="Fil d'Ariane" className={cn("flex items-center gap-1.5 text-xs font-medium text-muted-foreground", className)}>
      <Link to="/home" className="flex items-center transition-colors hover:text-orange">
        <Home className="h-3.5 w-3.5" />
      </Link>
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        return (
          <Fragment key={item.label}>
            <ChevronRight className="h-3 w-3 shrink-0" />
            {item.to && !isLast ? (
              <Link to={item.to} className="truncate transition-colors hover:text-orange">
                {item.label}
              </Link>
            ) : (
              <span className={cn("truncate", isLast && "font-semibold text-gray-700")}>{item.label}</span>
            )}
          </Fragment>
        );
      })}
    </nav>
  );
}
