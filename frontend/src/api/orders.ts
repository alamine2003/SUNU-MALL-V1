import { apiGet, apiPatch, apiPost } from "@/lib/api";
import type { Address, CheckoutPayload, Delivery, DeliveryStatus, Driver, DriverAvailability, Order, Paginated } from "@/types";

export async function listAddresses() {
  const data = await apiGet<Paginated<Address>>("/orders/addresses/");
  return data.results;
}

export function createAddress(payload: {
  label: string;
  street: string;
  city: string;
  country: string;
  latitude?: number;
  longitude?: number;
}) {
  return apiPost<Address>("/orders/addresses/", payload);
}

export async function listOrders() {
  const data = await apiGet<Paginated<Order>>("/orders/");
  return data.results;
}

export function getOrder(id: string) {
  return apiGet<Order>(`/orders/${id}/`);
}

export function checkout(payload: CheckoutPayload) {
  return apiPost<Order>("/orders/checkout/", payload);
}

export async function listAvailableDrivers() {
  const data = await apiGet<Paginated<Driver>>("/orders/drivers/");
  return data.results;
}

export function getMyDriverProfile() {
  return apiGet<Driver>("/orders/drivers/me/");
}

export function updateMyDriverProfile(payload: { vehicle_type?: string; availability_status?: DriverAvailability }) {
  return apiPatch<Driver>("/orders/drivers/me/", payload);
}

export async function listDeliveries() {
  const data = await apiGet<Paginated<Delivery>>("/orders/deliveries/");
  return data.results;
}

export function getDelivery(id: string) {
  return apiGet<Delivery>(`/orders/deliveries/${id}/`);
}

export function assignDriver(deliveryId: string, driverId: string) {
  return apiPost<Delivery>(`/orders/deliveries/${deliveryId}/assign/`, { driver: driverId });
}

export function updateDeliveryStatus(deliveryId: string, status: DeliveryStatus) {
  return apiPost<Delivery>(`/orders/deliveries/${deliveryId}/status/`, { status });
}

export function shareDeliveryPosition(deliveryId: string, latitude: number, longitude: number) {
  return apiPost(`/orders/deliveries/${deliveryId}/track/`, { latitude, longitude });
}
