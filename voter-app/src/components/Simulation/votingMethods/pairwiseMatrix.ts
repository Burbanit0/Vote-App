import type { VotingMethodVisualizationProps } from './types';

/**
 * Shared pairwise-count computation for the Condorcet-family visualisations
 * (Minimax, Schulze, Kemeny-Young — all three build a head-to-head matrix
 * before doing anything method-specific with it).
 */

/** counts[a][b] = number of ballots that rank `a` strictly before `b`. */
export function pairwiseCounts(
  rankings: VotingMethodVisualizationProps['rankings'],
  candidates: string[]
): Record<string, Record<string, number>> {
  const counts: Record<string, Record<string, number>> = {};

  candidates.forEach((c1) => {
    counts[c1] = {};
    candidates.forEach((c2) => {
      if (c1 !== c2) counts[c1][c2] = 0;
    });
  });

  candidates.forEach((c1) => {
    candidates.forEach((c2) => {
      if (c1 === c2) return;
      rankings.forEach(({ ranking }) => {
        if (ranking.indexOf(c1) < ranking.indexOf(c2)) counts[c1][c2]++;
      });
    });
  });

  return counts;
}
