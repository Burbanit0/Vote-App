/**
 * useAuthStore — auth slice (Phase 5.4/5.5).
 *
 * The source of truth for the logged-in user + token. `localStorage['user']` is
 * the persistence medium (the openapi-fetch auth middleware in api/client.ts
 * reads the token from this store, falling back to localStorage). The store
 * self-hydrates from localStorage at module init, so no provider is needed;
 * `useAuth()` is the convenience hook the former AuthContext consumers use.
 */
import { create } from 'zustand';
import { User } from '../types';

interface AuthState {
  user: User | null;
  loading: boolean;
  /** Re-read the persisted user from localStorage (called on app mount). */
  hydrate: () => void;
  login: (userData: User) => void;
  logout: () => void;
}

function readStoredUser(): User | null {
  try {
    const raw = localStorage.getItem('user');
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  // Self-hydrated at module init from localStorage (no provider needed).
  user: readStoredUser(),
  loading: false,
  hydrate: () => set({ user: readStoredUser(), loading: false }),
  login: (userData) => {
    localStorage.setItem('user', JSON.stringify(userData));
    set({ user: userData, loading: false });
  },
  logout: () => {
    localStorage.removeItem('user');
    set({ user: null, loading: false });
  },
}));

/** Current Bearer token from the store, or null. */
export function getAuthToken(): string | null {
  return useAuthStore.getState().user?.access_token ?? null;
}

// ── Convenience hook (former AuthContext API) ─────────────────────────────────

export interface AuthValue {
  user: User | null;
  login: (userData: User) => void;
  logout: () => void;
  loading: boolean;
}

export function useAuth(): AuthValue {
  const user = useAuthStore((s) => s.user);
  const login = useAuthStore((s) => s.login);
  const logout = useAuthStore((s) => s.logout);
  const loading = useAuthStore((s) => s.loading);
  return { user, login, logout, loading };
}
