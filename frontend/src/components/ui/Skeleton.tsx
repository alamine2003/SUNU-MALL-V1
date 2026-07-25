import { cn } from "@/lib/utils";

type Variant = "rect" | "text" | "circle";

export function Skeleton({ className, variant = "rect" }: { className?: string; variant?: Variant }) {
  return (
    <div
      className={cn(
        "skeleton",
        variant === "text" && "h-4 w-full rounded-md",
        variant === "circle" && "aspect-square rounded-full",
        variant === "rect" && "h-4 w-full",
        className,
      )}
    />
  );
}
