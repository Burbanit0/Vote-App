// ballotLanguages.ts — one opinion, five ballot languages.
//
// A voter's opinion is an affinity per candidate in [0,1] (intensity, not just
// order). A ballot LANGUAGE is how much of that opinion the paper is allowed to
// carry: a single name throws away everything but the argmax; a full ranking keeps
// the order but not the intensity; scores and points keep both.
//
// Two consequences drive the whole page:
//   1. The language decides which counting rules are computable at all — you cannot
//      find a Condorcet winner from ballots that only name one candidate.
//   2. For `approve`, `score` and `points`, "sincere" is UNDER-DETERMINED: where do
//      you cut, how much do you contrast, how do you spread? The voter must make a
//      tactical call before they have even voted. That is not a modelling gap — it
//      is the thing to show.

import type { Rule } from './playgroundVoting';

export type BallotLanguage = 'one' | 'rank' | 'approve' | 'score' | 'points';

export const BALLOT_LANGUAGES: BallotLanguage[] = ['one', 'rank', 'approve', 'score', 'points'];

/** A ballot the engine can count: ranks always, scores for cardinal languages. */
export interface Ballot {
  rank: number[];
  score?: number[];
}

/** The knobs that make "sincere" under-determined. Defaults = the sincere reading. */
export interface BallotOptions {
  /** `approve`: how many candidates you tick. */
  approveK?: number;
  /** `score`: number of grades (1..levels). */
  levels?: number;
  /** `score`: 1 = faithful to your affinities, >1 = exaggerated toward the top. */
  contrast?: number;
  /** `points`: 1 = spread in proportion, >1 = concentrated on your favourite. */
  concentration?: number;
}

/**
 * The rules each language makes computable. A richer ballot subsumes a poorer one:
 * a full ranking unlocks every ordinal rule, a single name unlocks almost nothing.
 * `two_round` is deliberately absent from `one`: a runoff needs a SECOND ballot, not
 * more information in this one.
 */
export const RULES_FOR: Record<BallotLanguage, Rule[]> = {
  one: ['plurality'],
  rank: [
    'plurality',
    'two_round',
    'irv',
    'coombs',
    'borda',
    'bucklin',
    'nanson',
    'baldwin',
    'condorcet',
    'minimax',
    'schulze',
    'ranked_pairs',
  ],
  approve: ['approval'],
  score: ['score', 'star', 'majority_judgment'],
  points: ['cumulative'],
};

const clamp = (x: number, lo: number, hi: number): number => Math.min(hi, Math.max(lo, x));

/** Candidate indices best→worst. Ties break by index so the model stays deterministic. */
export function orderOf(affinity: number[]): number[] {
  return affinity.map((_, i) => i).sort((a, b) => affinity[b] - affinity[a] || a - b);
}

/** Translate ONE opinion into a ballot in the given language. */
export function ballotFrom(
  affinity: number[],
  lang: BallotLanguage,
  opt: BallotOptions = {}
): Ballot {
  const m = affinity.length;
  const rank = orderOf(affinity);

  switch (lang) {
    // Only the first name survives; the engine's plurality reads rank[0].
    case 'one':
    case 'rank':
      return { rank };

    case 'approve': {
      const k = clamp(Math.round(opt.approveK ?? Math.max(1, Math.floor(m / 2))), 1, m);
      const ticked = new Set(rank.slice(0, k));
      return { rank, score: affinity.map((_, i) => (ticked.has(i) ? 1 : 0)) };
    }

    case 'score': {
      const levels = opt.levels ?? 5;
      const contrast = opt.contrast ?? 1;
      // Grade on `levels` steps, then back to the engine's [0,1] scale.
      return {
        rank,
        score: affinity.map((x) => {
          const stretched = Math.pow(clamp(x, 0, 1), contrast);
          return Math.round(stretched * (levels - 1)) / (levels - 1);
        }),
      };
    }

    case 'points': {
      const gamma = opt.concentration ?? 1;
      const w = affinity.map((x) => Math.pow(clamp(x, 0, 1), gamma));
      const sum = w.reduce((a, x) => a + x, 0);
      // winCumulative renormalises anyway; an all-zero opinion spreads evenly.
      return { rank, score: sum > 0 ? w.map((x) => x / sum) : affinity.map(() => 1 / m) };
    }
  }
}

