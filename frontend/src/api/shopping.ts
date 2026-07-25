import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import type { Cart, Wishlist } from "@/types";

export function getCart() {
  return apiGet<Cart>("/shopping/cart/");
}

export function addCartItem(productVariant: string, quantity = 1) {
  return apiPost<Cart>("/shopping/cart/items/", { product_variant: productVariant, quantity });
}

export function updateCartItem(itemId: string, quantity: number) {
  return apiPatch<Cart>(`/shopping/cart/items/${itemId}/`, { quantity });
}

export function removeCartItem(itemId: string) {
  return apiDelete<Cart>(`/shopping/cart/items/${itemId}/`);
}

export function clearCart() {
  return apiPost<Cart>("/shopping/cart/clear/");
}

export function getWishlist() {
  return apiGet<Wishlist>("/shopping/wishlist/");
}

export function addWishlistItem(productId: string) {
  return apiPost<Wishlist>("/shopping/wishlist/items/", { product: productId });
}

export function removeWishlistItem(productId: string) {
  return apiDelete<Wishlist>(`/shopping/wishlist/items/${productId}/`);
}
