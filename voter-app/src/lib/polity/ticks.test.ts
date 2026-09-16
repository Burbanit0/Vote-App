import { FRAME_CHUNK, chunkOf, clampTick, completedYears, simulatedDate } from './ticks';

describe('polity ticks', () => {
  it('maps every tick to a fixed chunk of the API span, cut at the last tick', () => {
    expect(FRAME_CHUNK).toBe(40);
    expect(chunkOf(0, 32)).toEqual({ from: 0, to: 32 });
    expect(chunkOf(39, 120)).toEqual({ from: 0, to: 39 });
    expect(chunkOf(40, 120)).toEqual({ from: 40, to: 79 });
    expect(chunkOf(119, 119)).toEqual({ from: 80, to: 119 });
  });

  it('clamps a tick into the run', () => {
    expect(clampTick(-3, 12)).toBe(0);
    expect(clampTick(7.9, 12)).toBe(7);
    expect(clampTick(99, 12)).toBe(12);
    expect(clampTick(Number.NaN, 12)).toBe(0);
    expect(clampTick(5, -1)).toBe(0);
  });

  it('reads a tick as a simulated year and quarter', () => {
    expect(simulatedDate(0, 4)).toEqual({ year: 1, quarter: 1 });
    expect(simulatedDate(9, 4)).toEqual({ year: 3, quarter: 2 });
    expect(simulatedDate(3, 0)).toEqual({ year: 4, quarter: 1 });
  });

  it('counts the years a run completed, never the one it stopped inside', () => {
    expect(completedYears(11, 4)).toBe(3); // three full years
    expect(completedYears(12, 4)).toBe(3); // one tick into the fourth
    expect(completedYears(13, 4)).toBe(3); // halfway through it, still three
    expect(completedYears(15, 4)).toBe(4);
    expect(completedYears(0, 4)).toBe(0);
    expect(completedYears(-3, 4)).toBe(0); // a run with no tick at all
    expect(completedYears(3, 0)).toBe(4); // no ticks per year reads as one, as simulatedDate does
  });
});
