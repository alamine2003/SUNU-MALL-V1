import { create } from "zustand";
import { browserSessionRequest } from "@/lib/session";
import type { AuthUser, Role } from "@/types";

export type { AuthUser, Role };

export interface LoginPayload {
  user: AuthUser;
  access: string | null;
  refresh: string | null;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  hasHydrated: boolean;
  sessionVersion: number;
  loginSuccess: (payload: LoginPayload) => void;
  setTokens: (access: string, refresh?: string) => void;
  updateUser: (patch: Partial<AuthUser>) => void;
  logout: () => void;
  hasRole: (role: Role) => boolean;
  setHasHydrated: (value: boolean) => void;
}

// Efface les anciens JWT persistés lors de la migration vers le cookie HttpOnly.
try { globalThis.localStorage?.removeItem("sunu-mall-auth"); } catch { /* stockage indisponible */ }

export const useAuthStore = create<AuthState>()((set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      hasHydrated: false,
      sessionVersion: 0,

      loginSuccess: ({ user, access, refresh }) =>
        set((state) => ({ user, accessToken: access, refreshToken: refresh, sessionVersion: state.sessionVersion + 1 })),

      setTokens: (access, refresh) =>
        set((state) => ({
          accessToken: access,
          refreshToken: refresh ?? state.refreshToken,
        })),

      updateUser: (patch) => set((state) => (state.user ? { user: { ...state.user, ...patch } } : {})),

      logout: () => {
        set((state) => ({ user: null, accessToken: null, refreshToken: null, sessionVersion: state.sessionVersion + 1 }));
        void browserSessionRequest("logout").catch(() => undefined);
      },

      hasRole: (role) => !!get().user?.roles.includes(role),

      setHasHydrated: (value) => set({ hasHydrated: value }),
}));
