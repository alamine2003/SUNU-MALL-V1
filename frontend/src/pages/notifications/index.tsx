import { Bell } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as monetizationApi from "@/api/monetization";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";

export default function NotificationsPage() {
  const { data: notifications, loading, error, refetch } = useAsync(() => monetizationApi.listNotifications(), []);

  if (loading) return <Spinner label="Chargement des notifications…" />;

  return (
    <div>
      <h1 className="mb-6 flex items-center gap-2 font-display text-2xl font-bold text-gray-900">
        <Bell className="h-6 w-6 text-orange" /> Notifications
      </h1>
      {error ? (
        <ErrorState fullPage onRetry={refetch} />
      ) : notifications?.length === 0 ? (
        <EmptyState icon={Bell} title="Aucune notification pour le moment" description="Vous serez prévenu ici des mises à jour de vos commandes." />
      ) : (
        <div className="flex flex-col gap-3">
          {notifications?.map((n) => (
            <Card key={n.id} className="flex gap-3">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-accent text-orange">
                <Bell className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate font-semibold text-ink">{n.subject}</p>
                  <span className="shrink-0 text-xs text-muted-foreground">{formatDate(n.created_at)}</span>
                </div>
                <p className="mt-0.5 text-sm text-muted-foreground">{n.message}</p>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
