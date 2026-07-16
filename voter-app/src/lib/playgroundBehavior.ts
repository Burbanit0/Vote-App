// playgroundBehavior.ts — voter behaviour → welfare. The research question this
// app exists to illustrate: as voters stop voting sincerely, how much of the
// electorate's welfare does each method throw away?
//
// That measure is **Voter Satisfaction Efficiency** (VSE), popularised by Jameson
// Quinn (2017) and descended from Merrill's "efficiency" (1984) and Bayesian
// regret:
//
//     VSE = ( E[u(winner)] − E[u(random candidate)] )
//           ─────────────────────────────────────────
//           ( E[u(best candidate)] − E[u(random candidate)] )
//
//   1  → the method elects the utilitarian-best candidate every time;
//   0  → the method is no better than drawing a candidate out of a hat;
//   <0 → the method is actively worse than random.
//
// ── Stated conventions (nothing smuggled) ──────────────────────────────────
//
// · STRATEGIC VOTER = the repo's EXISTING Duverger compression probe
//   (`compressRanks`, scorecard.ts): read the two frontrunners off the sincere
//   first preferences — that IS the poll — then rank your preferred frontrunner
//   top and the other bottom (approval: bullet-vote the preferred frontrunner).
//   Reusing it keeps ONE strategic model in the client instead of a second one
//   that could silently drift from the manipulation lens / strategic_resistance
//   axis. It also makes "polls-aware" voting the same thing as strategic voting
//   here: the poll is the sincere first round.
//
// · UTILITY = `computeScores` (per-voter min-max normalised utility), the very
//   same scale the scorecard's welfare axis uses. Utility is always read off the
//   voter's TRUE preferences — a strategic voter lies on the ballot, never about
//   what they actually want. That distinction is the whole point of VSE.
//
// · This layer sits strictly ABOVE `ruleWinnerFromRanks`: it only ever chooses
//   which ballots to feed the rules. No rule logic is touched, so the
//   client⇄backend engine parity fixtures are unaffected by design.
//
// · NB — VSE is NOT the scorecard's `welfare` axis. Both are normalised Bayesian
//   regret, but welfare divides by (best − WORST) while VSE divides by
//   (best − RANDOM). Different stated baselines; we keep both rather than
//   silently redefining the existing axis.
//
// Pure + deterministic: same sampler and seed ⇒ same curves.

import {
  computeRanks,
  computeScores,
  ruleWinnerFromRanks,
  type NamedPt,
  type Pt,
  type Rule,
} from './playgroundVoting';
import { band, compressRanks, type Band } from './scorecard';

/** The methods plotted on the sweep. A curated, readable subset of LEADER_RULES —
 *  the families a reader can actually tell apart on one chart (one-round, runoff,
 *  elimination, positional, cardinal, Condorcet). A stated editorial choice. */
export const VSE_RULES: Rule[] = [
  'plurality',
  'two_round',
  'irv',
  'borda',
  'approval',
  'star',
  'condorcet',
];

/** Strategic shares sampled along the x-axis, 0 → 100 %. */
export const VSE_SHARES = [0, 0.2, 0.4, 0.6, 0.8, 1];

export interface VsePoint {
  /** Share of the electorate voting strategically, [0,1]. */
  share: number;
  vse: Band;
}
export interface VseCurve {
  rule: Rule;
  points: VsePoint[];
  /** VSE lost between an all-sincere and an all-strategic electorate (mean at
   *  share 0 − mean at share 1). Positive = the method degrades under strategy. */
  degradation: number;
}

// Golden-ratio low-discrepancy pick: voter i votes strategically when the
// sequence falls under `share`. Deterministic and, unlike a prefix, spread evenly
// across the array — a composed electorate emits voters bloc by bloc, so taking a
// prefix would make "20 % strategic" mean "the first community, all of it".
const PHI = 0.6180339887498949;
const isStrategic = (i: number, share: number): boolean => ((i + 1) * PHI) % 1 < share;

