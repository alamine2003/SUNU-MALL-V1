import type { Store } from "@/types";
import { useAuthStore } from "@/store/authStore";

export function myStores(stores: Store[]): Store[] {
  const userId = useAuthStore.getState().user?.id;
  return stores.filter((s) => s.owner === userId);
}
