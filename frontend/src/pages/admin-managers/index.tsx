import { useMemo } from "react";
import { ShieldCheck } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as usersApi from "@/api/users";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";

export default function AdminManagersPage() {
  const { data: users, loading, refetch } = useAsync(() => usersApi.listUsers(), []);

  const admins = useMemo(() => users?.filter((u) => u.roles.includes("admin")) ?? [], [users]);

  async function toggleActive(id: number, isActive: boolean) {
    await usersApi.setUserActive(id, !isActive);
    refetch();
  }

  if (loading) return <Spinner label="Chargement des administrateurs…" />;

  return (
    <div>
      <h1 className="mb-6 flex items-center gap-2 font-display text-2xl font-bold text-gray-900">
        <ShieldCheck className="h-6 w-6 text-orange" /> Administrateurs
      </h1>
      {admins.length === 0 ? (
        <EmptyState icon={ShieldCheck} title="Aucun autre administrateur" />
      ) : (
        <div className="flex flex-col gap-3">
          {admins.map((admin) => (
            <Card key={admin.id} className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-ink">
                  {admin.first_name} {admin.last_name}
                </p>
                <p className="text-sm text-muted-foreground">{admin.email}</p>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant={admin.is_active ? "success" : "danger"}>{admin.is_active ? "Actif" : "Suspendu"}</Badge>
                <Button size="sm" variant="secondary" onClick={() => toggleActive(admin.id, admin.is_active)}>
                  {admin.is_active ? "Suspendre" : "Réactiver"}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
