import type { Rule } from '../lib/playgroundVoting';
import registry from './method_criteria.json';

export type Satisfaction = 'yes' | 'no' | 'conditional';

export type CriterionKey =
  | 'condorcet_winner'
  | 'condorcet_loser'
  | 'majority'
  | 'monotonicity'
  | 'iia'
  | 'strategy_proof'
  | 'participation'
  | 'reversal';

export const CRITERION_KEYS: CriterionKey[] = [
  'condorcet_winner',
  'condorcet_loser',
  'majority',
  'monotonicity',
  'iia',
  'strategy_proof',
  'participation',
  'reversal',
];

export type MethodCriteriaRow = Record<CriterionKey, Satisfaction>;

// The verdicts live in method_criteria.json, one entry per (rule, criterion) with its basis
// (engine-tested, literature or variant), its source and a note (PLAN_BEYOND_CI W1.2). This
// file narrows them to the types the UI uses and refuses a missing or unknown verdict.
// 'conditional' = holds under restricted conditions or is debated in the literature.
const VERDICTS: readonly Satisfaction[] = ['yes', 'no', 'conditional'];

export type CriterionBasis = 'engine-tested' | 'literature' | 'variant';
export interface CriterionEntry {
  verdict: Satisfaction;
  basis: CriterionBasis;
  source: string | null;
  note?: string;
}

function loadVerdicts(): Record<Rule, MethodCriteriaRow> {
  if (registry.criteria.join() !== CRITERION_KEYS.join()) {
    throw new Error(
      `method_criteria.json: criteria ${registry.criteria.join()} are not ${CRITERION_KEYS.join()}`
    );
  }
  const out = {} as Record<Rule, MethodCriteriaRow>;
  for (const [rule, cells] of Object.entries(registry.rules)) {
    const unknown = Object.keys(cells).filter(
      (key) => !CRITERION_KEYS.includes(key as CriterionKey)
    );
    if (unknown.length)
      throw new Error(`method_criteria.json: ${rule} has unknown criteria ${unknown.join()}`);
    const row = {} as MethodCriteriaRow;
    for (const key of CRITERION_KEYS) {
      const verdict = (cells as Record<string, { verdict?: string }>)[key]?.verdict;
      if (!VERDICTS.includes(verdict as Satisfaction)) {
        throw new Error(`method_criteria.json: ${rule}.${key} has verdict ${String(verdict)}`);
      }
      row[key] = verdict as Satisfaction;
    }
    out[rule as Rule] = row;
  }
  return out;
}

export const METHOD_CRITERIA: Record<Rule, MethodCriteriaRow> = loadVerdicts();
export const METHOD_CRITERIA_ENTRIES = registry.rules as unknown as Record<
  Rule,
  Record<CriterionKey, CriterionEntry>
>;
