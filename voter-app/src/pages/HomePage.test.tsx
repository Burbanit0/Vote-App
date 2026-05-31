import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router';
import HomePage from './HomePage';
import { ElectionProvider } from '../stores/useElectionStore';

jest.mock('../services/simulationCompareApi', () => ({
  runComparisonSimulation: jest.fn().mockResolvedValue({
    condorcet_winner: 'Alice',
    methods: {
      plurality: { winner: 'Alice', bayesian_regret: 0.12, majority_satisfaction: 0.75, strategic_vulnerability: 0.2, condorcet_consistent: true },
      borda:     { winner: 'Bob',   bayesian_regret: 0.05, majority_satisfaction: 0.9,  strategic_vulnerability: 0.08, condorcet_consistent: false },
      irv:       { winner: 'Alice', bayesian_regret: 0.09, majority_satisfaction: 0.82, strategic_vulnerability: 0.11, condorcet_consistent: true },
    },
  }),
}));

jest.mock('../services/electionApi', () => ({
  simulateElection:  jest.fn().mockResolvedValue({
    config: {}, voters_snapshot: [], candidates: [],
    methods: {
      plurality:     { winner: 'Chirac', bayesian_regret: 0.03, majority_satisfaction: 0.7, condorcet_consistent: null },
      schulze:       { winner: 'Jospin', bayesian_regret: 0.02, majority_satisfaction: 0.8, condorcet_consistent: null },
      borda:         { winner: 'Chirac', bayesian_regret: 0.03, majority_satisfaction: 0.7, condorcet_consistent: null },
      irv:           { winner: 'Chirac', bayesian_regret: 0.03, majority_satisfaction: 0.7, condorcet_consistent: null },
      two_round:     { winner: 'Chirac', bayesian_regret: 0.03, majority_satisfaction: 0.7, condorcet_consistent: null },
      approval:      { winner: 'Chirac', bayesian_regret: 0.03, majority_satisfaction: 0.7, condorcet_consistent: null },
      star_voting:   { winner: 'Chirac', bayesian_regret: 0.03, majority_satisfaction: 0.7, condorcet_consistent: null },
      median_voting: { winner: 'Chirac', bayesian_regret: 0.03, majority_satisfaction: 0.7, condorcet_consistent: null },
    },
    condorcet_winner: 'Jospin', blank_rate: 0,
    campaign_trajectory: null, inter_method_agreement: 0.5, condorcet_exists: true,
  }),
  interpretElection: jest.fn().mockResolvedValue(null),
}));

jest.mock('../components/shared/OnboardingTour', () => () => null);

async function renderPage() {
  await act(async () => {
    render(
      <MemoryRouter>
        <ElectionProvider>
          <HomePage />
        </ElectionProvider>
      </MemoryRouter>
    );
  });
}

describe('HomePage', () => {
  beforeEach(() => { localStorage.clear(); });

  it('renders the hero title', async () => {
    await renderPage();
    // heroTitle key → English or French
    expect(
      screen.queryByText(/ballot changes everything|bulletin de vote change/i) ??
      screen.queryByText(/testez|see how/i)
    ).not.toBeNull();
  });

  it('renders the Election Lab CTA button', async () => {
    await renderPage();
    expect(screen.getByText(/Découvrir le Lab|Discover the Lab/i)).toBeInTheDocument();
  });

  it('renders the QuickCompare widget section', async () => {
    await renderPage();
    expect(screen.getByText(/Essayez|Try it now/i)).toBeInTheDocument();
  });

  it('renders the 3 feature items', async () => {
    await renderPage();
    expect(screen.getByText(/Ce que vous pouvez faire|What you can do/i)).toBeInTheDocument();
  });

  it('renders the stats section', async () => {
    await renderPage();
    expect(screen.getByText(/voting methods compared|méthodes de vote comparées/i)).toBeInTheDocument();
  });

  it('shows disagreeing methods count after API resolves', async () => {
    await renderPage();
    // plurality→Alice, borda→Bob, irv→Alice → 1 method disagrees
    await waitFor(() => {
      expect(screen.getByText('1/3')).toBeInTheDocument();
    });
  });

  it('renders scenario cards in the widget', async () => {
    await renderPage();
    expect(screen.getAllByText(/France 2002/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/USA 1992/i).length).toBeGreaterThan(0);
  });
});
