import { describe, expect, it } from 'vitest';
import { candidateColor } from '../palette';
import { DEFAULT_CONFIG } from '../../stores/useElectionStore';
import { homeExampleCandidates, isUntouched } from './carry';
import { CANDIDATES } from './scenario';

describe('homeExampleCandidates', () => {
  it('is the home example, in the playground order and domain', () => {
    expect(homeExampleCandidates()).toEqual([
      { name: 'Alice', x: -0.45, y: 0.37 },
      { name: 'Bob', x: 0.65, y: 0.32 },
      { name: 'Carol', x: -0.08, y: -0.11 },
    ]);
  });

  it('keeps the hue the home gives each name: the palette order matches it', () => {
    // The two sets are different tokens (the home's own, the playground's palette): compare them
    // with each other, by the channel that dominates.
    const dominant = (hex: string): number => {
      const ch = [1, 3, 5].map((k) => parseInt(hex.slice(k, k + 2), 16));
      return ch.indexOf(Math.max(...ch));
    };
    const home = Object.fromEntries(CANDIDATES.map((c) => [c.name, c.color]));
    homeExampleCandidates().forEach((c, i) => {
      expect(dominant(candidateColor(i)), c.name).toBe(dominant(home[c.name]));
    });
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

describe('isUntouched', () => {
  it('is true for the default config, a copy of it included', () => {
    expect(isUntouched(DEFAULT_CONFIG)).toBe(true);
    expect(isUntouched({ ...DEFAULT_CONFIG })).toBe(true);
  });

  it('is false once any candidate was moved, renamed, added or removed', () => {
    const [a, ...rest] = DEFAULT_CONFIG.candidates;
    for (const candidates of [
      [{ ...a, x: a.x + 0.1 }, ...rest],
      [{ ...a, name: 'Zed' }, ...rest],
      [a, ...rest, { name: 'Dan', x: 0, y: 0 }],
      rest,
    ]) {
      expect(isUntouched({ ...DEFAULT_CONFIG, candidates })).toBe(false);
    }
  });

  it('is false when anything else of the config was chosen (a scenario, a seed)', () => {
    expect(isUntouched({ ...DEFAULT_CONFIG, seed: 2002 })).toBe(false);
  });
});
