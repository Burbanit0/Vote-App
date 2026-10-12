import type { Rule } from '../lib/playgroundVoting';

// Method families for visual grouping in the matrix and the Bilan. Kept apart from
// methodCriteria.ts so the playground does not load the criteria registry for them.
export type MethodFamily = 'majoritarian' | 'ordinal' | 'condorcet' | 'cardinal';

export const METHOD_FAMILY: Record<Rule, MethodFamily> = {
  plurality: 'majoritarian',
  two_round: 'majoritarian',
  irv: 'ordinal',
  borda: 'ordinal',
  bucklin: 'ordinal',
  coombs: 'ordinal',
  nanson: 'ordinal',
  baldwin: 'ordinal',
  condorcet: 'condorcet',
  minimax: 'condorcet',
  schulze: 'condorcet',
  ranked_pairs: 'condorcet',
  approval: 'cardinal',
  score: 'cardinal',
  star: 'cardinal',
  majority_judgment: 'cardinal',
  random_ballot: 'cardinal',
  anti_plurality: 'majoritarian',
  dowdall: 'ordinal',
  black: 'condorcet',
  smith_irv: 'condorcet',
  split_cycle: 'condorcet',
  kemeny: 'condorcet',
  cumulative: 'cardinal',
  maximin: 'cardinal',
  benham: 'condorcet',
  river: 'condorcet',
  nash: 'cardinal',
  raynaud: 'condorcet',
};

export const FAMILY_ORDER: MethodFamily[] = ['majoritarian', 'ordinal', 'condorcet', 'cardinal'];
