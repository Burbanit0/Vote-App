import React from 'react';
import { Card, Container, Row, Col } from 'react-bootstrap';
import { Radar } from 'react-chartjs-2';
import { Chart } from 'react-google-charts';
import preprocessForGoogleSankey from './SimulationSankey';
import preprocessRadarData from './SimulationRadar';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';
import VotingMethodsComparison from './VotingMethodsComparison';
import ScoreVotingComparison from './ScoreVotingComparison';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

// Basic types
type VoterId = number;
type Candidate = string;
type Preference = Candidate;
type Score = number;
type Ranking = Candidate[];
type Tally = Record<Candidate, number>;
type AverageScores = Record<Candidate, number>;

// Voter types
interface BaseVoter {
  id: VoterId;
  age: string;
  gender: string;
  location: string;
  education: string;
  income: string;
  ideology: string;
  turnout: boolean;
}

interface StandardVoter extends BaseVoter {
  preference: Preference;
}

interface ScoreVoter extends BaseVoter {
  scores: Record<Candidate, Score>;
}

// Result types
interface VoteResult {
  voter_id: VoterId;
  preference: Preference;
}

interface RankingResult {
  voter_id: VoterId;
  ranking: Ranking;
}

interface ScoreResult {
  voter_id: VoterId;
  scores: Record<Candidate, Score>;
}

interface SimulationMetadata {
  population_size: number;
  candidates: Candidate[];
  turnout_rate: number;
  demographics: Record<string, Record<string, number>>;
  influence_weights: Record<string, Record<string, Record<Candidate, number>>>;
}

// Response types
export interface SimulationResponse {
  simulation_type: ('votes' | 'ranked' | 'scores')[];
  metadata: SimulationMetadata;
  votes?: VoteResult[];
  tally?: Tally;
  voters_r?: StandardVoter[];
  rankings?: RankingResult[];
  first_choice_tally?: Tally;
  voters_n?: ScoreVoter[];
  all_scores?: ScoreResult[];
  avg_scores?: AverageScores;

  //Voting ranking methods
  condorcet_winner?: Candidate;
  two_round_winner?: Candidate;
  borda_winner?: Candidate;
  plurality_winner?: Candidate;
  approval_winner?: Candidate;
  irv_winner?: Candidate;
  coombs_winner?: Candidate;
  score_winner?: Candidate;
  kemeny_young_winner?: Candidate;
  bucklin_winner?: Candidate;
  minimax_winner?: Candidate;
  schulze_winner?: Candidate;
}

interface SimulationResultProps {
  result: SimulationResponse | null;
}

