import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Store as StoreIcon, TriangleAlert } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

const schema = z.object({
  name: z.string().min(2, "Nom de boutique requis"),
  category: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export default function CreateShopPage() {
  const navigate = useNavigate();
  const { data: categories } = useAsync(() => catalogApi.listCategories(), []);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setError(null);
    try {
      await catalogApi.createStore({ name: values.name, category: values.category || null });
      navigate("/merchant");
    } catch {
      setError("Impossible de créer la boutique.");
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
          <Select label="Catégorie" {...register("category")}>
            <option value="">Sélectionner…</option>
            {categories?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
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
