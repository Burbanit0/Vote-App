import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import HomePage from './HomePage';

jest.mock('../services/simulationCompareApi', () => ({
  runComparisonSimulation: jest.fn().mockResolvedValue({
    condorcet_winner: 'Alice',
    methods: {
      plurality: {
        winner: 'Alice',
        bayesian_regret: 0.12,
        majority_satisfaction: 0.75,
        strategic_vulnerability: 0.2,
        condorcet_consistent: true,
      },
      borda: {
        winner: 'Bob',
        bayesian_regret: 0.05,
        majority_satisfaction: 0.9,
        strategic_vulnerability: 0.08,
        condorcet_consistent: false,
      },
      irv: {
        winner: 'Alice',
        bayesian_regret: 0.09,
        majority_satisfaction: 0.82,
        strategic_vulnerability: 0.11,
        condorcet_consistent: true,
      },
    },
  }),
}));

// Wrap every render in act(async () => {}) so React flushes the useQuickStats
// promise resolution (mockResolvedValue) before assertions run, avoiding
// "not wrapped in act(...)" warnings.
async function renderPage() {
  await act(async () => {
    render(<HomePage />);
  });
}

describe('HomePage', () => {
  it('renders the hero title', async () => {
    await renderPage();
    expect(
      screen.getByText('See how your ballot changes everything')
    ).toBeInTheDocument();
  });

  it('renders the 3 action cards', async () => {
    await renderPage();
    expect(screen.getByText('Simulate an election')).toBeInTheDocument();
    expect(screen.getAllByText('Compare methods').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('What if blank votes counted?')).toBeInTheDocument();
  });

  it('renders the stats section', async () => {
    await renderPage();
    expect(screen.getByText('voting methods compared')).toBeInTheDocument();
  });

  it('renders the historical elections section', async () => {
    await renderPage();
    expect(screen.getByText('Historical elections analyzed')).toBeInTheDocument();
    expect(screen.getAllByText(/Presidential/).length).toBeGreaterThanOrEqual(1);
  });

  it('shows disagreeing methods count after API resolves', async () => {
    await renderPage();
    // plurality→Alice, borda→Bob, irv→Alice → 1 method disagrees with plurality
    await waitFor(() => {
      expect(screen.getByText('1/3')).toBeInTheDocument();
    });
  });

  it('renders action card links to the right pages', async () => {
    await renderPage();
    const links = screen.getAllByRole('link');
    const hrefs = links.map((l) => l.getAttribute('href'));
    expect(hrefs).toContain('/scenario-builder');
    expect(hrefs).toContain('/simulation/compare');
    expect(hrefs).toContain('/constitutional-crisis');
  });
});
