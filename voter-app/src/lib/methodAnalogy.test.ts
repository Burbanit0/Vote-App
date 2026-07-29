import { describe, it, expect } from 'vitest';
import { METHOD_ANALOGY, methodAnalogy, METHOD_INFO, methodKey } from './methodInfo';

// Phase-6 analogies. Bounded (not every method), but every entry must be a real
// method key with both locales — and aliases must resolve through methodKey.

describe('method analogies', () => {
  it('every analogy targets a real method and has fr + en', () => {
    for (const [id, a] of Object.entries(METHOD_ANALOGY)) {
      expect(METHOD_INFO[id], `${id} is a canonical method`).toBeDefined();
      expect(a.fr, `${id}.fr`).toBeTruthy();
      expect(a.en, `${id}.en`).toBeTruthy();
    }
  });

  it('covers the common newcomer methods', () => {
    for (const id of ['plurality', 'irv', 'condorcet', 'approval', 'borda'])
      expect(METHOD_ANALOGY[id], id).toBeDefined();
  });

  it('methodAnalogy resolves aliases and returns null for the unknown', () => {
    expect(methodAnalogy('copeland', 'fr')).toBe(METHOD_ANALOGY[methodKey('copeland')].fr);
    expect(methodAnalogy('star_voting', 'en')).toBe(METHOD_ANALOGY.star.en);
    expect(methodAnalogy('kemeny', 'fr')).toBe(METHOD_ANALOGY[methodKey('kemeny')].fr); // aliases to kemeny_young
    expect(methodAnalogy('schulze', 'fr')).toBeNull(); // no analogy → null, safely hidden
  });
});
