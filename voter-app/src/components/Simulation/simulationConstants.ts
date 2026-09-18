import { useTranslation } from 'react-i18next';

// The methods the simulation surfaces report on, in display order.
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

/** Every method's label, translated. Both locales carry all 18 keys (tsc
 *  enforces the EN/FR mirror), so there is no English fallback map to keep in
 *  step -- there used to be one, listing the same 18 names a second time. */
export function useMethodLabels(): Record<string, string> {
  const { t } = useTranslation();
  return Object.fromEntries(METHOD_KEYS.map((k) => [k, t(`methods.${k}.label`)]));
}
