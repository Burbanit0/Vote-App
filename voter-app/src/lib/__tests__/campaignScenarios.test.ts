import { describe, it, expect } from 'vitest';
import { CAMPAIGN_SCENARIOS, DEFAULT_SCENARIO, driftOf, __selfCheck } from '../campaignScenarios';
import { sampleVoters, type NamedPt, type Pt } from '../playgroundVoting';
import type { BestResponseCtx } from '../candidateDynamics';

const base: NamedPt[] = [{ name: 'A', x: 0.8, y: 0 }];
const target: Pt = { x: 0, y: 0, z: 0 };
// Rule-dependent scenarios build their drift from a context; static ones ignore it.
const ctx: BestResponseCtx = {
  voters: sampleVoters(120, 42, 'centrist', 2),
  candidates: base,
  rule: 'plurality',
  dims: 2,
  strength: 0.6,
};
const drift = (id: string) => driftOf(CAMPAIGN_SCENARIOS.find((s) => s.id === id)!, ctx)!;

describe('campaignScenarios', () => {
  it('passes its self-check (J0 identity, derive inward, harden outward)', () => {
    expect(__selfCheck()).toBe(true);
  });

  it('exposes 4 scenarios with dérive as the default', () => {
    expect(CAMPAIGN_SCENARIOS.map((s) => s.id)).toEqual([
      'derive',
      'sondages',
      'durcissement',
      'meilleure_reponse',
    ]);
    expect(DEFAULT_SCENARIO.id).toBe('derive');
  });

  it('every scenario is the identity at J0 — including the rule-dependent one', () => {
    for (const s of CAMPAIGN_SCENARIOS) {
      expect(drift(s.id)(base, target, 0, 0.6)[0].x, s.id).toBeCloseTo(0.8);
    }
  });

  it('exactly one scenario depends on the electorate + rule', () => {
    const dynamic = CAMPAIGN_SCENARIOS.filter((s) => s.makeDrift);
    expect(dynamic.map((s) => s.id)).toEqual(['meilleure_reponse']);
    // …and it is the only one with no static, rule-independent script.
    for (const s of CAMPAIGN_SCENARIOS) expect(!!s.drift || !!s.makeDrift, s.id).toBe(true);
  });

  it('dérive pulls toward the median, durcissement pushes away', () => {
    expect(Math.abs(drift('derive')(base, target, 1, 0.6)[0].x)).toBeLessThan(0.8);
    expect(Math.abs(drift('durcissement')(base, target, 1, 0.6)[0].x)).toBeGreaterThan(0.8);
  });
});
