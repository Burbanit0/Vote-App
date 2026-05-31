/**
 * ThemeContext — compatibility shim over useUIStore (Phase 5.4).
 * Theme state now lives in stores/useUIStore; this keeps useTheme()/ThemeProvider
 * working until 5.5 deletes the shim.
 */
import React, { useEffect } from 'react';
import { useUIStore, type Theme } from '../stores/useUIStore';

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
}

export function useTheme(): ThemeContextValue {
  const theme = useUIStore((s) => s.theme);
  const toggleTheme = useUIStore((s) => s.toggleTheme);
  return { theme, toggleTheme };
}

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const hydrate = useUIStore((s) => s.hydrate);
  // Re-read persisted prefs + apply theme to <html> on mount.
  useEffect(() => { hydrate(); }, [hydrate]);
  return <>{children}</>;
};
