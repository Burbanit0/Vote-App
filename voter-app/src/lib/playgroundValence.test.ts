import { describe, it, expect } from 'vitest';
import { ruleWinner, computeScores, type NamedPt, type Pt } from './playgroundVoting';

// Stokes valence: utility = -distance + valence. With valence off (default 0) the
// model is purely positional; switching it on can let a spatially non-central
// candidate win — the realism this lever adds. These lock both directions.

const voters: Pt[] = [
  { x: -0.1, y: 0 },
  { x: 0, y: 0 },
  { x: 0.1, y: 0 },
]; // clustered at centre
const A: NamedPt = { name: 'A', x: 0, y: 0 }; // central — wins on position alone
const B: NamedPt = { name: 'B', x: 0.9, y: 0 }; // far from the voters

describe('valence (Stokes non-spatial quality)', () => {
  it('is inert by default: the central candidate wins', () => {
    expect(ruleWinner(voters, [A, B], 'plurality')).toBe(0); // A
    expect(ruleWinner(voters, [A, B], 'condorcet')).toBe(0); // A beats B head-to-head
  });

  it('enough valence lets the non-central candidate win', () => {
    const Bv: NamedPt = { ...B, valence: 2 };
    expect(ruleWinner(voters, [A, Bv], 'plurality')).toBe(1); // B
    expect(ruleWinner(voters, [A, Bv], 'condorcet')).toBe(1); // B now beats A for all voters
  });

  it('lifts the cardinal score of the valenced candidate', () => {
    const plain = computeScores(voters, [A, B])[1][1]; // B's score, no valence
    const lifted = computeScores(voters, [A, { ...B, valence: 2 }])[1][1];
    expect(lifted).toBeGreaterThan(plain);
  });
});
