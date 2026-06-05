import React from 'react';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Col, Container, Row } from '@/components/ui/grid';
import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Sankey,
  Tooltip,
} from 'recharts';
import preprocessForGoogleSankey from './SimulationSankey';
import preprocessRadarData from './SimulationRadar';
import { VIZ_COLORS } from './votingMethods/types';
import VotingMethodsComparison from './VotingMethodsComparison';
import ScoreVotingComparison from './ScoreVotingComparison';

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

  const rankings = result.rankings || [];
  const candidates = result.metadata.candidates;

  // Reshape the legacy preprocessor outputs into Recharts shapes (the
  // preprocessors + their unit tests stay untouched; we only adapt here).
  const sankeyRows = (
    preprocessForGoogleSankey(rankings) as unknown as Array<[string, string, number]>
  ).slice(1); // drop the ['From','To','Weight'] header row
  const sankeyNodeNames = [...new Set(sankeyRows.flatMap(([from, to]) => [from, to]))];
  const sankeyIndex: Record<string, number> = Object.fromEntries(
    sankeyNodeNames.map((name, i) => [name, i])
  );
  const sankeyData = {
    nodes: sankeyNodeNames.map((name) => ({ name })),
    links: sankeyRows.map(([from, to, value]) => ({
      source: sankeyIndex[from],
      target: sankeyIndex[to],
      value,
    })),
  };

  const radarRaw = preprocessRadarData(rankings) as {
    labels?: string[];
    datasets?: Array<{ label: string; data: number[] }>;
  };
  const radarSeries = radarRaw.datasets ?? [];
  const radarRows = (radarRaw.labels ?? []).map((label, ri) => {
    const row: Record<string, number | string> = { rank: label };
    radarSeries.forEach((ds) => {
      row[ds.label] = ds.data[ri] ?? 0;
    });
    return row;
  });

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
          <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
            Simulation Results
          </CardHeader>
          <CardBody>
            <p>
              <strong>Simulation Types:</strong> {result.simulation_type.join(', ')}
            </p>
            <p>
              <strong>Population Size:</strong> {result.metadata.population_size}
            </p>
            <p>
              <strong>Turnout Rate:</strong> {(result.metadata.turnout_rate * 100).toFixed(1)}%
            </p>
            <p>
              <strong>Candidates:</strong> {result.metadata.candidates.join(', ')}
            </p>

            {/* Votes Simulation Results */}
            {hasVotes && (
              <>
                <p className="mt-4">Standard Voting Results</p>

                {result.votes && (
                  <>
                    <p>Sample Votes:</p>
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
                    <p className="mt-3">Vote Tally:</p>
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
                              <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
                                Sankey Chart
                              </CardHeader>
                              <CardBody>
                                <div data-testid="sankey-chart">
                                  {sankeyData.links.length > 0 && (
                                    <ResponsiveContainer width="100%" height={300}>
                                      <Sankey
                                        data={sankeyData}
                                        nodePadding={24}
                                        node={{ stroke: '#777', strokeWidth: 1 }}
                                        link={{ stroke: '#1f78b4', strokeOpacity: 0.25 }}
                                      >
                                        <Tooltip />
                                      </Sankey>
                                    </ResponsiveContainer>
                                  )}
                                </div>
                              </CardBody>
                            </Card>
                          </Col>
                          <Col md={6}>
                            <Card>
                              <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
                                Radar Chart
                              </CardHeader>
                              <CardBody>
                                <div data-testid="radar-chart">
                                  <p
                                    className="text-center font-semibold mb-2"
                                    style={{ fontSize: '0.95rem' }}
                                  >
                                    Voter Consensus (Normalized)
                                  </p>
                                  <ResponsiveContainer width="100%" height={300}>
                                    <RadarChart data={radarRows} outerRadius="70%">
                                      <PolarGrid />
                                      <PolarAngleAxis dataKey="rank" tick={{ fontSize: 11 }} />
                                      <PolarRadiusAxis
                                        domain={[0, 1]}
                                        tickCount={6}
                                        tick={{ fontSize: 10 }}
                                      />
                                      {radarSeries.map((ds, ci) => (
                                        <Radar
                                          key={ds.label}
                                          name={ds.label}
                                          dataKey={ds.label}
                                          stroke={VIZ_COLORS[ci % VIZ_COLORS.length]}
                                          fill={VIZ_COLORS[ci % VIZ_COLORS.length]}
                                          fillOpacity={0.15}
                                          isAnimationActive={false}
                                        />
                                      ))}
                                      <Legend wrapperStyle={{ fontSize: 12 }} />
                                      <Tooltip />
                                    </RadarChart>
                                  </ResponsiveContainer>
                                </div>
                              </CardBody>
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
                    <p className="mt-4">Voting Method Winners:</p>
                    <VotingMethodsComparison
                      rankings={rankings}
                      candidates={candidates}
                      winners={winners}
                    />
                  </>
                )}
                {result.all_scores && result.all_scores.length > 0 && (
                  <Card>
                    <CardBody>
                      <ScoreVotingComparison scores={result.all_scores} candidates={candidates} />
                    </CardBody>
                  </Card>
                )}
              </>
            )}
          </CardBody>
        </Card>
      </Row>
    </Container>
  );
};

export default SimulationResult;
