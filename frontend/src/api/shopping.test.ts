import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { addCartItem, getCart } from "./shopping";
import { checkout } from "./orders";
import { useShoppingStore } from "@/store/shoppingStore";
import { useAuthStore } from "@/store/authStore";
import type { CheckoutPayload } from "@/types";

const user = { id: "buyer", email: "buyer@example.test", first_name: "", last_name: "", phone: "", roles: ["client" as const], is_verified: true, has_password: true };
const response = (data: unknown) => new Response(JSON.stringify(data), { headers: { "Content-Type": "application/json" } });

beforeEach(() => {
  useAuthStore.setState({ user, accessToken: "local-test" });
  useShoppingStore.setState({ cartCount: 0, favCount: 0 });
});
afterEach(() => vi.unstubAllGlobals());

it("actualise le compteur après ajout puis conserve les articles de l'autre boutique après checkout", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.endsWith("/items/")) return response({ items: [{ quantity: 2 }, { quantity: 3 }] });
    if (url.endsWith("/checkout/")) return response({ id: "order" });
    return response({ items: [{ quantity: 3 }] });
  }));
  await addCartItem("variant", 2);
  expect(useShoppingStore.getState().cartCount).toBe(5);
  await checkout({} as CheckoutPayload);
  await vi.waitFor(() => expect(useShoppingStore.getState().cartCount).toBe(3));
});

it("ignore une réponse de panier appartenant au compte précédent", async () => {
  let finish!: (value: Response) => void;
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => { finish = resolve; })));
  const pending = getCart();
  useAuthStore.setState({ user: { ...user, id: "other-buyer" } });
  finish(response({ items: [{ quantity: 9 }] }));
  await pending;
  expect(useShoppingStore.getState().cartCount).toBe(0);
});
