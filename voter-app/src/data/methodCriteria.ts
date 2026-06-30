import type { Rule } from '../lib/playgroundVoting';

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

// Static satisfaction table — mathematical proofs, not empirical.
// Sources: Arrow (1951), Gibbard (1973/1977), Young (1974), Tideman (1987),
// Brandt et al. "Handbook of Computational Social Choice" (2016).
// 'conditional' = holds under restricted conditions or is debated in the literature.
export const METHOD_CRITERIA: Record<Rule, MethodCriteriaRow> = {
  plurality: {
    condorcet_winner: 'no',
    condorcet_loser: 'no',
    majority: 'yes',
    monotonicity: 'yes',
    iia: 'no',
    strategy_proof: 'no',
    participation: 'yes',
    reversal: 'no',
  },
  two_round: {
    condorcet_winner: 'no',
    condorcet_loser: 'no',
    majority: 'yes',
    monotonicity: 'no',
    iia: 'no',
    strategy_proof: 'no',
    participation: 'no',
    reversal: 'no',
  },
  irv: {
    condorcet_winner: 'no',
    condorcet_loser: 'yes',
    majority: 'yes',
    monotonicity: 'no',
    iia: 'no',
    strategy_proof: 'no',
    participation: 'no',
    reversal: 'no',
  },
  borda: {
    condorcet_winner: 'no',
    condorcet_loser: 'conditional',
    majority: 'no',
    monotonicity: 'yes',
    iia: 'no',
    strategy_proof: 'no',
    participation: 'yes',
    reversal: 'yes',
  },
  approval: {
    condorcet_winner: 'no',
    condorcet_loser: 'no',
    majority: 'conditional',
    monotonicity: 'yes',
    iia: 'no',
    strategy_proof: 'conditional',
    participation: 'yes',
    reversal: 'no',
  },
  // Copeland's method
  condorcet: {
    condorcet_winner: 'yes',
    condorcet_loser: 'yes',
    majority: 'yes',
    monotonicity: 'yes',
    iia: 'no',
    strategy_proof: 'no',
    participation: 'yes',
    reversal: 'yes',
  },
  minimax: {
    condorcet_winner: 'yes',
    condorcet_loser: 'no',
    majority: 'yes',
    monotonicity: 'yes',
    iia: 'no',
    strategy_proof: 'no',
    participation: 'no',
    reversal: 'no',
  },
  schulze: {
    condorcet_winner: 'yes',
    condorcet_loser: 'yes',
    majority: 'yes',
    monotonicity: 'yes',
    iia: 'no',
    strategy_proof: 'no',
    participation: 'no',
    reversal: 'yes',
  },
  bucklin: {
    condorcet_winner: 'conditional',
    condorcet_loser: 'no',
    majority: 'yes',
    monotonicity: 'yes',
    iia: 'no',
    strategy_proof: 'no',
    participation: 'yes',
    reversal: 'no',
  },
  coombs: {
    condorcet_winner: 'no',
    condorcet_loser: 'yes',
    majority: 'yes',
    monotonicity: 'no',
    iia: 'no',
    strategy_proof: 'no',
    participation: 'no',
    reversal: 'no',
  },
  nanson: {
    condorcet_winner: 'yes',
    condorcet_loser: 'yes',
    majority: 'yes',
    monotonicity: 'no',
    iia: 'no',
    strategy_proof: 'no',
    participation: 'no',
    reversal: 'yes',
  },
  baldwin: {
    condorcet_winner: 'yes',
    condorcet_loser: 'yes',
    majority: 'yes',
    monotonicity: 'no',
    iia: 'no',
    strategy_proof: 'no',
    participation: 'no',
    reversal: 'yes',
  },
  ranked_pairs: {
    condorcet_winner: 'yes',
    condorcet_loser: 'yes',
    majority: 'yes',
    monotonicity: 'yes',
    iia: 'no',
    strategy_proof: 'no',
    participation: 'no',
    reversal: 'yes',
  },
  // ponytail: only strategy-proof deterministic rule (Gibbard 1977); IIA holds vacuously
  random_ballot: {
    condorcet_winner: 'no',
    condorcet_loser: 'no',
    majority: 'no',
    monotonicity: 'yes',
    iia: 'yes',
    strategy_proof: 'yes',
    participation: 'yes',
    reversal: 'yes',
  },
  star: {
    condorcet_winner: 'no',
    condorcet_loser: 'no',
    majority: 'yes',
    monotonicity: 'yes',
    iia: 'no',
    strategy_proof: 'conditional',
    participation: 'yes',
    reversal: 'no',
  },
  majority_judgment: {
    condorcet_winner: 'no',
    condorcet_loser: 'no',
    majority: 'yes',
    monotonicity: 'yes',
    iia: 'no',
    strategy_proof: 'conditional',
    participation: 'yes',
    reversal: 'yes',
  },
  score: {
    condorcet_winner: 'no',
    condorcet_loser: 'no',
    majority: 'no',
    monotonicity: 'yes',
    iia: 'no',
    strategy_proof: 'conditional',
    participation: 'yes',
    reversal: 'yes',
  },
};

// Method families for visual grouping in the matrix
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
};

export const FAMILY_ORDER: MethodFamily[] = ['majoritarian', 'ordinal', 'condorcet', 'cardinal'];
