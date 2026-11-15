import { describe, it, expect } from 'vitest';
import { makeSvgToDomain } from './useDragTouch';

const box = (left: number, top: number, width: number, height: number) =>
  ({ left, top, width, height }) as DOMRect;

// A 400 x 400 viewBox with a 40 inset: the plot spans 40..360, so domain -1..1.
const toDomain = makeSvgToDomain({ width: 400, height: 400, pad: 40 });

describe('makeSvgToDomain', () => {
  it('maps a box of the viewBox’s own aspect straight across', () => {
    const rect = box(100, 50, 200, 200); // scale 0.5
    expect(toDomain(200, 150, rect)).toEqual({ x: 0, y: 0 }); // the centre
    expect(toDomain(100 + 40 * 0.5, 50 + 40 * 0.5, rect)).toEqual({ x: -1, y: 1 }); // top-left of the plot
    expect(toDomain(100 + 360 * 0.5, 50 + 360 * 0.5, rect)).toEqual({ x: 1, y: -1 }); // bottom-right
  });

  it('does not count the margin of a box wider than the drawing', () => {
    // 500 x 200: the 400-unit square is drawn at scale 0.5, 200 wide, centred: 150 px margin each side.
    const rect = box(0, 0, 500, 200);
    expect(toDomain(250, 100, rect)).toEqual({ x: 0, y: 0 });
    // The plot's left edge is at 150 + 40 * 0.5 = 170 px and it is 160 px wide: 25% along is 210.
    expect(toDomain(170, 100, rect).x).toBeCloseTo(-1, 10);
    expect(toDomain(210, 100, rect).x).toBeCloseTo(-0.5, 10);
    // Inside the margin is outside the plot: clamped, not read as the drawing's edge.
    expect(toDomain(20, 100, rect).x).toBe(-1);
  });

  it('does not count the margin of a box taller than the drawing', () => {
    const rect = box(0, 0, 200, 500);
    expect(toDomain(100, 250, rect)).toEqual({ x: 0, y: 0 });
    // The plot's top edge is at 150 + 20 = 170 px, 160 px tall: 25% down is 210, and y is up.
    expect(toDomain(100, 210, rect).y).toBeCloseTo(0.5, 10);
    expect(toDomain(100, 480, rect).y).toBe(-1);
  });

  it('moves with the box: only its position and size count, not the page', () => {
    const a = toDomain(300, 200, box(100, 50, 400, 300));
    const b = toDomain(300 + 40, 200 - 10, box(100 + 40, 50 - 10, 400, 300));
    expect(b).toEqual(a);
  });

  it('does not count the margin either when the viewBox is not square (the Lab replay)', () => {
    // A 360 x 300 viewBox in a box 600 wide and 280 tall (the replay's `maxHeight: 280`): the
    // drawing is scaled to 280 / 300 and is 336 wide, centred: 132 px of margin each side.
    const replay = makeSvgToDomain({ width: 360, height: 300, pad: 28 });
    const rect = box(0, 0, 600, 280);
    const scale = 280 / 300;
    expect(replay(300, 140, rect)).toEqual({ x: 0, y: 0 });
    expect(replay(132 + 28 * scale, 140, rect).x).toBeCloseTo(-1, 10); // the plot's left edge
    expect(replay(132 + (360 - 28) * scale, 140, rect).x).toBeCloseTo(1, 10); // and its right
    expect(replay(50, 140, rect).x).toBe(-1); // inside the margin: clamped
  });

  it('keeps a non-square viewBox exact when the box has its aspect', () => {
    const wide = makeSvgToDomain({ width: 600, height: 280, pad: 30 });
    const rect = box(10, 10, 300, 140); // scale 0.5
    expect(wide(10 + 300 * 0.5, 10 + 140 * 0.5, rect)).toEqual({ x: 0, y: 0 });
  });
});
