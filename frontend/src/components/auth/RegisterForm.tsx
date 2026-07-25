import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CheckCircle2, Lock, Mail, Phone, TriangleAlert, User } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { ApiError } from "@/lib/api";
import * as authApi from "@/api/auth";

const schema = z.object({
  first_name: z.string().min(1, "Prénom requis"),
  last_name: z.string().min(1, "Nom requis"),
  email: z.string().email("Email invalide"),
  phone: z.string().min(6, "Numéro de téléphone requis"),
  password: z.string().min(8, "8 caractères minimum"),
});

type FormValues = z.infer<typeof schema>;

export function RegisterForm({ role }: { role: "client" | "merchant" }) {
  const [serverError, setServerError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await authApi.register({ ...values, role_name: role });
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError) {
        const data = err.data as Record<string, unknown>;
        const firstError = Object.values(data ?? {})[0];
        setServerError(Array.isArray(firstError) ? String(firstError[0]) : "Inscription impossible.");
      } else {
        setServerError("Impossible de contacter le serveur.");
      }
    }
  }

  if (done) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-2xl bg-green-50/60 py-8 text-center">
        <span className="grid h-14 w-14 place-items-center rounded-full bg-green-100">
          <CheckCircle2 className="h-8 w-8 text-success" />
        </span>
        <h2 className="font-display text-lg font-bold text-ink">Inscription réussie !</h2>
        <p className="max-w-xs text-sm text-muted-foreground">
          Vérifiez votre boîte mail pour activer votre compte avant de vous connecter.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-4">
        <Input label="Prénom" icon={User} {...register("first_name")} error={errors.first_name?.message} />
        <Input label="Nom" icon={User} {...register("last_name")} error={errors.last_name?.message} />
      </div>
      <Input label="Email" type="email" icon={Mail} {...register("email")} error={errors.email?.message} />
      <Input label="Téléphone" icon={Phone} {...register("phone")} error={errors.phone?.message} />
      <Input label="Mot de passe" type="password" icon={Lock} {...register("password")} error={errors.password?.message} />

      {serverError && (
        <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-red-50 px-3.5 py-2.5 text-sm text-danger">
          <TriangleAlert className="h-4 w-4 shrink-0" />
          {serverError}
        </div>
      )}

      <Button type="submit" loading={isSubmitting} className="mt-2 w-full">
        Créer mon compte
      </Button>
    </form>
  );
}
