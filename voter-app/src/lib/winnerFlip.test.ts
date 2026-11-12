import { describe, expect, it } from 'vitest';
import { nextFlip, type WinnerMark } from './winnerFlip';

const mark = (winner: string, rule = 'plurality', names = ['A', 'B', 'C']): WinnerMark => ({
  rule,
  names,
  winner,
});

describe('nextFlip', () => {
  it('shows nothing on the first reading, or when there is no winner to compare', () => {
    expect(nextFlip(null, mark('A'), null)).toBeNull();
    expect(nextFlip(mark('A'), null, { from: 'B', to: 'A' })).toBeNull();
  });

  it('names the change when the winner moves under the same method and candidates', () => {
    expect(nextFlip(mark('A'), mark('B'), null)).toEqual({ from: 'A', to: 'B' });
  });

  it('keeps what is showing while the winner stays put', () => {
    const flip = { from: 'A', to: 'B' };
    expect(nextFlip(mark('B'), mark('B'), flip)).toBe(flip);
    expect(nextFlip(mark('A'), mark('A'), null)).toBeNull();
  });

  it('reads the latest change: A, B, then C is "B to C"', () => {
    expect(nextFlip(mark('B'), mark('C'), { from: 'A', to: 'B' })).toEqual({ from: 'B', to: 'C' });
  });

  it('shows nothing once the winner is back where the flip began', () => {
    expect(nextFlip(mark('B'), mark('A'), { from: 'A', to: 'B' })).toBeNull();
  });

  it('is not a flip when the method changes: that is another question', () => {
    expect(nextFlip(mark('A'), mark('B', 'irv'), { from: 'C', to: 'A' })).toBeNull();
  });

  it('is not a flip when the candidates are edited (added, removed, renamed, reordered)', () => {
    expect(nextFlip(mark('A'), mark('B', 'plurality', ['A', 'B']), null)).toBeNull();
    expect(nextFlip(mark('A'), mark('B', 'plurality', ['A', 'B', 'D']), null)).toBeNull();
    expect(nextFlip(mark('A'), mark('B', 'plurality', ['B', 'A', 'C']), null)).toBeNull();
  });
});
