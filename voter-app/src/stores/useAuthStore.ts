/**
 * useAuthStore — auth slice (Phase 5.4).
 *
 * Replaces AuthContext as the source of truth for the logged-in user + token.
 * `localStorage['user']` stays the persistence medium (the openapi-fetch auth
 * middleware in api/client.ts reads the token from the store, falling back to
 * localStorage). `context/AuthContext.tsx` is now a thin shim over this store so
 * existing `useAuth()` consumers + the <AuthProvider> in App.tsx keep working
 * until 5.5 deletes the shim.
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
  user: null,
  loading: true,
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
