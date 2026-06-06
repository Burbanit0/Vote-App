/**
 * Design tokens — single source of truth for colours, layout sizes and spacing.
 *
 * Goal: replace the 1 397 hardcoded hex codes and the per-page `maxWidth: N`
 * litter with named constants. Import from this file instead of typing
 * '#005CAB' or `maxWidth: 1400` directly in components.
 *
 * Convention:
 *   COLORS.party.Liberal   — semantic, what it represents
 *   COLORS.brand.primary   — the Vote Lab blue
 *   COLORS.neutral[600]    — greyscale (matches Bootstrap 5 grey scale)
 *   LAYOUT.pageFull        — for <Container style={{ maxWidth }}>
 */

export const COLORS = {
  // ── Brand ────────────────────────────────────────────────────────────────
  brand: {
    primary: '#005CAB', // Vote Lab blue
    secondary: '#C8590A', // Vote Lab orange (used for method-B comparisons)
    accent: '#7B2D8B', // violet (Condorcet, multi-winner, dual-mode tags)
  },

  // ── Party / candidate palette ────────────────────────────────────────────
  // Used consistently across the map, hémicycles, and result badges.
  party: {
    Green: '#007A33',
    Liberal: '#005CAB',
    Conservative: '#C8590A',
    Independent: '#6c757d',
  } as Record<string, string>,

  // ── Status (matches Bootstrap variants) ──────────────────────────────────
  status: {
    success: '#198754',
    danger: '#dc3545',
    warning: '#ffc107',
    info: '#0dcaf0',
  },

  // ── Neutral / greyscale (Bootstrap 5) ────────────────────────────────────
  neutral: {
    50: '#f8f9fa',
    100: '#e9ecef',
    200: '#dee2e6',
    300: '#ced4da',
    400: '#adb5bd',
    500: '#6c757d',
    600: '#6c757d',
    700: '#495057',
    800: '#343a40',
    900: '#212529',
  },

  // ── Common aliases (Bootstrap convention) ────────────────────────────────
  primary: '#0d6efd', // Bootstrap primary (subtly different from brand)
  white: '#ffffff',
  black: '#000000',
} as const;

/**
 * Page max widths — pick one of these instead of typing a literal pixel value.
 *   pageNarrow  — forms, quiz, OAuth callbacks
 *   pageMedium  — articles, theory pages, API docs
 *   pageWide    — dashboards, scenario gallery
 *   pageFull    — Lab, full-screen simulators
 */
export const LAYOUT = {
  pageNarrow: 680,
  pageMedium: 960,
  pageWide: 1200,
  pageFull: 1400,
} as const;

export type LayoutVariant = keyof typeof LAYOUT;

/**
 * Spacing scale (multiples of 4). Mostly informational — most spacing is done
 * via Bootstrap classes (m-2, gap-3, py-4). Use these when you need an
 * inline style for a precise pixel value.
 */
export const SPACING = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

/**
 * Helper: party colour with a safe fallback for unknown party names.
 *   partyColor('Liberal')        -> '#005CAB'
 *   partyColor('SomeNewParty')   -> '#6c757d'   (Independent)
 */
export function partyColor(party: string | null | undefined): string {
  return COLORS.party[party ?? 'Independent'] ?? COLORS.party.Independent;
}
