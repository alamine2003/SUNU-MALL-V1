import { useState } from "react";
import { cn } from "@/lib/utils";

export interface TrendPoint {
  label: string;
  value: number;
}

interface TrendChartProps {
  data: TrendPoint[];
  valueFormatter?: (value: number) => string;
  className?: string;
}

/**
 * Mini graphique en barres, une seule série (magnitude dans le temps) :
 * une teinte séquentielle unique (orange de marque), pas de légende
 * nécessaire pour une série unique, extrémité arrondie côté valeur,
 * base carrée ancrée à la ligne de référence, infobulle au survol.
 */
export function TrendChart({ data, valueFormatter = (v) => String(v), className }: TrendChartProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className={cn("relative", className)}>
      <div className="flex h-40 items-end gap-1 border-b border-border">
        {data.map((d, i) => {
          const heightPct = Math.max((d.value / max) * 100, d.value > 0 ? 2 : 0);
          const isHovered = hoverIndex === i;
          return (
            <div
              key={`${d.label}-${i}`}
              className="group relative flex h-full flex-1 items-end"
              onMouseEnter={() => setHoverIndex(i)}
              onMouseLeave={() => setHoverIndex(null)}
            >
              {isHovered && (
                <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1.5 -translate-x-1/2 whitespace-nowrap rounded-md bg-navy px-2 py-1 text-center shadow-lg">
                  <p className="text-[11px] font-bold text-white">{valueFormatter(d.value)}</p>
                  <p className="text-[10px] text-white/70">{d.label}</p>
                </div>
              )}
              <div
                className={cn("w-full rounded-t-[4px] transition-colors", isHovered ? "bg-orange-dark" : "bg-orange/80")}
                style={{ height: `${heightPct}%` }}
              />
            </div>
          );
        })}
      </div>
      <div className="mt-1.5 flex justify-between text-[10px] text-muted-foreground">
        <span>{data[0]?.label}</span>
        <span>{data[data.length - 1]?.label}</span>
      </div>
    </div>
  );
}
