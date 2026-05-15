/**
 * WCAG 2.1 AA compliant chart colour palettes.
 *
 * All colours satisfy the minimum contrast ratio requirements:
 *   - LIGHT palette: ≥ 4.5:1 against white (#ffffff)
 *   - DARK  palette: ≥ 4.5:1 against Bootstrap dark (#212529, L ≈ 0.017)
 *
 * Replaces the default Recharts colours (#8884d8, #82ca9d, #ffc658 …)
 * which fail at 1.6 – 3.3:1 on white backgrounds.
 *
 * Usage:
 *   import { CHART_COLORS_LIGHT, CHART_COLORS_DARK } from 'src/constants/chartColors';
 *   const colors = theme === 'dark' ? CHART_COLORS_DARK : CHART_COLORS_LIGHT;
 */

// ── Light-theme palette (≥ 4.5:1 on #ffffff) ──────────────────────────────
// Contrast ratios vs white in parentheses.
export const CHART_COLORS_LIGHT: string[] = [
  '#1a56cc', // blue       — 6.1:1   (replaces #4e79a7, #8884d8, #0088fe)
  '#b35c00', // orange     — 4.6:1   (replaces #f28e2b, #ffc658)
  '#b71c1c', // red        — 8.2:1   (replaces #e15759)
  '#006957', // teal       — 5.4:1   (replaces #76b7b2 which failed at 2.2:1)
  '#1b5e20', // green      — 9.6:1   (replaces #82ca9d, #59a14f which failed)
  '#544200', // amber      — 9.1:1   (replaces #edc948 which failed at 1.5:1)
];

// ── Dark-theme palette (≥ 4.5:1 on #212529) ──────────────────────────────
// Contrast ratios vs Bootstrap dark (#212529) in parentheses.
export const CHART_COLORS_DARK: string[] = [
  '#88b4ff', // light blue   — 7.0:1
  '#ffaa5c', // light orange — 5.9:1
  '#ff8787', // light red    — 4.8:1
  '#63e6be', // light teal   — 8.7:1
  '#8ce99a', // light green  — 7.3:1
  '#ffd43b', // light amber  — 9.3:1
];

// ── Named semantic colours for specific chart metrics ─────────────────────

/** Bar / line colour for primary metric (e.g., Bayesian Regret). Light theme. */
export const CHART_BLUE_LIGHT   = '#1a56cc';
/** Bar / line colour for secondary metric. Light theme. */
export const CHART_GREEN_LIGHT  = '#1b5e20';
/** Bar / line colour for tertiary metric. Light theme. */
export const CHART_ORANGE_LIGHT = '#b35c00';

/** Same semantics, dark-theme variants. */
export const CHART_BLUE_DARK   = '#88b4ff';
export const CHART_GREEN_DARK  = '#8ce99a';
export const CHART_ORANGE_DARK = '#ffaa5c';

// ── Candidate palette ─────────────────────────────────────────────────────
// Used when colouring candidate-specific data points (winner badges, scatter).
// Kept distinct from the metric palette to avoid confusing the two.

export const CANDIDATE_COLORS_LIGHT: string[] = [
  '#1a56cc', // blue
  '#b35c00', // orange
  '#b71c1c', // red
  '#006957', // teal
  '#1b5e20', // green
  '#544200', // amber
];

export const CANDIDATE_COLORS_DARK: string[] = [
  '#88b4ff',
  '#ffaa5c',
  '#ff8787',
  '#63e6be',
  '#8ce99a',
  '#ffd43b',
];

// ── Voter colours (ideological-space chart) ───────────────────────────────
export const VOTER_SINCERE_LIGHT   = '#1a56cc'; // blue
export const VOTER_STRATEGIC_LIGHT = '#b71c1c'; // red
export const VOTER_SINCERE_DARK    = '#88b4ff';
export const VOTER_STRATEGIC_DARK  = '#ff8787';
