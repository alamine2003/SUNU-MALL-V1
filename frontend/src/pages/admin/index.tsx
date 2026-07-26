import { type ComponentType, useMemo } from "react";
import { ShieldCheck, Store as StoreIcon, Users } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as usersApi from "@/api/users";
import * as catalogApi from "@/api/catalog";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { TrendChart } from "@/components/ui/TrendChart";

function lastNDays(n: number) {
  const days: { key: string; label: string }[] = [];
  const now = new Date();
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(now.getDate() - i);
    days.push({ key: d.toISOString().slice(0, 10), label: d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" }) });
  }
  return days;
}

function bucketByDay(createdAts: string[]) {
  const days = lastNDays(14).map((d) => ({ ...d, value: 0 }));
  const byKey = new Map(days.map((d) => [d.key, d]));
  for (const createdAt of createdAts) {
    const bucket = byKey.get(createdAt.slice(0, 10));
    if (bucket) bucket.value += 1;
  }
  return days;
}

export default function AdminDashboardPage() {
  const { data: stats, loading: loadingStats } = useAsync(() => usersApi.getDashboardStats(), []);
  const { data: users, loading: loadingUsers } = useAsync(() => usersApi.listUsers(), []);
  const { data: stores, loading: loadingStores } = useAsync(() => catalogApi.listStores(), []);

  const newUsersByDay = useMemo(() => bucketByDay((users ?? []).map((u) => u.created_at)), [users]);
  const newStoresByDay = useMemo(() => bucketByDay((stores ?? []).map((s) => s.created_at)), [stores]);

  if (loadingStats) return <Spinner label="Chargement des statistiques…" />;
  if (!stats) return null;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-2xl font-bold text-gray-900">Tableau de bord administrateur</h1>

      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-muted-foreground">
          <Users className="h-4 w-4" /> Utilisateurs
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Stat label="Total" value={stats.users.total} icon={Users} />
          <Stat label="Actifs" value={stats.users.active} icon={Users} />
          <Stat label="Non vérifiés" value={stats.users.unverified} icon={Users} />
        </div>
      </div>

      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-muted-foreground">
          <StoreIcon className="h-4 w-4" /> Boutiques
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
          <Stat label="Total" value={stats.stores.total} icon={StoreIcon} />
          <Stat label="Actives" value={stats.stores.active} icon={StoreIcon} />
          <Stat label="En attente" value={stats.stores.pending_review} icon={StoreIcon} />
          <Stat label="Suspendues" value={stats.stores.suspended} icon={StoreIcon} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-4 flex items-center gap-2 font-semibold text-ink">
            <Users className="h-4 w-4 text-orange" /> Nouveaux utilisateurs (14 derniers jours)
          </h2>
          {loadingUsers ? <Spinner /> : <TrendChart data={newUsersByDay} />}
        </Card>
        <Card>
          <h2 className="mb-4 flex items-center gap-2 font-semibold text-ink">
            <StoreIcon className="h-4 w-4 text-orange" /> Nouvelles boutiques (14 derniers jours)
          </h2>
          {loadingStores ? <Spinner /> : <TrendChart data={newStoresByDay} />}
        </Card>
      </div>

      <Card className="flex items-center gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent text-orange">
          <ShieldCheck className="h-5 w-5" />
        </span>
        <p className="text-sm text-muted-foreground">
          Consultez « Boutiques » pour valider les nouvelles demandes d'ouverture.
        </p>
      </Card>
    </div>
  );
}

function Stat({ label, value, icon: Icon }: { label: string; value: number; icon: ComponentType<{ className?: string }> }) {
  return (
    <Card className="flex items-center gap-3">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent text-orange">
        <Icon className="h-5 w-5" />
      </span>
      <div>
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <p className="font-display text-2xl font-bold text-ink">{value}</p>
      </div>
    </Card>
  );
}
