import type { ElectionCandidate } from '../../stores/useElectionStore';
import { CANDIDATES } from './scenario';

// The homepage teaches one electorate: Alice, Bob and Carol on a map, three rules, three winners.
// "Open the instrument" used to load France 2002 (eight candidates), a different story, and over
// the visitor's own saved candidates. This is the home example, in the playground's own terms,
// so the instrument opens on the picture the visitor has just seen.

/** The order the playground colours them in (blue, red, green): the home's colours, name for name. */
const ORDER = ['Alice', 'Bob', 'Carol'];

/** Two decimals: tidy to read, store and compare. */
const hundredth = (n: number): number => Math.round(n * 100) / 100;

/**
 * The home example's candidates in playground coordinates. The home map is a unit square with y
 * pointing down the screen; the playground's domain is [-1, 1] with y pointing up: the same
 * picture, left to right and top to bottom.
 */
export function homeExampleCandidates(): ElectionCandidate[] {
  return ORDER.map((name) => {
    const c = CANDIDATES.find((k) => k.name === name);
    if (!c) throw new Error(`home example has no candidate ${name}`);
    return { name, x: hundredth(2 * c.x - 1), y: hundredth(1 - 2 * c.y) };
  });
}
