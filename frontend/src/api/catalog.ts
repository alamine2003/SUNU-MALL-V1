import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import type { Category, Paginated, Product, ProductImage, ProductVariant, Store } from "@/types";

export async function listStores(params?: { search?: string }) {
  const qs = params?.search ? `?search=${encodeURIComponent(params.search)}` : "";
  const data = await apiGet<Paginated<Store>>(`/catalog/stores/${qs}`);
  return data.results;
}

export function getStore(id: string) {
  return apiGet<Store>(`/catalog/stores/${id}/`);
}

export function createStore(payload: { name: string; category?: string | null }) {
  return apiPost<Store>("/catalog/stores/", payload);
}

export function approveStore(id: string) {
  return apiPost<Store>(`/catalog/stores/${id}/approve/`);
}

export function rejectStore(id: string, reason?: string) {
  return apiPost<Store>(`/catalog/stores/${id}/reject/`, { reason });
}

export async function listCategories() {
  const data = await apiGet<Paginated<Category>>("/catalog/categories/");
  return data.results;
}

export async function listProducts(params?: { search?: string; store?: string; category?: string }) {
  const search = new URLSearchParams();
  if (params?.search) search.set("search", params.search);
  if (params?.store) search.set("store", params.store);
  if (params?.category) search.set("category", params.category);
  const qs = search.toString();
  const data = await apiGet<Paginated<Product>>(`/catalog/products/${qs ? `?${qs}` : ""}`);
  return data.results;
}

/** Comme `listProducts`, mais renvoie l'enveloppe de pagination DRF complète (count/next/previous), pour les écrans de navigation catalogue avec pagination (recherche, catégories). */
export async function searchProducts(params?: { search?: string; store?: string; category?: string; page?: number }) {
  const qs = new URLSearchParams();
  if (params?.search) qs.set("search", params.search);
  if (params?.store) qs.set("store", params.store);
  if (params?.category) qs.set("category", params.category);
  if (params?.page) qs.set("page", String(params.page));
  const query = qs.toString();
  return apiGet<Paginated<Product>>(`/catalog/products/${query ? `?${query}` : ""}`);
}

/** Comme `listStores`, mais renvoie l'enveloppe de pagination DRF complète, pour l'annuaire public des boutiques. */
export async function listStoresPaginated(params?: { search?: string; page?: number }) {
  const qs = new URLSearchParams();
  if (params?.search) qs.set("search", params.search);
  if (params?.page) qs.set("page", String(params.page));
  const query = qs.toString();
  return apiGet<Paginated<Store>>(`/catalog/stores/${query ? `?${query}` : ""}`);
}

export function getProduct(id: string) {
  return apiGet<Product>(`/catalog/products/${id}/`);
}

export function listSponsoredProducts() {
  return apiGet<Product[]>("/catalog/products/sponsored/");
}

export function createProduct(payload: {
  store: string;
  category?: string | null;
  brand?: string;
  name: string;
  description?: string;
  base_price: number;
}) {
  return apiPost<Product>("/catalog/products/", payload);
}

export function updateProduct(id: string, payload: Partial<Product>) {
  return apiPatch<Product>(`/catalog/products/${id}/`, payload);
}

export function deleteProduct(id: string) {
  return apiDelete<void>(`/catalog/products/${id}/`);
}

export function createVariant(payload: {
  product: string;
  sku: string;
  attributes?: Record<string, string>;
  price: number;
  initial_quantity?: number;
}) {
  return apiPost<ProductVariant>("/catalog/variants/", payload);
}

export function uploadProductImage(productId: string, file: File) {
  const formData = new FormData();
  formData.append("image", file);
  return apiPost<ProductImage>(`/catalog/products/${productId}/images/`, formData);
}

export function deleteProductImage(productId: string, imageId: string) {
  return apiDelete<void>(`/catalog/products/${productId}/images/?image_id=${imageId}`);
}
