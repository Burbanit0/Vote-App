import { describe, it, expect } from 'vitest';
import { CANDIDATE_PALETTE, candidateColor, candidateColorByName } from './palette';

describe('palette — one candidate identity', () => {
  it('is the palette the central map already used (the signature surface moves for nobody)', () => {
    // Locked deliberately: changing these repaints the instrument people know.
    expect(CANDIDATE_PALETTE[0]).toBe('#2563eb');
    expect(CANDIDATE_PALETTE[1]).toBe('#dc2626');
    expect(CANDIDATE_PALETTE[2]).toBe('#16a34a');
    expect(CANDIDATE_PALETTE).toHaveLength(8);
  });

  it('gives every candidate a colour, wrapping past the end of the palette', () => {
    expect(candidateColor(0)).toBe(CANDIDATE_PALETTE[0]);
    expect(candidateColor(8)).toBe(CANDIDATE_PALETTE[0]); // wraps
    expect(candidateColor(9)).toBe(CANDIDATE_PALETTE[1]);
    // A negative index must not produce `undefined` (would paint nothing).
    expect(candidateColor(-1)).toBe(CANDIDATE_PALETTE[7]);
  });

  it('by-name lookup agrees with by-index — the two surfaces cannot disagree', () => {
    const names = ['Alice', 'Bob', 'Carol'];
    names.forEach((n, i) => expect(candidateColorByName(n, names)).toBe(candidateColor(i)));
  });

  it('falls back to neutral grey for an unknown or absent name', () => {
    expect(candidateColorByName(null, ['Alice'])).toBe('#9ca3af');
    expect(candidateColorByName('Nobody', ['Alice'])).toBe('#9ca3af');
  });
});
