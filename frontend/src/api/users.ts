import { apiGet, apiPatch } from "@/lib/api";
import type { Paginated } from "@/types";

export interface AdminUser {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  roles: string[];
  permissions: string[];
}

export interface DashboardStats {
  users: { total: number; active: number; unverified: number };
  stores: { total: number; active: number; pending_review: number; suspended: number };
}

export async function listUsers() {
  const data = await apiGet<Paginated<AdminUser>>("/users/");
  return data.results;
}

export function setUserActive(id: number, isActive: boolean) {
  return apiPatch<AdminUser>(`/users/${id}/`, { is_active: isActive });
}

export function getDashboardStats() {
  return apiGet<DashboardStats>("/users/admin/dashboard/stats/");
}
