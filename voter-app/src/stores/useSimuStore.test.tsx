import { render, screen, fireEvent } from '@testing-library/react';
import { useSimulation, useSimuStore } from './useSimuStore';
import { VoterSimu, CandidateSimu } from '../types';

const mockVoter: VoterSimu = {
  id: 0,
  age: 35,
  gender: 'male',
  education: 'bachelor',
  income: 'middle',
  region: 'urban',
  employment_status: 'employed',
  family_status: 'single',
  ethnicity_immigration: 'native',
  religion: 'non_religious',
  political_lean: 0,
  political_lean_normalized: 0.5,
  issue_priorities: { economy: 0.5, environment: 0.5 },
  issue_positions: { economy: 0.5, environment: 0.5 },
  party_loyalty: 0.5,
  preferred_party: 'Independent',
  likelihood_to_vote: 0.8,
  mood: 0,
  strategic_propensity: 0.2,
  voting_style: 'sincere',
};

const mockCandidate: CandidateSimu = {
  id: 0,
  name: 'Alice',
  party: 'Green',
  party_lean: -0.8,
  ideology_position: 0.2,
  policies: { economy: 0.3, environment: 0.8 },
  charisma: 0.7,
  scandals: 0,
  campaign_funds: 500000,
  experience: 10,
  popularity: 0.6,
};

const TestConsumer = () => {
  const { voters, setVoters, candidates, setCandidates, issues, setIssues } = useSimulation();
  return (
    <div>
      <span data-testid="voters-count">{voters.length}</span>
      <span data-testid="candidates-count">{candidates.length}</span>
      <span data-testid="issues-count">{issues.length}</span>
      <button data-testid="set-voters" onClick={() => setVoters([mockVoter])}>
        Add Voter
      </button>
      <button data-testid="set-candidates" onClick={() => setCandidates([mockCandidate])}>
        Add Candidate
      </button>
      <button data-testid="set-issues" onClick={() => setIssues(['economy', 'environment'])}>
        Set Issues
      </button>
    </div>
  );
};

describe('useSimuStore (useSimulation)', () => {
  beforeEach(() => {
    useSimuStore.setState({ voters: [], candidates: [], issues: [] });
  });

  it('starts with empty arrays', () => {
    render(<TestConsumer />);
    expect(screen.getByTestId('voters-count')).toHaveTextContent('0');
    expect(screen.getByTestId('candidates-count')).toHaveTextContent('0');
    expect(screen.getByTestId('issues-count')).toHaveTextContent('0');
  });

  it('sets voters', () => {
    render(<TestConsumer />);
    fireEvent.click(screen.getByTestId('set-voters'));
    expect(screen.getByTestId('voters-count')).toHaveTextContent('1');
  });

  it('sets candidates', () => {
    render(<TestConsumer />);
    fireEvent.click(screen.getByTestId('set-candidates'));
    expect(screen.getByTestId('candidates-count')).toHaveTextContent('1');
  });

  it('sets issues', () => {
    render(<TestConsumer />);
    fireEvent.click(screen.getByTestId('set-issues'));
    expect(screen.getByTestId('issues-count')).toHaveTextContent('2');
  });

  it('replaces voters on subsequent calls', () => {
    render(<TestConsumer />);
    fireEvent.click(screen.getByTestId('set-voters'));
    expect(screen.getByTestId('voters-count')).toHaveTextContent('1');
    fireEvent.click(screen.getByTestId('set-voters'));
    expect(screen.getByTestId('voters-count')).toHaveTextContent('1');
  });
});