const SimulationResult: React.FC<SimulationResultProps> = ({ result }) => {
  if (!result) return null;

  const hasVotes = result.simulation_type.includes('votes');
  const hasRanked = result.simulation_type.includes('ranked');
  const hasScores = result.simulation_type.includes('scores');

  const rankings = result.rankings || [];
  const candidates = result.metadata.candidates;

  const winners = {
    condorcet_winner: result.condorcet_winner,
    two_round_winner: result.two_round_winner,
    borda_winner: result.borda_winner,
    plurality_winner: result.plurality_winner,
    approval_winner: result.approval_winner,
    irv_winner: result.irv_winner,
    coombs_winner: result.coombs_winner,
    score_winner: result.score_winner,
    bucklin_winner: result.bucklin_winner,
    minimax_winner: result.minimax_winner,
    schulze_winner: result.schulze_winner,
    kemeny_young_winner: result.kemeny_young_winner,
  };

  return (
    <Container>
      <Row className="mt-4">
        <Card>
          <Card.Header as="h3">Simulation Results</Card.Header>
          <Card.Body>
            <Card.Text>
              <strong>Simulation Types:</strong> {result.simulation_type.join(', ')}
            </Card.Text>
            <Card.Text>
              <strong>Population Size:</strong> {result.metadata.population_size}
            </Card.Text>
            <Card.Text>
              <strong>Turnout Rate:</strong> {(result.metadata.turnout_rate * 100).toFixed(1)}%
            </Card.Text>
            <Card.Text>
              <strong>Candidates:</strong> {result.metadata.candidates.join(', ')}
            </Card.Text>

            {/* Votes Simulation Results */}
            {hasVotes && (
              <>
                <Card.Text as="h4" className="mt-4">
                  Standard Voting Results
                </Card.Text>

                {result.votes && (
                  <>
                    <Card.Text as="h5">Sample Votes:</Card.Text>
                    <ul>
                      {result.votes.slice(0, 5).map((vote, index) => (
                        <li key={index}>
                          Voter {vote.voter_id}: {vote.preference}
                        </li>
                      ))}
                    </ul>
                  </>
                )}

                {result.tally && (
                  <>
                    <Card.Text as="h5" className="mt-3">
                      Vote Tally:
                    </Card.Text>
                    <ul>
                      {Object.entries(result.tally).map(([candidate, count]) => (
                        <li key={candidate}>
                          {candidate}: {count} votes
                        </li>
                      ))}
                    </ul>

                    {hasRanked && result.rankings && (
                      <>
                        <Row className="mt-3">
                          <Col md={6}>
                            <Card>
                              <Card.Header as="h5">Sankey Chart</Card.Header>
                              <Card.Body>
                                <Chart
                                  chartType="Sankey"
                                  width="100%"
                                  height="300px"
                                  data={preprocessForGoogleSankey(result.rankings)}
                                  options={{
                                    sankey: {
                                      node: {
                                        colors: [
                                          '#a6cee3',
                                          '#1f78b4',
                                          '#b2df8a',
                                          '#33a02c',
                                          '#fb9a99',
                                          '#e31a1c',
                                        ],
                                        width: 20,
                                      },
                                      link: {
                                        colorMode: 'gradient',
                                        colors: [
                                          '#a6cee3',
                                          '#1f78b4',
                                          '#b2df8a',
                                          '#33a02c',
                                          '#fb9a99',
                                          '#e31a1c',
                                        ],
                                      },
                                    },
                                  }}
                                />
                              </Card.Body>
                            </Card>
                          </Col>
                          <Col md={6}>
                            <Card>
                              <Card.Header as="h5">Radar Chart</Card.Header>
                              <Card.Body>
                                <Radar
                                  data={preprocessRadarData(result.rankings)}
                                  options={{
                                    scales: {
                                      r: {
                                        min: 0,
                                        max: 1,
                                        ticks: {
                                          stepSize: 0.2,
                                        },
                                      },
                                    },
                                    plugins: {
                                      title: {
                                        display: true,
                                        text: 'Voter Consensus (Normalized)',
                                      },
                                    },
                                  }}
                                />
                              </Card.Body>
                            </Card>
                          </Col>
                        </Row>
                      </>
                    )}
                  </>
                )}

                {/* Display all voting method winners in a table */}
                {(result.condorcet_winner ||
                  result.two_round_winner ||
                  result.borda_winner ||
                  result.plurality_winner ||
                  result.approval_winner ||
                  result.irv_winner ||
                  result.coombs_winner ||
                  result.score_winner ||
                  result.kemeny_young_winner ||
                  result.bucklin_winner ||
                  result.minimax_winner ||
                  result.schulze_winner) && (
                  <>
                    <Card.Text as="h5" className="mt-4">
                      Voting Method Winners:
                    </Card.Text>
                    <VotingMethodsComparison
                      rankings={rankings}
                      candidates={candidates}
                      winners={winners}
                    />
                  </>
                )}
                {result.all_scores && result.all_scores.length > 0 && (
                  <Card>
                    <Card.Body>
                      <ScoreVotingComparison scores={result.all_scores} candidates={candidates} />
                    </Card.Body>
                  </Card>
                )}
              </>
            )}
          </Card.Body>
        </Card>
      </Row>
    </Container>
  );
};

export default SimulationResult;
