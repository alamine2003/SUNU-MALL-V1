import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Store as StoreIcon, TriangleAlert } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ApiError } from "@/lib/api";

const schema = z.object({
  name: z.string().min(2, "Nom de boutique requis"),
  phone: z.string().min(6, "Téléphone requis"),
  category: z.string().min(1, "Catégorie requise"),
  description: z.string().optional(),
  address: z.string().optional(),
  city: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export default function CreateShopPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const { data: categories } = useAsync(() => catalogApi.listStoreCategories(), []);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setError(null);
    try {
      await catalogApi.createStore({
        name: values.name,
        phone: values.phone,
        category: values.category ? Number(values.category) : null,
        description: values.description,
        address: values.address,
        city: values.city,
      });
      navigate("/merchant");
    } catch (err) {
      if (err instanceof ApiError) {
        const data = err.data as Record<string, unknown>;
        const firstError = Object.values(data ?? {})[0];
        setError(Array.isArray(firstError) ? String(firstError[0]) : "Impossible de créer la boutique.");
      } else {
        setError("Impossible de contacter le serveur.");
      }
    }
  }

  return (
    <div className="max-w-lg">
      <div className="mb-6 flex items-center gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-accent text-orange">
          <StoreIcon className="h-5 w-5" />
        </span>
        <div>
          <h1 className="font-display text-xl font-bold text-gray-900">Créer ma boutique</h1>
          <p className="text-sm text-muted-foreground">Soumise à validation par un administrateur avant publication.</p>
        </div>
      </div>
      <Card>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Input label="Nom de la boutique" {...register("name")} error={errors.name?.message} />
          <Input label="Téléphone" {...register("phone")} error={errors.phone?.message} placeholder="77 000 00 00" />
          <Select label="Catégorie" {...register("category")} error={errors.category?.message}>
            <option value="">Sélectionner…</option>
            {categories?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
          <Textarea
            label="Description de votre activité (optionnel)"
            {...register("description")}
            placeholder="Ce que vous vendez, votre expérience…"
            rows={3}
          />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Adresse (optionnel)" {...register("address")} />
            <Input label="Ville (optionnel)" {...register("city")} placeholder="Dakar" />
          </div>
          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-red-50 px-3.5 py-2.5 text-sm text-danger">
              <TriangleAlert className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}
          <Button type="submit" loading={isSubmitting}>
            Créer la boutique
          </Button>
        </form>
      </Card>
    </div>
  );
}
