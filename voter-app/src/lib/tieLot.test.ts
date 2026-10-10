import { describe, it, expect } from 'vitest';
import { drawName, bestIndex, drawIndex, isTied } from './tieLot';

// fast_api_voter/api/tests/test_tie_lot.py pins the same values: the two engines must
// draw the same candidate from the same tie.
describe('the tie lot', () => {
  it.each([
    [['Ann', 'Ben'], 0, 'Ben'],
    [['Ann', 'Ben'], 7, 'Ann'],
    [['Alice', 'Bob', 'Carol'], 0, 'Carol'],
    [['Alice', 'Bob', 'Carol'], 7, 'Alice'],
    [['Zoé', 'Émile', 'Ana'], 0, 'Zoé'],
    [['Zoé', 'Émile', 'Ana'], 7, 'Ana'],
    [['C0', 'C1', 'C2', 'C3'], 0, 'C3'],
    [['C0', 'C1', 'C2', 'C3'], 7, 'C2'],
    [['Ann', 'Anna'], 0, 'Ann'], // one name a prefix of the other
    [['Ann', 'Anna'], 7, 'Anna'],
  ] as const)('%j with seed %i draws %s, whatever the order', (names, seed, drawn) => {
    expect(drawName(names, seed)).toBe(drawn);
    expect(drawName([...names].reverse(), seed)).toBe(drawn);
  });

  it('sorts by code point, as Python does (an astral character sorts after U+FFFD)', () => {
    expect(drawName(['\u{1F600}', '�'], 0)).toBe(drawName(['�', '\u{1F600}'], 0));
  });

  it('float noise is a tie, a real gap is not (as tie_lot.py)', () => {
    expect(isTied(3.178053830347945, 3.1780538303479458)).toBe(true);
    expect(isTied(-Infinity, -Infinity)).toBe(true);
    expect(isTied(1, 1.000001)).toBe(false);
    expect(isTied(Infinity, 1e308)).toBe(false);
    const names = ['Bob', 'Zed', 'Mo'];
    expect(bestIndex([3.1780538303479458, 3.178053830347945, 1], names)).toBe(
      names.indexOf(drawName(['Bob', 'Zed']))
    );
  });

  it('bestIndex falls back to the first index when no value ranks (NaN)', () => {
    expect(bestIndex([NaN, NaN], ['A', 'B'])).toBe(0);
  });

  it('a name two candidates share never picks one outside the tie', () => {
    // Indices 1 and 2 tie; index 0 shares index 2's name but is not tied.
    expect([1, 2]).toContain(bestIndex([0, 5, 5], ['Ann', 'Ben', 'Ann']));
  });

  it('bestIndex draws only among the tied top, and keeps a strict maximum', () => {
    const names = ['Cy', 'Ben', 'Ann'];
    expect(bestIndex([1, 3, 3], names)).toBe(names.indexOf(drawName(['Ann', 'Ben'])));
    expect(bestIndex([1, 3, 2], names)).toBe(1);
    expect(drawIndex([0, 2], names)).toBe(names.indexOf(drawName(['Cy', 'Ann'])));
  });
});
