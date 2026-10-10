// The leader map in words (PLAN_BEYOND_CI W3.6): where each candidate stands and the share
// of voters who rank them first, for a reader who cannot see the map.
import {
  computeRanks,
  pluralityCounts,
  type Dims,
  type NamedPt,
  type Pt,
} from './playgroundVoting';

export interface CandidateSummary {
  name: string;
  /** Its position, one decimal per axis the map shows: "(-0.6, 0.2)". */
  position: string;
  /** Share of voters who rank it first, in whole percent. */
  firstChoicePct: number;
}

export function summarizeMap(voters: Pt[], candidates: NamedPt[], dims: Dims): CandidateSummary[] {
  const counts = pluralityCounts(
    computeRanks(voters, candidates),
    candidates.map(() => true),
    candidates.length
  );
  const axis = (v: number | undefined) => (v ?? 0).toFixed(1).replace('-0.0', '0.0');
  return candidates.map((c, i) => ({
    name: c.name,
    position: `(${[c.x, c.y, c.z].slice(0, dims).map(axis).join(', ')})`,
    firstChoicePct: voters.length ? Math.round((100 * counts[i]) / voters.length) : 0,
  }));
}