/**
 * Ballots for an electorate where `share` of voters vote strategically (Duverger
 * compression) and the rest sincerely. `ranks`/`scores` are the SINCERE ballots.
 */
export function ballotsAtShare(
  ranks: number[][],
  scores: number[][],
  m: number,
  share: number
): { ranks: number[][]; scores: number[][] } {
  if (share <= 0 || m < 2) return { ranks, scores };
  const probe = compressRanks(ranks, m);
  return {
    ranks: ranks.map((r, i) => (isStrategic(i, share) ? probe.ranks[i] : r)),
    scores: scores.map((s, i) => (isStrategic(i, share) ? probe.scores[i] : s)),
  };
}

/** Mean TRUE utility of each candidate over the electorate (sincere scores). */
function meanUtility(scores: number[][], m: number): number[] {
  const u = new Array<number>(m).fill(0);
  for (const s of scores) for (let c = 0; c < m; c++) u[c] += s[c];
  return u.map((x) => x / Math.max(1, scores.length));
}

/** VSE of a single elected candidate against the electorate's true utilities. */
export function vseOfWinner(meanU: number[], winner: number): number {
  if (winner < 0 || meanU.length === 0) return 0;
  const best = Math.max(...meanU);
  const rand = meanU.reduce((s, x) => s + x, 0) / meanU.length;
  // Every candidate equally good ⇒ any winner is optimal.
  if (best - rand < 1e-9) return 1;
  return (meanU[winner] - rand) / (best - rand);
}

/** VSE of one rule on ONE electorate at a given strategic share. */
export function vseAt(voters: Pt[], cands: NamedPt[], rule: Rule, share: number): number {
  const m = cands.length;
  if (m === 0 || voters.length === 0) return 0;
  const ranks = computeRanks(voters, cands);
  const scores = computeScores(voters, cands);
  const meanU = meanUtility(scores, m);
  const b = ballotsAtShare(ranks, scores, m, share);
  return vseOfWinner(meanU, ruleWinnerFromRanks(b.ranks, m, rule, b.scores));
}

export interface VseSweepOpts {
  rules?: Rule[];
  shares?: number[];
  replications?: number;
}

/**
 * The headline curve: VSE per method as the strategic share sweeps 0 → 100 %,
 * Monte-Carlo'd over fresh electorates so every point carries a p10–p90 band.
 *
 * `sampleAtSeed` re-draws the SAME electorate composition on a new seed — pass the
 * playground controller's own sampler so the sweep inherits turnout, the composed
 * mixture and the dimension count instead of re-deriving them here.
 */
export function vseSweep(
  sampleAtSeed: (seed: number) => Pt[],
  baseSeed: number,
  cands: NamedPt[],
  opts: VseSweepOpts = {}
): VseCurve[] {
  const { rules = VSE_RULES, shares = VSE_SHARES, replications = 14 } = opts;
  const m = cands.length;
  if (m < 2) return [];

  // [rule][share] → one VSE sample per replication.
  const acc: Record<string, number[][]> = {};
  for (const r of rules) acc[r] = shares.map(() => []);

  for (let k = 0; k < replications; k++) {
    const voters = sampleAtSeed(baseSeed + 977 + k * 31);
    if (voters.length === 0) continue;
    const ranks = computeRanks(voters, cands);
    const scores = computeScores(voters, cands);
    const meanU = meanUtility(scores, m);
    // Ballots depend only on the share, not the rule — build each set once.
    const ballots = shares.map((s) => ballotsAtShare(ranks, scores, m, s));
    for (const rule of rules) {
      for (let si = 0; si < shares.length; si++) {
        const b = ballots[si];
        acc[rule][si].push(vseOfWinner(meanU, ruleWinnerFromRanks(b.ranks, m, rule, b.scores)));
      }
    }
  }

  return rules.map((rule) => {
    const points = shares.map((share, si) => ({ share, vse: band(acc[rule][si]) }));
    const first = points[0]?.vse.mean ?? 0;
    const last = points[points.length - 1]?.vse.mean ?? 0;
    return { rule, points, degradation: first - last };
  });
}
