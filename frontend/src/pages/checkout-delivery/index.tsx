import { Navigate, useNavigate } from "react-router-dom";
import { Bike, ChevronRight, MapPin, Truck, Store as StoreIcon } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { useCheckoutStore } from "@/store/checkoutStore";
import { formatPrice } from "@/lib/utils";

const OPTIONS = [
  { id: "standard" as const, label: "Livraison standard", eta: "24-48h", fee: 1000, icon: Truck },
  { id: "express" as const, label: "Livraison express", eta: "2-4h", fee: 2000, icon: Bike },
  { id: "pickup" as const, label: "Retrait en boutique", eta: "Selon disponibilité", fee: 0, icon: StoreIcon },
];

export default function CheckoutDeliveryPage() {
  const navigate = useNavigate();
  const storeId = useCheckoutStore((s) => s.storeId);
  const address = useCheckoutStore((s) => s.address);
  const setDelivery = useCheckoutStore((s) => s.setDelivery);

  if (!storeId) return <Navigate to="/cart" replace />;
  if (!address) return <Navigate to="/checkout-address" replace />;

  function choose(option: (typeof OPTIONS)[number]) {
    setDelivery(option.id, option.fee);
    navigate("/checkout-payment");
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-2xl font-bold text-gray-900">Mode de livraison</h1>
      <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <MapPin className="h-4 w-4 text-orange" />
        Livraison à : {address.street}, {address.city}
      </p>
      <div className="flex flex-col gap-3">
        {OPTIONS.map((option) => (
          <button key={option.id} onClick={() => choose(option)} className="text-left">
            <Card variant="interactive" className="flex items-center gap-4">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-accent text-orange">
                <option.icon className="h-5 w-5" />
              </span>
              <div className="flex-1">
                <p className="font-semibold text-ink">{option.label}</p>
                <p className="text-xs text-muted-foreground">{option.eta}</p>
              </div>
              <p className="font-bold text-ink">{option.fee === 0 ? "Gratuit" : formatPrice(option.fee)}</p>
              <ChevronRight className="h-5 w-5 shrink-0 text-muted-foreground" />
            </Card>
          </button>
        ))}
      </div>
    </div>
  );
}
