import { Minus, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

interface QuantityStepperProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  disabled?: boolean;
  size?: "sm" | "md";
  className?: string;
}

export function QuantityStepper({ value, onChange, min = 1, max = 99, disabled, size = "md", className }: QuantityStepperProps) {
  const btnSize = size === "sm" ? "h-7 w-7" : "h-9 w-9";
  const textSize = size === "sm" ? "text-sm" : "text-base";

  return (
    <div className={cn("inline-flex items-center rounded-lg border border-border bg-white", disabled && "opacity-50", className)}>
      <button
        type="button"
        onClick={() => onChange(Math.max(min, value - 1))}
        disabled={disabled || value <= min}
        aria-label="Diminuer la quantité"
        className={cn(
          "focus-ring grid place-items-center rounded-l-lg text-gray-500 transition-colors hover:bg-muted hover:text-orange disabled:pointer-events-none disabled:opacity-40",
          btnSize,
        )}
      >
        <Minus className="h-3.5 w-3.5" />
      </button>
      <span className={cn("w-8 select-none text-center font-bold text-ink", textSize)}>{value}</span>
      <button
        type="button"
        onClick={() => onChange(Math.min(max, value + 1))}
        disabled={disabled || value >= max}
        aria-label="Augmenter la quantité"
        className={cn(
          "focus-ring grid place-items-center rounded-r-lg text-gray-500 transition-colors hover:bg-muted hover:text-orange disabled:pointer-events-none disabled:opacity-40",
          btnSize,
        )}
      >
        <Plus className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
