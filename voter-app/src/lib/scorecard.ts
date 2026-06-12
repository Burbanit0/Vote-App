// scorecard.ts — pure helpers for the playground scorecard + values lens
// (Lab reshape P5).
//
// Leader-mode axes are computed CLIENT-SIDE over Monte-Carlo re-rolls of the
// electorate (fresh seeds, same assumptions), so every number carries a band.
// All heuristics are documented here — knobs and conventions, never smuggled:
//  · Efficacité Condorcet — share of re-rolls (with a Condorcet winner) where
//    the rule elects them.
//  · Résistance stratégique — share of re-rolls where the winner SURVIVES a
//    Duverger-style compression probe (every voter pushes their preferred
//    frontrunner top / the other bottom). A transparent heuristic, not a full
//    Gibbard–Satterthwaite analysis.
//  · Bien-être — 1 − normalised Bayesian regret of the winner (utility = −distance).
//  · Satisfaction majoritaire — share of voters for whom the winner is at least
//    as good as their median candidate.
//  · Simplicité — a stated CONVENTION (ballot + tally complexity), constant per
//    rule, zero-width band.
//  · Stabilité — share of re-rolls electing the modal winner (binomial band).
//
// The values lens (shared by both modes): first ELIMINATE strictly
// Pareto-dominated systems (an objective claim), then let weights merely
// SPOTLIGHT a point on the remaining frontier. Never a leaderboard.

import {
  computeRanks,
  computeScores,
  ruleWinnerFromRanks,
  sampleVoters,
  type NamedPt,
  type Rule,
} from './playgroundVoting';

export interface Band {
  mean: number;
  lo: number;
  hi: number;
}

export type AxisScores = Record<string, Band>;

export const LEADER_AXES_KEYS = [
  'condorcet_efficiency',
  'strategic_resistance',
  'welfare',
  'majority_satisfaction',
  'simplicity',
  'stability',
] as const;

export const LEADER_RULES: Rule[] = [
  'plurality',
  'two_round',
  'irv',
  'borda',
  'approval',
  'condorcet',
];

/** Stated convention: ballot expressiveness + tally complexity, 1 = simplest. */
const SIMPLICITY: Record<Rule, number> = {
  plurality: 1.0,
  two_round: 0.85,
  approval: 0.8,
  borda: 0.6,
  irv: 0.5,
  condorcet: 0.35,
};

const mean = (xs: number[]): number =>
  xs.length ? xs.reduce((s, x) => s + x, 0) / xs.length : 0;

const pct = (xs: number[], p: number): number => {
  if (!xs.length) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const i = Math.min(s.length - 1, Math.max(0, Math.floor(p * (s.length - 1))));
  return s[i];
};

const band = (xs: number[]): Band => ({ mean: mean(xs), lo: pct(xs, 0.1), hi: pct(xs, 0.9) });

/** Binomial-style band around a rate measured over n trials. */
const rateBand = (p: number, n: number): Band => {
  const half = n > 0 ? 1.96 * Math.sqrt((p * (1 - p)) / n) : 0;
  return { mean: p, lo: Math.max(0, p - half), hi: Math.min(1, p + half) };
};

/** Condorcet winner index from rankings, or -1 if none (cycle/tie). */
export function condorcetFromRanks(ranks: number[][], m: number): number {
  for (let a = 0; a < m; a++) {
    let beatsAll = true;
    for (let b = 0; b < m && beatsAll; b++) {
      if (a === b) continue;
      let av = 0;
      for (const r of ranks) {
        if (r.indexOf(a) < r.indexOf(b)) av++;
      }
      if (av * 2 <= ranks.length) beatsAll = false;
    }
    if (beatsAll) return a;
  }
  return -1;
}

/** Duverger-style compression probe: preferred frontrunner top, other bottom. */
export function compressRanks(ranks: number[][], m: number): { ranks: number[][]; scores: number[][] } {
  // Frontrunners = top-2 by sincere first preferences.
  const firsts = new Array(m).fill(0);
  for (const r of ranks) firsts[r[0]] += 1;
  const order = firsts.map((_, i) => i).sort((a, b) => firsts[b] - firsts[a]);
  const [f1, f2] = [order[0], order[1]];
  const out: number[][] = [];
  const scores: number[][] = [];
  for (const r of ranks) {
    const pref = r.indexOf(f1) < r.indexOf(f2) ? f1 : f2;
    const other = pref === f1 ? f2 : f1;
    out.push([pref, ...r.filter((c) => c !== pref && c !== other), other]);
    // Approval under compression: approve only the preferred frontrunner.
    const s = new Array(m).fill(0);
    s[pref] = 1;
    scores.push(s);
  }
  return { ranks: out, scores };
}

export type LeaderScorecard = Record<string, AxisScores>; // keyed by rule

