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

/** A point on the axes the map shows, one decimal each: "(-0.6, 0.2)". */
export function position(p: Pt, dims: Dims): string {
  const axis = (v: number | undefined) => (v ?? 0).toFixed(1).replace('-0.0', '0.0');
  return `(${[p.x, p.y, p.z].slice(0, dims).map(axis).join(', ')})`;
}

export function summarizeMap(voters: Pt[], candidates: NamedPt[], dims: Dims): CandidateSummary[] {
  const counts = pluralityCounts(
    computeRanks(voters, candidates),
    candidates.map(() => true),
    candidates.length
  );
  return candidates.map((c, i) => ({
    name: c.name,
    position: position(c, dims),
    firstChoicePct: voters.length ? Math.round((100 * counts[i]) / voters.length) : 0,
  }));
}
