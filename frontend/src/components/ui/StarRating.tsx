import { Star } from "lucide-react";
import { cn } from "@/lib/utils";

interface StarRatingProps {
  value: number;
  onChange?: (value: number) => void;
  size?: "sm" | "md";
  className?: string;
}

/** Étoiles en lecture seule si `onChange` est omis, interactives sinon (formulaire d'avis). */
export function StarRating({ value, onChange, size = "md", className }: StarRatingProps) {
  const starSize = size === "sm" ? "h-3.5 w-3.5" : "h-5 w-5";
  return (
    <div className={cn("flex items-center gap-0.5", className)}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          disabled={!onChange}
          onClick={() => onChange?.(n)}
          aria-label={`${n} étoile${n > 1 ? "s" : ""}`}
          className={cn("focus-ring rounded", onChange && "cursor-pointer")}
        >
          <Star className={cn(starSize, n <= Math.round(value) ? "fill-orange text-orange" : "text-border")} />
        </button>
      ))}
    </div>
  );
}
