import { create } from "zustand";

// Compteurs d'affichage alimentés par les réponses du serveur, sans persistance.
export const useShoppingStore = create<{ cartCount: number; favCount: number }>(() => ({
  cartCount: 0,
  favCount: 0,
}));
