import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import type { Cart, Wishlist } from "@/types";
import { useAuthStore } from "@/store/authStore";
import { useShoppingStore } from "@/store/shoppingStore";

function updateCount<T extends Cart | Wishlist>(request: Promise<T>, kind: "cart" | "wishlist") {
  const userId = useAuthStore.getState().user?.id;
  return request.then((data) => {
    if (useAuthStore.getState().user?.id === userId) {
      if (kind === "cart") {
        useShoppingStore.setState({ cartCount: (data as Cart).items.reduce((total, item) => total + item.quantity, 0) });
      } else {
        useShoppingStore.setState({ favCount: data.items.length });
      }
    }
    return data;
  });
}

export function getCart() {
  return updateCount(apiGet<Cart>("/shopping/cart/"), "cart");
}

export function addCartItem(productVariant: string, quantity = 1) {
  return updateCount(apiPost<Cart>("/shopping/cart/items/", { product_variant: productVariant, quantity }), "cart");
}

export function updateCartItem(itemId: string, quantity: number) {
  return updateCount(apiPatch<Cart>(`/shopping/cart/items/${itemId}/`, { quantity }), "cart");
}

export function removeCartItem(itemId: string) {
  return updateCount(apiDelete<Cart>(`/shopping/cart/items/${itemId}/`), "cart");
}

export function clearCart() {
  return updateCount(apiPost<Cart>("/shopping/cart/clear/"), "cart");
}

export function getWishlist() {
  return updateCount(apiGet<Wishlist>("/shopping/wishlist/"), "wishlist");
}

export function addWishlistItem(productId: string) {
  return updateCount(apiPost<Wishlist>("/shopping/wishlist/items/", { product: productId }), "wishlist");
}

export function removeWishlistItem(productId: string) {
  return updateCount(apiDelete<Wishlist>(`/shopping/wishlist/items/${productId}/`), "wishlist");
}
