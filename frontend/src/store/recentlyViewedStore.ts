import { create } from "zustand";
import { persist } from "zustand/middleware";

const MAX_ITEMS = 12;

interface RecentlyViewedState {
  productIds: string[];
  addProduct: (id: string) => void;
}

export const useRecentlyViewedStore = create<RecentlyViewedState>()(
  persist(
    (set) => ({
      productIds: [],
      addProduct: (id) =>
        set((state) => ({
          productIds: [id, ...state.productIds.filter((p) => p !== id)].slice(0, MAX_ITEMS),
        })),
    }),
    { name: "sunu-mall-recently-viewed" },
  ),
);
