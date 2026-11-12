import { describe, expect, it } from 'vitest';
import {
  approach,
  bounce,
  clamp01,
  coverPolygon,
  dropPose,
  easeInOutCubic,
  finaleDuration,
  finaleHeap,
  momentDraw,
  odometer,
  slipPolygon,
} from './motion';

describe('motion primitives', () => {
  it('clamps to 0 … 1', () => {
    expect([clamp01(-1), clamp01(0.4), clamp01(2)]).toEqual([0, 0.4, 1]);
  });

  it('eases in and out symmetrically', () => {
    expect(easeInOutCubic(0)).toBe(0);
    expect(easeInOutCubic(0.25)).toBeCloseTo(0.0625);
    expect(easeInOutCubic(0.75)).toBeCloseTo(0.9375);
    expect(easeInOutCubic(1)).toBe(1);
  });

  it('bounces from 0 to rest at exactly 1, overshooting nothing', () => {
    expect(bounce(0)).toBe(0);
    expect(bounce(1)).toBe(1);
    for (let f = 0; f <= 1; f += 0.01) expect(bounce(f)).toBeLessThanOrEqual(1);
    // It hits the floor before the end, then lifts off again.
    expect(bounce(1 / 7)).toBeCloseTo(1);
    expect(bounce(0.3)).toBeLessThan(1);
  });

  it('rolls an odometer column only on the last unit before a carry', () => {
    expect(odometer(42, 0)).toBe(2);
    expect(odometer(42.5, 0)).toBeCloseTo(2.5);
    expect(odometer(42.5, 1)).toBe(4);
    expect(odometer(49.5, 1)).toBeCloseTo(4.5);
    expect(odometer(100, 2)).toBe(1);
  });

  it('approaches a target and snaps once close', () => {
    expect(approach(0, 100, 0.1)).toBeCloseTo(10);
    expect(approach(99.9, 100, 0.1)).toBe(100);
  });

  it('builds the slip and the cover as five-point polygons', () => {
    expect(slipPolygon(10, 20)).toBe(
      'polygon(11.0px 21.0px, 23.0px 21.0px, 29.0px 27.0px, 29.0px 45.0px, 11.0px 45.0px)'
    );
    expect(coverPolygon(1000, 500).match(/px/g)).toHaveLength(10);
  });

  it('draws the moment panels in order', () => {
    expect(momentDraw(0, 0)).toBe(1);
    expect(momentDraw(0, 1)).toBe(0);
    expect(momentDraw(1, 4)).toBe(1);
  });

  it('drops each heap ballot from above the box onto its resting place', () => {
    const heap = finaleHeap();
    expect(heap).toHaveLength(100);
    const d = heap[0];
    expect(dropPose(d, d.delay - 1)).toMatchObject({ y: -24, rot: d.r0, o: 0 });
    const end = dropPose(d, finaleDuration(heap));
    expect(end.y).toBeCloseTo(d.y);
    expect(end.rot).toBeCloseTo(d.r);
    expect(end.o).toBe(1);
  });
});
