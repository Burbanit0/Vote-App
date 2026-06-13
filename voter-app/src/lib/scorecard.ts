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
  applyTurnout,
  computeRanks,
  computeScores,
  ruleWinnerFromRanks,
  sampleVoters,
  type Dims,
  type NamedPt,
  type Pt,
  type Rule,
  type TurnoutModel,
} from './playgroundVoting';
import { composeElectorate, type Community } from './playgroundElectorate';

export interface TurnoutConfig {
  model: TurnoutModel;
  intensity: number;
}
const NO_TURNOUT: TurnoutConfig = { model: 'full', intensity: 0 };

/** Optional composed electorate; when set, re-rolls use it instead of the
 * ideology Gaussian, so the scorecard matches the displayed cloud. */
export interface ElectorateSampler {
  communities: Community[];
  correlation: number;
}
function rollVoters(
  electorate: ElectorateSampler | null,
  numVoters: number,
  seed: number,
  ideology: string,
  dims: Dims
): Pt[] {
  return electorate
    ? composeElectorate(electorate.communities, electorate.correlation, numVoters, seed, dims)
        .voters
    : sampleVoters(numVoters, seed, ideology, dims);
}

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
  'score',
  'star',
  'majority_judgment',
  'bucklin',
  'coombs',
  'condorcet',
  'minimax',
  'schulze',
  'nanson',
  'baldwin',
];

/** Stated convention: ballot expressiveness + tally complexity, 1 = simplest. */
const SIMPLICITY: Record<Rule, number> = {
  plurality: 1.0,
  score: 0.8,
  two_round: 0.85,
  approval: 0.8,
  star: 0.7,
  bucklin: 0.55,
  majority_judgment: 0.6,
  borda: 0.6,
  coombs: 0.5,
  irv: 0.5,
  nanson: 0.4,
  baldwin: 0.4,
  condorcet: 0.35,
  minimax: 0.35,
  schulze: 0.3,
};

