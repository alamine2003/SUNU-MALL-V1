import { beforeEach, describe, expect, it } from "vitest";
import { useCheckoutStore } from "./checkoutStore";
import type { Address, CartItem } from "@/types";

const item: CartItem = {
  id: "item-1",
  product_variant: "variant-1",
  product_name: "Chargeur",
  unit_price: "6000",
  quantity: 2,
  subtotal: 12000,
  added_at: "2026-07-19T00:00:00Z",
  store: "store-1",
};

const address: Address = {
  id: "addr-1",
  user: "user-1",
  label: "Maison",
  street: "Rue 1",
  city: "Dakar",
  country: "Sénégal",
  latitude: null,
  longitude: null,
  created_at: "2026-07-19T00:00:00Z",
};

beforeEach(() => {
  useCheckoutStore.getState().reset();
});

describe("useCheckoutStore", () => {
  it("starts with an empty checkout", () => {
    const state = useCheckoutStore.getState();
    expect(state.storeId).toBeNull();
    expect(state.items).toEqual([]);
    expect(state.paymentMethod).toBe("wave");
  });

  it("startCheckout captures the store and cart items", () => {
    useCheckoutStore.getState().startCheckout("store-1", "Tech World Dakar", [item]);
    const state = useCheckoutStore.getState();
    expect(state.storeId).toBe("store-1");
    expect(state.storeName).toBe("Tech World Dakar");
    expect(state.items).toEqual([item]);
  });

  it("setAddress and setDelivery update independently", () => {
    useCheckoutStore.getState().setAddress(address);
    useCheckoutStore.getState().setDelivery("express", 2000);
    const state = useCheckoutStore.getState();
    expect(state.address).toEqual(address);
    expect(state.deliveryMethod).toBe("express");
    expect(state.deliveryFee).toBe(2000);
  });

  it("reset clears everything back to defaults", () => {
    useCheckoutStore.getState().startCheckout("store-1", "Boutique", [item]);
    useCheckoutStore.getState().setAddress(address);
    useCheckoutStore.getState().setDelivery("express", 2000);
    useCheckoutStore.getState().setPaymentMethod("orange_money");

    useCheckoutStore.getState().reset();

    const state = useCheckoutStore.getState();
    expect(state.storeId).toBeNull();
    expect(state.address).toBeNull();
    expect(state.deliveryFee).toBe(0);
    expect(state.paymentMethod).toBe("wave");
  });
});
