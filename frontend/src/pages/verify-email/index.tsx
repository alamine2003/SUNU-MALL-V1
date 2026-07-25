import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { ApiError } from "@/lib/api";
import * as authApi from "@/api/auth";

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const uid = searchParams.get("uid");
    const token = searchParams.get("token");
    if (!uid || !token) {
      setStatus("error");
      setMessage("Lien de vérification incomplet.");
      return;
    }
    authApi
      .verifyEmail(uid, token)
      .then((res) => {
        setStatus("success");
        setMessage(res.message);
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err instanceof ApiError ? String((err.data as any)?.error ?? err.message) : "Lien invalide ou expiré.");
      });
  }, [searchParams]);

  if (status === "loading") return <Spinner label="Vérification de votre email…" />;

  return (
    <div className="flex flex-col items-center gap-3 py-6 text-center">
      <span className={`grid h-16 w-16 place-items-center rounded-full ${status === "success" ? "bg-green-100" : "bg-red-100"}`}>
        {status === "success" ? (
          <CheckCircle2 className="h-9 w-9 text-success" />
        ) : (
          <XCircle className="h-9 w-9 text-danger" />
        )}
      </span>
      <h1 className="font-display text-lg font-bold text-ink">
        {status === "success" ? "Email vérifié !" : "Échec de la vérification"}
      </h1>
      <p className="max-w-xs text-sm text-muted-foreground">{message}</p>
      <Link to="/login" className="mt-2 w-full">
        <Button className="w-full">Aller à la connexion</Button>
      </Link>
    </div>
  );
}
