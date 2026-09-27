/**
 * Candidate colour palette — WCAG 2.1 AA against a light ground (≥ 4.5:1 on
 * #ffffff), used when colouring candidate-specific marks: winner badges,
 * scatter points, per-candidate series.
 *
 * This file used to carry a second, parallel system: CHART_COLORS_LIGHT/DARK,
 * six named metric colours in two variants, a dark candidate palette and four
 * voter colours — thirteen exports whose contrast ratios were computed against
 * Bootstrap's dark background (#212529). The app moved to Tailwind v4 with CSS
 * custom properties, which theme themselves, so nothing had imported any of it
 * for a long time. Only this one palette is still used (7 files).
 *
 * If per-theme chart colours are ever needed again, they belong in the Tailwind
 * theme as CSS variables, not as a hand-maintained hex table that has to be
 * switched on `theme === 'dark'` at every call site.
 */
export const CANDIDATE_COLORS_LIGHT: string[] = [
  '#1a56cc', // blue    — 6.1:1
  '#b35c00', // orange  — 4.6:1
  '#b71c1c', // red     — 8.2:1
  '#006957', // teal    — 5.4:1
  '#1b5e20', // green   — 9.6:1
  '#544200', // amber   — 9.1:1
];
