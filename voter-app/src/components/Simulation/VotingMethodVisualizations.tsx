// VotingMethodVisualizations.tsx
//
// Dispatcher component for per-method visualisations. The 3 simplest methods
// (Plurality, Borda, IRV) have been extracted to ./votingMethods/ and are
// imported from there; the other 9 still live in this file pending extraction.
// See ./votingMethods/index.ts for migration status.
import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Table } from '@/components/ui/table';
import {
  Bar,
  BarChart,
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { VotingMethodVisualizationProps } from './votingMethods/types';
import { VIZ_COLORS } from './votingMethods/types';
import MethodBarChart from './votingMethods/MethodBarChart';
import { PluralityVisualization, BordaVisualization, IRVVisualization } from './votingMethods';

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
      <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
        <h5>{method.charAt(0).toUpperCase() + method.slice(1)} Method Visualization</h5>
      </CardHeader>
      <CardBody>{renderMethodVisualization()}</CardBody>
    </Card>
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

      <MethodBarChart
        labels={candidates}
        values={candidates.map((candidate) => approvalVotes[candidate])}
        seriesName={`Approval Votes (Top ${approvalThreshold})`}
        title={`Approval Votes (Top ${approvalThreshold} Candidates)`}
        yLabel="Number of Approvals"
      />

      <p className="mt-3">
        <strong>Winner:</strong>{' '}
        {candidates.reduce((a, b) => (approvalVotes[a] > approvalVotes[b] ? a : b))}
      </p>
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

      <p className="mt-3">
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
      </p>

      <Card className="mt-3">
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
          Pairwise Comparison Matrix
        </CardHeader>
        <CardBody>
          <Table className="[&_th]:p-2 [&_td]:p-2 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border [&_tbody_tr:hover]:bg-muted/50">
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
        </CardBody>
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

  return (
    <>
      <p>
        The Two-Round System has two rounds of voting. In the first round, if a candidate receives a
        majority of votes, they win. If not, the top two candidates proceed to a second round.
      </p>

      <p className="mt-3">
        <strong>First Round Results:</strong>
      </p>

      <MethodBarChart
        labels={candidates}
        values={candidates.map((candidate) => firstRoundVotes[candidate])}
        seriesName="First Round Votes"
        title="First Round Votes"
        yLabel="Number of Votes"
      />

      <p className="mt-2">Majority threshold: {majority} votes</p>

      {firstRoundWinner ? (
        <div className="alert alert-success mt-3">
          <strong>First Round Winner:</strong> {firstRoundWinner}
          <p>Achieved majority with {firstRoundVotes[firstRoundWinner]} votes</p>
        </div>
      ) : (
        <>
          <p className="mt-3">
            <strong>Top Two Candidates Proceed to Second Round:</strong>
            <div className="flex flex-wrap gap-2 mt-1">
              {secondRoundCandidates.map((candidate) => (
                <Badge key={candidate} variant="primary" className="p-2">
                  {candidate}
                </Badge>
              ))}
            </div>
          </p>

          {secondRoundCandidates.length > 0 && (
            <>
              <p className="mt-3">
                <strong>Second Round Results:</strong>
              </p>

              <MethodBarChart
                labels={secondRoundCandidates}
                values={secondRoundCandidates.map((candidate) => secondRoundVotes[candidate])}
                seriesName="Second Round Votes"
                title="Second Round Votes"
                yLabel="Number of Votes"
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

  return (
    <>
      <p>
        Coombs method eliminates candidates with the most last-place votes in each round, until one
        candidate remains as the winner.
      </p>

      {!winner ? (
        <>
          <Card className="mt-3">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              Round {round} - Last Place Votes
            </CardHeader>
            <CardBody>
              <MethodBarChart
                labels={candidates.filter((c) => !eliminated.includes(c))}
                values={candidates
                  .filter((c) => !eliminated.includes(c))
                  .map((candidate) => lastPlaceVotes[candidate] || 0)}
                seriesName="Last Place Votes"
                title={`Last Place Votes - Round ${round}`}
                yLabel="Number of Last Place Votes"
              />
            </CardBody>
          </Card>

          {eliminated.length > 0 && (
            <Card className="mt-3">
              <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
                Eliminated Candidates
              </CardHeader>
              <CardBody>
                <div className="flex flex-wrap gap-2">
                  {eliminated.map((candidate) => (
                    <Badge key={candidate} variant="secondary" className="p-2">
                      {candidate}
                    </Badge>
                  ))}
                </div>
              </CardBody>
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

  // Radar: average score per candidate
  const radarRows = candidates.map((candidate) => ({
    candidate,
    score: Number(scoreData[candidate].avg.toFixed(3)),
  }));

  // Distribution: bin each candidate's scores into 0.5-wide buckets (0..5)
  const bins = candidates.map(() => Array.from({ length: 11 }, () => 0));
  candidates.forEach((candidate, index) => {
    scoreData[candidate].scores.forEach((score) => {
      const binIndex = Math.floor(score * 2); // Convert to 0.5 bins
      if (binIndex >= 0 && binIndex < 11) {
        bins[index][binIndex]++;
      }
    });
  });
  const distributionRows = Array.from({ length: 11 }, (_, bi) => {
    const row: Record<string, number | string> = { score: (bi * 0.5).toString() };
    candidates.forEach((candidate, ci) => {
      row[candidate] = bins[ci][bi];
    });
    return row;
  });

  return (
    <>
      <p>
        Score Voting allows voters to give each candidate a score (typically 0-5). In this
        visualization, we convert rankings to scores where higher ranks get higher scores. The
        candidate with the highest average score wins.
      </p>

      <div className="row">
        <div className="md:w-6/12">
          <Card>
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              Average Scores
            </CardHeader>
            <CardBody>
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={radarRows} outerRadius="72%">
                  <PolarGrid />
                  <PolarAngleAxis dataKey="candidate" tick={{ fontSize: 12 }} />
                  <PolarRadiusAxis domain={[0, 5]} tickCount={6} tick={{ fontSize: 11 }} />
                  <Radar
                    name="Average Scores"
                    dataKey="score"
                    stroke="#36A2EB"
                    fill="#36A2EB"
                    fillOpacity={0.3}
                    isAnimationActive={false}
                  />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            </CardBody>
          </Card>
        </div>

        <div className="md:w-6/12">
          <Card>
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              Score Distribution
            </CardHeader>
            <CardBody>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={distributionRows}
                  margin={{ top: 8, right: 16, left: 8, bottom: 16 }}
                >
                  <XAxis
                    dataKey="score"
                    tick={{ fontSize: 11 }}
                    label={{
                      value: 'Score (0-5)',
                      position: 'insideBottom',
                      offset: -8,
                      style: { fontSize: 12 },
                    }}
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fontSize: 12 }}
                    label={{
                      value: 'Number of Voters',
                      angle: -90,
                      position: 'insideLeft',
                      style: { fontSize: 12 },
                    }}
                  />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {candidates.map((candidate, ci) => (
                    <Bar
                      key={candidate}
                      dataKey={candidate}
                      fill={VIZ_COLORS[ci % VIZ_COLORS.length]}
                      isAnimationActive={false}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </CardBody>
          </Card>
        </div>
      </div>

      <p className="mt-3">
        <strong>Winner:</strong>{' '}
        {candidates.reduce((a, b) => (scoreData[a].avg > scoreData[b].avg ? a : b))}
        <span>
          {' '}
          (Average score: {Math.max(...candidates.map((c) => scoreData[c].avg)).toFixed(2)})
        </span>
      </p>
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

      <MethodBarChart
        labels={candidates}
        values={candidates.map((candidate) => roundVotes[currentRound][candidate])}
        seriesName={`Round ${currentRound} Votes`}
        title={`Round ${currentRound} Votes`}
        yLabel="Number of Votes"
      />

      <p className="mt-3">Majority threshold: {Math.ceil(rankings.length / 2)} votes</p>

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
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
          Pairwise Opposition Matrix
        </CardHeader>
        <CardBody>
          <div className="table-responsive">
            <Table className="[&_th]:p-2 [&_td]:p-2 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border [&_tbody_tr:hover]:bg-muted/50">
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
                      <td key={`${c1}-${c2}`} className={c1 === c2 ? 'bg-slate-100' : ''}>
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
        </CardBody>
      </Card>

      <Card className="mt-3">
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
          Maximum Opposition per Candidate
        </CardHeader>
        <CardBody>
          <MethodBarChart
            labels={candidates}
            values={candidates.map((candidate) => maxOpposition[candidate])}
            seriesName="Maximum Opposition"
            title="Maximum Opposition per Candidate"
            yLabel="Number of Votes Against"
          />
        </CardBody>
      </Card>

      <p className="mt-3">
        <strong>Minimax Winner:</strong> {winner}
        <p className="mt-1">
          {winner} has the smallest maximum opposition ({maxOpposition[winner]} votes)
        </p>
      </p>
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
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
          Strength of Strongest Paths
        </CardHeader>
        <CardBody>
          <div className="table-responsive">
            <Table className="[&_th]:p-2 [&_td]:p-2 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border [&_tbody_tr:hover]:bg-muted/50">
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
                      <td key={`${c1}-${c2}`} className={i === j ? 'bg-slate-100' : ''}>
                        {i === j ? '-' : matrixData[i][j]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </CardBody>
      </Card>

      <p className="mt-3">
        <strong>Schulze Winner:</strong> {winner}
      </p>
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
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
          Pairwise Preference Matrix
        </CardHeader>
        <CardBody>
          <div className="table-responsive">
            <Table className="[&_th]:p-2 [&_td]:p-2 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border [&_tbody_tr:hover]:bg-muted/50">
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
                      <td key={`${c1}-${c2}`} className={c1 === c2 ? 'bg-slate-100' : ''}>
                        {c1 === c2 ? '-' : pref[c1][c2]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </CardBody>
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
