/**
 * AuthContext — compatibility shim over useAuthStore (Phase 5.4).
 *
 * The auth state now lives in `stores/useAuthStore`. This file keeps the
 * historical `useAuth()` hook + `<AuthProvider>` surface so the existing
 * consumers and App.tsx don't change; 5.5 will delete the shim and point
 * consumers at the store directly.
 */
import React, { useEffect, ReactNode } from 'react';
import { User } from '../types';
import { useAuthStore } from '../stores/useAuthStore';

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const hydrate = useAuthStore((s) => s.hydrate);
  // Re-read the persisted user on mount (mirrors the old provider effect).
  useEffect(() => { hydrate(); }, [hydrate]);
  return <>{children}</>;
};

export interface AuthContextValue {
  user: User | null;
  login: (userData: User) => void;
  logout: () => void;
  loading: boolean;
}

export const useAuth = (): AuthContextValue => {
  const user = useAuthStore((s) => s.user);
  const login = useAuthStore((s) => s.login);
  const logout = useAuthStore((s) => s.logout);
  const loading = useAuthStore((s) => s.loading);
  return { user, login, logout, loading };
};
