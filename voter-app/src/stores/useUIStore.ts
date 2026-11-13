/**
 * useUIStore — UI-preferences slice (Phase 5.4).
 *
 * Consolidates two small UI contexts:
 *   - theme            (light/dark, persisted as votelab_theme, sets data-bs-theme)
 *   - plainLanguage    (persisted as votelab_plain)
 */
import { create } from 'zustand';

// ── Types ───────────────────────────────────────────────────────────────────

export type Theme = 'light' | 'dark';

interface UIState {
  /** Re-read theme/plain-language from localStorage (mount). */
  hydrate: () => void;
  // Theme
  theme: Theme;
  toggleTheme: () => void;
  // Plain-language mode — swaps technical method labels for plain ones. Default
  // off: the app teaches the real vocabulary; this is an on-demand assist.
  plainLanguage: boolean;
  setPlainLanguage: (value: boolean) => void;
}

// ── Storage helpers ─────────────────────────────────────────────────────────

function initialTheme(): Theme {
  if (typeof window === 'undefined') return 'light';
  return (localStorage.getItem('votelab_theme') as Theme) ?? 'light';
}

function initialPlain(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem('votelab_plain') === 'true';
}

function applyTheme(theme: Theme) {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-bs-theme', theme);
  }
}

// ── Store ─────────────────────────────────────────────────────────────────

export const useUIStore = create<UIState>((set, get) => ({
  hydrate: () => {
    const theme = initialTheme();
    applyTheme(theme);
    set({ theme, plainLanguage: initialPlain() });
  },

  // ── Theme ──
  theme: initialTheme(),
  toggleTheme: () => {
    const next: Theme = get().theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('votelab_theme', next);
    applyTheme(next);
    set({ theme: next });
  },

  // ── Plain-language mode ──
  plainLanguage: initialPlain(),
  setPlainLanguage: (value) => {
    localStorage.setItem('votelab_plain', String(value));
    set({ plainLanguage: value });
  },
}));

/** Apply the persisted theme to <html> on app start. */
export function initUITheme(): void {
  applyTheme(useUIStore.getState().theme);
}

// ── Convenience hooks (former context APIs) ───────────────────────────────────
// Select fields individually — never return a fresh composite object from one
// selector (that defeats zustand's snapshot caching).

export function useTheme(): { theme: Theme; toggleTheme: () => void } {
  const theme = useUIStore((s) => s.theme);
  const toggleTheme = useUIStore((s) => s.toggleTheme);
  return { theme, toggleTheme };
}

export function usePlainLanguage(): {
  plainLanguage: boolean;
  setPlainLanguage: (v: boolean) => void;
} {
  const plainLanguage = useUIStore((s) => s.plainLanguage);
  const setPlainLanguage = useUIStore((s) => s.setPlainLanguage);
  return { plainLanguage, setPlainLanguage };
}
