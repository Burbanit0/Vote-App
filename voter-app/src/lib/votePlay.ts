// votePlay.ts — the fixed election behind "À vous de jouer".
//
// A deliberately SMALL and CLOSE election (41 voters), because the page's promise
// only holds at a scale where one ballot can matter. The configuration is not
// decorative: it is a textbook centre-squeeze, verified against the engine —
//
//   first choices   Alice 16 · Bruno 15 · Carla 3 · Diane 7
//   a single name → Alice        (the largest bloc)
//   an order      → Bruno (two-round, IRV) or Carla (Borda, Condorcet, Schulze…)
//   notes/points  → Carla        (everyone's acceptable second)
//
// So the SAME electorate elects three different people depending only on how much
// of each voter's opinion the ballot was allowed to carry. That is the page.

import {
  sampleVoters,
  computeScores,
  ruleWinnerFromRanks,
  type NamedPt,
  type Rule,
} from './playgroundVoting';
import {
  ballotFrom,
  electorateBallots,
  type BallotLanguage,
  type BallotOptions,
} from './ballotLanguages';

export const CANDIDATES: NamedPt[] = [
  { name: 'Alice', x: -0.6, y: 0.0 },
  { name: 'Bruno', x: 0.6, y: 0.1 },
  { name: 'Carla', x: 0.0, y: 0.05 },
  { name: 'Diane', x: -0.15, y: 0.5 },
];

export const VOTER_COUNT = 41;
const SEED = 17;
const IDEOLOGY = 'polarized';

/** The other voters' opinions — affinity in [0,1] per candidate. */
export const ELECTORATE: number[][] = computeScores(
  sampleVoters(VOTER_COUNT, SEED, IDEOLOGY, 2),
  CANDIDATES
);

/**
 * Your starting opinion: a centre-left voter who finds Carla best and Bruno
 * unacceptable. Chosen so the lesson bites — under a single-name ballot your voice
 * cannot say most of this.
 */
export const DEFAULT_YOU: number[] = [0.72, 0.05, 0.95, 0.4];

/** Winner index per rule, with your ballot added to the electorate's. */
export function winnersFor(
  you: number[],
  lang: BallotLanguage,
  rules: Rule[],
  opt: BallotOptions = {}
): Record<string, number> {
  const base = electorateBallots(ELECTORATE, lang);
  const mine = ballotFrom(you, lang, opt);
  const ranks = [...base.ranks, mine.rank];
  const scores = [...base.scores, mine.score ?? you];
  const out: Record<string, number> = {};
  for (const rule of rules) {
    out[rule] = ruleWinnerFromRanks(ranks, CANDIDATES.length, rule, scores);
  }
  return out;
}

/** Your rank of a candidate: 1 = your favourite. 0 when the index is unknown. */
export function yourRankOf(you: number[], candidate: number): number {
  if (candidate < 0) return 0;
  const order = you.map((_, i) => i).sort((a, b) => you[b] - you[a] || a - b);
  return order.indexOf(candidate) + 1;
}
