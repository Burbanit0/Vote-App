// campaignTimeline.ts — pure metrics for the "Campagne & dynamique" timeline (C2).
//
// The timeline answers Q2 (one axis, both continuous campaign days AND discrete
// rounds) and Q4 (a "value of the result" trajectory). Everything here is pure,
// client-side and instant: from the inherited J0 electorate it re-derives, at
// each point of campaign progress t∈[0,1], the drifted candidates (Hotelling),
// the winner under the chosen rule, and four readouts of *result quality*:
//   • regret      — utilitarian: how far the winner is from the welfare-optimal
//                   candidate (0 = optimal, 1 = worst possible).
//   • congruence  — how central the winner is among the field vs the median voter
//                   (1 = the most central candidate, 0 = the least).
//   • condorcet   — does the winner coincide with the Condorcet winner (when one
//                   exists)? null when there is no Condorcet winner (a cycle).
//   • flip        — has the winner changed since J0?
//
// It reuses the SAME public helpers the playground uses (composeElectorate /
// sampleVoters / applyTurnout / driftCandidates / medianPoint / ruleWinner /
// computeRanks / condorcetFromRanks), so a given (config, playground, rule) is
// scored identically on both pages — the page is a faithful continuation of J0.

import {
  applyTurnout,
  computeRanks,
  ruleWinner,
  sampleVoters,
  type Dims,
  type NamedPt,
  type Pt,
  type Rule,
  type TurnoutModel,
} from './playgroundVoting';
import { condorcetFromRanks } from './scorecard';
import { composeElectorate } from './playgroundElectorate';
import { driftCandidates, medianPoint } from './playgroundDynamics';
import type { ElectionConfig, PlaygroundState } from '../stores/useElectionStore';

function dist(a: Pt, b: Pt): number {
  const dx = a.x - b.x;
  const dy = (a.y ?? 0) - (b.y ?? 0);
  const dz = (a.z ?? 0) - (b.z ?? 0);
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

/** Project candidates onto the active dimension count (mirrors the playground). */
function projectCandidates(cands: NamedPt[], dims: Dims): NamedPt[] {
  return cands.map((c) => ({
    ...c,
    y: dims >= 2 ? c.y : 0,
    z: dims >= 3 ? (c.z ?? 0) : 0,
  }));
}

/**
 * Build the J0 voter cloud from the inherited (config, playground), exactly as
 * the playground does: a community mixture when the electorate is 'composed',
 * otherwise the single ideology Gaussian. Turnout is applied per-step (it depends
 * on the drifted candidates), so it is NOT applied here.
 */
export function buildBaseVoters(config: ElectionConfig, playground: PlaygroundState): Pt[] {
  const dims = playground.space.dims;
  const e = playground.electorate;
  if (e.mode === 'composed') {
    return composeElectorate(
      e.communities,
      e.correlation,
      config.num_voters,
      config.seed,
      dims,
      e.noise ?? 0
    ).voters;
  }
  return sampleVoters(config.num_voters, config.seed, config.ideology, dims);
}

export interface ResultMetrics {
  /** Campaign progress in [0,1]. */
  t: number;
  /** Campaign day (round(t * numDays)). */
  day: number;
  winner: string | null;
  winnerIdx: number;
  /** Utilitarian regret in [0,1] (0 = welfare-optimal winner). */
  regret: number;
  /** Centrality of the winner among the field in [0,1] (1 = most central). */
  congruence: number;
  condorcetWinner: string | null;
  /** true/false when a Condorcet winner exists, null on a cycle. */
  condorcetHeld: boolean | null;
  /** Whether the winner differs from the J0 winner. */
  flippedFromStart: boolean;
}

export interface TimelineParams {
  rule: Rule;
  dims: Dims;
  turnout: { model: TurnoutModel; intensity: number };
  /** How far candidates travel toward the median by t=1 (Hotelling strength). */
  strength: number;
  /** Campaign length in days (for the day readout). */
  numDays: number;
}

/** Social cost of a candidate = mean voter→candidate distance (lower = better). */
function socialCosts(voters: Pt[], cands: NamedPt[]): number[] {
  return cands.map((c) => {
    if (!voters.length) return 0;
    let s = 0;
    for (const v of voters) s += dist(v, c);
    return s / voters.length;
  });
}

/**
 * Score the result at a single point of campaign progress `t`. `startWinnerIdx`
 * is the J0 winner index, used only for the flip flag (pass the t=0 winner).
 */
export function metricsAt(
  baseVoters: Pt[],
  baseCandidates: NamedPt[],
  target: Pt,
  t: number,
  params: TimelineParams,
  startWinnerIdx: number
): ResultMetrics {
  const drifted = projectCandidates(
    t > 0 ? driftCandidates(baseCandidates, target, t, params.strength) : baseCandidates,
    params.dims
  );
  const voters = applyTurnout(
    baseVoters,
    drifted,
    params.turnout.model,
    params.turnout.intensity
  ).voters;
  const m = drifted.length;

  const winnerIdx = ruleWinner(voters, drifted, params.rule);
  const ranks = computeRanks(voters, drifted);
  const cwIdx = condorcetFromRanks(ranks, m);

  // Regret — utilitarian, normalized to [0,1] over the field.
  const costs = socialCosts(voters, drifted);
  const best = Math.min(...costs);
  const worst = Math.max(...costs);
  const span = worst - best;
  const regret = winnerIdx < 0 || span <= 0 ? 0 : (costs[winnerIdx] - best) / span;

  // Congruence — centrality of the winner vs the field, against the median voter.
  const dToMedian = drifted.map((c) => dist(c, target));
  const near = Math.min(...dToMedian);
  const far = Math.max(...dToMedian);
  const cspan = far - near;
  const congruence = winnerIdx < 0 || cspan <= 0 ? 1 : 1 - (dToMedian[winnerIdx] - near) / cspan;

  return {
    t,
    day: Math.round(t * params.numDays),
    winner: winnerIdx >= 0 ? drifted[winnerIdx].name : null,
    winnerIdx,
    regret,
    congruence,
    condorcetWinner: cwIdx >= 0 ? drifted[cwIdx].name : null,
    condorcetHeld: cwIdx < 0 ? null : winnerIdx === cwIdx,
    flippedFromStart: winnerIdx !== startWinnerIdx,
  };
}

/**
 * Sample the whole campaign trajectory at `steps + 1` evenly-spaced points of t
 * (J0 … J{numDays}). The flip flag is measured against the J0 winner.
 */
export function trajectory(
  baseVoters: Pt[],
  baseCandidates: NamedPt[],
  params: TimelineParams,
  steps = 30
): ResultMetrics[] {
  const target = medianPoint(baseVoters);
  const n = Math.max(1, steps);
  // J0 winner (drift-free) anchors the flip flag.
  const drift0 = projectCandidates(baseCandidates, params.dims);
  const voters0 = applyTurnout(
    baseVoters,
    drift0,
    params.turnout.model,
    params.turnout.intensity
  ).voters;
  const startWinnerIdx = ruleWinner(voters0, drift0, params.rule);

  const out: ResultMetrics[] = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    out.push(metricsAt(baseVoters, baseCandidates, target, t, params, startWinnerIdx));
  }
  return out;
}

/** The t∈[0,1] positions of `rounds` evenly-spaced discrete round markers. */
export function roundStops(rounds: number): number[] {
  const r = Math.max(1, rounds);
  if (r === 1) return [0];
  return Array.from({ length: r }, (_, i) => i / (r - 1));
}
