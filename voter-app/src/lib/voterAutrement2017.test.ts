import { describe, it, expect } from 'vitest';
import { VOTER_AUTREMENT_2017, reordering } from './voterAutrement2017';

// Honesty gate: these are published numbers, not a spatial model. Approval rates
// from the Baujard et al. "Voter Autrement" 2017 in-situ experiment (as reported
// on rangevoting.org/France2017); official first-round shares from the Ministère
// de l'Intérieur. If either drifts, the "real election" claim becomes fiction.

describe('Voter Autrement 2017 — matches the published record', () => {
  it('ships all 11 first-round candidates and the ballot count', () => {
    expect(VOTER_AUTREMENT_2017.candidates).toHaveLength(11);
    expect(VOTER_AUTREMENT_2017.approvalBallots).toBe(3894);
  });

  it('official first-round shares sum to 100.00', () => {
    const sum = VOTER_AUTREMENT_2017.candidates.reduce((s, c) => s + c.plurality, 0);
    expect(sum).toBeCloseTo(100, 2);
  });

  it('same winner, collapsed order: Macron leads both formats', () => {
    const rows = reordering();
    expect(rows[0].name).toBe('Macron');
    expect(rows[0].approvalRank).toBe(1);
    expect(rows[0].pluralityRank).toBe(1);
    expect(rows[0].delta).toBe(0);
  });

  it('the twist: Le Pen falls 2nd→5th, Mélenchon and Hamon climb', () => {
    const by = Object.fromEntries(reordering().map((r) => [r.name, r]));
    // Le Pen: runoff opponent officially (2nd), fifth on approval — a 3-place drop.
    expect(by['Le Pen'].pluralityRank).toBe(2);
    expect(by['Le Pen'].approvalRank).toBe(5);
    expect(by['Le Pen'].delta).toBe(-3);
    // Mélenchon overtakes to become the approval runner-up (would-be runoff rival).
    expect(by['Mélenchon'].pluralityRank).toBe(4);
    expect(by['Mélenchon'].approvalRank).toBe(2);
    // Hamon: 5th officially, 3rd on approval.
    expect(by['Hamon'].pluralityRank).toBe(5);
    expect(by['Hamon'].approvalRank).toBe(3);
  });

  it('rows are sorted by approval, descending', () => {
    const a = reordering().map((r) => r.approval);
    expect(a).toEqual([...a].sort((x, y) => y - x));
  });
});
