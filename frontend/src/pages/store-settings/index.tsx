import { useEffect, useState } from "react";
import { CheckCircle2, Settings, Store as StoreIcon, TriangleAlert } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";
import { Card } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { myStores } from "@/lib/merchant";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

const DAYS = [
  { key: "monday", label: "Lundi" },
  { key: "tuesday", label: "Mardi" },
  { key: "wednesday", label: "Mercredi" },
  { key: "thursday", label: "Jeudi" },
  { key: "friday", label: "Vendredi" },
  { key: "saturday", label: "Samedi" },
  { key: "sunday", label: "Dimanche" },
];

interface DayHours {
  closed: boolean;
  open: string;
  close: string;
}
type BusinessHours = Record<string, DayHours>;

const DEFAULT_HOURS: DayHours = { closed: false, open: "08:00", close: "19:00" };

export default function StoreSettingsPage() {
  const { data: stores, loading: loadingStores } = useAsync(() => catalogApi.listStores(), []);
  const own = myStores(stores ?? []);
  const [storeId, setStoreId] = useState<string>("");

  useEffect(() => {
    if (!storeId && own.length > 0) setStoreId(own[0].id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [own.length]);

  const {
    data: settings,
    loading: loadingSettings,
    refetch,
  } = useAsync(() => (storeId ? catalogApi.getStoreSettings(storeId) : Promise.resolve(null)), [storeId]);

  const [hours, setHours] = useState<BusinessHours>({});
  const [minOrder, setMinOrder] = useState("0");
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    if (!settings) return;
    const raw = (settings.business_hours ?? {}) as Partial<BusinessHours>;
    const normalized: BusinessHours = {};
    for (const day of DAYS) {
      normalized[day.key] = raw[day.key] ?? { ...DEFAULT_HOURS };
    }
    setHours(normalized);
    setMinOrder(settings.min_order_amount);
  }, [settings]);

  async function handleSave() {
    setSaving(true);
    setFeedback(null);
    try {
      await catalogApi.updateStoreSettings(storeId, {
        business_hours: hours,
        min_order_amount: parseFloat(minOrder) || 0,
      });
      setFeedback({ type: "success", text: "Paramètres enregistrés." });
      refetch();
    } catch (err) {
      setFeedback({
        type: "error",
        text: err instanceof ApiError ? "Impossible d'enregistrer." : "Impossible de contacter le serveur.",
      });
    } finally {
      setSaving(false);
    }
  }

  if (loadingStores) return <Spinner label="Chargement…" />;
  if (own.length === 0) {
    return <EmptyState icon={StoreIcon} title="Aucune boutique" description="Créez d'abord votre boutique pour configurer ses paramètres." />;
  }

  return (
    <div className="max-w-2xl">
      <h1 className="mb-6 flex items-center gap-2 font-display text-2xl font-bold text-gray-900">
        <Settings className="h-6 w-6 text-orange" /> Paramètres boutique
      </h1>

      {own.length > 1 && (
        <div className="mb-4 max-w-xs">
          <Select label="Boutique" value={storeId} onChange={(e) => setStoreId(e.target.value)}>
            {own.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        </div>
      )}

      {loadingSettings ? (
        <Spinner label="Chargement des paramètres…" />
      ) : (
        <Card className="flex flex-col gap-5">
          <div>
            <p className="mb-3 text-sm font-semibold text-ink">Horaires d'ouverture</p>
            <div className="flex flex-col gap-2">
              {DAYS.map((day) => {
                const dayHours = hours[day.key] ?? DEFAULT_HOURS;
                return (
                  <div key={day.key} className="flex flex-wrap items-center gap-3 rounded-lg border border-border px-3 py-2">
                    <label className="flex w-28 shrink-0 items-center gap-2 text-sm font-medium text-ink">
                      <input
                        type="checkbox"
                        checked={!dayHours.closed}
                        onChange={(e) => setHours((h) => ({ ...h, [day.key]: { ...dayHours, closed: !e.target.checked } }))}
                        className="h-4 w-4 accent-orange"
                      />
                      {day.label}
                    </label>
                    {!dayHours.closed ? (
                      <div className="flex items-center gap-2 text-sm">
                        <input
                          type="time"
                          value={dayHours.open}
                          onChange={(e) => setHours((h) => ({ ...h, [day.key]: { ...dayHours, open: e.target.value } }))}
                          className="focus-ring rounded-md border border-border px-2 py-1"
                        />
                        <span className="text-muted-foreground">à</span>
                        <input
                          type="time"
                          value={dayHours.close}
                          onChange={(e) => setHours((h) => ({ ...h, [day.key]: { ...dayHours, close: e.target.value } }))}
                          className="focus-ring rounded-md border border-border px-2 py-1"
                        />
                      </div>
                    ) : (
                      <span className="text-sm text-muted-foreground">Fermé</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <Input
            label="Montant minimum de commande (XOF)"
            type="number"
            step="1"
            value={minOrder}
            onChange={(e) => setMinOrder(e.target.value)}
            className="max-w-xs"
          />

          {feedback && (
            <div
              className={cn(
                "flex items-center gap-2 rounded-lg border px-3.5 py-2.5 text-sm font-medium",
                feedback.type === "success" ? "border-green-200 bg-green-50 text-green-700" : "border-danger/30 bg-red-50 text-danger",
              )}
            >
              {feedback.type === "success" ? <CheckCircle2 className="h-4 w-4 shrink-0" /> : <TriangleAlert className="h-4 w-4 shrink-0" />}
              {feedback.text}
            </div>
          )}

          <Button onClick={handleSave} loading={saving} className="self-start">
            Enregistrer
          </Button>
        </Card>
      )}
    </div>
  );
}
