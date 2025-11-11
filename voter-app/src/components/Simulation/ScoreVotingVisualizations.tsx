// ScoreVotingVisualizations.tsx
import React from 'react';
import { Card, Table, ProgressBar, Badge } from 'react-bootstrap';
import { Bar, Radar, Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, PointElement, LineElement, RadialLinearScale, ArcElement } from 'chart.js';
import { ScoreVote, ScoreVotingComparisonProps, ScoreVotingResult } from '../../types';

ChartJS.register(
  CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend,
  PointElement, LineElement, RadialLinearScale, ArcElement
);

interface ScoreVotingVisualizationProps {
  scores: ScoreVote[];
  candidates: string[];
  result: ScoreVotingResult;
}

const ScoreVotingVisualizations: React.FC<ScoreVotingComparisonProps> = ({ scores, candidates, results }) => {
  return (
    <div className="score-voting-comparison">
      <h3 className="mb-4">Score-Based Voting Method Comparison</h3>

      {/* Summary of winners */}
      <div className="card mb-4">
        <div className="card-header">
          <h5>Winners Summary</h5>
        </div>
        <div className="card-body">
          <div className="row">
            {Object.entries(results).map(([methodKey, methodResult]) => (
              <div key={methodKey} className="col-md-4 mb-3">
                <div className="card h-100">
                  <div className="card-body">
                    <h6 className="card-title">{methodResult.method}</h6>
                    <p className="card-text">
                      <strong>Winner:</strong> {methodResult.winner || 'None'}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Individual method visualizations */}
      <SimpleScoreVisualization
        scores={scores}
        candidates={candidates}
        result={results.simple_score}
      />

      <STARVotingVisualization
        scores={scores}
        candidates={candidates}
        result={results.star_voting}
      />

      <MedianVotingVisualization
        scores={scores}
        candidates={candidates}
        result={results.median_voting}
      />

      <MeanMedianHybridVisualization
        scores={scores}
        candidates={candidates}
        result={results.mean_median_hybrid}
      />

      <VarianceBasedVisualization
        scores={scores}
        candidates={candidates}
        result={results.variance_based}
      />

      <ScoreDistributionVisualization
        scores={scores}
        candidates={candidates}
        result={results.score_distribution}
      />

      <BayesianRegretVisualization
        scores={scores}
        candidates={candidates}
        result={results.bayesian_regret}
      />
    </div>
  );
};

// 1. Simple Score Visualization
const SimpleScoreVisualization: React.FC<ScoreVotingVisualizationProps> = ({ scores, candidates, result }) => {
  // Calculate average scores for visualization
  const candidateScores = candidates.reduce((acc, candidate) => {
    acc[candidate] = { sum: 0, count: 0 };
    return acc;
  }, {} as Record<string, { sum: number, count: number }>);

  scores.forEach(({ scores: voterScores }) => {
    candidates.forEach(candidate => {
      if (candidate in voterScores) {
        candidateScores[candidate].sum += voterScores[candidate];
        candidateScores[candidate].count++;
      }
    });
  });

  const averages = candidates.map(candidate => {
    const { sum, count } = candidateScores[candidate];
    return count > 0 ? sum / count : 0;
  });

  const data = {
    labels: candidates,
    datasets: [
      {
        label: 'Average Score',
        data: averages,
        backgroundColor: [
          '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
          '#9966FF', '#FF9F40', '#8AC24A', '#EA5F89'
        ],
      },
    ],
  };

  return (
    <Card className="mb-4">
      <Card.Header>Simple Score Voting</Card.Header>
      <Card.Body>
        <p>
          Simple Score Voting calculates the average score for each candidate.
          The candidate with the highest average score wins.
        </p>

        <div className="row">
          <div className="col-md-6">
            <Bar
              data={data}
              options={{
                responsive: true,
                plugins: {
                  title: {
                    display: true,
                    text: 'Average Scores per Candidate',
                  },
                },
                scales: {
                  y: {
                    min: 0,
                    max: 5,
                    title: {
                      display: true,
                      text: 'Average Score (0-5)',
                    },
                  },
                },
              }}
            />
          </div>

          <div className="col-md-6">
            <Table striped bordered hover>
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>Average Score</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((candidate, index) => (
                  <tr key={candidate}>
                    <td>{candidate}</td>
                    <td>{averages[index].toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </Table>

            {result.winner && (
              <div className="alert alert-success mt-3">
                <strong>Winner:</strong> {result.winner}
              </div>
            )}
          </div>
        </div>
      </Card.Body>
    </Card>
  );
};

// 2. STAR Voting Visualization
const STARVotingVisualization: React.FC<ScoreVotingVisualizationProps> = ({ scores, candidates, result }) => {
  const details = result.details;

  // Prepare data for first round (average scores)
  const firstRoundData = {
    labels: candidates,
    datasets: [
      {
        label: 'Average Score',
        data: candidates.map(candidate =>
          details.first_round ? details.first_round[candidate] || 0 : 0
        ),
        backgroundColor: [
          '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
          '#9966FF', '#FF9F40', '#8AC24A', '#EA5F89'
        ],
      },
    ],
  };

  // Prepare data for runoff if available
  let runoffData = null;
  if (details.runoff) {
    const { candidate1, candidate2, votes1, votes2 } = details.runoff;
    runoffData = {
      labels: [candidate1, candidate2],
      datasets: [
        {
          label: 'Runoff Votes',
          data: [votes1, votes2],
          backgroundColor: ['#FF6384', '#36A2EB'],
        },
      ],
    };
  }

  return (
    <Card className="mb-4">
      <Card.Header>STAR Voting (Score Then Automatic Runoff)</Card.Header>
      <Card.Body>
        <p>
          STAR Voting first calculates average scores for all candidates.
          Then it holds an automatic runoff between the top two scorers.
        </p>

        <h6>First Round: Average Scores</h6>
        <div className="row">
          <div className="col-md-6">
            <Bar
              data={firstRoundData}
              options={{
                responsive: true,
                plugins: {
                  title: {
                    display: true,
                    text: 'First Round: Average Scores',
                  },
                },
                scales: {
                  y: {
                    min: 0,
                    max: 5,
                    title: {
                      display: true,
                      text: 'Average Score (0-5)',
                    },
                  },
                },
              }}
            />
          </div>

          <div className="col-md-6">
            <Table striped bordered hover>
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>Average Score</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map(candidate => (
                  <tr key={candidate}>
                    <td>{candidate}</td>
                    <td>{(details.first_round?.[candidate] || 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </div>

        {runoffData && (
          <>
            <h6 className="mt-4">Runoff Round</h6>
            <div className="row">
              <div className="col-md-6">
                <Bar
                  data={runoffData}
                  options={{
                    responsive: true,
                    plugins: {
                      title: {
                        display: true,
                        text: `Runoff: ${runoffData.labels[0]} vs ${runoffData.labels[1]}`,
                      },
                    },
                    scales: {
                      y: {
                        beginAtZero: true,
                        title: {
                          display: true,
                          text: 'Number of Voters',
                        },
                      },
                    },
                  }}
                />
              </div>

              <div className="col-md-6">
                <Card>
                  <Card.Body>
                    <Card.Title>Runoff Results</Card.Title>
                    <ul>
                      <li>
                        {runoffData.labels[0]}: {details.runoff.votes1} votes
                        ({((details.runoff.votes1 / scores.length) * 100).toFixed(1)}%)
                      </li>
                      <li>
                        {runoffData.labels[1]}: {details.runoff.votes2} votes
                        ({((details.runoff.votes2 / scores.length) * 100).toFixed(1)}%)
                      </li>
                      <li>Tied: {details.runoff.tied} votes</li>
                    </ul>
                  </Card.Body>
                </Card>
              </div>
            </div>
          </>
        )}

        {result.winner && (
          <div className="alert alert-success mt-3">
            <strong>STAR Voting Winner:</strong> {result.winner}
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

// 3. Median Voting Visualization
const MedianVotingVisualization: React.FC<ScoreVotingVisualizationProps> = ({ scores, candidates, result }) => {
  const details = result.details;

  const medians = candidates.map(candidate => details[candidate] || 0);

  const data = {
    labels: candidates,
    datasets: [
      {
        label: 'Median Score',
        data: medians,
        backgroundColor: [
          '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
          '#9966FF', '#FF9F40', '#8AC24A', '#EA5F89'
        ],
      },
    ],
  };

  return (
    <Card className="mb-4">
      <Card.Header>Median Voting</Card.Header>
      <Card.Body>
        <p>
          Median Voting selects the candidate with the highest median score.
          The median is less sensitive to outliers than the mean.
        </p>

        <div className="row">
          <div className="col-md-6">
            <Bar
              data={data}
              options={{
                responsive: true,
                plugins: {
                  title: {
                    display: true,
                    text: 'Median Scores per Candidate',
                  },
                },
                scales: {
                  y: {
                    min: 0,
                    max: 5,
                    title: {
                      display: true,
                      text: 'Median Score (0-5)',
                    },
                  },
                },
              }}
            />
          </div>

          <div className="col-md-6">
            <Table striped bordered hover>
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>Median Score</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map(candidate => (
                  <tr key={candidate}>
                    <td>{candidate}</td>
                    <td>{(details[candidate] || 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </div>

        {result.winner && (
          <div className="alert alert-success mt-3">
            <strong>Median Voting Winner:</strong> {result.winner}
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

// 4. Mean-Median Hybrid Visualization
const MeanMedianHybridVisualization: React.FC<ScoreVotingVisualizationProps> = ({ scores, candidates, result }) => {
  const details = result.details;

  const meanData = {
    labels: candidates,
    datasets: [
      {
        label: 'Mean Score',
        data: details.map((item: any) => item.mean),
        backgroundColor: 'rgba(54, 162, 235, 0.5)',
      },
    ],
  };

  const medianData = {
    labels: candidates,
    datasets: [
      {
        label: 'Median Score',
        data: details.map((item: any) => item.median),
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
      },
    ],
  };

  const combinedData = {
    labels: candidates,
    datasets: [
      {
        label: 'Combined Score',
        data: details.map((item: any) => item.combined),
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
      },
    ],
  };

  return (
    <Card className="mb-4">
      <Card.Header>Mean-Median Hybrid</Card.Header>
      <Card.Body>
        <p>
          This method combines both mean and median scores to balance
          average performance with consistency.
        </p>

        <div className="row">
          <div className="col-md-4">
            <h6>Mean Scores</h6>
            <Bar
              data={meanData}
              options={{
                responsive: true,
                plugins: {
                  title: {
                    display: false,
                  },
                },
                scales: {
                  y: {
                    min: 0,
                    max: 5,
                  },
                },
              }}
            />
          </div>

          <div className="col-md-4">
            <h6>Median Scores</h6>
            <Bar
              data={medianData}
              options={{
                responsive: true,
                plugins: {
                  title: {
                    display: false,
                  },
                },
                scales: {
                  y: {
                    min: 0,
                    max: 5,
                  },
                },
              }}
            />
          </div>

          <div className="col-md-4">
            <h6>Combined Scores</h6>
            <Bar
              data={combinedData}
              options={{
                responsive: true,
                plugins: {
                  title: {
                    display: false,
                  },
                },
                scales: {
                  y: {
                    min: 0,
                    max: 5,
                  },
                },
              }}
            />
          </div>
        </div>

        <Table striped bordered hover className="mt-3">
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Mean</th>
              <th>Median</th>
              <th>Combined</th>
            </tr>
          </thead>
          <tbody>
            {details.map((item: any) => (
              <tr key={item.candidate}>
                <td>{item.candidate}</td>
                <td>{item.mean.toFixed(2)}</td>
                <td>{item.median.toFixed(2)}</td>
                <td>{item.combined.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </Table>

        {result.winner && (
          <div className="alert alert-success mt-3">
            <strong>Mean-Median Hybrid Winner:</strong> {result.winner}
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

// 5. Variance-Based Visualization
const VarianceBasedVisualization: React.FC<ScoreVotingVisualizationProps> = ({ scores, candidates, result }) => {
  const details = result.details;

  const meanData = {
    labels: candidates,
    datasets: [
      {
        label: 'Mean Score',
        data: details.map((item: any) => item.mean),
        backgroundColor: 'rgba(54, 162, 235, 0.5)',
      },
    ],
  };

  const varianceData = {
    labels: candidates,
    datasets: [
      {
        label: 'Standard Deviation',
        data: details.map((item: any) => item.stdDev),
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
      },
    ],
  };

  const weightedData = {
    labels: candidates,
    datasets: [
      {
        label: 'Weighted Score',
        data: details.map((item: any) => item.weighted_score),
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
      },
    ],
  };

  return (
    <Card className="mb-4">
      <Card.Header>Variance-Based Voting</Card.Header>
      <Card.Body>
        <p>
          This method considers both average scores and score consistency.
          Candidates with high average scores and low variance (consistent scores)
          are preferred.
        </p>

        <div className="row">
          <div className="col-md-4">
            <h6>Mean Scores</h6>
            <Bar
              data={meanData}
              options={{
                responsive: true,
                plugins: {
                  title: {
                    display: false,
                  },
                },
                scales: {
                  y: {
                    min: 0,
                    max: 5,
                  },
                },
              }}
            />
          </div>

          <div className="col-md-4">
            <h6>Standard Deviation</h6>
            <Bar
              data={varianceData}
              options={{
                responsive: true,
                plugins: {
                  title: {
                    display: false,
                  },
                },
                scales: {
                  y: {
                    min: 0,
                    max: 2.5, // Max possible std dev for 0-5 range
                  },
                },
              }}
            />
          </div>

          <div className="col-md-4">
            <h6>Weighted Scores</h6>
            <Bar
              data={weightedData}
              options={{
                responsive: true,
                plugins: {
                  title: {
                    display: false,
                  },
                },
                scales: {
                  y: {
                    min: 0,
                    max: 5,
                  },
                },
              }}
            />
          </div>
        </div>

        <Table striped bordered hover className="mt-3">
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Mean</th>
              <th>Std Dev</th>
              <th>Weighted Score</th>
            </tr>
          </thead>
          <tbody>
            {details.map((item: any) => (
              <tr key={item.candidate}>
                <td>{item.candidate}</td>
                <td>{item.mean.toFixed(2)}</td>
                <td>{item.stdDev.toFixed(2)}</td>
                <td>{item.weighted_score.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </Table>

        {result.winner && (
          <div className="alert alert-success mt-3">
            <strong>Variance-Based Winner:</strong> {result.winner}
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

// 6. Score Distribution Visualization
const ScoreDistributionVisualization: React.FC<ScoreVotingVisualizationProps> = ({ scores, candidates, result }) => {
  const details = result.details;

  // Prepare data for radar chart (showing distribution percentages)
  const radarData = {
    labels: ['0-0.5', '0.5-1', '1-1.5', '1.5-2', '2-2.5', '2.5-3', '3-3.5', '3.5-4', '4-4.5', '4.5-5'],
    datasets: candidates.map((candidate, index) => ({
      label: candidate,
      data: details.find((d: any) => d.candidate === candidate)?.percentages || [],
      borderColor: [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
        '#9966FF', '#FF9F40', '#8AC24A', '#EA5F89'
      ][index % 8],
      backgroundColor: [
        'rgba(255, 99, 132, 0.2)', 'rgba(54, 162, 235, 0.2)', 'rgba(255, 206, 86, 0.2)',
        'rgba(75, 192, 192, 0.2)', 'rgba(153, 102, 255, 0.2)', 'rgba(255, 159, 64, 0.2)',
        'rgba(138, 194, 74, 0.2)', 'rgba(234, 95, 137, 0.2)'
      ][index % 8],
      borderWidth: 1,
    })),
  };

  return (
    <Card className="mb-4">
      <Card.Header>Score Distribution Analysis</Card.Header>
      <Card.Body>
        <p>
          This analysis shows the distribution of scores for each candidate.
          The radar chart below shows the percentage of scores in each range (0-0.5, 0.5-1, etc.)
          for each candidate.
        </p>

        <Radar
          data={radarData}
          options={{
            responsive: true,
            plugins: {
              title: {
                display: true,
                text: 'Score Distribution by Candidate',
              },
            },
            scales: {
              r: {
                min: 0,
                max: 0.5, // Since we're showing percentages (0-1 normalized to 0-0.5)
                ticks: {
                  stepSize: 0.1,
                //   callback: function(value: number) {
                //     return (value * 200).toFixed(0) + '%';
                //   }
                },
              },
            },
          }}
        />

        <Table striped bordered hover className="mt-3">
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Mode Range</th>
              <th>Total Votes</th>
            </tr>
          </thead>
          <tbody>
            {details.map((item: any) => (
              <tr key={item.candidate}>
                <td>{item.candidate}</td>
                <td>{item.modeRange}</td>
                <td>{item.total}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card.Body>
    </Card>
  );
};

// 7. Bayesian Regret Visualization
const BayesianRegretVisualization: React.FC<ScoreVotingVisualizationProps> = ({ scores, candidates, result }) => {
  const details = result.details;

  const regretData = {
    labels: candidates,
    datasets: [
      {
        label: 'Average Regret',
        data: details.map((item: any) => item.avgRegret),
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
      },
    ],
  };

  const utilityData = {
    labels: candidates,
    datasets: [
      {
        label: 'Average Utility',
        data: details.map((item: any) => item.avgUtility),
        backgroundColor: 'rgba(54, 162, 235, 0.5)',
      },
    ],
  };

  return (
    <Card className="mb-4">
      <Card.Header>Bayesian Regret Analysis</Card.Header>
      <Card.Body>
        <p>
          Bayesian Regret measures the expected disappointment voters would feel
          if a particular candidate wins. A lower regret is better.
        </p>

        <div className="row">
          <div className="col-md-6">
            <h6>Average Utility</h6>
            <Bar
              data={utilityData}
              options={{
                responsive: true,
                plugins: {
                  title: {
                    display: false,
                  },
                },
                scales: {
                  y: {
                    min: 0,
                    max: 1,
                    title: {
                      display: true,
                      text: 'Average Utility (0-1)',
                    },
                  },
                },
              }}
            />
          </div>

          <div className="col-md-6">
            <h6>Average Regret</h6>
            <Bar
              data={regretData}
              options={{
                responsive: true,
                plugins: {
                  title: {
                    display: false,
                  },
                },
                scales: {
                  y: {
                    min: 0,
                    max: 1,
                    title: {
                      display: true,
                      text: 'Average Regret (0-1)',
                    },
                  },
                },
              }}
            />
          </div>
        </div>

        <Table striped bordered hover className="mt-3">
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Avg Utility</th>
              <th>Avg Regret</th>
            </tr>
          </thead>
          <tbody>
            {details.map((item: any) => (
              <tr key={item.candidate}>
                <td>{item.candidate}</td>
                <td>{item.avgUtility.toFixed(3)}</td>
                <td>{item.avgRegret.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </Table>

        {result.winner && (
          <div className="alert alert-success mt-3">
            <strong>Bayesian Regret Winner:</strong> {result.winner}
            <p className="mb-0">
              (Lowest Regret: {details.find((item: any) => item.candidate === result.winner)?.avgRegret.toFixed(3)})
            </p>
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export default ScoreVotingVisualizations;
