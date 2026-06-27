import { describe, it, expect } from 'vitest';
import { wilson, wilsonFromRate, pctPm } from './ci';

describe('wilson score interval', () => {
  it('brackets the observed proportion and stays inside [0,1]', () => {
    const iv = wilson(30, 60); // 50% over 60 draws
    expect(iv.p).toBe(0.5);
    expect(iv.lo).toBeGreaterThan(0);
    expect(iv.hi).toBeLessThan(1);
    expect(iv.lo).toBeLessThan(0.5);
    expect(iv.hi).toBeGreaterThan(0.5);
  });

  it('never escapes [0,1] at the extremes (where the normal approx fails)', () => {
    const sure = wilson(60, 60); // 100% — normal approx would give hi > 1
    expect(sure.hi).toBeLessThanOrEqual(1);
    expect(sure.lo).toBeGreaterThan(0); // Wilson still admits uncertainty
    const none = wilson(0, 60);
    expect(none.lo).toBe(0);
    expect(none.hi).toBeLessThan(1);
  });

  it('tightens as the sample grows', () => {
    expect(wilson(6, 12).half).toBeGreaterThan(wilson(600, 1200).half); // same p, more n
  });

  it('degenerate n=0 is maximally uncertain, not NaN', () => {
    const iv = wilson(0, 0);
    expect(iv.half).toBe(0.5);
    expect(Number.isNaN(iv.half)).toBe(false);
  });

  it('wilsonFromRate recovers the count and pctPm formats it', () => {
    expect(wilsonFromRate(0.5, 60).p).toBe(0.5);
    expect(pctPm(wilson(30, 60))).toMatch(/^50% ± \d+%$/);
  });
});
