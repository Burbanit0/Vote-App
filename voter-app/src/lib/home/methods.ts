import type { Rule } from '../playgroundVoting';
import { TALLY, type RuleId } from './scenario';

// Who the homepage's 100 voters elect under each method the app counts with a fixed
// winner (scorecard's LEADER_RULES, the lottery left out), in the instrument's order.
// Written down rather than computed, so the homepage doesn't carry the voting engine:
// methods.test.ts recomputes every one with the engine and fails if they disagree.
// Approval is the homepage's own approval ballot (everyone within APPROVAL_RADIUS), the
// one its tally sheet and its count show; the engine draws its approvals another way.

const [ALICE, CAROL, BOB] = [0, 1, 2];

export const METHOD_WINNERS: { rule: Rule; winner: number }[] = [
  { rule: 'plurality', winner: BOB },
  { rule: 'two_round', winner: ALICE },
  { rule: 'irv', winner: ALICE },
  { rule: 'borda', winner: CAROL },
  { rule: 'approval', winner: TALLY.approval.winner },
  { rule: 'score', winner: CAROL },
  { rule: 'star', winner: CAROL },
  { rule: 'majority_judgment', winner: CAROL },
  { rule: 'cumulative', winner: CAROL },
  { rule: 'maximin', winner: CAROL },
  { rule: 'nash', winner: CAROL },
  { rule: 'bucklin', winner: CAROL },
  { rule: 'coombs', winner: CAROL },
  { rule: 'condorcet', winner: CAROL },
  { rule: 'minimax', winner: CAROL },
  { rule: 'schulze', winner: CAROL },
  { rule: 'nanson', winner: CAROL },
  { rule: 'baldwin', winner: CAROL },
  { rule: 'ranked_pairs', winner: CAROL },
  { rule: 'kemeny', winner: CAROL },
  { rule: 'black', winner: CAROL },
  { rule: 'anti_plurality', winner: CAROL },
  { rule: 'dowdall', winner: BOB },
  { rule: 'raynaud', winner: CAROL },
  { rule: 'benham', winner: CAROL },
  { rule: 'river', winner: CAROL },
  { rule: 'smith_irv', winner: CAROL },
  { rule: 'split_cycle', winner: CAROL },
];

/** The hero's three rules, as the engine names them. */
export const ENGINE_RULE: Record<RuleId, Rule> = {
  plurality: 'plurality',
  runoff: 'two_round',
  approval: 'approval',
};

/** How many methods elect each candidate. */
export const winsByCandidate = (): number[] =>
  METHOD_WINNERS.reduce((n, m) => (n[m.winner]++, n), [0, 0, 0]);
