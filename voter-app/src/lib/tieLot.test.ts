import { describe, it, expect } from 'vitest';
import { drawName, bestIndex, drawIndex } from './tieLot';

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

  it('bestIndex draws only among the tied top, and keeps a strict maximum', () => {
    const names = ['Cy', 'Ben', 'Ann'];
    expect(bestIndex([1, 3, 3], names)).toBe(names.indexOf(drawName(['Ann', 'Ben'])));
    expect(bestIndex([1, 3, 2], names)).toBe(1);
    expect(drawIndex([0, 2], names)).toBe(names.indexOf(drawName(['Cy', 'Ann'])));
  });
});
