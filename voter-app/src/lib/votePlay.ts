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
  ballotSpace,
  electorateBallots,
  type Ballot,
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
 * Base electorate's first-choice tally (count per candidate) — the shape of the
 * crowd you are joining. Reveals the centre-squeeze at a glance: the compromise
 * has almost no first-choice support, yet wins the moment a second choice can be
 * expressed. Alice 16 · Bruno 15 · Carla 3 · Diane 7.
 */
export const ELECTORATE_FIRST_CHOICE: number[] = (() => {
  const counts = CANDIDATES.map(() => 0);
  for (const a of ELECTORATE) {
    let top = 0;
    for (let i = 1; i < a.length; i++) if (a[i] > a[top]) top = i;
    counts[top] += 1;
  }
  return counts;
})();

/**
 * Your starting opinion: a centre-left voter who finds Carla best and Bruno
 * unacceptable. Chosen so the lesson bites — under a single-name ballot your voice
 * cannot say most of this.
 */
export const DEFAULT_YOU: number[] = [0.72, 0.05, 0.95, 0.4];

// The electorate's ballots depend only on the language, and the page recomputes on
// every slider tick — translate each language once.
const BASE = new Map<BallotLanguage, { ranks: number[][]; scores: number[][] }>();
function base(lang: BallotLanguage): { ranks: number[][]; scores: number[][] } {
  let b = BASE.get(lang);
  if (!b) BASE.set(lang, (b = electorateBallots(ELECTORATE, lang)));
  return b;
}

/**
 * Winner under `rule` when `copies` voters cast `mine` — or nobody does (`null`, or
 * `copies` of 0). `copies` is you plus everyone who shares your opinion: a single
 * ballot is almost never pivotal in a 41-voter election, so the honest question is
 * not "did my vote decide it" but "how many of us does it take". Same convention as
 * the playground's sincerity probe, where strategic pressure is also collective.
 */
export function winnerWith(
  mine: Ballot | null,
  lang: BallotLanguage,
  rule: Rule,
  copies = 1
): number {
  const b = base(lang);
  const ranks = b.ranks.slice();
  const scores = b.scores.slice();
  if (mine) {
    const score = mine.score ?? mine.rank.map(() => 0);
    for (let i = 0; i < copies; i++) {
      ranks.push(mine.rank);
      scores.push(score);
    }
  }
  return ruleWinnerFromRanks(ranks, CANDIDATES.length, rule, scores);
}

/** How large your camp can get before it stops being a minority worth measuring. */
export const MAX_BLOC = 15;

/** Winner index per rule, with your ballot added to the electorate's. */
export function winnersFor(
  you: number[],
  lang: BallotLanguage,
  rules: Rule[],
  opt: BallotOptions = {}
): Record<string, number> {
  const mine = ballotFrom(you, lang, opt);
  const out: Record<string, number> = {};
  for (const rule of rules) out[rule] = winnerWith(mine, lang, rule);
  return out;
}

export type Posture = 'sincere' | 'strategic' | 'abstain';

export interface BestResponse {
  /** The ballot that serves you best, everyone else voting sincerely. */
  ballot: Ballot;
  winner: number;
  /** True when your sincere ballot already is the best you can do — the method
   *  gives you no reason to lie, which is the whole point of measuring this. */
  sincereIsBest: boolean;
}

/**
 * Your best response under one rule: the ballot in this language that elects the
 * candidate you like most, holding the rest of the electorate sincere. Exhaustive
 * over `ballotSpace`, so the answer is exact, not a heuristic. Ties go to sincerity —
 * a lie has to strictly pay before we call it a temptation.
 */
export function bestResponse(
  you: number[],
  lang: BallotLanguage,
  rule: Rule,
  opt: BallotOptions = {},
  copies = 1
): BestResponse {
  const sincere = ballotFrom(you, lang, opt);
  const util = (w: number): number => (w >= 0 ? you[w] : -Infinity);
  let best: BestResponse = {
    ballot: sincere,
    winner: winnerWith(sincere, lang, rule, copies),
    sincereIsBest: true,
  };
  // An undecided sincere outcome is not a temptation to escape: any ballot "beats"
  // no-winner, which would flag a lie as paying when nothing was actually at stake.
  if (best.winner < 0) return best;
  for (const ballot of ballotSpace(you, lang)) {
    const winner = winnerWith(ballot, lang, rule, copies);
    if (util(winner) > util(best.winner) + 1e-9) best = { ballot, winner, sincereIsBest: false };
  }
  return best;
}

export interface Pivot {
  /** Smallest camp that changes the winner just by turning out — 0 if none up to max. */
  toFlip: number;
  /** Smallest camp for which a tactical ballot beats an honest one — 0 if none. */
  toTempt: number;
}

// ponytail: no "how many to persuade" counter here on purpose. Converting the
// leader's voters to your ballot flips this race after only 2 — straight to Bruno,
// the candidate you rank LAST, because the runner-up is waiting. In a four-way race
// "a switch counts double" is not a usable number. It is exactly right on a two-way
// margin, which is where the page states it.

/**
 * How many voters like you it takes, under one rule. Scanned from 1 upward rather
 * than bisected on purpose: turnout is NOT monotone under every rule (IRV and the
 * two-round can elect someone you like less as your camp grows — the no-show
 * paradox), so the smallest camp that works is the only defensible answer.
 */
export function pivot(
  you: number[],
  lang: BallotLanguage,
  rule: Rule,
  opt: BallotOptions = {},
  max = MAX_BLOC
): Pivot {
  const sincere = ballotFrom(you, lang, opt);
  const none = winnerWith(null, lang, rule);
  const out: Pivot = { toFlip: 0, toTempt: 0 };
  for (let k = 1; k <= max; k++) {
    // A camp that only turns the race into a dead heat has not changed the winner —
    // the counter promises someone else elected, so it must deliver someone.
    if (!out.toFlip) {
      const w = winnerWith(sincere, lang, rule, k);
      if (w >= 0 && w !== none) out.toFlip = k;
    }
    if (!out.toTempt && !bestResponse(you, lang, rule, opt, k).sincereIsBest) out.toTempt = k;
    if (out.toFlip && out.toTempt) break;
  }
  return out;
}

/** Your rank of a candidate: 1 = your favourite. 0 when the index is unknown. */
export function yourRankOf(you: number[], candidate: number): number {
  if (candidate < 0) return 0;
  const order = you.map((_, i) => i).sort((a, b) => you[b] - you[a] || a - b);
  return order.indexOf(candidate) + 1;
}
