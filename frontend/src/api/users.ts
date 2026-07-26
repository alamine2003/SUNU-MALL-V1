import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import type { Paginated } from "@/types";

export interface AdminUser {
  id: string;
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

export interface DailyCount {
  date: string;
  count: number;
}

export interface DashboardStats {
  users: { total: number; active: number; unverified: number };
  stores: { total: number; active: number; pending_review: number; suspended: number };
  trend: { new_users: DailyCount[]; new_stores: DailyCount[] };
}

export interface Role {
  id: number;
  name: string;
  description: string;
}

export interface UserRoleAssignment {
  id: number;
  user: string;
  user_email: string;
  role: number;
  role_name: string;
}

export async function listUsers() {
  const data = await apiGet<Paginated<AdminUser>>("/users/");
  return data.results;
}

export function listUsersPaginated(params?: { role?: string; page?: number }) {
  const qs = new URLSearchParams();
  if (params?.role) qs.set("role", params.role);
  if (params?.page) qs.set("page", String(params.page));
  const query = qs.toString();
  return apiGet<Paginated<AdminUser>>(`/users/${query ? `?${query}` : ""}`);
}

export function setUserActive(id: string, isActive: boolean) {
  return apiPatch<AdminUser>(`/users/${id}/`, { is_active: isActive });
}

export function getDashboardStats() {
  return apiGet<DashboardStats>("/users/admin/dashboard/stats/");
}

export async function listRoles() {
  const data = await apiGet<Paginated<Role>>("/users/roles/");
  return data.results;
}

export async function listUserRoles() {
  const data = await apiGet<Paginated<UserRoleAssignment>>("/users/user-roles/");
  return data.results;
}

/** Récupère toutes les pages : nécessaire pour calculer correctement les rôles affichés quel que soit le nombre total d'attributions. */
export async function listAllUserRoles() {
  const all: UserRoleAssignment[] = [];
  let page = 1;
  for (;;) {
    const data = await apiGet<Paginated<UserRoleAssignment>>(`/users/user-roles/?page=${page}`);
    all.push(...data.results);
    if (!data.next) break;
    page += 1;
  }
  return all;
}

export function assignRole(userId: string, roleId: number) {
  return apiPost<UserRoleAssignment>("/users/user-roles/", { user: userId, role: roleId });
}

export function removeUserRole(userRoleId: number) {
  return apiDelete<void>(`/users/user-roles/${userRoleId}/`);
}
