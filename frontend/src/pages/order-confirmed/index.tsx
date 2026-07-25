import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, PackageX } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as ordersApi from "@/api/orders";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatPrice } from "@/lib/utils";

export default function OrderConfirmedPage() {
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get("order");
  const { data: order, loading } = useAsync(() => (orderId ? ordersApi.getOrder(orderId) : Promise.resolve(null)), [orderId]);

  if (!orderId) return <EmptyState icon={PackageX} title="Aucune commande à afficher" />;
  if (loading) return <Spinner label="Chargement de votre commande…" />;
  if (!order) return <EmptyState icon={PackageX} title="Commande introuvable" />;

  return (
    <div className="flex flex-col items-center gap-4 py-10 text-center">
      <div className="relative">
        <img
          src="/order-handoff.jpg"
          alt="Remise de commande Sunu Mall"
          className="h-40 w-40 rounded-full border-4 border-white object-cover shadow-xl sm:h-48 sm:w-48"
        />
        <span className="absolute -bottom-2 -right-2 grid h-14 w-14 place-items-center rounded-full border-4 border-white bg-green-100 shadow-md">
          <CheckCircle2 className="h-7 w-7 text-success" />
        </span>
      </div>
      <h1 className="font-display text-2xl font-extrabold text-gray-900">Commande confirmée !</h1>
      <p className="text-sm text-muted-foreground">
        Commande n°{order.id.slice(0, 8)} chez <strong className="text-ink">{order.store_name}</strong> —{" "}
        <strong className="text-orange">{formatPrice(order.total_amount)}</strong>
      </p>
      <div className="flex gap-3">
        <Link to={`/tracking?order=${order.id}`}>
          <Button>Suivre ma livraison</Button>
        </Link>
        <Link to="/orders">
          <Button variant="secondary">Voir mes commandes</Button>
        </Link>
      </div>
    </div>
  );
}
