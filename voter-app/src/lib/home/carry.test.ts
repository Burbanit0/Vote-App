import { describe, expect, it } from 'vitest';
import { candidateColor } from '../palette';
import { homeExampleCandidates } from './carry';
import { CANDIDATES } from './scenario';

describe('homeExampleCandidates', () => {
  it('is the home example, in the playground order and domain', () => {
    expect(homeExampleCandidates()).toEqual([
      { name: 'Alice', x: -0.45, y: 0.37 },
      { name: 'Bob', x: 0.65, y: 0.32 },
      { name: 'Carol', x: -0.08, y: -0.11 },
    ]);
  });

  it('keeps the colours the home gives each name (blue, red, green)', () => {
    const colours = Object.fromEntries(CANDIDATES.map((c) => [c.name, c.color]));
    // The home's hues are its own tokens; the playground's are the palette's. Same family, in
    // the same order: Alice blue, Bob red, Carol green.
    expect(homeExampleCandidates().map((c, i) => [c.name, candidateColor(i)])).toEqual([
      ['Alice', '#2563eb'],
      ['Bob', '#dc2626'],
      ['Carol', '#16a34a'],
    ]);
    expect(colours.Alice).toMatch(/^#2F5B/i);
    expect(colours.Bob).toMatch(/^#C835/i);
    expect(colours.Carol).toMatch(/^#1E8A/i);
  });

  it('keeps the picture: left to right, top to bottom, as on the home map', () => {
    const [alice, bob, carol] = homeExampleCandidates();
    const home = Object.fromEntries(CANDIDATES.map((c) => [c.name, c]));
    expect(alice.x).toBeLessThan(carol.x);
    expect(carol.x).toBeLessThan(bob.x);
    // y grows down the home screen and up the playground's: the lowest on screen is Carol.
    expect(home.Carol.y).toBeGreaterThan(home.Alice.y);
    expect(carol.y).toBeLessThan(alice.y);
    expect(carol.y).toBeLessThan(bob.y);
  });

  it('stays inside the playground domain, to the hundredth', () => {
    for (const c of homeExampleCandidates()) {
      for (const v of [c.x, c.y]) {
        expect(Math.abs(v)).toBeLessThanOrEqual(1);
        expect(Math.round(v * 100) / 100).toBe(v);
      }
    }
  });
});
