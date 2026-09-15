/**
 * lib/polity/playerClock.ts — the tick player's clock, as a pure reducer.
 *
 * The tick itself lives in the page URL (PolityController); the clock only says
 * whether playback runs and how fast, and turns keys, buttons and timer beats
 * into the next tick. Playback stops on its own at the run's last tick, and
 * never starts from there: play from the end rewinds to the start first.
 */

export const PLAYER_SPEEDS = [1, 2, 4, 8] as const;
/** Ticks advanced per second of playback. */
export type PlayerSpeed = (typeof PLAYER_SPEEDS)[number];

export interface PlayerState {
  playing: boolean;
  speed: PlayerSpeed;
}

export type PlayerAction =
  { type: 'toggle' } | { type: 'pause' } | { type: 'speed'; speed: PlayerSpeed };

export const INITIAL_PLAYER: PlayerState = { playing: false, speed: 2 };

export function playerReducer(state: PlayerState, action: PlayerAction): PlayerState {
  switch (action.type) {
    case 'toggle':
      return { ...state, playing: !state.playing };
    case 'pause':
      return state.playing ? { ...state, playing: false } : state;
    case 'speed':
      return { ...state, speed: action.speed };
  }
}

/** Milliseconds between two timer beats at `speed`. */
export function beatMs(speed: PlayerSpeed): number {
  return 1000 / speed;
}

/**
 * Where one beat of playback takes the player: the next tick, or null when the
 * run's end is reached (playback then stops).
 */
export function nextBeat(tick: number, lastTick: number): number | null {
  return tick < lastTick ? tick + 1 : null;
}

/** The tick playback starts from: the start again when it would begin at the end. */
export function playFrom(tick: number, lastTick: number): number {
  return tick >= lastTick ? 0 : tick;
}

/**
 * A key on the player, as the tick it moves to, or 'toggle' for Space; null for
 * a key the player does not handle. PageUp/PageDown move a simulated year.
 */
export function keyTarget(
  key: string,
  tick: number,
  lastTick: number,
  ticksPerYear: number
): number | 'toggle' | null {
  const clamp = (t: number) => Math.min(Math.max(t, 0), lastTick);
  switch (key) {
    case ' ':
      return 'toggle';
    case 'ArrowRight':
      return clamp(tick + 1);
    case 'ArrowLeft':
      return clamp(tick - 1);
    case 'PageDown':
      return clamp(tick + ticksPerYear);
    case 'PageUp':
      return clamp(tick - ticksPerYear);
    case 'Home':
      return 0;
    case 'End':
      return lastTick;
    default:
      return null;
  }
}
