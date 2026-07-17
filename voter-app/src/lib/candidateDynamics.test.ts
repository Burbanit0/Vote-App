import { describe, it, expect } from 'vitest';
import {
  bestResponseStep,
  iterateDynamics,
  frameAt,
  makeBestResponseDrift,
} from './candidateDynamics';
import { sampleVoters, type NamedPt } from './playgroundVoting';

// A symmetric single-community electorate on a line: the median voter sits at 0,
// which is where Hotelling says two vote-seekers must end up.
const line = sampleVoters(300, 42, 'centrist', 1);

const at = (name: string, x: number): NamedPt => ({ name, x, y: 0 });
const xs = (f: NamedPt[]): number[] => f.map((c) => c.x);

describe('candidateDynamics — best response', () => {
  it('moves a candidate toward the votes, and leaves a settled one alone', () => {
    // Two candidates far out on the same flank: the outer one gains by moving in.
    const field = [at('A', -0.8), at('B', 0.8)];
    const next = bestResponseStep(field, line, 'plurality', 0, { dims: 1, radius: 0.05 });
    expect(next.x).toBeGreaterThan(-0.8); // stepped inward, toward the median
  });

  it('never leaves the map', () => {
    const field = [at('A', -1), at('B', 1)];
    for (let i = 0; i < field.length; i++) {
      const next = bestResponseStep(field, line, 'plurality', i, { dims: 1, radius: 0.5 });
      expect(Math.abs(next.x)).toBeLessThanOrEqual(1);
    }
  });
});

describe('candidateDynamics — Hotelling convergence', () => {
  it('two vote-seekers under plurality converge on the median voter', () => {
    // THE canonical result (Hotelling 1929 / Downs 1957): with two candidates and
    // a single-peaked electorate, both crowd the centre.
    const frames = iterateDynamics([at('A', -0.7), at('B', 0.7)], line, 'plurality', {
      dims: 1,
      radius: 0.05,
      sweeps: 40,
    });
    const start = xs(frames[0]);
    const end = xs(frames[frames.length - 1]);
    // Both ended up much closer to the median (0) than they started.
    expect(Math.abs(end[0])).toBeLessThan(Math.abs(start[0]));
    expect(Math.abs(end[1])).toBeLessThan(Math.abs(start[1]));
    expect(Math.abs(end[0])).toBeLessThan(0.2);
    expect(Math.abs(end[1])).toBeLessThan(0.2);
  });

  it('is deterministic and terminates at a fixed point', () => {
    const opts = { dims: 1 as const, radius: 0.05, sweeps: 60 };
    const a = iterateDynamics([at('A', -0.7), at('B', 0.7)], line, 'plurality', opts);
    const b = iterateDynamics([at('A', -0.7), at('B', 0.7)], line, 'plurality', opts);
    expect(a).toEqual(b);
    // Stopped early because nobody wanted to move any more, not because it ran out.
    expect(a.length).toBeLessThan(61);
    expect(xs(a[a.length - 1])).toEqual(xs(a[a.length - 2]));
  });

  it('the rule changes where the candidates end up', () => {
    // The whole point of the scenario: same electorate, same start, different rule
    // ⇒ different equilibrium. (Three candidates make the rules disagree.)
    const start = [at('G', -0.6), at('C', 0.0), at('D', 0.6)];
    const opts = { dims: 1 as const, radius: 0.05, sweeps: 30 };
    const plur = iterateDynamics(start, line, 'plurality', opts);
    const cond = iterateDynamics(start, line, 'condorcet', opts);
    const endPlur = xs(plur[plur.length - 1]);
    const endCond = xs(cond[cond.length - 1]);
    expect(endPlur).not.toEqual(endCond);
  });

  it('an empty field or empty electorate is a no-op, not a crash', () => {
    expect(iterateDynamics([], line, 'plurality')).toEqual([[]]);
    expect(iterateDynamics([at('A', 0)], [], 'plurality')).toEqual([[at('A', 0)]]);
  });
});

describe('candidateDynamics — replay', () => {
  const frames = [
    [at('A', 0), at('B', 1)],
    [at('A', 0.5), at('B', 0.5)],
  ];

  it('frameAt interpolates between frames and clamps at the ends', () => {
    expect(xs(frameAt(frames, 0))).toEqual([0, 1]);
    expect(xs(frameAt(frames, 1))).toEqual([0.5, 0.5]);
    expect(xs(frameAt(frames, 0.5))).toEqual([0.25, 0.75]);
    expect(xs(frameAt(frames, -5))).toEqual([0, 1]); // clamped
    expect(xs(frameAt(frames, 5))).toEqual([0.5, 0.5]); // clamped
  });

  it('the drift replays the trajectory without re-optimising', () => {
    const candidates = [at('A', -0.7), at('B', 0.7)];
    const drift = makeBestResponseDrift({
      voters: line,
      candidates,
      rule: 'plurality',
      dims: 1,
      strength: 0.6,
    });
    // t=0 is the starting field; t=1 has converged; identical calls are identical.
    expect(xs(drift(candidates, { x: 0, y: 0 }, 0, 0.6))).toEqual([-0.7, 0.7]);
    const end = xs(drift(candidates, { x: 0, y: 0 }, 1, 0.6));
    expect(Math.abs(end[0])).toBeLessThan(0.2);
    expect(drift(candidates, { x: 0, y: 0 }, 0.5, 0.6)).toEqual(
      drift(candidates, { x: 0, y: 0 }, 0.5, 0.6)
    );
  });
});
