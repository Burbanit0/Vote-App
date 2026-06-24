import { describe, it, expect } from 'vitest';
import { CAMPAIGN_SCENARIOS, DEFAULT_SCENARIO, __selfCheck } from '../campaignScenarios';
import type { NamedPt, Pt } from '../playgroundVoting';

const base: NamedPt[] = [{ name: 'A', x: 0.8, y: 0 }];
const target: Pt = { x: 0, y: 0, z: 0 };
const drift = (id: string) => CAMPAIGN_SCENARIOS.find((s) => s.id === id)!.drift;

describe('campaignScenarios', () => {
  it('passes its self-check (J0 identity, derive inward, harden outward)', () => {
    expect(__selfCheck()).toBe(true);
  });

  it('exposes 3 scenarios with dérive as the default', () => {
    expect(CAMPAIGN_SCENARIOS.map((s) => s.id)).toEqual(['derive', 'sondages', 'durcissement']);
    expect(DEFAULT_SCENARIO.id).toBe('derive');
  });

  it('every scenario is the identity at J0', () => {
    for (const s of CAMPAIGN_SCENARIOS) {
      expect(s.drift(base, target, 0, 0.6)[0].x).toBeCloseTo(0.8);
    }
  });

  it('dérive pulls toward the median, durcissement pushes away', () => {
    expect(Math.abs(drift('derive')(base, target, 1, 0.6)[0].x)).toBeLessThan(0.8);
    expect(Math.abs(drift('durcissement')(base, target, 1, 0.6)[0].x)).toBeGreaterThan(0.8);
  });
});
