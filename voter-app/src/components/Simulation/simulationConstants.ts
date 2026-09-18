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

/**
 * The engine's rules, in the `playground` namespace. It names 29 of them, which
 * is where the ones METHOD_KEYS never listed come from -- see below.
 */
const PLAYGROUND_RULE_KEYS = [
  'copeland',
  'nanson',
  'baldwin',
  'ranked_pairs',
  'black',
  'anti_plurality',
  'dowdall',
  'raynaud',
  'benham',
  'river',
  'smith_irv',
  'split_cycle',
  'cumulative',
  'maximin',
  'nash',
  'majority_judgment',
  'evaluative',
  'random_ballot',
] as const;

/**
 * Every method's label, translated.
 *
 * METHOD_KEYS is the set the simulation surfaces *used* to receive, back when
 * /monte-carlo and /campaign-sensitivity answered 14 rules. The engine reports
 * 34, so consumers doing `METHOD_LABELS[m] ?? m` were falling through to the
 * raw slug -- `smith_irv`, `anti_plurality` -- in a French UI.
 *
 * The 18 extra names already existed, one namespace over: `playground`'s `rules`
 * map names 29 rules. Reusing them beats writing a second set of translations
 * that would then have to be kept in step.
 */
export function useMethodLabels(): Record<string, string> {
  const { t } = useTranslation();
  return {
    ...Object.fromEntries(PLAYGROUND_RULE_KEYS.map((k) => [k, t(`playground:rules.${k}`)])),
    // METHOD_KEYS last: where a rule is named in both namespaces, the
    // simulation surfaces' own wording wins.
    ...Object.fromEntries(METHOD_KEYS.map((k) => [k, t(`methods.${k}.label`)])),
  };
}
