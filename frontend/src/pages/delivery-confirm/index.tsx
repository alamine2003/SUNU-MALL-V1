import { useSearchParams } from "react-router-dom";
import { PackageCheck, PackageSearch } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as ordersApi from "@/api/orders";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";

export default function DeliveryConfirmPage() {
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get("order");
  const { data: order, loading } = useAsync(
    () => (orderId ? ordersApi.getOrder(orderId) : Promise.resolve(null)),
    [orderId],
  );

  if (!orderId) return <EmptyState icon={PackageSearch} title="Aucune commande sélectionnée" />;
  if (loading) return <Spinner label="Chargement…" />;
  if (!order) return <EmptyState icon={PackageSearch} title="Commande introuvable" />;

  const delivered = order.delivery?.status === "delivered" || !!order.delivery?.delivered_at;

  return (
    <Card className="flex flex-col items-center gap-4 py-10 text-center">
      <span className={`grid h-16 w-16 place-items-center rounded-full ${delivered ? "bg-green-100" : "bg-accent"}`}>
        <PackageCheck className={`h-9 w-9 ${delivered ? "text-success" : "text-orange"}`} />
      </span>
      <h1 className="font-display text-xl font-bold text-ink">Confirmation de livraison</h1>
      <p className="text-sm text-muted-foreground">
        Commande n°{order.id.slice(0, 8)} — statut actuel : <strong className="text-ink">{order.delivery?.status ?? "inconnu"}</strong>
      </p>
      <Button disabled={delivered} title="Confirmation de réception (code OTP) — endpoint backend à venir">
        {delivered ? "Réception déjà confirmée" : "Confirmer la réception"}
      </Button>
      <p className="max-w-sm text-xs text-muted-foreground">
        La confirmation par code OTP nécessite un endpoint backend dédié, pas encore disponible.
      </p>
    </Card>
  );
}
