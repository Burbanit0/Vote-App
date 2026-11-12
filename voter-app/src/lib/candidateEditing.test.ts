import { describe, it, expect } from 'vitest';
import {
  MAX_CANDIDATES,
  MAX_NAME_LENGTH,
  MIN_CANDIDATES,
  addCandidate,
  canAdd,
  canRemove,
  nameProblem,
  nextName,
  placeNewcomer,
  removeCandidate,
  renameCandidate,
} from './candidateEditing';
import { DEFAULT_CONFIG, type ElectionConfig } from '../stores/useElectionStore';

const config = (bias: Record<string, number> = {}): ElectionConfig => ({
  ...DEFAULT_CONFIG,
  information_model: { ...DEFAULT_CONFIG.information_model, media_bias: bias },
});

describe('limits (the backend takes 2 to 8 candidates)', () => {
  it('agree with what the editor allows', () => {
    expect([MIN_CANDIDATES, MAX_CANDIDATES, MAX_NAME_LENGTH]).toEqual([2, 8, 64]);
    expect([canAdd(7), canAdd(8)]).toEqual([true, false]);
    expect([canRemove(3), canRemove(2)]).toEqual([true, false]);
  });
});

describe('nameProblem', () => {
  const others = ['Alice', 'Bob'];
  it('accepts a fresh name, trimmed', () => {
    expect(nameProblem('  Carol ', others)).toBeNull();
  });
  it('refuses an empty or blank name', () => {
    expect(nameProblem('', others)).toBe('empty');
    expect(nameProblem('   ', others)).toBe('empty');
  });
  it('refuses a name past the backend limit, and accepts exactly the limit', () => {
    expect(nameProblem('x'.repeat(MAX_NAME_LENGTH + 1), others)).toBe('tooLong');
    expect(nameProblem('x'.repeat(MAX_NAME_LENGTH), others)).toBeNull();
  });
  it('refuses a name another candidate has, exactly as the backend compares them', () => {
    expect(nameProblem('Alice', others)).toBe('duplicate');
    expect(nameProblem(' Bob ', others)).toBe('duplicate'); // trimmed first
    expect(nameProblem('alice', others)).toBeNull(); // case counts
  });
});

describe('nextName', () => {
  it('counts up from the next free number', () => {
    expect(nextName('Candidate', ['Alice', 'Bob', 'Carol'])).toBe('Candidate 4');
  });
  it('skips a number somebody already took', () => {
    expect(nextName('Candidate', ['A', 'B', 'Candidate 3'])).toBe('Candidate 4');
  });
});

describe('placeNewcomer', () => {
  const near = (a: { x: number; y: number; z?: number }, b: { x: number; y: number; z?: number }) =>
    Math.hypot(a.x - b.x, a.y - b.y, (a.z ?? 0) - (b.z ?? 0));

  it('stays inside the domain cube', () => {
    for (const dims of [1, 2, 3] as const) {
      const p = placeNewcomer(DEFAULT_CONFIG.candidates, dims);
      for (const v of [p.x, p.y, p.z]) expect(Math.abs(v)).toBeLessThanOrEqual(0.9 + 1e-9);
    }
  });

  it('goes where nobody is: farther from every candidate than any existing pair is close', () => {
    const p = placeNewcomer(DEFAULT_CONFIG.candidates, 2);
    for (const c of DEFAULT_CONFIG.candidates) expect(near(p, c)).toBeGreaterThan(0.5);
  });

  it('picks the biggest gap: with one candidate far left, the newcomer is far right', () => {
    const p = placeNewcomer([{ name: 'L', x: -0.9, y: 0 }], 1);
    expect(p.x).toBeCloseTo(0.9, 5);
    expect(p.y).toBe(0);
  });

  it('keeps the dimensions it is not asked about at zero', () => {
    const one = placeNewcomer(DEFAULT_CONFIG.candidates, 1);
    expect([one.y, one.z]).toEqual([0, 0]);
    const two = placeNewcomer(DEFAULT_CONFIG.candidates, 2);
    expect(two.z).toBe(0);
  });

  it('uses depth in 3-D: a candidate high on z pushes the newcomer low on it', () => {
    const p = placeNewcomer([{ name: 'Up', x: 0, y: 0, z: 0.9 }], 3);
    expect(p.z).toBeLessThan(0);
  });

  it('is deterministic, and survives an empty field', () => {
    expect(placeNewcomer(DEFAULT_CONFIG.candidates, 2)).toEqual(
      placeNewcomer(DEFAULT_CONFIG.candidates, 2)
    );
    expect(placeNewcomer([], 2)).toEqual({ x: -0.9, y: -0.9, z: 0 });
  });
});

describe('config patches', () => {
  it('addCandidate appends and leaves the others alone', () => {
    const patch = addCandidate(config(), { name: 'Dana', x: 0.1, y: 0.2 });
    expect(patch.candidates.map((c) => c.name)).toEqual(['Alice', 'Bob', 'Carol', 'Dana']);
    expect(patch.candidates.slice(0, 3)).toEqual(DEFAULT_CONFIG.candidates);
  });

  it('removeCandidate drops that one and keeps the order of the rest', () => {
    const patch = removeCandidate(config(), 1);
    expect(patch.candidates.map((c) => c.name)).toEqual(['Alice', 'Carol']);
  });

  it("removeCandidate drops that candidate's media bias too", () => {
    const patch = removeCandidate(config({ Alice: 0.4, Bob: -0.2 }), 0);
    expect(patch.information_model.media_bias).toEqual({ Bob: -0.2 });
  });

  it('renameCandidate trims, keeps position and valence, and renames only that one', () => {
    const base = config();
    base.candidates = base.candidates.map((c, i) => (i === 1 ? { ...c, valence: 0.3 } : c));
    const patch = renameCandidate(base, 1, '  Robert ');
    expect(patch.candidates.map((c) => c.name)).toEqual(['Alice', 'Robert', 'Carol']);
    expect(patch.candidates[1]).toMatchObject({ x: 0.5, y: 0.2, valence: 0.3 });
  });

  it('renameCandidate moves the media bias to the new name', () => {
    const patch = renameCandidate(config({ Bob: -0.2, Alice: 0.4 }), 1, 'Robert');
    expect(patch.information_model.media_bias).toEqual({ Alice: 0.4, Robert: -0.2 });
  });

  it('renameCandidate leaves a bias map with no entry for it untouched', () => {
    const patch = renameCandidate(config({ Alice: 0.4 }), 1, 'Robert');
    expect(patch.information_model.media_bias).toEqual({ Alice: 0.4 });
  });

  it('never mutates the config it was given', () => {
    const base = config({ Bob: -0.2 });
    const snapshot = JSON.stringify(base);
    renameCandidate(base, 1, 'Robert');
    removeCandidate(base, 0);
    addCandidate(base, { name: 'Dana', x: 0, y: 0 });
    expect(JSON.stringify(base)).toBe(snapshot);
  });
});
