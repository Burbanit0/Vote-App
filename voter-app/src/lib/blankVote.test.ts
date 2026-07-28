import { describe, it, expect } from 'vitest';
import { blankVerdict, allBlankVerdicts, BLANK_LENSES } from './blankVote';

// Same ballots, four fates. The point is that the counting rule — not the
// voters — decides. These lock the mechanical verdict of each lens.

describe('blankVote — one result, four regimes', () => {
  // A: 38, B: 32, C: 10, blank: 20 (as fractions of all ballots).
  const shares = [0.38, 0.32, 0.1];
  const blank = 0.2;

  it('france_today: blanks excluded → A elected on its share of the candidate votes', () => {
    const v = blankVerdict(shares, blank, 'france_today');
    expect(v.outcome).toBe('elected');
    expect(v.winner).toBe(0);
    expect(v.redo).toBe(false);
    expect(v.winnerShareOfExprimes).toBeCloseTo(0.38 / 0.8); // 47.5% of the exprimés
  });

  it('in_exprimes: blanks in the denominator can strip the majority', () => {
    const v = blankVerdict(shares, blank, 'in_exprimes');
    expect(v.winnerShareOfExprimes).toBeCloseTo(0.38); // 38% of all ballots
    expect(v.outcome).toBe('no_majority');
    expect(v.redo).toBe(true);
  });

  it('in_exprimes: a real majority still elects', () => {
    const v = blankVerdict([0.55, 0.2, 0.05], 0.2, 'in_exprimes');
    expect(v.outcome).toBe('elected');
    expect(v.redo).toBe(false);
  });

  it('competitive: the blank reopens the field only when it outpolls the top', () => {
    expect(blankVerdict(shares, blank, 'competitive').outcome).toBe('elected'); // 20% < 38%
    const v = blankVerdict([0.3, 0.15, 0.1], 0.45, 'competitive'); // blank leads
    expect(v.outcome).toBe('blank_wins');
    expect(v.winner).toBeNull();
    expect(v.redo).toBe(true);
  });

  it('threshold: only a blank majority (>50%) annuls', () => {
    expect(blankVerdict(shares, blank, 'threshold').outcome).toBe('elected');
    const v = blankVerdict([0.3, 0.1, 0.05], 0.55, 'threshold');
    expect(v.outcome).toBe('annulled');
    expect(v.redo).toBe(true);
  });

  it('allBlankVerdicts returns one verdict per lens, in order', () => {
    const all = allBlankVerdicts(shares, blank);
    expect(all.map((v) => v.lens)).toEqual(BLANK_LENSES);
  });

  it('degenerate input (no ballots) never throws and elects no one meaningfully', () => {
    const v = blankVerdict([], 0, 'france_today');
    expect(v.winner).toBeNull();
    expect(Number.isFinite(v.winnerShareOfExprimes)).toBe(true);
  });
});
