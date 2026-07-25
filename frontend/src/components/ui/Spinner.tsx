import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function Spinner({ className, label }: { className?: string; label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-10 text-muted-foreground">
      <Loader2 className={cn("h-6 w-6 animate-spin text-orange", className)} />
      {label && <p className="text-sm">{label}</p>}
    </div>
  );
}
