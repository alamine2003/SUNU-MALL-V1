import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ChevronRight, MapPin, Plus } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as ordersApi from "@/api/orders";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { useCheckoutStore } from "@/store/checkoutStore";

const schema = z.object({
  label: z.string().min(1, "Libellé requis"),
  street: z.string().min(1, "Adresse requise"),
  city: z.string().min(1, "Ville requise"),
  country: z.string().min(1, "Pays requis"),
});
type FormValues = z.infer<typeof schema>;

export default function CheckoutAddressPage() {
  const navigate = useNavigate();
  const storeId = useCheckoutStore((s) => s.storeId);
  const setAddress = useCheckoutStore((s) => s.setAddress);
  const { data: addresses, loading } = useAsync(() => ordersApi.listAddresses(), []);
  const [showForm, setShowForm] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { country: "Sénégal" } });

  if (!storeId) return <Navigate to="/cart" replace />;

  async function onCreate(values: FormValues) {
    const address = await ordersApi.createAddress(values);
    setAddress(address);
    navigate("/checkout-delivery");
  }

  function choose(addressId: string) {
    const address = addresses?.find((a) => a.id === addressId);
    if (address) {
      setAddress(address);
      navigate("/checkout-delivery");
    }
  }

  if (loading) return <Spinner label="Chargement de vos adresses…" />;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="flex items-center gap-2 font-display text-2xl font-bold text-gray-900">
        <MapPin className="h-6 w-6 text-orange" />
        Adresse de livraison
      </h1>

      {addresses && addresses.length > 0 && !showForm && (
        <div className="flex flex-col gap-3">
          {addresses.map((address) => (
            <button key={address.id} onClick={() => choose(address.id)} className="text-left">
              <Card variant="interactive" className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-ink">{address.label}</p>
                  <p className="text-sm text-muted-foreground">
                    {address.street}, {address.city}, {address.country}
                  </p>
                </div>
                <ChevronRight className="h-5 w-5 shrink-0 text-muted-foreground" />
              </Card>
            </button>
          ))}
          <button
            onClick={() => setShowForm(true)}
            className="focus-ring flex items-center gap-1.5 self-start rounded-md text-sm font-semibold text-orange transition-colors hover:text-orange-dark"
          >
            <Plus className="h-4 w-4" /> Ajouter une nouvelle adresse
          </button>
        </div>
      )}

      {(showForm || !addresses || addresses.length === 0) && (
        <Card>
          <form onSubmit={handleSubmit(onCreate)} className="flex flex-col gap-4">
            <Input label="Libellé (Maison, Bureau…)" {...register("label")} error={errors.label?.message} />
            <Input label="Adresse" {...register("street")} error={errors.street?.message} />
            <div className="grid grid-cols-2 gap-4">
              <Input label="Ville" {...register("city")} error={errors.city?.message} />
              <Input label="Pays" {...register("country")} error={errors.country?.message} />
            </div>
            <Button type="submit" loading={isSubmitting} className="mt-2">
              Enregistrer et continuer
            </Button>
          </form>
        </Card>
      )}
    </div>
  );
}
