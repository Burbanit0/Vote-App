/**
 * lib/polity/urlState.ts — the run explorer's URL, read and checked, pure.
 *
 * The page keeps what it shows in the URL (`?run=&tick=&lens=&citizen=`), so a
 * view can be linked and the browser's back button walks through it. Anything
 * unreadable falls back to the page's default instead of breaking it.
 */
import { parseTickParam } from './ticks';

/** How the population map colours citizens (population map, F3). */
export const POLITY_LENSES = ['activity', 'act', 'vote', 'candidacy', 'party'] as const;
export type PolityLens = (typeof POLITY_LENSES)[number];
export const DEFAULT_LENS: PolityLens = 'activity';

export function parseLens(raw: string | null): PolityLens {
  return (POLITY_LENSES as readonly string[]).includes(raw ?? '')
    ? (raw as PolityLens)
    : DEFAULT_LENS;
}

/** A citizen id inside the population, or null. */
export function parseCitizen(raw: string | null, population: number): number | null {
  const id = parseTickParam(raw);
  return id !== null && id < population ? id : null;
}

/** The run to show: the one the URL names when the server lists it, else the first listed. */
export function pickRun(requested: string | null, keys: readonly string[]): string | null {
  if (requested !== null && keys.includes(requested)) return requested;
  return keys[0] ?? null;
}
