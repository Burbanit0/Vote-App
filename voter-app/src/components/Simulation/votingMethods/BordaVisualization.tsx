import React from 'react';
import { Card } from 'react-bootstrap';
import MethodBarChart from './MethodBarChart';
import { VotingMethodVisualizationProps } from './types';

/**
 * Borda Count — each rank position gives a fixed number of points
 * (first place = n-1, second = n-2, … last = 0). Candidate with the
 * highest total wins. Often produces a different winner than Plurality
 * because it rewards consensus rather than just first-choice support.
 */
const BordaVisualization: React.FC<VotingMethodVisualizationProps> = ({ rankings, candidates }) => {
  const numCandidates = candidates.length;
  const scores = candidates.reduce(
    (acc, candidate) => {
      acc[candidate] = 0;
      return acc;
    },
    {} as Record<string, number>
  );

  rankings.forEach(({ ranking }) => {
    ranking.forEach((candidate, index) => {
      scores[candidate] += numCandidates - 1 - index;
    });
  });

  return (
    <>
      <p>
        Borda Count assigns points to each candidate based on their position in each voter&apos;s
        ranking. A candidate in first place gets {numCandidates - 1} points, second place gets{' '}
        {numCandidates - 2} points, and so on. The candidate with the most points wins.
      </p>
      <MethodBarChart
        labels={candidates}
        values={candidates.map((candidate) => scores[candidate])}
        seriesName="Borda Scores"
        title="Borda Count Scores"
        yLabel="Total Borda Points"
      />
      <Card.Text className="mt-3">
        <strong>Winner:</strong> {candidates.reduce((a, b) => (scores[a] > scores[b] ? a : b))}
      </Card.Text>
    </>
  );
};

export default BordaVisualization;