/** Grades actually written on a `score` ballot (1..levels) — for display. */
export function gradesOf(affinity: number[], opt: BallotOptions = {}): number[] {
  const levels = opt.levels ?? 5;
  const contrast = opt.contrast ?? 1;
  return affinity.map((x) => Math.round(Math.pow(clamp(x, 0, 1), contrast) * (levels - 1)) + 1);
}

/** Points actually written on a `points` ballot, out of `budget` — for display. */
export function pointsOf(affinity: number[], budget = 10, opt: BallotOptions = {}): number[] {
  return pipsFrom(ballotFrom(affinity, 'points', opt).score ?? [], budget);
}

/** Largest-remainder split of `budget` following `share` — the pips drawn on paper. */
export function pipsFrom(share: number[], budget = 10): number[] {
  const total = share.reduce((a, x) => a + x, 0);
  const raw = share.map((s) => (total > 0 ? s / total : 1 / share.length) * budget);
  // Largest-remainder so the displayed pips always sum to exactly `budget`.
  const floors = raw.map(Math.floor);
  let left = budget - floors.reduce((a, x) => a + x, 0);
  const order = raw
    .map((x, i) => ({ i, frac: x - Math.floor(x) }))
    .sort((a, b) => b.frac - a.frac || a.i - b.i);
  const out = floors.slice();
  for (const { i } of order) {
    if (left <= 0) break;
    out[i] += 1;
    left -= 1;
  }
  return out;
}

function permutations(arr: number[]): number[][] {
  if (arr.length <= 1) return [arr.slice()];
  const out: number[][] = [];
  for (let i = 0; i < arr.length; i++) {
    const rest = arr.slice(0, i).concat(arr.slice(i + 1));
    for (const p of permutations(rest)) out.push([arr[i], ...p]);
  }
  return out;
}

/**
 * Every ballot you could plausibly cast in this language — the search space for a
 * best response. Finite by construction on ordinal papers, and theory-backed where
 * the space would be infinite: on a `score` ballot the optimal single vote is always
 * min/max (an approval ballot in disguise), and on a `points` ballot splitting your
 * budget never beats going all in. The sincere ballot is not included; callers add
 * it as the baseline so ties resolve in favour of honesty.
 */
export function ballotSpace(affinity: number[], lang: BallotLanguage): Ballot[] {
  const m = affinity.length;
  const sincere = orderOf(affinity);
  const headed = (c: number): number[] => [c, ...sincere.filter((i) => i !== c)];
  const each = <T>(f: (c: number) => T): T[] => Array.from({ length: m }, (_, c) => f(c));

  switch (lang) {
    // Only rank[0] is read; the tail keeps your sincere order.
    case 'one':
      return each((c) => ({ rank: headed(c) }));

    case 'rank':
      // ponytail: exhaustive up to 6 candidates (720 orders). Beyond that, only the
      // "promote one candidate" ballots — the tactic anyone actually plays.
      return (m <= 6 ? permutations(sincere) : each(headed)).map((rank) => ({ rank }));

    case 'approve':
    case 'score': {
      const out: Ballot[] = [];
      for (let mask = 0; mask < 1 << m; mask++) {
        out.push({ rank: sincere, score: each((c) => ((mask >> c) & 1 ? 1 : 0)) });
      }
      return out;
    }

    case 'points':
      return each((c) => ({ rank: headed(c), score: each((j) => (j === c ? 1 : 0)) }));
  }
}

/**
 * Every voter's ballot in one language. The electorate votes SINCERELY (default
 * options) — only the reader's own ballot carries their tactical choices, so the
 * comparison isolates what the language does.
 */
export function electorateBallots(
  affinities: number[][],
  lang: BallotLanguage
): { ranks: number[][]; scores: number[][] } {
  const ranks: number[][] = [];
  const scores: number[][] = [];
  for (const a of affinities) {
    const b = ballotFrom(a, lang);
    ranks.push(b.rank);
    scores.push(b.score ?? a);
  }
  return { ranks, scores };
}
