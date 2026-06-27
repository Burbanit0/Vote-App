// playgroundEquilibrium.ts — the project's thesis under *settled* strategic play.
//
// playgroundSincerity asks a one-shot question: starting from an all-sincere
// electorate, would ONE bloc benefit from deviating? Real elections don't stop
// there: if a method tempts one camp to vote "utile", it tempts the others too,
// they all deviate, the winner moves, and they re-respond. This module plays that
// out — iterated better-response (the standard "iterative voting" model, Meir et
// al.) — and reports where it lands: does the sincere winner survive strategic
// play, or does the method settle on someone else (or fail to settle at all)?
//
// Move set is the SAME two canonical lies the rest of the playground teaches
// (compromise / burying), so this is the dynamic version of the same story, not a
// new model. Pure + deterministic; reuses the playground voting lib.

import {
  computeRanks,
  computeScores,
  ruleWinnerFromRanks,
  CARDINAL_RULES,
  type NamedPt,
  type Pt,
  type Rule,
} from './playgroundVoting';
import { LEADER_RULES } from './scorecard';

const MAX_PASSES = 25; // past this we declare "no equilibrium" (cycling)

export type EquilibriumOutcome = 'stable' | 'shifted' | 'cycle';

export interface EquilibriumVerdict {
  rule: Rule;
  /** Winner when everyone votes sincerely. */
  sincereWinner: string;
  /** Winner once better-response play settles; null if it never settles. */
  equilibriumWinner: string | null;
  /** stable = conviction survives (W*=W0); shifted = strategy changed the winner;
   *  cycle = no equilibrium reached within MAX_PASSES. */
  outcome: EquilibriumOutcome;
  /** Full passes over the groups until a fixed point (0 = already stable). */
  passes: number;
}

export interface EquilibriumReport {
  /** Distinct sincere-preference groups the electorate collapsed to. */
  groups: number;
  verdicts: EquilibriumVerdict[];
}

type Ballot = { rank: number[]; score: number[] };

// A bloc of voters that share one sincere ranking — the player of the game.
interface Group {
  weight: number; // how many voters
  rank: number[]; // sincere ranking, candidate indices best→worst
  score: number[]; // sincere cardinal ballot (per-candidate)
  pref: number[]; // pref[cand] = position in rank (0 = favourite); lower is better
}

// Evenly-strided sub-sample so a big electorate stays tractable on demand.
function subsample(arr: Pt[], cap: number): Pt[] {
  if (arr.length <= cap) return arr;
  const step = arr.length / cap;
  const out: Pt[] = [];
  for (let i = 0; i < cap; i++) out.push(arr[Math.floor(i * step)]);
  return out;
}

function buildGroups(voters: Pt[], cands: NamedPt[]): Group[] {
  const ranks = computeRanks(voters, cands);
  const scores = computeScores(voters, cands);
  const by = new Map<string, Group>();
  ranks.forEach((rank, v) => {
    const key = rank.join(',');
    const g = by.get(key);
    if (g) {
      g.weight += 1;
      return;
    }
    const pref = new Array(rank.length);
    rank.forEach((c, pos) => (pref[c] = pos));
    by.set(key, { weight: 1, rank, score: scores[v], pref });
  });
  // Largest blocs first → a deterministic, stable processing order.
  return [...by.values()].sort((a, b) => b.weight - a.weight);
}

// Expand the per-group ballots into per-voter rows and ask the rule for a winner.
function winnerOf(
  groups: Group[],
  ballots: Ballot[],
  m: number,
  rule: Rule,
  cardinal: boolean
): number {
  const ranks: number[][] = [];
  const scores: number[][] = [];
  groups.forEach((g, i) => {
    for (let k = 0; k < g.weight; k++) {
      ranks.push(ballots[i].rank);
      if (cardinal) scores.push(ballots[i].score);
    }
  });
  return ruleWinnerFromRanks(ranks, m, rule, cardinal ? scores : undefined);
}

// Winner when group i casts `move` and everyone else holds their current ballot.
function winnerWith(
  groups: Group[],
  ballots: Ballot[],
  i: number,
  move: Ballot,
  m: number,
  rule: Rule,
  cardinal: boolean
): number {
  const swapped = ballots.slice();
  swapped[i] = move;
  return winnerOf(groups, swapped, m, rule, cardinal);
}

