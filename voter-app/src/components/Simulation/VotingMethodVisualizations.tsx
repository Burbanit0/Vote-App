// VotingMethodVisualizations.tsx
import React from 'react';
import { Card, Table, Badge } from 'react-bootstrap';
import { Bar, Radar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  PointElement,
  LineElement,
  RadialLinearScale,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  PointElement,
  LineElement,
  RadialLinearScale
);

interface VotingMethodVisualizationProps {
  method: string;
  rankings: Array<{ voter_id: number; ranking: string[] }>;
  candidates: string[];
}

const VotingMethodVisualizations: React.FC<VotingMethodVisualizationProps> = ({
  method,
  rankings,
  candidates,
}) => {
  const renderMethodVisualization = () => {
    switch (method) {
      case 'plurality':
        return (
          <PluralityVisualization method={method} rankings={rankings} candidates={candidates} />
        );
      case 'borda':
        return <BordaVisualization method={method} rankings={rankings} candidates={candidates} />;
      case 'irv':
        return <IRVVisualization method={method} rankings={rankings} candidates={candidates} />;
      case 'approval':
        return (
          <ApprovalVisualization method={method} rankings={rankings} candidates={candidates} />
        );
      case 'condorcet':
        return (
          <CondorcetVisualization method={method} rankings={rankings} candidates={candidates} />
        );
      case 'two_round':
        return (
          <TwoRoundVisualization method={method} rankings={rankings} candidates={candidates} />
        );
      case 'coombs':
        return <CoombsVisualization method={method} rankings={rankings} candidates={candidates} />;
      case 'score':
        return <ScoreVisualization method={method} rankings={rankings} candidates={candidates} />;
      case 'bucklin':
        return <BucklinVisualization method={method} rankings={rankings} candidates={candidates} />;
      case 'minimax':
        return <MinimaxVisualization method={method} rankings={rankings} candidates={candidates} />;
      case 'schulze':
        return <SchulzeVisualization method={method} rankings={rankings} candidates={candidates} />;
      case 'kemeny_young':
        return (
          <KemenyYoungVisualization method={method} rankings={rankings} candidates={candidates} />
        );
      default:
        return <div>Unknown voting method</div>;
    }
  };

  return (
    <Card className="mb-4">
      <Card.Header>
        <h5>{method.charAt(0).toUpperCase() + method.slice(1)} Method Visualization</h5>
      </Card.Header>
      <Card.Body>{renderMethodVisualization()}</Card.Body>
    </Card>
  );
};

// 1. Plurality Visualization
const PluralityVisualization: React.FC<VotingMethodVisualizationProps> = ({
  rankings,
  candidates,
}) => {
  // Count first-choice votes
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
        backgroundColor: [
          '#FF6384',
          '#36A2EB',
          '#FFCE56',
          '#4BC0C0',
          '#9966FF',
          '#FF9F40',
          '#8AC24A',
          '#EA5F89',
        ],
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

// 2. Borda Count Visualization
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
      // Borda score: (number of candidates - 1) - position
      scores[candidate] += numCandidates - 1 - index;
    });
  });

  const data = {
    labels: candidates,
    datasets: [
      {
        label: 'Borda Scores',
        data: candidates.map((candidate) => scores[candidate]),
        backgroundColor: [
          '#FF6384',
          '#36A2EB',
          '#FFCE56',
          '#4BC0C0',
          '#9966FF',
          '#FF9F40',
          '#8AC24A',
          '#EA5F89',
        ],
      },
    ],
  };

  return (
    <>
      <p>
        Borda Count assigns points to each candidate based on their position in each voter&apos;s
        ranking. A candidate in first place gets {numCandidates - 1} points, second place gets{' '}
        {numCandidates - 2} points, and so on. The candidate with the most points wins.
      </p>
      <Bar
        data={data}
        options={{
          responsive: true,
          plugins: {
            title: {
              display: true,
              text: 'Borda Count Scores',
            },
          },
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: 'Total Borda Points',
              },
            },
          },
        }}
      />
      <Card.Text className="mt-3">
        <strong>Winner:</strong> {candidates.reduce((a, b) => (scores[a] > scores[b] ? a : b))}
      </Card.Text>
    </>
  );
};

