import { AlertTriangle } from "lucide-react";
import { Button } from "./Button";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
  fullPage?: boolean;
}

export function ErrorState({
  message = "Impossible de contacter le serveur. Vérifiez que le backend est démarré.",
  onRetry,
  fullPage,
}: ErrorStateProps) {
  if (fullPage) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-danger/20 bg-red-50/60 px-6 py-16 text-center">
        <div className="grid h-14 w-14 place-items-center rounded-full bg-red-100">
          <AlertTriangle className="h-7 w-7 text-danger" />
        </div>
        <p className="max-w-sm text-sm font-medium text-danger">{message}</p>
        {onRetry && (
          <Button variant="secondary" size="sm" onClick={onRetry}>
            Réessayer
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 rounded-lg border border-danger/30 bg-red-50 px-4 py-3 text-sm text-danger">
      <AlertTriangle className="h-4 w-4 shrink-0" />
      <span className="flex-1">{message}</span>
      {onRetry && (
        <button onClick={onRetry} className="focus-ring shrink-0 rounded-md font-bold underline-offset-2 hover:underline">
          Réessayer
        </button>
      )}
    </div>
  );
}
