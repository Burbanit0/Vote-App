import React from 'react';
import { Badge, Card } from 'react-bootstrap';
import MethodBarChart from './MethodBarChart';
import { VotingMethodVisualizationProps } from './types';

/**
 * Instant Runoff Voting (IRV) — repeated runoff: each round the candidate
 * with the fewest first-choice votes is eliminated and their ballots
 * transfer to the next-ranked remaining candidate. Continues until one
 * candidate has a majority. Often produces a different winner than
 * Plurality because eliminated-candidate ballots are not wasted.
 */
const IRVVisualization: React.FC<VotingMethodVisualizationProps> = ({ rankings, candidates }) => {
  const [round, setRound] = React.useState(1);
  const [eliminated, setEliminated] = React.useState<string[]>([]);
  const [currentVotes, setCurrentVotes] = React.useState<Record<string, number>>({});
  const [winner, setWinner] = React.useState<string | null>(null);

  React.useEffect(() => {
    simulateIRV();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const simulateIRV = () => {
    let remainingCandidates = [...candidates];
    const currentRound = 1;
    let votes = { ...currentVotes };
    let winnerFound = false;

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

    const checkRound = () => {
      if (remainingCandidates.length === 1) {
        setWinner(remainingCandidates[0]);
        return;
      }

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
        const minVotes = Math.min(...Object.values(votes));
        const toEliminate = Object.entries(votes)
          .filter(([_, count]) => count === minVotes)
          .map(([candidate, _]) => candidate);

        setEliminated((prev) => [...prev, ...toEliminate]);
        remainingCandidates = remainingCandidates.filter((c) => !toEliminate.includes(c));

        if (remainingCandidates.length === 1) {
          setWinner(remainingCandidates[0]);
          return;
        }

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

  const activeCandidates = candidates.filter((c) => !eliminated.includes(c));

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
          <MethodBarChart
            labels={activeCandidates}
            values={activeCandidates.map((candidate) => currentVotes[candidate] || 0)}
            seriesName={`Round ${round} Votes`}
            title={`Round ${round} Vote Distribution`}
            yLabel="Number of Votes"
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

export default IRVVisualization;
