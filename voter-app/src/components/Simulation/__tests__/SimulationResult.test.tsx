import React from 'react';
import { render, screen } from '@testing-library/react';
import SimulationResult from '../SimulationResult';

vi.mock('../VotingMethodsComparison', () => ({
  default: () => <div data-testid="voting-methods-comparison" />,
}));
vi.mock('../ScoreVotingComparison', () => ({
  default: () => <div data-testid="score-voting-comparison" />,
}));
// Charts now render with Recharts (no chart.js / react-google-charts). The
// preprocessors are mocked with minimal valid shapes; the component wraps each
// chart in a testid div so we assert presence without depending on SVG layout.
vi.mock('../SimulationSankey', () => ({
  default: () => [
    ['From', 'To', 'Weight'],
    ['Start', 'R:1-Alice', 1],
    ['R:1-Alice', 'Winner: Alice', 1],
  ],
}));
vi.mock('../SimulationRadar', () => ({
  default: () => ({
    labels: ['Rank 1', 'Rank 2'],
    datasets: [{ label: 'Alice', data: [0.5, 0.5] }],
  }),
}));

const baseResult = {
  simulation_type: ['votes', 'ranked'],
  metadata: {
    population_size: 500,
    candidates: ['Alice', 'Bob', 'Charlie'],
    turnout_rate: 0.75,
    demographics: {},
    influence_weights: {},
  },
  votes: [
    { voter_id: 1, preference: 'Alice' },
    { voter_id: 2, preference: 'Bob' },
  ],
  tally: { Alice: 1, Bob: 1 },
  rankings: [
    { voter_id: 1, ranking: ['Alice', 'Bob', 'Charlie'] },
    { voter_id: 2, ranking: ['Bob', 'Alice', 'Charlie'] },
  ],
  condorcet_winner: 'Alice',
  plurality_winner: 'Alice',
};

describe('SimulationResult', () => {
  it('returns null when result is null', () => {
    const { container } = render(<SimulationResult result={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders simulation metadata', () => {
    render(<SimulationResult result={baseResult as any} />);
    expect(screen.getByText('Simulation Results')).toBeInTheDocument();
    expect(screen.getByText(/Population Size:/)).toBeInTheDocument();
    expect(screen.getByText(/500/)).toBeInTheDocument();
    expect(screen.getByText(/Turnout Rate:/)).toBeInTheDocument();
    expect(screen.getByText(/75.0%/)).toBeInTheDocument();
    expect(screen.getByText(/Alice, Bob, Charlie/)).toBeInTheDocument();
  });

  it('renders standard voting results', () => {
    render(<SimulationResult result={baseResult as any} />);
    expect(screen.getByText('Standard Voting Results')).toBeInTheDocument();
    expect(screen.getByText('Sample Votes:')).toBeInTheDocument();
    expect(screen.getByText(/Voter 1: Alice/)).toBeInTheDocument();
    expect(screen.getByText(/Voter 2: Bob/)).toBeInTheDocument();
  });

  it('renders vote tally', () => {
    render(<SimulationResult result={baseResult as any} />);
    expect(screen.getByText('Vote Tally:')).toBeInTheDocument();
    expect(screen.getByText(/Alice: 1 votes/)).toBeInTheDocument();
    expect(screen.getByText(/Bob: 1 votes/)).toBeInTheDocument();
  });

  it('renders charts when rankings present', () => {
    render(<SimulationResult result={baseResult as any} />);
    expect(screen.getByTestId('sankey-chart')).toBeInTheDocument();
    expect(screen.getByTestId('radar-chart')).toBeInTheDocument();
  });

  it('renders voting methods comparison', () => {
    render(<SimulationResult result={baseResult as any} />);
    expect(screen.getByText('Voting Method Winners:')).toBeInTheDocument();
    expect(screen.getByTestId('voting-methods-comparison')).toBeInTheDocument();
  });

  it('renders score voting when all_scores provided', () => {
    const resultWithScores = {
      ...baseResult,
      all_scores: [{ voter_id: 1, scores: { Alice: 5, Bob: 3 } }],
    };
    render(<SimulationResult result={resultWithScores as any} />);
    expect(screen.getByTestId('score-voting-comparison')).toBeInTheDocument();
  });

  it('handles votes-only simulation types', () => {
    const votesOnly = {
      ...baseResult,
      simulation_type: ['votes'],
      rankings: undefined,
      condorcet_winner: undefined,
      all_scores: undefined,
    };
    render(<SimulationResult result={votesOnly as any} />);
    expect(screen.getByText('Standard Voting Results')).toBeInTheDocument();
    expect(screen.queryByTestId('sankey-chart')).not.toBeInTheDocument();
  });

  it('does not render tally when absent', () => {
    const noTally = {
      ...baseResult,
      tally: undefined,
    };
    render(<SimulationResult result={noTally as any} />);
    expect(screen.queryByText('Vote Tally:')).not.toBeInTheDocument();
  });
});
