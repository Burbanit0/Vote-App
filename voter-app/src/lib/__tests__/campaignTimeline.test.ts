import { describe, it, expect } from 'vitest';
import {
  buildBaseVoters,
  trajectory,
  metricsAt,
  driftedAt,
  roundStops,
  type TimelineParams,
} from '../campaignTimeline';
import { medianPoint } from '../playgroundDynamics';
import type { NamedPt } from '../playgroundVoting';
import {
  DEFAULT_CONFIG,
  DEFAULT_PLAYGROUND,
  type PlaygroundState,
} from '../../stores/useElectionStore';

const PARAMS: TimelineParams = {
  rule: 'plurality',
  dims: 2,
  turnout: { model: 'full', intensity: 0 },
  strength: 0.6,
  numDays: 30,
};

describe('campaignTimeline — buildBaseVoters', () => {
  it('samples config.num_voters voters in simple mode, deterministically', () => {
    const a = buildBaseVoters(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);
    const b = buildBaseVoters(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);
    expect(a).toHaveLength(DEFAULT_CONFIG.num_voters);
    expect(a).toEqual(b); // same seed → same cloud
  });

  it('uses the community mixture when the electorate is composed', () => {
    const pg: PlaygroundState = {
      ...DEFAULT_PLAYGROUND,
      electorate: { ...DEFAULT_PLAYGROUND.electorate, mode: 'composed' },
    };
    const voters = buildBaseVoters(DEFAULT_CONFIG, pg);
    // The community mixture distributes the budget by weight (may round down),
    // so it yields a non-empty cloud up to num_voters.
    expect(voters.length).toBeGreaterThan(0);
    expect(voters.length).toBeLessThanOrEqual(DEFAULT_CONFIG.num_voters);
  });
});

describe('campaignTimeline — trajectory', () => {
  const voters = buildBaseVoters(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);

  it('returns steps+1 points spanning J0 → J{numDays}', () => {
    const tr = trajectory(voters, DEFAULT_CONFIG.candidates, PARAMS, 30);
    expect(tr).toHaveLength(31);
    expect(tr[0].t).toBe(0);
    expect(tr[0].day).toBe(0);
    expect(tr[tr.length - 1].t).toBe(1);
    expect(tr[tr.length - 1].day).toBe(30);
  });

  it('keeps regret and congruence within [0,1]', () => {
    const tr = trajectory(voters, DEFAULT_CONFIG.candidates, PARAMS, 20);
    for (const m of tr) {
      expect(m.regret).toBeGreaterThanOrEqual(0);
      expect(m.regret).toBeLessThanOrEqual(1);
      expect(m.congruence).toBeGreaterThanOrEqual(0);
      expect(m.congruence).toBeLessThanOrEqual(1);
    }
  });

  it('reports no flip at J0', () => {
    const tr = trajectory(voters, DEFAULT_CONFIG.candidates, PARAMS, 10);
    expect(tr[0].flippedFromStart).toBe(false);
  });
});

describe('campaignTimeline — metricsAt / Condorcet', () => {
  // A one-dimensional electorate with a clear central (Condorcet) candidate.
  const cands: NamedPt[] = [
    { name: 'Left', x: -0.8, y: 0 },
    { name: 'Center', x: 0.0, y: 0 },
    { name: 'Right', x: 0.8, y: 0 },
  ];
  // Voters clustered slightly left of center → Center beats both head-to-head.
  const voters = Array.from({ length: 101 }, (_, i) => ({
    x: -0.5 + (i / 100) * 0.8, // spread across [-0.5, 0.3]
    y: 0,
  }));

  it('flags the Condorcet winner as held when the rule picks it', () => {
    const target = medianPoint(voters);
    const m = metricsAt(voters, cands, target, 0, { ...PARAMS, rule: 'minimax' }, 0);
    // Minimax is Condorcet-consistent; the central candidate is the CW here.
    expect(m.condorcetWinner).toBe('Center');
    expect(m.condorcetHeld).toBe(true);
  });

  it('gives the welfare-optimal central winner ~zero regret', () => {
    const target = medianPoint(voters);
    // Pass startWinnerIdx = 0 (Left); the actual winner is Center (idx 1) → flip.
    const m = metricsAt(voters, cands, target, 0, { ...PARAMS, rule: 'minimax' }, 0);
    expect(m.winner).toBe('Center');
    expect(m.regret).toBeLessThan(0.05);
    expect(m.flippedFromStart).toBe(true);
  });
});

describe('campaignTimeline — driftedAt (what "pin" writes back)', () => {
  const cands: NamedPt[] = [
    { name: 'Left', x: -0.8, y: 0 },
    { name: 'Right', x: 0.8, y: 0 },
  ];
  const target = { x: 0, y: 0, z: 0 };

  it('returns the original positions at J0', () => {
    const at0 = driftedAt(cands, target, 0, PARAMS);
    expect(at0[0].x).toBeCloseTo(-0.8);
    expect(at0[1].x).toBeCloseTo(0.8);
  });

  it('moves candidates toward the median by J{end}', () => {
    const at1 = driftedAt(cands, target, 1, PARAMS);
    // strength 0.6 → travel 60% of the way to the target (0).
    expect(Math.abs(at1[0].x)).toBeLessThan(0.8);
    expect(Math.abs(at1[1].x)).toBeLessThan(0.8);
    expect(at1[0].x).toBeCloseTo(-0.8 * (1 - 0.6));
  });
});

describe('campaignTimeline — roundStops', () => {
  it('places evenly-spaced discrete round markers on [0,1]', () => {
    expect(roundStops(1)).toEqual([0]);
    expect(roundStops(2)).toEqual([0, 1]);
    expect(roundStops(4)).toEqual([0, 1 / 3, 2 / 3, 1]);
  });
});
