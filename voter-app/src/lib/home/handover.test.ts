import { describe, expect, it } from 'vitest';
import { countViewport, handoverFrame, handoverProgress } from './handover';
import { CANDIDATES, VOTERS } from './scenario';
import { MAP, candidatePoint, voterPoint } from './countFrame';

const hero = { left: 800, top: 60, width: 500, height: 350 };
const count = { left: 0, top: 200, width: 1100, height: 550 };

describe('the hero-to-count handover', () => {
  it('measures progress between the two scroll positions, clamped', () => {
    expect(handoverProgress(-50, 0, 700)).toBe(0);
    expect(handoverProgress(350, 0, 700)).toBe(0.5);
    expect(handoverProgress(900, 0, 700)).toBe(1);
    // A handover with no room to run is already done.
    expect(handoverProgress(10, 10, 10)).toBe(0);
    expect(handoverProgress(11, 10, 10)).toBe(1);
  });

  it('fits the count drawing in its box, centred', () => {
    const vp = countViewport(count);
    expect(vp.s).toBe(1);
    expect(vp.point(0, 90)).toEqual({ x: 50, y: 200 });
  });

  it('starts exactly on the hero map', () => {
    const f = handoverFrame(0, hero, count);
    expect(f.card).toEqual({ x: 800, y: 60, w: 500, h: 350, r: 10 });
    expect(f.voters[0].x).toBeCloseTo(800 + VOTERS[0].x * 500);
    expect(f.voters[0].y).toBeCloseTo(60 + VOTERS[0].y * 350);
    expect(f.voters[0].r).toBeCloseTo(4.5);
    expect(f.candidates[1].x).toBeCloseTo(800 + CANDIDATES[1].x * 500);
    expect(f.grey).toBe(0);
    expect(f.voterOpacity).toBeCloseTo(0.6);
  });

  it('lands exactly on the count map, every voter grey', () => {
    const f = handoverFrame(1, hero, count);
    const vp = countViewport(count);
    const close = (got: Record<string, number>, want: Record<string, number>) =>
      Object.entries(want).forEach(([k, v]) => expect(got[k]).toBeCloseTo(v));
    close(f.card, { ...vp.point(MAP.x, MAP.y), w: MAP.w, h: MAP.h, r: 12 });
    const v = vp.point(voterPoint(7).x, voterPoint(7).y);
    close({ ...f.voters[7] }, { ...v, r: 3.2 });
    const c = vp.point(candidatePoint(2).x, candidatePoint(2).y);
    close({ ...f.candidates[2] }, { ...c, r: 8, labelY: c.y - 16, size: 15 });
    expect(f.grey).toBe(1);
  });

  it('turns grey only in the last part of the flight', () => {
    expect(handoverFrame(0.5, hero, count).grey).toBe(0);
    expect(handoverFrame(0.775, hero, count).grey).toBeCloseTo(0.5);
  });
});
