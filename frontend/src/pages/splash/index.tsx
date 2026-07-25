import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ShoppingBag } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { roleHomePath } from "@/lib/roles";

export default function SplashPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const hasHydrated = useAuthStore((s) => s.hasHydrated);

  useEffect(() => {
    if (!hasHydrated) return;
    const timer = setTimeout(() => {
      navigate(user ? roleHomePath(user.roles) : "/home", { replace: true });
    }, 900);
    return () => clearTimeout(timer);
  }, [hasHydrated, user, navigate]);

  return (
    <div className="flex flex-col items-center gap-4 py-12 text-center">
      <span className="grid h-16 w-16 place-items-center rounded-2xl bg-gradient-orange text-white shadow-orange animate-pulse-dot">
        <ShoppingBag className="h-8 w-8" />
      </span>
      <h1 className="text-2xl text-navy">
        Sunu<span className="text-orange">Mall</span>
      </h1>
      <p className="text-sm text-muted-foreground">La marketplace qui connecte le Sénégal.</p>
    </div>
  );
}