/**
 * Monte-Carlo leader scorecard: K re-rolled electorates × all rules × 6 axes.
 * Deterministic for a given base seed.
 */
export function leaderScorecard(
  candidates: NamedPt[],
  numVoters: number,
  baseSeed: number,
  ideology: string,
  replications = 24
): LeaderScorecard {
  const m = candidates.length;
  const perRule: Record<string, { ce: number[]; sr: number[]; wf: number[]; ms: number[]; winners: number[] }> = {};
  for (const r of LEADER_RULES) perRule[r] = { ce: [], sr: [], wf: [], ms: [], winners: [] };

  for (let k = 0; k < replications; k++) {
    const voters = sampleVoters(numVoters, baseSeed + 211 + k * 13, ideology);
    const ranks = computeRanks(voters, candidates);
    const scores = computeScores(voters, candidates);
    const cw = condorcetFromRanks(ranks, m);
    const probe = compressRanks(ranks, m);

    // Per-candidate mean utility (= mean score) for welfare/regret.
    const meanU = new Array(m).fill(0);
    for (const s of scores) for (let c = 0; c < m; c++) meanU[c] += s[c];
    for (let c = 0; c < m; c++) meanU[c] /= scores.length;
    const bestU = Math.max(...meanU);
    const worstU = Math.min(...meanU);

    for (const rule of LEADER_RULES) {
      const w = ruleWinnerFromRanks(ranks, m, rule, scores);
      perRule[rule].winners.push(w);
      if (cw >= 0) perRule[rule].ce.push(w === cw ? 1 : 0);
      const wProbe = ruleWinnerFromRanks(probe.ranks, m, rule, probe.scores);
      perRule[rule].sr.push(wProbe === w ? 1 : 0);
      perRule[rule].wf.push(
        bestU - worstU > 1e-9 ? 1 - (bestU - meanU[w]) / (bestU - worstU) : 1
      );
      // Majority satisfaction: winner at least as good as the voter's median candidate.
      let sat = 0;
      for (const s of scores) {
        const sorted = [...s].sort((a, b) => a - b);
        const med = sorted[Math.floor(m / 2)];
        if (s[w] >= med) sat++;
      }
      perRule[rule].ms.push(sat / scores.length);
    }
  }

  const out: LeaderScorecard = {};
  for (const rule of LEADER_RULES) {
    const d = perRule[rule];
    // Stability: how often the modal winner wins.
    const counts = new Map<number, number>();
    for (const w of d.winners) counts.set(w, (counts.get(w) ?? 0) + 1);
    const modal = Math.max(...counts.values()) / Math.max(1, d.winners.length);
    out[rule] = {
      condorcet_efficiency: d.ce.length ? band(d.ce) : { mean: 1, lo: 1, hi: 1 },
      strategic_resistance: band(d.sr),
      welfare: band(d.wf),
      majority_satisfaction: band(d.ms),
      simplicity: { mean: SIMPLICITY[rule], lo: SIMPLICITY[rule], hi: SIMPLICITY[rule] },
      stability: rateBand(modal, d.winners.length),
    };
  }
  return out;
}

// ── Values lens (shared) ──────────────────────────────────────────────────────

export interface LensItem {
  id: string;
  axes: AxisScores;
}

/** A strictly dominates B: ≥ on every axis mean, > on at least one. */
export function dominates(a: AxisScores, b: AxisScores, keys: string[]): boolean {
  let strict = false;
  for (const k of keys) {
    const av = a[k]?.mean ?? 0;
    const bv = b[k]?.mean ?? 0;
    if (av < bv - 1e-9) return false;
    if (av > bv + 1e-9) strict = true;
  }
  return strict;
}

/** Split items into the Pareto frontier and the dominated set (objective step). */
export function paretoSplit(
  items: LensItem[],
  keys: string[]
): { frontier: LensItem[]; dominated: LensItem[] } {
  const frontier: LensItem[] = [];
  const dominated: LensItem[] = [];
  for (const it of items) {
    if (items.some((o) => o.id !== it.id && dominates(o.axes, it.axes, keys))) {
      dominated.push(it);
    } else {
      frontier.push(it);
    }
  }
  return { frontier, dominated };
}

/** Weighted spotlight on the FRONTIER only — weights pick a point, not a ranking. */
export function spotlight(
  frontier: LensItem[],
  weights: Record<string, number>,
  keys: string[]
): string | null {
  let best: string | null = null;
  let bestScore = -Infinity;
  for (const it of frontier) {
    let s = 0;
    for (const k of keys) s += (weights[k] ?? 0) * (it.axes[k]?.mean ?? 0);
    if (s > bestScore) {
      bestScore = s;
      best = it.id;
    }
  }
  return best;
}
