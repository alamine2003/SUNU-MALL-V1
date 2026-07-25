import { type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "success" | "warning" | "danger" | "sponsored";

const variantClasses: Record<Variant, string> = {
  default: "bg-muted text-muted-foreground",
  success: "bg-green-100 text-green-700",
  warning: "bg-amber-100 text-amber-700",
  danger: "bg-red-100 text-red-700",
  sponsored: "badge-sponsored",
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: Variant;
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        variant === "sponsored"
          ? "badge-sponsored"
          : cn("rounded-md px-2 py-0.5 text-xs font-semibold", variantClasses[variant]),
        className,
      )}
      {...props}
    />
  );
}
