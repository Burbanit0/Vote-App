import React from 'react';
import { Card } from 'react-bootstrap';
import { Bar } from 'react-chartjs-2';
import './_chartjs';                          // side-effect: register Chart.js
import { VotingMethodVisualizationProps, VIZ_COLORS } from './types';

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

  const data = {
    labels: candidates,
    datasets: [
      {
        label: 'First Choice Votes',
        data: candidates.map((candidate) => firstChoiceCounts[candidate]),
        backgroundColor: VIZ_COLORS,
      },
    ],
  };

  return (
    <>
      <p>
        Plurality counts only first-choice votes. The candidate with the most first-choice votes
        wins.
      </p>
      <Bar
        data={data}
        options={{
          responsive: true,
          plugins: {
            title: {
              display: true,
              text: 'First Choice Votes Distribution',
            },
          },
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: 'Number of Votes',
              },
            },
          },
        }}
      />
      <Card.Text className="mt-3">
        <strong>Winner:</strong>{' '}
        {candidates.reduce((a, b) => (firstChoiceCounts[a] > firstChoiceCounts[b] ? a : b))}
      </Card.Text>
    </>
  );
};

export default PluralityVisualization;
