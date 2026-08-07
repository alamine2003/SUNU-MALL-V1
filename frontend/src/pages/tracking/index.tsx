import { lazy, Suspense, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CheckCircle2, Clock, MapPin, PackageCheck, PackageSearch, Truck, XCircle } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as ordersApi from "@/api/orders";
import * as paymentsApi from "@/api/payments";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";
import type { DeliveryStatus } from "@/types";

const PAYMENT_STATUS_VARIANT: Record<string, "default" | "success" | "warning" | "danger"> = {
  success: "success",
  pending: "warning",
  failed: "danger",
  refunded: "default",
};

const DeliveryMap = lazy(() => import("@/components/marketplace/DeliveryMap").then((m) => ({ default: m.DeliveryMap })));

const STEPS: { key: DeliveryStatus; label: string; icon: typeof Clock }[] = [
  { key: "pending", label: "En attente", icon: Clock },
  { key: "assigned", label: "Livreur affecté", icon: PackageCheck },
  { key: "picked_up", label: "En cours de livraison", icon: Truck },
  { key: "delivered", label: "Livrée", icon: CheckCircle2 },
];

export default function TrackingPage() {
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get("order");
  const { data: order, refetch } = useAsync(
    () => (orderId ? ordersApi.getOrder(orderId) : Promise.resolve(null)),
    [orderId],
  );
  const [cancelling, setCancelling] = useState(false);
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    if (!orderId) return;
    const interval = setInterval(refetch, 10000);
    return () => clearInterval(interval);
  }, [orderId, refetch]);

  if (!orderId) return <EmptyState icon={PackageSearch} title="Aucune commande sélectionnée" />;
  if (!order) return <Spinner label="Chargement du suivi…" />;

  const currentIndex = Math.max(0, STEPS.findIndex((s) => s.key === order.delivery?.status));

  async function handleCancel() {
    if (!order || !confirm("Annuler cette commande ?")) return;
    setCancelling(true);
    try {
      await ordersApi.cancelOrder(order.id);
      refetch();
    } finally {
      setCancelling(false);
    }
  }

  async function handleRetryPayment() {
    if (!order?.payment) return;
    setRetrying(true);
    try {
      await paymentsApi.sandboxConfirmPayment(order.payment.id, "success");
      refetch();
    } finally {
      setRetrying(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-2xl font-bold text-gray-900">Suivi de livraison</h1>
      <Card className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground">
            Commande n°{order.id.slice(0, 8)} — <strong className="text-ink">{order.store_name}</strong>
          </p>
          {order.can_be_cancelled && (
            <Button variant="danger" size="sm" onClick={handleCancel} loading={cancelling}>
              <XCircle className="h-4 w-4" />
              Annuler la commande
            </Button>
          )}
        </div>

        {order.payment?.status === "failed" && (
          <div className="flex flex-wrap items-center gap-2 rounded-lg border border-danger/30 bg-red-50 p-3">
            <Badge variant={PAYMENT_STATUS_VARIANT[order.payment.status]}>Paiement échoué</Badge>
            <p className="flex-1 text-xs text-danger">Le paiement n'a pas abouti.</p>
            <Button size="sm" onClick={handleRetryPayment} loading={retrying}>
              Réessayer le paiement
            </Button>
          </div>
        )}

        {order.payment?.refund && (
          <div className="flex flex-wrap items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
            <Badge variant={order.payment.refund.status === "completed" ? "success" : "warning"}>
              {order.payment.refund.status === "completed" ? "Remboursé" : "Remboursement en attente"}
            </Badge>
            <p className="flex-1 text-xs text-amber-800">
              {order.payment.refund.status === "completed"
                ? `Remboursé le ${order.payment.refund.refunded_at ? formatDate(order.payment.refund.refunded_at) : ""}.`
                : "Votre remboursement est en cours de traitement."}
            </p>
          </div>
        )}

        <div className="flex items-start">
          {STEPS.map((step, i) => (
            <div key={step.key} className="flex flex-1 items-center last:flex-none">
              <div className="flex flex-col items-center gap-2 text-center">
                <span
                  className={`grid h-10 w-10 shrink-0 place-items-center rounded-full transition-colors ${
                    i <= currentIndex ? "bg-gradient-orange text-white shadow-orange" : "bg-muted text-muted-foreground"
                  }`}
                >
                  <step.icon className="h-5 w-5" />
                </span>
                <p className={`text-xs font-medium ${i <= currentIndex ? "text-gray-700" : "text-muted-foreground"}`}>{step.label}</p>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`mb-6 h-0.5 flex-1 rounded-full transition-colors ${i < currentIndex ? "bg-orange" : "bg-border"}`} />
              )}
            </div>
          ))}
        </div>
        {order.delivery?.driver_detail && (
          <div className="flex items-center gap-3 border-t border-border pt-4">
            <Truck className="h-5 w-5 text-orange" />
            <div>
              <p className="text-sm font-medium text-ink">{order.delivery.driver_detail.full_name}</p>
              <p className="text-xs text-muted-foreground">{order.delivery.driver_detail.phone}</p>
            </div>
          </div>
        )}
        {(order.delivery?.last_position || (order.address_detail?.latitude != null && order.address_detail?.longitude != null)) && (
          <div className="border-t border-border pt-4">
            <Suspense fallback={<div className="h-56 w-full animate-pulse rounded-2xl bg-muted" />}>
              <DeliveryMap
                driverPosition={
                  order.delivery?.last_position
                    ? {
                        lat: parseFloat(order.delivery.last_position.latitude),
                        lng: parseFloat(order.delivery.last_position.longitude),
                        label: "Position du livreur",
                      }
                    : null
                }
                destination={
                  order.address_detail?.latitude != null && order.address_detail?.longitude != null
                    ? {
                        lat: parseFloat(order.address_detail.latitude),
                        lng: parseFloat(order.address_detail.longitude),
                        label: "Votre adresse",
                      }
                    : null
                }
                className="h-56 w-full"
              />
            </Suspense>
            {order.delivery?.last_position && (
              <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                <MapPin className="h-3.5 w-3.5 text-orange" />
                Position mise à jour {formatDate(order.delivery.last_position.recorded_at)}
              </p>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
