// The default affiliation of an identity group: the candidate nearest its ideology centre, on the
// axis voters judge candidates on. The twin of `_nearest_candidate` in
// fast_api_voter/api/domain/theory/workers.py (the backend's default groups): an exact tie is
// drawn by the seeded lot over the tied names (tieLot.ts), never the first listed.
import { bestIndex } from './tieLot';

export function nearestCandidate(
  candidates: ReadonlyArray<{ name: string; x: number }>,
  centre: number,
  seed: number
): string {
  const nearest = bestIndex(
    candidates.map((c) => -Math.abs(c.x - centre)),
    candidates.map((c) => c.name),
    seed
  );
  return candidates[nearest].name;
}
