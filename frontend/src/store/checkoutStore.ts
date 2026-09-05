import { create } from "zustand";
import type { Address, CartItem } from "@/types";

interface CheckoutState {
  checkoutKey: string | null;
  storeId: string | null;
  storeName: string | null;
  items: CartItem[];
  address: Address | null;
  deliveryMethod: "standard" | "express" | "pickup";
  deliveryFee: number;
  paymentMethod: "wave" | "orange_money";
  startCheckout: (storeId: string, storeName: string, items: CartItem[]) => void;
  setAddress: (address: Address) => void;
  setDelivery: (method: "standard" | "express" | "pickup", fee: number) => void;
  setPaymentMethod: (method: "wave" | "orange_money") => void;
  reset: () => void;
}

export const useCheckoutStore = create<CheckoutState>()((set) => ({
  checkoutKey: null,
  storeId: null,
  storeName: null,
  items: [],
  address: null,
  deliveryMethod: "standard",
  deliveryFee: 0,
  paymentMethod: "wave",

  startCheckout: (storeId, storeName, items) => set({ storeId, storeName, items, checkoutKey: crypto.randomUUID() }),
  setAddress: (address) => set((state) => ({ address, checkoutKey: state.address?.id === address.id ? state.checkoutKey : crypto.randomUUID() })),
  setDelivery: (deliveryMethod, deliveryFee) => set((state) => ({ deliveryMethod, deliveryFee, checkoutKey: state.deliveryMethod === deliveryMethod ? state.checkoutKey : crypto.randomUUID() })),
  setPaymentMethod: (paymentMethod) => set((state) => ({ paymentMethod, checkoutKey: state.paymentMethod === paymentMethod ? state.checkoutKey : crypto.randomUUID() })),
  reset: () =>
    set({
      checkoutKey: null,
      storeId: null,
      storeName: null,
      items: [],
      address: null,
      deliveryMethod: "standard",
      deliveryFee: 0,
      paymentMethod: "wave",
    }),
}));
