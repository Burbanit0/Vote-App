import { useTranslation } from 'react-i18next';
import { SimulationCompareResult } from '../../types';

// Static keys — used as fallback IDs and in non-React contexts (report generation, CSV export)
const METHOD_KEYS = [
  'plurality',
  'two_round',
  'borda',
  'approval',
  'irv',
  'coombs',
  'bucklin',
  'minimax',
  'schulze',
  'kemeny_young',
  'condorcet',
  'positional_score',
  'simple_score',
  'star_voting',
  'median_voting',
  'mean_median_hybrid',
  'variance_based',
  'quadratic',
] as const;

// Fallback labels used in non-React contexts (report HTML, CSV, buildConclusion)
const METHOD_LABELS: Record<string, string> = {
  plurality: 'Plurality',
  two_round: 'Two-Round',
  borda: 'Borda',
  approval: 'Approval',
  irv: 'IRV',
  coombs: "Coombs'",
  bucklin: 'Bucklin',
  minimax: 'Minimax',
  schulze: 'Schulze',
  kemeny_young: 'Kemeny-Young',
  condorcet: 'Condorcet',
  positional_score: 'Positional score',
  simple_score: 'Simple score',
  star_voting: 'STAR',
  median_voting: 'Median score',
  mean_median_hybrid: 'Mean-Median',
  variance_based: 'Variance-based',
  quadratic: 'Quadratic Vote',
};

export function useMethodLabels(): Record<string, string> {
  const { t } = useTranslation();
  return Object.fromEntries(
    METHOD_KEYS.map((k) => [k, t(`methods.${k}.label`, { defaultValue: METHOD_LABELS[k] })])
  );
}

export function mostCommonWinner(
  results: SimulationCompareResult[],
  method: string
): string | null {
  const winners = results.map((r) => r.methods[method]?.winner).filter((w): w is string => !!w);
  if (!winners.length) return null;
  const counts = winners.reduce(
    (acc, w) => ({ ...acc, [w]: (acc[w] ?? 0) + 1 }),
    {} as Record<string, number>
  );
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0];
}
