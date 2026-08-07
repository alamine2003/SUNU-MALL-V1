import { apiGet } from "@/lib/api";
import type { SalesStatistic, StoreSummary } from "@/types";

/** Statistiques de vente journalières d'une boutique (non paginé : un an ~365 lignes, sans risque). */
export function listSalesStatistics(storeId: string) {
  return apiGet<SalesStatistic[]>(`/analytics/sales/?store=${storeId}`);
}

/** Résumé chiffré (30 derniers jours) : panier moyen, taux de livraison, note moyenne. */
export function getStoreSummary(storeId: string) {
  return apiGet<StoreSummary>(`/analytics/store-summary/?store=${storeId}`);
}
