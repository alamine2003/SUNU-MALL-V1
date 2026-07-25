import { type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "success" | "warning" | "danger" | "sponsored";
type Size = "sm" | "md";

const variantClasses: Record<Variant, string> = {
  default: "bg-muted text-muted-foreground border border-border",
  success: "bg-green-50 text-green-700 border border-green-200",
  warning: "bg-amber-50 text-amber-700 border border-amber-200",
  danger: "bg-red-50 text-danger border border-red-200",
  sponsored: "badge-sponsored",
};

const sizeClasses: Record<Size, string> = {
  sm: "px-1.5 py-0.5 text-[10px]",
  md: "px-2 py-0.5 text-xs",
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: Variant;
  size?: Size;
}

export function Badge({ className, variant = "default", size = "md", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md font-bold tracking-wide",
        variant === "sponsored" ? "badge-sponsored" : variantClasses[variant],
        variant !== "sponsored" && sizeClasses[size],
        className,
      )}
      {...props}
    />
  );
}
