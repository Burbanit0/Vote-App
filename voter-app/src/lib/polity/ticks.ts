/**
 * lib/polity/ticks.ts — the run explorer's notion of time, pure.
 *
 * A polity run advances in ticks, `ticksPerYear` to a simulated year. The page
 * addresses a tick in its URL and loads frames from the API in fixed chunks of
 * FRAME_CHUNK ticks (the API refuses longer spans), so a tick always maps to
 * the same chunk and chunks cache independently.
 */

/** The API serves at most this many frames per request (explorer_workers.MAX_FRAME_SPAN). */
export const FRAME_CHUNK = 40;

export interface TickRange {
  from: number;
  to: number;
}

/** The chunk holding `tick`, cut at the run's last tick. */
export function chunkOf(tick: number, lastTick: number): TickRange {
  const from = Math.floor(tick / FRAME_CHUNK) * FRAME_CHUNK;
  return { from, to: Math.min(from + FRAME_CHUNK - 1, lastTick) };
}

/** A whole tick inside [0, lastTick]; anything unreadable goes to 0. */
export function clampTick(value: number, lastTick: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(Math.max(Math.trunc(value), 0), Math.max(lastTick, 0));
}

export interface SimulatedDate {
  /** 1-based simulated year. */
  year: number;
  /** 1-based quarter (tick within the year). */
  quarter: number;
}

/** Tick 0 is year 1, quarter 1; the ticks of a year are its quarters. */
export function simulatedDate(tick: number, ticksPerYear: number): SimulatedDate {
  const perYear = Math.max(ticksPerYear, 1);
  return { year: Math.floor(tick / perYear) + 1, quarter: (tick % perYear) + 1 };
}

/**
 * The years a run covers, counting only years it completed.
 *
 * A run's last tick can land mid-year: an 8-year run killed in its fifth year covers 4,
 * not 5, and not "4 or 5 depending on the quarter it stopped in". The tick fact beside
 * this one says which year the tick shown belongs to (`simulatedDate`), so this one is
 * the run's length, never rounded up to a year it did not finish.
 */
export function completedYears(lastTick: number, ticksPerYear: number): number {
  return Math.floor((Math.max(lastTick, 0) + 1) / Math.max(ticksPerYear, 1));
}
