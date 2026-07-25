import { type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore, type Role } from "@/store/authStore";
import { Spinner } from "@/components/ui/Spinner";

export function RoleGuard({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const hasHydrated = useAuthStore((s) => s.hasHydrated);

  if (!hasHydrated) {
    return <Spinner label="Vérification de l'accès…" />;
  }

  const allowed = !!user && roles.some((role) => user.roles.includes(role));

  if (!allowed) {
    return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  }

  return <>{children}</>;
}
