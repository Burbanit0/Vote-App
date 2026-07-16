// candidateDynamics.ts — the OTHER half of "simulate people's behaviour": the
// candidates move too. Hotelling (1929) and Downs (1957) modelled candidates as
// vote-seekers who relocate to wherever the votes are; the punchline is that
// where they end up depends on the COUNTING RULE. Plurality lets flanks survive,
// Condorcet-consistent rules drag everyone to the median voter, IRV can leave a
// hole in the centre.
//
// The existing "Dérive (Hotelling)" campaign scenario slides every candidate at
// the median on a fixed script, whatever the rule. This is the real game instead:
// each candidate hill-climbs to its own best position GIVEN the rule and given
// where the others stand. Switch the rule in the timeline and the equilibrium
// moves — that is the whole pedagogical payoff.
//
// ── Stated conventions ─────────────────────────────────────────────────────
// · Objective (Downsian vote-seeking): win under the rule first; failing that,
//   maximise your own first-preference share. The share is the gradient that
//   keeps a losing candidate moving instead of standing still.
// · Moves are a local hill-climb: probe a fixed ring of offsets around your
//   current spot, take the best strict improvement, else stay. Deterministic —
//   no randomness, so the same setup always animates the same way.
// · Round-robin, one candidate at a time (a Gauss–Seidel best-response dynamic),
//   which converges visibly; it is NOT a proof of Nash equilibrium.
// · The trajectory is computed ONCE and then replayed by t — the animation never
//   re-optimises on a frame.

import {
  computeRanks,
  computeScores,
  ruleWinnerFromRanks,
  CARDINAL_RULES,
  type Dims,
  type NamedPt,
  type Pt,
  type Rule,
} from './playgroundVoting';
import type { DriftFn } from './campaignTimeline';

/** Keep the hill-climb snappy: it is O(sweeps × candidates × probes × voters). */
const VOTER_CAP = 240;

const clamp1 = (v: number): number => Math.max(-1, Math.min(1, v));

/** Probe directions: a line in 1-D, the 8 compass points in 2-D/3-D (z is left
 *  alone — the map the user watches is the x–y plane). */
function directions(dims: Dims): [number, number][] {
  if (dims === 1)
    return [
      [-1, 0],
      [1, 0],
    ];
  const out: [number, number][] = [];
  for (let k = 0; k < 8; k++) {
    const a = (k / 8) * Math.PI * 2;
    out.push([Math.cos(a), Math.sin(a)]);
  }
  return out;
}

/** Downsian payoff of candidate `i` in `field`: winning dominates, share breaks ties. */
function payoff(voters: Pt[], field: NamedPt[], rule: Rule, i: number): number {
  const m = field.length;
  const ranks = computeRanks(voters, field);
  const scores = CARDINAL_RULES.has(rule) ? computeScores(voters, field) : undefined;
  const winner = ruleWinnerFromRanks(ranks, m, rule, scores);
  let firsts = 0;
  for (const r of ranks) if (r[0] === i) firsts++;
  return (winner === i ? 2 : 0) + firsts / Math.max(1, voters.length);
}

export interface DynamicsOpts {
  dims?: Dims;
  /** How far a candidate may move in one sweep. */
  radius?: number;
  /** Number of round-robin sweeps to run. */
  sweeps?: number;
}

/**
 * One candidate's best response: probe the ring around it (plus standing still)
 * and return the position with the highest payoff, everyone else held fixed.
 */
export function bestResponseStep(
  candidates: NamedPt[],
  voters: Pt[],
  rule: Rule,
  focal: number,
  opts: DynamicsOpts = {}
): NamedPt {
  const { dims = 2, radius = 0.05 } = opts;
  const me = candidates[focal];
  if (!me || voters.length === 0) return me;

  let best = me;
  let bestScore = payoff(voters, candidates, rule, focal); // standing still
  for (const [dx, dy] of directions(dims)) {
    const probe: NamedPt = {
      ...me,
      x: clamp1(me.x + dx * radius),
      y: dims === 1 ? me.y : clamp1(me.y + dy * radius),
    };
    const field = candidates.map((c, i) => (i === focal ? probe : c));
    const s = payoff(voters, field, rule, focal);
    if (s > bestScore + 1e-9) {
      bestScore = s;
      best = probe;
    }
  }
  return best;
}

/**
 * Round-robin best responses. Returns the full trajectory — frame 0 is the
 * starting field, one frame per sweep — so the UI can replay it without ever
 * re-optimising. Stops early at a fixed point (nobody wants to move).
 */
export function iterateDynamics(
  candidates: NamedPt[],
  voters: Pt[],
  rule: Rule,
  opts: DynamicsOpts = {}
): NamedPt[][] {
  const { sweeps = 24 } = opts;
  // Stride the electorate down to the cap: the hill-climb is the hot loop.
  const step = Math.max(1, Math.ceil(voters.length / VOTER_CAP));
  const sample = voters.filter((_, i) => i % step === 0);

  const frames: NamedPt[][] = [candidates.map((c) => ({ ...c }))];
  if (candidates.length === 0 || sample.length === 0) return frames;

  let field = candidates.map((c) => ({ ...c }));
  for (let s = 0; s < sweeps; s++) {
    let moved = false;
    for (let i = 0; i < field.length; i++) {
      const next = bestResponseStep(field, sample, rule, i, opts);
      if (next.x !== field[i].x || next.y !== field[i].y) {
        field = field.map((c, j) => (j === i ? next : c));
        moved = true;
      }
    }
    frames.push(field.map((c) => ({ ...c })));
    if (!moved) break; // fixed point — the field has settled
  }
  return frames;
}

/** Positions at campaign progress `t`, linearly interpolated between frames. */
export function frameAt(frames: NamedPt[][], t: number): NamedPt[] {
  if (frames.length === 0) return [];
  if (frames.length === 1) return frames[0];
  const x = Math.max(0, Math.min(1, t)) * (frames.length - 1);
  const i = Math.floor(x);
  const j = Math.min(frames.length - 1, i + 1);
  const f = x - i;
  return frames[i].map((c, k) => ({
    ...c,
    x: c.x + (frames[j][k].x - c.x) * f,
    y: c.y + (frames[j][k].y - c.y) * f,
  }));
}

export interface BestResponseCtx {
  voters: Pt[];
  candidates: NamedPt[];
  rule: Rule;
  dims: Dims;
  /** Scenario intensity → how far a candidate may travel per sweep. */
  strength: number;
}

/**
 * Build the campaign DriftFn for the best-response scenario. The hill-climb runs
 * ONCE here; the returned function is a cheap frame lookup, so scrubbing and
 * playback stay smooth and the trajectory is never recomputed per frame.
 */
export function makeBestResponseDrift(ctx: BestResponseCtx): DriftFn {
  const { voters, candidates, rule, dims, strength } = ctx;
  const frames = iterateDynamics(candidates, voters, rule, {
    dims,
    radius: 0.02 + 0.08 * strength,
    sweeps: 24,
  });
  return (_base, _target, t) => frameAt(frames, t);
}
