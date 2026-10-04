/**
 * lib/polity/playerClock.ts — the tick player's speeds and keys, pure.
 *
 * The tick itself lives in the page URL (PolityController); the player only
 * holds whether playback runs and how fast, and turns keys into the next tick.
 */

export const PLAYER_SPEEDS = [1, 2, 4, 8] as const;
/** Ticks advanced per second of playback. */
export type PlayerSpeed = (typeof PLAYER_SPEEDS)[number];

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
