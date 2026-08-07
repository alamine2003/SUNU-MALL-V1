import { cn } from "@/lib/utils";

interface DonutChartProps {
  /** Proportion (0-100) représentée par le segment orange. */
  percentage: number;
  label: string;
  remainderLabel: string;
  className?: string;
}

const RADIUS = 42;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/**
 * Anneau à un seul segment (part-à-tout, 2 catégories fixes) : teinte
 * unique de marque pour la part mise en avant, gris neutre pour le
 * reste — jamais de dégradé arc-en-ciel pour une proportion binaire.
 * Légende toujours affichée (2 séries), valeur en label direct au centre.
 */
export function DonutChart({ percentage, label, remainderLabel, className }: DonutChartProps) {
  const clamped = Math.max(0, Math.min(100, percentage));
  const dash = (clamped / 100) * CIRCUMFERENCE;

  return (
    <div className={cn("flex flex-col items-center gap-4", className)}>
      <div className="relative grid h-32 w-32 place-items-center">
        <svg width="128" height="128" viewBox="0 0 100 100" className="-rotate-90">
          <circle cx="50" cy="50" r={RADIUS} fill="none" stroke="#E5E7EB" strokeWidth="10" />
          {clamped > 0 && (
            <circle
              cx="50"
              cy="50"
              r={RADIUS}
              fill="none"
              className="stroke-orange transition-[stroke-dasharray] duration-500"
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={`${dash} ${CIRCUMFERENCE - dash}`}
            />
          )}
        </svg>
        <span className="absolute font-display text-2xl font-bold text-navy">{clamped.toFixed(0)}%</span>
      </div>
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-orange" /> {label}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-border" /> {remainderLabel}
        </span>
      </div>
    </div>
  );
}
