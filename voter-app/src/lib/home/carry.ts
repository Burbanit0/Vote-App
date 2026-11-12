import {
  DEFAULT_CONFIG,
  type ElectionCandidate,
  type ElectionConfig,
} from '../../stores/useElectionStore';
import { CANDIDATES } from './scenario';

// The homepage teaches one electorate: Alice, Bob and Carol on a map, three rules, three winners.
// "Open the instrument" used to load France 2002 (eight candidates), a different story, and over
// the visitor's own candidates. This is the home example's cast, in the playground's own terms,
// so the instrument opens on the picture the visitor has just seen. (The cast only: the home's
// hundred hand-placed voters are not the playground's electorate, which draws its own.)

/** Where each name sits in the playground's colour order (blue, red, green): the home's hues. */
const SLOT: Record<string, number> = { Alice: 0, Bob: 1, Carol: 2 };

/** Two decimals: tidy to read, store and compare. */
const hundredth = (n: number): number => Math.round(n * 100) / 100;

/**
 * The home example's candidates in playground coordinates. The home map is a unit square with y
 * pointing down the screen; the playground's domain is [-1, 1] with y pointing up: the same
 * picture, left to right and top to bottom.
 */
export function homeExampleCandidates(): ElectionCandidate[] {
  return [...CANDIDATES]
    .sort((a, b) => SLOT[a.name] - SLOT[b.name])
    .map((c) => ({ name: c.name, x: hundredth(2 * c.x - 1), y: hundredth(1 - 2 * c.y) }));
}

/**
 * Whether the visitor has made no choice yet: the config in memory is still the default one. Read
 * from memory, not from storage: an edit still waiting for its (debounced) write counts, and an
 * unreadable or corrupt saved value, which the store loads as the default, does not.
 */
export const isUntouched = (config: ElectionConfig): boolean =>
  JSON.stringify(config) === JSON.stringify(DEFAULT_CONFIG);