// 3. Instant Runoff Voting (IRV) Visualization
const IRVVisualization: React.FC<VotingMethodVisualizationProps> = ({ rankings, candidates }) => {
  const [round, setRound] = React.useState(1);
  const [eliminated, setEliminated] = React.useState<string[]>([]);
  const [currentVotes, setCurrentVotes] = React.useState<Record<string, number>>({});
  const [winner, setWinner] = React.useState<string | null>(null);

  // Initialize simulation
  React.useEffect(() => {
    simulateIRV();
  }, []);

  const simulateIRV = () => {
    let remainingCandidates = [...candidates];
    const currentRound = 1;
    let votes = { ...currentVotes };
    let winnerFound = false;

    // Count first round votes
    const firstRoundVotes = candidates.reduce(
      (acc, candidate) => {
        acc[candidate] = 0;
        return acc;
      },
      {} as Record<string, number>
    );

    rankings.forEach(({ ranking }) => {
      for (const candidate of ranking) {
        if (remainingCandidates.includes(candidate)) {
          firstRoundVotes[candidate]++;
          break;
        }
      }
    });

    setCurrentVotes(firstRoundVotes);
    setRound(currentRound);
    setEliminated([]);

    // Check for winner in each round
    const checkRound = () => {
      if (remainingCandidates.length === 1) {
        setWinner(remainingCandidates[0]);
        return;
      }

      // Check for majority
      const totalVotes = Object.values(votes).reduce((a, b) => a + b, 0);
      const majority = totalVotes / 2;

      for (const [candidate, count] of Object.entries(votes)) {
        if (count > majority) {
          setWinner(candidate);
          winnerFound = true;
          return;
        }
      }

      if (!winnerFound) {
        // Eliminate candidate with fewest votes
        const minVotes = Math.min(...Object.values(votes));
        const toEliminate = Object.entries(votes)
          .filter(([_, count]) => count === minVotes)
          .map(([candidate, _]) => candidate);

        setEliminated((prev) => [...prev, ...toEliminate]);

        // Update remaining candidates
        remainingCandidates = remainingCandidates.filter((c) => !toEliminate.includes(c));

        if (remainingCandidates.length === 1) {
          setWinner(remainingCandidates[0]);
          return;
        }

        // Count votes for next round
        const nextRoundVotes = remainingCandidates.reduce(
          (acc, candidate) => {
            acc[candidate] = 0;
            return acc;
          },
          {} as Record<string, number>
        );

        rankings.forEach(({ ranking }) => {
          for (const candidate of ranking) {
            if (remainingCandidates.includes(candidate)) {
              nextRoundVotes[candidate]++;
              break;
            }
          }
        });

        setCurrentVotes(nextRoundVotes);
        setRound((prev) => prev + 1);
        votes = nextRoundVotes;
      }
    };

    checkRound();
  };

  const colors = [
    '#FF6384',
    '#36A2EB',
    '#FFCE56',
    '#4BC0C0',
    '#9966FF',
    '#FF9F40',
    '#8AC24A',
    '#EA5F89',
  ];

  const data = {
    labels: candidates.filter((c) => !eliminated.includes(c)),
    datasets: [
      {
        label: `Round ${round} Votes`,
        data: candidates
          .filter((c) => !eliminated.includes(c))
          .map((candidate) => currentVotes[candidate] || 0),
        backgroundColor: candidates
          .filter((c) => !eliminated.includes(c))
          .map((_, i) => colors[i % colors.length]),
      },
    ],
  };

  return (
    <>
      <p>
        Instant Runoff Voting (IRV) simulates a series of runoff elections. In each round, the
        candidate with the fewest votes is eliminated, and their votes are redistributed to the
        remaining candidates based on voters preferences. This continues until one candidate has a
        majority.
      </p>

      {!winner ? (
        <>
          <Bar
            data={data}
            options={{
              responsive: true,
              plugins: {
                title: {
                  display: true,
                  text: `Round ${round} Vote Distribution`,
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

          {eliminated.length > 0 && (
            <Card className="mt-3">
              <Card.Header>Eliminated Candidates</Card.Header>
              <Card.Body>
                <div className="d-flex flex-wrap gap-2">
                  {eliminated.map((candidate) => (
                    <Badge key={candidate} bg="secondary" className="p-2">
                      {candidate}
                    </Badge>
                  ))}
                </div>
              </Card.Body>
            </Card>
          )}

          <button className="btn btn-primary mt-3" onClick={simulateIRV} disabled={winner !== null}>
            Next Round
          </button>
        </>
      ) : (
        <div className="alert alert-success mt-3">
          <h5>Winner: {winner}</h5>
          <p>Achieved majority in round {round}</p>
          <button
            className="btn btn-secondary mt-2"
            onClick={() => {
              setRound(1);
              setEliminated([]);
              setWinner(null);
              simulateIRV();
            }}
          >
            Restart Simulation
          </button>
        </div>
      )}
    </>
  );
};

// 4. Approval Voting Visualization
const ApprovalVisualization: React.FC<VotingMethodVisualizationProps> = ({
  rankings,
  candidates,
}) => {
  const [approvalThreshold, setApprovalThreshold] = React.useState(2);
  const approvalVotes = candidates.reduce(
    (acc, candidate) => {
      acc[candidate] = 0;
      return acc;
    },
    {} as Record<string, number>
  );

  // Count approval votes
  rankings.forEach(({ ranking }) => {
    // Approve top N candidates
    const approved = ranking.slice(0, approvalThreshold);
    approved.forEach((candidate) => {
      approvalVotes[candidate]++;
    });
  });

  const data = {
    labels: candidates,
    datasets: [
      {
        label: `Approval Votes (Top ${approvalThreshold})`,
        data: candidates.map((candidate) => approvalVotes[candidate]),
        backgroundColor: [
          '#FF6384',
          '#36A2EB',
          '#FFCE56',
          '#4BC0C0',
          '#9966FF',
          '#FF9F40',
          '#8AC24A',
          '#EA5F89',
        ],
      },
    ],
  };

  return (
    <>
      <p>
        Approval Voting allows voters to approve of multiple candidates. Each voter approves of
        their top {approvalThreshold} candidates, and the candidate with the most approvals wins.
      </p>

      <div className="mb-3">
        <label htmlFor="approvalThreshold" className="form-label">
          Number of candidates to approve:
        </label>
        <input
          type="range"
          className="form-range"
          min="1"
          max={candidates.length}
          id="approvalThreshold"
          value={approvalThreshold}
          onChange={(e) => setApprovalThreshold(parseInt(e.target.value))}
        />
        <div className="text-center">{approvalThreshold}</div>
      </div>

      <Bar
        data={data}
        options={{
          responsive: true,
          plugins: {
            title: {
              display: true,
              text: `Approval Votes (Top ${approvalThreshold} Candidates)`,
            },
          },
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: 'Number of Approvals',
              },
            },
          },
        }}
      />

      <Card.Text className="mt-3">
        <strong>Winner:</strong>{' '}
        {candidates.reduce((a, b) => (approvalVotes[a] > approvalVotes[b] ? a : b))}
      </Card.Text>
    </>
  );
};

// 5. Condorcet Method Visualization
const CondorcetVisualization: React.FC<VotingMethodVisualizationProps> = ({
  rankings,
  candidates,
}) => {
  // Calculate pairwise comparisons
  const pairwiseResults: Record<string, Record<string, number>> = {};

  // Initialize the matrix
  candidates.forEach((c1) => {
    pairwiseResults[c1] = {};
    candidates.forEach((c2) => {
      if (c1 !== c2) {
        pairwiseResults[c1][c2] = 0;
      }
    });
  });

  // Count pairwise preferences
  candidates.forEach((c1) => {
    candidates.forEach((c2) => {
      if (c1 !== c2) {
        let count = 0;
        rankings.forEach(({ ranking }) => {
          const pos1 = ranking.indexOf(c1);
          const pos2 = ranking.indexOf(c2);
          if (pos1 < pos2) {
            count++;
          }
        });
        pairwiseResults[c1][c2] = count;
      }
    });
  });

  // Check for Condorcet winner
  let condorcetWinner: string | null = null;
  for (const candidate of candidates) {
    let isWinner = true;
    for (const other of candidates) {
      if (
        candidate !== other &&
        pairwiseResults[candidate][other] <= pairwiseResults[other][candidate]
      ) {
        isWinner = false;
        break;
      }
    }
    if (isWinner) {
      condorcetWinner = candidate;
      break;
    }
  }

  return (
    <>
      <p>
        The Condorcet method compares candidates in pairwise contests. A Condorcet winner is a
        candidate who would win a two-candidate election against each of the other candidates. If
        such a candidate exists, they are the winner.
      </p>

      <Card.Text className="mt-3">
        {condorcetWinner ? (
          <>
            <strong>Condorcet Winner:</strong> {condorcetWinner}
            <p className="mt-2">
              {condorcetWinner} beats every other candidate in head-to-head comparisons.
            </p>
          </>
        ) : (
          <strong>No Condorcet winner exists for this election.</strong>
        )}
      </Card.Text>

      <Card className="mt-3">
        <Card.Header>Pairwise Comparison Matrix</Card.Header>
        <Card.Body>
          <Table bordered hover>
            <thead>
              <tr>
                <th></th>
                {candidates.map((candidate) => (
                  <th key={candidate}>{candidate}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {candidates.map((c1) => (
                <tr key={c1}>
                  <th>{c1}</th>
                  {candidates.map((c2) => (
                    <td key={`${c1}-${c2}`}>
                      {c1 === c2
                        ? '-'
                        : `${pairwiseResults[c1][c2]} vs ${pairwiseResults[c2] ? pairwiseResults[c2][c1] : 0}`}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
      </Card>
    </>
  );
};

// 6. Two-Round System Visualization
const TwoRoundVisualization: React.FC<VotingMethodVisualizationProps> = ({
  rankings,
  candidates,
}) => {
  // First round: count first-choice votes
  const firstRoundVotes = candidates.reduce(
    (acc, candidate) => {
      acc[candidate] = 0;
      return acc;
    },
    {} as Record<string, number>
  );

  rankings.forEach(({ ranking }) => {
    if (ranking.length > 0) {
      firstRoundVotes[ranking[0]]++;
    }
  });

  const totalVoters = rankings.length;
  const majority = totalVoters / 2;

  // Check for first-round winner
  const firstRoundWinner = candidates.find((candidate) => firstRoundVotes[candidate] > majority);

  let secondRoundCandidates: string[] = [];
  let secondRoundVotes: Record<string, number> = {};
  let finalWinner: string | null = null;

  if (!firstRoundWinner) {
    // Get top two candidates for second round
    secondRoundCandidates = candidates
      .sort((a, b) => firstRoundVotes[b] - firstRoundVotes[a])
      .slice(0, 2);

    // Count second round votes
    secondRoundVotes = secondRoundCandidates.reduce(
      (acc, candidate) => {
        acc[candidate] = 0;
        return acc;
      },
      {} as Record<string, number>
    );

    rankings.forEach(({ ranking }) => {
      for (const candidate of ranking) {
        if (secondRoundCandidates.includes(candidate)) {
          secondRoundVotes[candidate]++;
          break;
        }
      }
    });

    // Determine final winner
    finalWinner = secondRoundCandidates.reduce((a, b) =>
      secondRoundVotes[a] > secondRoundVotes[b] ? a : b
    );
  }

  const firstRoundData = {
    labels: candidates,
    datasets: [
      {
        label: 'First Round Votes',
        data: candidates.map((candidate) => firstRoundVotes[candidate]),
        backgroundColor: [
          '#FF6384',
          '#36A2EB',
          '#FFCE56',
          '#4BC0C0',
          '#9966FF',
          '#FF9F40',
          '#8AC24A',
          '#EA5F89',
        ],
      },
    ],
  };

  const secondRoundData =
    secondRoundCandidates.length > 0
      ? {
          labels: secondRoundCandidates,
          datasets: [
            {
              label: 'Second Round Votes',
              data: secondRoundCandidates.map((candidate) => secondRoundVotes[candidate]),
              backgroundColor: ['#FF6384', '#36A2EB'],
            },
          ],
        }
      : null;

  return (
    <>
      <p>
        The Two-Round System has two rounds of voting. In the first round, if a candidate receives a
        majority of votes, they win. If not, the top two candidates proceed to a second round.
      </p>

      <Card.Text className="mt-3">
        <strong>First Round Results:</strong>
      </Card.Text>

      <Bar
        data={firstRoundData}
        options={{
          responsive: true,
          plugins: {
            title: {
              display: true,
              text: 'First Round Votes',
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

      <Card.Text className="mt-2">Majority threshold: {majority} votes</Card.Text>

      {firstRoundWinner ? (
        <div className="alert alert-success mt-3">
          <strong>First Round Winner:</strong> {firstRoundWinner}
          <p>Achieved majority with {firstRoundVotes[firstRoundWinner]} votes</p>
        </div>
      ) : (
        <>
          <Card.Text className="mt-3">
            <strong>Top Two Candidates Proceed to Second Round:</strong>
            <div className="d-flex flex-wrap gap-2 mt-1">
              {secondRoundCandidates.map((candidate) => (
                <Badge key={candidate} bg="primary" className="p-2">
                  {candidate}
                </Badge>
              ))}
            </div>
          </Card.Text>

          {secondRoundData && (
            <>
              <Card.Text className="mt-3">
                <strong>Second Round Results:</strong>
              </Card.Text>

              <Bar
                data={secondRoundData}
                options={{
                  responsive: true,
                  plugins: {
                    title: {
                      display: true,
                      text: 'Second Round Votes',
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

              {finalWinner && (
                <div className="alert alert-success mt-3">
                  <strong>Final Winner:</strong> {finalWinner}
                </div>
              )}
            </>
          )}
        </>
      )}
    </>
  );
};

// 7. Coombs' Method Visualization
const CoombsVisualization: React.FC<VotingMethodVisualizationProps> = ({
  rankings,
  candidates,
}) => {
  const [round, setRound] = React.useState(1);
  const [eliminated, setEliminated] = React.useState<string[]>([]);
  const [, setCurrentVotes] = React.useState<Record<string, number>>({});
  const [winner, setWinner] = React.useState<string | null>(null);
  const [lastPlaceVotes, setLastPlaceVotes] = React.useState<Record<string, number>>({});

  // Initialize simulation
  React.useEffect(() => {
    simulateCoombs();
  }, []);

  const simulateCoombs = () => {
    let remainingCandidates = [...candidates];
    const currentRound = 1;
    let lastPlace: Record<string, number> = {};

    // Count last place votes for first round
    candidates.forEach((candidate) => {
      lastPlace[candidate] = 0;
    });

    rankings.forEach(({ ranking }) => {
      // Find the lowest-ranked remaining candidate
      for (let i = ranking.length - 1; i >= 0; i--) {
        const candidate = ranking[i];
        if (remainingCandidates.includes(candidate)) {
          lastPlace[candidate]++;
          break;
        }
      }
    });

    setLastPlaceVotes(lastPlace);
    setCurrentVotes({});
    setRound(currentRound);
    setEliminated([]);

    // Check for winner in each round
    const checkRound = () => {
      if (remainingCandidates.length === 1) {
        setWinner(remainingCandidates[0]);
        return;
      }

      // Eliminate candidate(s) with most last-place votes
      const maxLastVotes = Math.max(...Object.values(lastPlace));
      const toEliminate = Object.entries(lastPlace)
        .filter(([_, count]) => count === maxLastVotes)
        .map(([candidate, _]) => candidate);

      setEliminated((prev) => [...prev, ...toEliminate]);

      // Update remaining candidates
      remainingCandidates = remainingCandidates.filter((c) => !toEliminate.includes(c));

      if (remainingCandidates.length === 1) {
        setWinner(remainingCandidates[0]);
        return;
      }

      // Count last place votes for next round
      lastPlace = remainingCandidates.reduce(
        (acc, candidate) => {
          acc[candidate] = 0;
          return acc;
        },
        {} as Record<string, number>
      );

      rankings.forEach(({ ranking }) => {
        // Find the lowest-ranked remaining candidate
        for (let i = ranking.length - 1; i >= 0; i--) {
          const candidate = ranking[i];
          if (remainingCandidates.includes(candidate)) {
            lastPlace[candidate]++;
            break;
          }
        }
      });

      setLastPlaceVotes(lastPlace);
      setRound((prev) => prev + 1);
    };

    checkRound();
  };

  const colors = [
    '#FF6384',
    '#36A2EB',
    '#FFCE56',
    '#4BC0C0',
    '#9966FF',
    '#FF9F40',
    '#8AC24A',
    '#EA5F89',
  ];

  return (
    <>
      <p>
        Coombs method eliminates candidates with the most last-place votes in each round, until one
        candidate remains as the winner.
      </p>

      {!winner ? (
        <>
          <Card className="mt-3">
            <Card.Header>Round {round} - Last Place Votes</Card.Header>
            <Card.Body>
              <Bar
                data={{
                  labels: candidates.filter((c) => !eliminated.includes(c)),
                  datasets: [
                    {
                      label: 'Last Place Votes',
                      data: candidates
                        .filter((c) => !eliminated.includes(c))
                        .map((candidate) => lastPlaceVotes[candidate] || 0),
                      backgroundColor: candidates
                        .filter((c) => !eliminated.includes(c))
                        .map((_, i) => colors[i % colors.length]),
                    },
                  ],
                }}
                options={{
                  responsive: true,
                  plugins: {
                    title: {
                      display: true,
                      text: `Last Place Votes - Round ${round}`,
                    },
                  },
                  scales: {
                    y: {
                      beginAtZero: true,
                      title: {
                        display: true,
                        text: 'Number of Last Place Votes',
                      },
                    },
                  },
                }}
              />
            </Card.Body>
          </Card>

          {eliminated.length > 0 && (
            <Card className="mt-3">
              <Card.Header>Eliminated Candidates</Card.Header>
              <Card.Body>
                <div className="d-flex flex-wrap gap-2">
                  {eliminated.map((candidate) => (
                    <Badge key={candidate} bg="secondary" className="p-2">
                      {candidate}
                    </Badge>
                  ))}
                </div>
              </Card.Body>
            </Card>
          )}

          <button
            className="btn btn-primary mt-3"
            onClick={simulateCoombs}
            disabled={winner !== null}
          >
            Next Round
          </button>
        </>
      ) : (
        <div className="alert alert-success mt-3">
          <h5>Winner: {winner}</h5>
          <p>Last remaining candidate after {round - 1} rounds</p>
          <button
            className="btn btn-secondary mt-2"
            onClick={() => {
              setRound(1);
              setEliminated([]);
              setWinner(null);
              simulateCoombs();
            }}
          >
            Restart Simulation
          </button>
        </div>
      )}
    </>
  );
};

// 8. Score Voting Visualization
const ScoreVisualization: React.FC<VotingMethodVisualizationProps> = ({ rankings, candidates }) => {
  // Calculate average scores for each candidate
  const scoreData: Record<string, { scores: number[]; avg: number }> = {};

  candidates.forEach((candidate) => {
    scoreData[candidate] = { scores: [], avg: 0 };
  });

  // Collect all scores
  rankings.forEach(({ ranking }) => {
    const numCandidates = ranking.length;
    ranking.forEach((candidate, index) => {
      // Convert rank position to score (0-5 scale)
      const score = 5 - (index / (numCandidates - 1)) * 5;
      scoreData[candidate].scores.push(score);
    });
  });

  // Calculate averages
  candidates.forEach((candidate) => {
    const total = scoreData[candidate].scores.reduce((a, b) => a + b, 0);
    scoreData[candidate].avg = total / scoreData[candidate].scores.length;
  });

  // Prepare radar chart data
  const radarData = {
    labels: candidates,
    datasets: [
      {
        label: 'Average Scores',
        data: candidates.map((candidate) => scoreData[candidate].avg),
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 2,
      },
    ],
  };

  // Prepare distribution data for each candidate
  const distributionData = {
    labels: Array.from({ length: 11 }, (_, i) => i * 0.5), // 0 to 5 in 0.5 increments
    datasets: candidates.map((candidate, index) => ({
      label: candidate,
      data: Array.from({ length: 11 }, () => 0), // Initialize with zeros
      borderColor: [
        '#FF6384',
        '#36A2EB',
        '#FFCE56',
        '#4BC0C0',
        '#9966FF',
        '#FF9F40',
        '#8AC24A',
        '#EA5F89',
      ][index % 8],
      backgroundColor: [
        'rgba(255, 99, 132, 0.2)',
        'rgba(54, 162, 235, 0.2)',
        'rgba(255, 206, 86, 0.2)',
        'rgba(75, 192, 192, 0.2)',
        'rgba(153, 102, 255, 0.2)',
        'rgba(255, 159, 64, 0.2)',
        'rgba(138, 194, 74, 0.2)',
        'rgba(234, 95, 137, 0.2)',
      ][index % 8],
      borderWidth: 1,
    })),
  };

  // Bin scores into 0.5 increments
  candidates.forEach((candidate, index) => {
    scoreData[candidate].scores.forEach((score) => {
      const binIndex = Math.floor(score * 2); // Convert to 0.5 bins
      if (binIndex >= 0 && binIndex < 11) {
        distributionData.datasets[index].data[binIndex]++;
      }
    });
  });

  return (
    <>
      <p>
        Score Voting allows voters to give each candidate a score (typically 0-5). In this
        visualization, we convert rankings to scores where higher ranks get higher scores. The
        candidate with the highest average score wins.
      </p>

      <div className="row">
        <div className="col-md-6">
          <Card>
            <Card.Header>Average Scores</Card.Header>
            <Card.Body>
              <Radar
                data={radarData}
                options={{
                  responsive: true,
                  plugins: {
                    title: {
                      display: true,
                      text: 'Average Scores by Candidate',
                    },
                  },
                  scales: {
                    r: {
                      min: 0,
                      max: 5,
                      ticks: {
                        stepSize: 1,
                      },
                    },
                  },
                }}
              />
            </Card.Body>
          </Card>
        </div>

        <div className="col-md-6">
          <Card>
            <Card.Header>Score Distribution</Card.Header>
            <Card.Body>
              <Bar
                data={distributionData}
                options={{
                  responsive: true,
                  plugins: {
                    title: {
                      display: true,
                      text: 'Score Distribution by Candidate',
                    },
                    tooltip: {
                      callbacks: {
                        label: function (context) {
                          const label = context.dataset.label || '';
                          const value = context.raw as number;
                          return `${label}: ${value} votes`;
                        },
                      },
                    },
                  },
                  scales: {
                    x: {
                      title: {
                        display: true,
                        text: 'Score (0-5)',
                      },
                    },
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
            </Card.Body>
          </Card>
        </div>
      </div>

      <Card.Text className="mt-3">
        <strong>Winner:</strong>{' '}
        {candidates.reduce((a, b) => (scoreData[a].avg > scoreData[b].avg ? a : b))}
        <span>
          {' '}
          (Average score: {Math.max(...candidates.map((c) => scoreData[c].avg)).toFixed(2)})
        </span>
      </Card.Text>
    </>
  );
};

// 9. Bucklin Voting Visualization
const BucklinVisualization: React.FC<VotingMethodVisualizationProps> = ({
  rankings,
  candidates,
}) => {
  const maxRounds = Math.max(...rankings.map((vote) => vote.ranking.length));
  const [currentRound, setCurrentRound] = React.useState(1);
  const [winner, setWinner] = React.useState<string | null>(null);

  // Calculate votes for each round
  const roundVotes: Record<number, Record<string, number>> = {};

  for (let round = 1; round <= maxRounds; round++) {
    roundVotes[round] = candidates.reduce(
      (acc, candidate) => {
        acc[candidate] = 0;
        return acc;
      },
      {} as Record<string, number>
    );

    rankings.forEach(({ ranking }) => {
      if (ranking.length >= round) {
        const candidate = ranking[round - 1];
        roundVotes[round][candidate]++;
      }
    });
  }

  // Check for winner in each round
  React.useEffect(() => {
    const majority = rankings.length / 2;
    const votes = roundVotes[currentRound];

    const roundWinner = Object.entries(votes).find(([_, count]) => count > majority);

    if (roundWinner) {
      setWinner(roundWinner[0]);
    } else if (currentRound === maxRounds) {
      // If no majority in final round, pick candidate with most votes
      const finalRoundWinner = Object.entries(votes).reduce((a, b) => (a[1] > b[1] ? a : b))[0];
      setWinner(finalRoundWinner);
    }
  }, [currentRound, maxRounds, rankings.length, roundVotes]);

  const data = {
    labels: candidates,
    datasets: [
      {
        label: `Round ${currentRound} Votes`,
        data: candidates.map((candidate) => roundVotes[currentRound][candidate]),
        backgroundColor: [
          '#FF6384',
          '#36A2EB',
          '#FFCE56',
          '#4BC0C0',
          '#9966FF',
          '#FF9F40',
          '#8AC24A',
          '#EA5F89',
        ],
      },
    ],
  };

  return (
    <>
      <p>
        Bucklin Voting counts votes in rounds. In each round, it counts votes for candidates ranked
        at that position or higher. If a candidate achieves a majority, they win. Otherwise, it
        moves to the next round until a winner is found.
      </p>

      <div className="mb-3">
        <label htmlFor="bucklinRound" className="form-label">
          Current Round: {currentRound}
        </label>
        <input
          type="range"
          className="form-range"
          min="1"
          max={maxRounds}
          id="bucklinRound"
          value={currentRound}
          onChange={(e) => setCurrentRound(parseInt(e.target.value))}
        />
      </div>

      <Bar
        data={data}
        options={{
          responsive: true,
          plugins: {
            title: {
              display: true,
              text: `Round ${currentRound} Votes`,
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
        Majority threshold: {Math.ceil(rankings.length / 2)} votes
      </Card.Text>

      {winner && (
        <div className="alert alert-success mt-3">
          <strong>Winner in Round {currentRound}:</strong> {winner}
        </div>
      )}
    </>
  );
};

// 10. Minimax Visualization
const MinimaxVisualization: React.FC<VotingMethodVisualizationProps> = ({
  rankings,
  candidates,
}) => {
  // Calculate pairwise opposition
  const opposition: Record<string, Record<string, number>> = {};

  candidates.forEach((c1) => {
    opposition[c1] = {};
    candidates.forEach((c2) => {
      if (c1 !== c2) {
        opposition[c1][c2] = 0;
      }
    });
  });

  // Count pairwise preferences
  candidates.forEach((c1) => {
    candidates.forEach((c2) => {
      if (c1 !== c2) {
        rankings.forEach(({ ranking }) => {
          const pos1 = ranking.indexOf(c1);
          const pos2 = ranking.indexOf(c2);
          if (pos2 < pos1) {
            // c2 is preferred over c1
            opposition[c1][c2]++;
          }
        });
      }
    });
  });

  // Find the maximum opposition for each candidate
  const maxOpposition: Record<string, number> = {};
  candidates.forEach((candidate) => {
    maxOpposition[candidate] = Math.max(
      ...candidates.filter((c) => c !== candidate).map((other) => opposition[candidate][other] || 0)
    );
  });

  // Prepare data for visualization
  const data = {
    labels: candidates,
    datasets: [
      {
        label: 'Maximum Opposition',
        data: candidates.map((candidate) => maxOpposition[candidate]),
        backgroundColor: [
          '#FF6384',
          '#36A2EB',
          '#FFCE56',
          '#4BC0C0',
          '#9966FF',
          '#FF9F40',
          '#8AC24A',
          '#EA5F89',
        ],
      },
    ],
  };

  // Find the winner (candidate with smallest maximum opposition)
  const winner = candidates.reduce((a, b) => (maxOpposition[a] < maxOpposition[b] ? a : b));

  return (
    <>
      <p>
        The Minimax method finds the candidate with the smallest maximum opposition. For each
        candidate, we find their worst pairwise defeat (the most votes against them in any
        head-to-head comparison), and the candidate with the smallest such defeat wins.
      </p>

      <Card className="mt-3">
        <Card.Header>Pairwise Opposition Matrix</Card.Header>
        <Card.Body>
          <div className="table-responsive">
            <Table bordered hover>
              <thead>
                <tr>
                  <th></th>
                  {candidates.map((candidate) => (
                    <th key={candidate}>{candidate}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {candidates.map((c1) => (
                  <tr key={c1}>
                    <th>{c1}</th>
                    {candidates.map((c2) => (
                      <td key={`${c1}-${c2}`} className={c1 === c2 ? 'bg-light' : ''}>
                        {c1 === c2
                          ? '-'
                          : `${opposition[c1][c2]} vs ${opposition[c2] ? opposition[c2][c1] : 0}`}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </Card.Body>
      </Card>

      <Card className="mt-3">
        <Card.Header>Maximum Opposition per Candidate</Card.Header>
        <Card.Body>
          <Bar
            data={data}
            options={{
              responsive: true,
              plugins: {
                title: {
                  display: true,
                  text: 'Maximum Opposition per Candidate',
                },
              },
              scales: {
                y: {
                  beginAtZero: true,
                  title: {
                    display: true,
                    text: 'Number of Votes Against',
                  },
                },
              },
            }}
          />
        </Card.Body>
      </Card>

      <Card.Text className="mt-3">
        <strong>Minimax Winner:</strong> {winner}
        <p className="mt-1">
          {winner} has the smallest maximum opposition ({maxOpposition[winner]} votes)
        </p>
      </Card.Text>
    </>
  );
};

// 11. Schulze Method Visualization
const SchulzeVisualization: React.FC<VotingMethodVisualizationProps> = ({
  rankings,
  candidates,
}) => {
  // Calculate pairwise preferences
  const pref: Record<string, Record<string, number>> = {};

  candidates.forEach((c1) => {
    pref[c1] = {};
    candidates.forEach((c2) => {
      if (c1 !== c2) {
        pref[c1][c2] = 0;
      }
    });
  });

  // Count pairwise preferences
  candidates.forEach((c1) => {
    candidates.forEach((c2) => {
      if (c1 !== c2) {
        rankings.forEach(({ ranking }) => {
          const pos1 = ranking.indexOf(c1);
          const pos2 = ranking.indexOf(c2);
          if (pos1 < pos2) {
            pref[c1][c2]++;
          }
        });
      }
    });
  });

  // Calculate the strength of the strongest paths
  const strength: Record<string, Record<string, number>> = {};

  candidates.forEach((c1) => {
    strength[c1] = {};
    candidates.forEach((c2) => {
      if (c1 !== c2) {
        strength[c1][c2] = pref[c1][c2];
      }
    });
  });

  // Floyd-Warshall algorithm to find strongest paths
  candidates.forEach((c1) => {
    candidates.forEach((c2) => {
      if (c1 !== c2) {
        candidates.forEach((c3) => {
          if (c1 !== c3 && c2 !== c3) {
            strength[c1][c2] = Math.max(
              strength[c1][c2],
              Math.min(strength[c1][c3], strength[c3][c2])
            );
          }
        });
      }
    });
  });

  // Find the Schulze winner
  const wins: Record<string, number> = {};
  candidates.forEach((candidate) => {
    wins[candidate] = 0;
  });

  candidates.forEach((c1) => {
    candidates.forEach((c2) => {
      if (c1 !== c2 && strength[c1][c2] > strength[c2][c1]) {
        wins[c1]++;
      }
    });
  });

  const winner = candidates.reduce((a, b) => (wins[a] > wins[b] ? a : b));

  // Prepare data for visualization
  const matrixData = candidates.map((c1) =>
    candidates.map((c2) => {
      if (c1 === c2) return '-';
      return strength[c1][c2];
    })
  );

  return (
    <>
      <p>
        The Schulze method is a Condorcet method that uses a complex path-finding algorithm to
        determine the strongest paths between candidates. It always elects the Condorcet winner when
        one exists, and provides a complete ranking of candidates.
      </p>

      <Card className="mt-3">
        <Card.Header>Strength of Strongest Paths</Card.Header>
        <Card.Body>
          <div className="table-responsive">
            <Table bordered hover>
              <thead>
                <tr>
                  <th></th>
                  {candidates.map((candidate) => (
                    <th key={candidate}>{candidate}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {candidates.map((c1, i) => (
                  <tr key={c1}>
                    <th>{c1}</th>
                    {candidates.map((c2, j) => (
                      <td key={`${c1}-${c2}`} className={i === j ? 'bg-light' : ''}>
                        {i === j ? '-' : matrixData[i][j]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </Card.Body>
      </Card>

      <Card.Text className="mt-3">
        <strong>Schulze Winner:</strong> {winner}
      </Card.Text>
    </>
  );
};

// 12. Kemeny-Young Visualization
const KemenyYoungVisualization: React.FC<VotingMethodVisualizationProps> = ({
  rankings,
  candidates,
}) => {
  // This is a simplified visualization as the full Kemeny-Young method
  // is computationally intensive for more than a few candidates

  // Calculate pairwise preferences
  const pref: Record<string, Record<string, number>> = {};

  candidates.forEach((c1) => {
    pref[c1] = {};
    candidates.forEach((c2) => {
      if (c1 !== c2) {
        pref[c1][c2] = 0;
      }
    });
  });

  // Count pairwise preferences
  candidates.forEach((c1) => {
    candidates.forEach((c2) => {
      if (c1 !== c2) {
        rankings.forEach(({ ranking }) => {
          const pos1 = ranking.indexOf(c1);
          const pos2 = ranking.indexOf(c2);
          if (pos1 < pos2) {
            pref[c1][c2]++;
          }
        });
      }
    });
  });

  // For visualization, we'll just show the pairwise preference matrix
  // The actual Kemeny-Young winner would require finding the ranking with
  // the minimum Kendall tau distance to all voter rankings

  return (
    <>
      <p>
        The Kemeny-Young method finds the ranking that minimizes the total disagreement with all
        voters rankings. It is computationally intensive but provides a consensus ranking that best
        represents the voters preferences.
      </p>

      <Card className="mt-3">
        <Card.Header>Pairwise Preference Matrix</Card.Header>
        <Card.Body>
          <div className="table-responsive">
            <Table bordered hover>
              <thead>
                <tr>
                  <th></th>
                  {candidates.map((candidate) => (
                    <th key={candidate}>{candidate}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {candidates.map((c1) => (
                  <tr key={c1}>
                    <th>{c1}</th>
                    {candidates.map((c2) => (
                      <td key={`${c1}-${c2}`} className={c1 === c2 ? 'bg-light' : ''}>
                        {c1 === c2 ? '-' : pref[c1][c2]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </Card.Body>
      </Card>

      <div className="alert alert-info mt-3">
        <strong>Note:</strong> The full Kemeny-Young method requires computing the ranking with
        minimal Kendall tau distance to all voter rankings, which is computationally intensive and
        not visualized here. The table above shows the pairwise preference counts.
      </div>
    </>
  );
};

export default VotingMethodVisualizations;
