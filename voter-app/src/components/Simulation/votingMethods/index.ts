/**
 * Per-method visualisations for SimulationPage.
 *
 * This sub-folder splits the formerly-1684-line VotingMethodVisualizations.tsx
 * into one file per voting method, so each is independently reviewable,
 * testable, and easier to extend.
 *
 * Migration status (1 PR per visualisation to keep diffs reviewable):
 *   - ✅ Plurality
 *   - ✅ Borda
 *   - ✅ IRV
 *   - ⏳ Approval, Condorcet, TwoRound, Coombs, Score, Bucklin, Minimax,
 *        Schulze, KemenyYoung (still in VotingMethodVisualizations.tsx)
 */
export { default as PluralityVisualization } from './PluralityVisualization';
export { default as BordaVisualization } from './BordaVisualization';
export { default as IRVVisualization } from './IRVVisualization';
export type { VotingMethodVisualizationProps } from './types';
export { VIZ_COLORS } from './types';
