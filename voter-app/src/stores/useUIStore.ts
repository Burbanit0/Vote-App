/**
 * useUIStore — UI-preferences slice (Phase 5.4).
 *
 * Consolidates two small UI contexts:
 *   - theme            (light/dark, persisted as votelab_theme, sets data-bs-theme)
 *   - expertMode       (persisted as votelab_expert)
 */
import { create } from 'zustand';

// ── Types ───────────────────────────────────────────────────────────────────

export type Theme = 'light' | 'dark';

interface UIState {
  /** Re-read theme/expert from localStorage (mount). */
  hydrate: () => void;
  // Theme
  theme: Theme;
  toggleTheme: () => void;
  // Expert mode
  expertMode: boolean;
  setExpertMode: (value: boolean) => void;
}

// ── Storage helpers ─────────────────────────────────────────────────────────

function initialTheme(): Theme {
  if (typeof window === 'undefined') return 'light';
  return (localStorage.getItem('votelab_theme') as Theme) ?? 'light';
}

function initialExpert(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem('votelab_expert') === 'true';
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
    set({ theme, expertMode: initialExpert() });
  },

  // ── Theme ──
  theme: initialTheme(),
  toggleTheme: () => {
    const next: Theme = get().theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('votelab_theme', next);
    applyTheme(next);
    set({ theme: next });
  },

  // ── Expert mode ──
  expertMode: initialExpert(),
  setExpertMode: (value) => {
    localStorage.setItem('votelab_expert', String(value));
    set({ expertMode: value });
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

export function useExpertMode(): { expertMode: boolean; setExpertMode: (v: boolean) => void } {
  const expertMode = useUIStore((s) => s.expertMode);
  const setExpertMode = useUIStore((s) => s.setExpertMode);
  return { expertMode, setExpertMode };
}
