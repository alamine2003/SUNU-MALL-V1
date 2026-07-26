import { apiGet } from "@/lib/api";
import type { SalesStatistic } from "@/types";

/** Statistiques de vente journalières d'une boutique (non paginé : un an ~365 lignes, sans risque). */
export function listSalesStatistics(storeId: string) {
  return apiGet<SalesStatistic[]>(`/analytics/sales/?store=${storeId}`);
}