const mean = (xs: number[]): number => (xs.length ? xs.reduce((s, x) => s + x, 0) / xs.length : 0);

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
export function compressRanks(
  ranks: number[][],
  m: number
): { ranks: number[][]; scores: number[][] } {
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
  replications = 24,
  dims: Dims = 2,
  turnout: TurnoutConfig = NO_TURNOUT,
  electorate: ElectorateSampler | null = null
): LeaderScorecard {
  const m = candidates.length;
  const perRule: Record<
    string,
    { ce: number[]; sr: number[]; wf: number[]; ms: number[]; winners: number[] }
  > = {};
  for (const r of LEADER_RULES) perRule[r] = { ce: [], sr: [], wf: [], ms: [], winners: [] };

  for (let k = 0; k < replications; k++) {
    const voters = applyTurnout(
      rollVoters(electorate, numVoters, baseSeed + 211 + k * 13, ideology, dims),
      candidates,
      turnout.model,
      turnout.intensity
    ).voters;
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
      perRule[rule].wf.push(bestU - worstU > 1e-9 ? 1 - (bestU - meanU[w]) / (bestU - worstU) : 1);
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

// ── Manipulation hardness (frontier FC-1) ────────────────────────────────────
//
// Bartholdi–Tovey–Trick: resistance to strategic voting is partly
// COMPUTATIONAL. Gibbard–Satterthwaite says every reasonable rule is gameable
// in principle; what differs is whether finding the right lie is tractable.
// Two parts, kept separate and honest:
//  · an EMPIRICAL probe — the smallest coalition share whose naive
//    "compromise" strategy (rank the strongest challenger first, the winner
//    last) actually flips the winner on THIS electorate;
//  · the LITERATURE flag — the known complexity class of computing a
//    manipulation, with the citation (a stated reference, not our claim).

export interface ManipProbe {
  /** Smallest coalition share (of all voters) whose compromise flips the
   * winner, or null if none ≤ maxShare succeeded. */
  minCoalitionShare: number | null;
  /** A tried coalition produced a winner the coalition likes LESS than the
   * original (the strategy backfired) — the practical face of hardness. */
  backfired: boolean;
}

export const MANIP_COMPLEXITY: Record<Rule, { hard: boolean; label: string; ref: string }> = {
  plurality: { hard: false, label: 'P (calcul trivial)', ref: 'compromission directe' },
  approval: { hard: false, label: 'P (calcul trivial)', ref: 'approuver le challenger' },
  score: { hard: false, label: 'P (calcul trivial)', ref: 'note maximale au challenger' },
  star: { hard: false, label: 'P (note + finale)', ref: 'STAR — note puis duel' },
  majority_judgment: { hard: false, label: 'P (médiane)', ref: 'Balinski–Laraki 2010' },
  borda: {
    hard: false,
    label: 'P pour un manipulateur · NP-difficile en coalition',
    ref: 'Bartholdi–Tovey–Trick 1989 ; Betzler et al. / Davies et al. 2011',
  },
  two_round: { hard: false, label: 'P (un manipulateur)', ref: 'Conitzer–Sandholm–Lang 2007' },
  condorcet: { hard: false, label: 'P (Copeland)', ref: 'Bartholdi–Tovey–Trick 1989' },
  minimax: { hard: false, label: 'P (paires)', ref: 'minimax — calcul polynomial' },
  schulze: { hard: false, label: 'P (chemin le plus fort)', ref: 'Schulze 2011' },
  bucklin: { hard: false, label: 'P (calcul direct)', ref: 'Xia et al. 2009' },
  coombs: { hard: false, label: 'P (élimination par derniers)', ref: 'élimination, cf. IRV' },
  nanson: {
    hard: true,
    label: 'NP-difficile à manipuler',
    ref: 'Narodytska–Walsh–Xia 2011',
  },
  baldwin: {
    hard: true,
    label: 'NP-difficile à manipuler',
    ref: 'Narodytska–Walsh–Xia 2011',
  },
  irv: {
    hard: true,
    label: 'NP-difficile, même pour un seul manipulateur',
    ref: 'Bartholdi–Orlin 1991 (STV/IRV)',
  },
};

const COALITION_STEPS = [0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4];

/**
 * Empirical compromise probe for one rule on one electorate. For each of the
 * two strongest challengers: voters preferring them to the winner (most
 * motivated first) compromise in increasing coalition sizes until the winner
 * flips. Reports the smallest working share, and whether any attempt
 * backfired (elected someone the coalition likes less).
 */
export function manipulationProbe(voters: Pt[], cands: NamedPt[], rule: Rule): ManipProbe {
  const m = cands.length;
  if (m < 3 || voters.length === 0) return { minCoalitionShare: null, backfired: false };
  const ranks = computeRanks(voters, cands);
  const scores = computeScores(voters, cands);
  const w = ruleWinnerFromRanks(ranks, m, rule, scores);
  if (w < 0) return { minCoalitionShare: null, backfired: false };

  // Two strongest challengers by first preferences (excluding the winner).
  const firsts = new Array(m).fill(0);
  for (const r of ranks) firsts[r[0]] += 1;
  const challengers = firsts
    .map((_, i) => i)
    .filter((i) => i !== w)
    .sort((a, b) => firsts[b] - firsts[a])
    .slice(0, 2);

  let best: number | null = null;
  let backfired = false;

  for (const c of challengers) {
    // Coalition: voters strictly preferring c to w whose ballot actually
    // CHANGES under the compromise (already-c-first voters add nothing),
    // the most motivated first.
    const sympathisers = ranks
      .map((r, v) => ({ v, gain: r.indexOf(w) - r.indexOf(c) }))
      .filter((s) => s.gain > 0 && ranks[s.v][0] !== c)
      .sort((a, b) => b.gain - a.gain);
    for (const share of COALITION_STEPS) {
      if (best !== null && share >= best) break;
      const size = Math.floor(share * voters.length);
      if (size === 0 || size > sympathisers.length) continue;
      const coalition = new Set(sympathisers.slice(0, size).map((s) => s.v));
      const ranks2 = ranks.map((r, v) => {
        if (!coalition.has(v)) return r;
        // Compromise: challenger first, winner last, the rest sincere.
        return [c, ...r.filter((x) => x !== c && x !== w), w];
      });
      const scores2 = scores.map((s, v) => {
        if (!coalition.has(v)) return s;
        const s2 = new Array(m).fill(0);
        s2[c] = 1;
        return s2;
      });
      const w2 = ruleWinnerFromRanks(ranks2, m, rule, scores2);
      if (w2 === c) {
        best = share;
        break;
      }
      if (w2 !== w) {
        // The lie elected a third candidate — worse than honesty if the
        // coalition prefers w to w2 on average.
        const prefersOld = ranks.filter(
          (r, v) => coalition.has(v) && r.indexOf(w) < r.indexOf(w2)
        ).length;
        if (prefersOld * 2 > coalition.size) backfired = true;
      }
    }
  }
  return { minCoalitionShare: best, backfired };
}

// ── Lijphart lens (frontier FA-2) ────────────────────────────────────────────
//
// Lijphart (Patterns of Democracy): real systems cluster on a MAJORITARIAN
// (decisive, accountable, winner-take-all) ↔ CONSENSUS (proportional,
// power-sharing, minority-protective) axis. We compute a consensus index in
// [0,1] from the parliament scorecard axes — a stated convention, the mean of
// proportionality, pluralism, minority representation and (1 − governability),
// i.e. the executives-parties dimension our model can actually speak to.
// (Lijphart's second, federal-unitary dimension is NOT modelled — we stay 1D.)

/** Approximate executives-parties scores (Lijphart 2012, ~1981–2010 period),
 * on his standardised scale ≈ [-2, +2], positive = consensus. Orders of
 * magnitude for context, not data claims. */
export const LIJPHART_REFERENCE: { name: string; score: number }[] = [
  { name: 'Royaume-Uni', score: -1.2 },
  { name: 'Canada', score: -1.3 },
  { name: 'France', score: -1.0 },
  { name: 'Australie', score: -0.8 },
  { name: 'Nouvelle-Zélande', score: -0.5 },
  { name: 'États-Unis', score: -0.4 },
  { name: 'Espagne', score: -0.3 },
  { name: 'Japon', score: -0.1 },
  { name: 'Allemagne', score: 0.7 },
  { name: 'Suède', score: 0.7 },
  { name: 'Italie', score: 0.7 },
  { name: 'Israël', score: 1.0 },
  { name: 'Pays-Bas', score: 1.2 },
  { name: 'Belgique', score: 1.3 },
  { name: 'Suisse', score: 1.8 },
];

/** Map a Lijphart-scale score (≈[-2,2]) onto the display strip [0,1]. */
export const lijphartTo01 = (score: number): number => Math.max(0, Math.min(1, (score + 2) / 4));

/** Consensus index of a structure from its scorecard axes (band-propagated). */
export function consensusIndex(axes: AxisScores): Band {
  const pick = (k: string) => axes[k] ?? { mean: 0.5, lo: 0.5, hi: 0.5 };
  const p = pick('proportionality');
  const pl = pick('pluralism');
  const mr = pick('minority_representation');
  const g = pick('governability');
  const agg = (f: (b: Band) => number, gv: number) => (f(p) + f(pl) + f(mr) + gv) / 4;
  return {
    mean: agg((b) => b.mean, 1 - g.mean),
    lo: agg((b) => b.lo, 1 - g.hi),
    hi: agg((b) => b.hi, 1 - g.lo),
  };
}

/**
 * The identity dial: one majoritarian↔consensualist position `d` ∈ [0,1] sets
 * CORRELATED axis weights (stated mapping). d=0 weighs decisiveness/simplicity,
 * d=1 weighs proportionality/inclusion. The granular sliders remain the
 * escape hatch — the dial is a shortcut, not a hidden assumption.
 */
export function dialWeights(d: number, mode: 'leader' | 'parliament'): Record<string, number> {
  const x = Math.max(0, Math.min(1, d));
  if (mode === 'parliament') {
    return {
      proportionality: x,
      pluralism: x,
      effective_votes: x,
      minority_representation: x,
      governability: 1 - x,
      gerrymander_resistance: 0.5,
    };
  }
  return {
    condorcet_efficiency: x,
    welfare: x,
    majority_satisfaction: x,
    simplicity: 1 - x,
    stability: 1 - x,
    strategic_resistance: 0.5,
  };
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
