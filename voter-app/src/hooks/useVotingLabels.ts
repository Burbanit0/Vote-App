import { useTranslation } from 'react-i18next';
import { RULE_LABELS, type Rule } from '../lib/playgroundVoting';
import { MANIP_COMPLEXITY } from '../lib/scorecard';
import { usePlainLanguage } from '../stores/useUIStore';

// useVotingLabels — translated versions of the shared label maps (rule names,
// structure names, manipulation-complexity flags, scorecard axis meta). The raw
// consts in lib/ keep the keys/structure (and the `hard` boolean); the display
// strings come from the `playground` i18n namespace so they switch with language.

const LEADER_AXIS_KEYS = [
  'condorcet_efficiency',
  'strategic_resistance',
  'welfare',
  'majority_satisfaction',
  'simplicity',
  'stability',
] as const;

const PARLIAMENT_AXIS_KEYS = [
  'proportionality',
  'pluralism',
  'effective_votes',
  'minority_representation',
  'governability',
  'gerrymander_resistance',
] as const;

const STRUCTURE_KEYS = ['pr', 'fptp', 'mmp'] as const;

export interface AxisMeta {
  key: string;
  label: string;
  hint: string;
}

export function useVotingLabels() {
  const { t } = useTranslation('playground');
  const { plainLanguage } = usePlainLanguage();

  // Plain-language mode swaps the technical method name for a plain one, but only
  // where a plain label exists (bounded set) — otherwise it keeps the real term.
  const ruleLabels = Object.fromEntries(
    (Object.keys(RULE_LABELS) as Rule[]).map((r) => [
      r,
      plainLanguage ? t(`rulesPlain.${r}`, { defaultValue: t(`rules.${r}`) }) : t(`rules.${r}`),
    ])
  ) as Record<Rule, string>;

  const structureLabels = Object.fromEntries(
    STRUCTURE_KEYS.map((s) => [s, t(`structures.${s}`)])
  ) as Record<string, string>;

  const manipComplexity = Object.fromEntries(
    (Object.keys(MANIP_COMPLEXITY) as Rule[]).map((r) => [
      r,
      { hard: MANIP_COMPLEXITY[r].hard, label: t(`manip.${r}.label`), ref: t(`manip.${r}.ref`) },
    ])
  ) as Record<Rule, { hard: boolean; label: string; ref: string }>;

  const axisMetaOf = (keys: readonly string[]): AxisMeta[] =>
    keys.map((key) => ({ key, label: t(`axes.${key}.label`), hint: t(`axes.${key}.hint`) }));

  return {
    ruleLabels,
    structureLabels,
    manipComplexity,
    leaderAxisMeta: axisMetaOf(LEADER_AXIS_KEYS),
    parliamentAxisMeta: axisMetaOf(PARLIAMENT_AXIS_KEYS),
  };
}