// The candidate moves a group will consider: stay sincere, compromise onto any
// candidate it prefers to the current winner, or bury that winner. Same two
// canonical lies as playgroundSincerity — just enumerated as concrete ballots.
function candidateMoves(g: Group, m: number, curWinner: number): Ballot[] {
  const moves: Ballot[] = [{ rank: g.rank, score: g.score }];
  // Compromise: promote a preferred-to-winner candidate, bury the winner last.
  for (const c of g.rank) {
    if (c === curWinner) break; // ranking is best→worst: stop once we reach the winner
    const rank = [c, ...g.rank.filter((x) => x !== c && x !== curWinner), curWinner];
    const score = new Array(m).fill(0);
    score[c] = 1; // bullet-vote the compromise candidate (cardinal rules)
    moves.push({ rank, score });
  }
  // Burying: keep the favourite first, push the current winner to the bottom.
  if (g.rank[0] !== curWinner) {
    const fav = g.rank[0];
    const rank = [fav, ...g.rank.filter((x) => x !== fav && x !== curWinner), curWinner];
    const wPref = g.pref[curWinner];
    const score = g.rank.map((_, c) => (c === curWinner ? 0 : Math.max(0, wPref - g.pref[c])));
    moves.push({ rank, score });
  }
  return moves;
}

/**
 * Play iterated better-response for one rule and return where it settles.
 * Groups move one at a time (Gauss–Seidel) in a fixed order; a group switches
 * ballot only if, holding everyone else fixed, the move strictly improves the
 * winner by its own sincere preference. A full pass with no change = equilibrium.
 */
function settle(groups: Group[], names: string[], m: number, rule: Rule): EquilibriumVerdict {
  const cardinal = CARDINAL_RULES.has(rule);
  const ballots: Ballot[] = groups.map((g) => ({ rank: g.rank, score: g.score }));
  const w0 = winnerOf(groups, ballots, m, rule, cardinal);

  const name = (i: number) => names[i] ?? '—';
  // Strategyproof (random ballot) or degenerate (<3 candidates, no winner): the
  // sincere ballot is always a best response → nothing to settle.
  if (rule === 'random_ballot' || m < 3 || w0 < 0) {
    return {
      rule,
      sincereWinner: w0 >= 0 ? name(w0) : '—',
      equilibriumWinner: w0 >= 0 ? name(w0) : null,
      outcome: 'stable',
      passes: 0,
    };
  }

  for (let passes = 0; passes < MAX_PASSES; passes++) {
    let changed = false;
    for (let i = 0; i < groups.length; i++) {
      const g = groups[i];
      const curWinner = winnerWith(groups, ballots, i, ballots[i], m, rule, cardinal);
      let best = ballots[i];
      let bestPref = g.pref[curWinner];
      for (const move of candidateMoves(g, m, curWinner)) {
        const w = winnerWith(groups, ballots, i, move, m, rule, cardinal);
        if (g.pref[w] < bestPref) {
          bestPref = g.pref[w];
          best = move;
        }
      }
      if (best !== ballots[i]) {
        ballots[i] = best;
        changed = true;
      }
    }
    if (!changed) {
      const wStar = winnerOf(groups, ballots, m, rule, cardinal);
      return {
        rule,
        sincereWinner: name(w0),
        equilibriumWinner: name(wStar),
        outcome: wStar === w0 ? 'stable' : 'shifted',
        passes,
      };
    }
  }
  // Never settled within the budget → no pure equilibrium under these dynamics.
  return {
    rule,
    sincereWinner: name(w0),
    equilibriumWinner: null,
    outcome: 'cycle',
    passes: MAX_PASSES,
  };
}

/**
 * For each leader rule, play iterated better-response from an all-sincere start
 * and report whether the sincere winner survives. On-demand (not live): groups
 * the electorate by sincere ranking, then settles each rule independently.
 */
export function equilibriumReport(voters: Pt[], cands: NamedPt[]): EquilibriumReport {
  const m = cands.length;
  const names = cands.map((c) => c.name);
  const sample = subsample(voters, 240);
  if (sample.length === 0 || m < 1) {
    return { groups: 0, verdicts: [] };
  }
  const groups = buildGroups(sample, cands);
  const verdicts = LEADER_RULES.map((rule) => settle(groups, names, m, rule));
  return { groups: groups.length, verdicts };
}
