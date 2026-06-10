import React from 'react';
import MethodBarChart from './MethodBarChart';
import { VotingMethodVisualizationProps } from './types';

/**
 * Plurality — first-choice-only counting. The candidate with the most
 * first-choice votes wins. Naive but the most widely-used method in
 * real-world elections.
 */
const PluralityVisualization: React.FC<VotingMethodVisualizationProps> = ({
  rankings,
  candidates,
}) => {
  const firstChoiceCounts = candidates.reduce(
    (acc, candidate) => {
      acc[candidate] = 0;
      return acc;
    },
    {} as Record<string, number>
  );

  rankings.forEach(({ ranking }) => {
    if (ranking.length > 0) {
      firstChoiceCounts[ranking[0]]++;
    }
  });

  return (
    <>
      <p>
        Plurality counts only first-choice votes. The candidate with the most first-choice votes
        wins.
      </p>
      <MethodBarChart
        labels={candidates}
        values={candidates.map((candidate) => firstChoiceCounts[candidate])}
        seriesName="First Choice Votes"
        title="First Choice Votes Distribution"
        yLabel="Number of Votes"
      />
      <p className="mt-3">
        <strong>Winner:</strong>{' '}
        {candidates.reduce((a, b) => (firstChoiceCounts[a] > firstChoiceCounts[b] ? a : b))}
      </p>
    </>
  );
};

export default PluralityVisualization;
