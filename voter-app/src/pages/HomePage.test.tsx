import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import HomePage from './HomePage';

// Mock the API call made by the useQuickStats hook on mount
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

describe('HomePage', () => {
  it('renders the hero title', () => {
    render(<HomePage />);
    expect(
      screen.getByText('Testez comment votre bulletin de vote change tout')
    ).toBeInTheDocument();
  });

  it('renders the 3 action cards', () => {
    render(<HomePage />);
    expect(screen.getByText('Simuler une élection')).toBeInTheDocument();
    // "Comparer les méthodes" appears in both the hero CTA and the action card
    expect(screen.getAllByText('Comparer les méthodes').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Et si le vote blanc comptait ?')).toBeInTheDocument();
  });

  it('renders the "Pourquoi ça compte" section', () => {
    render(<HomePage />);
    expect(screen.getByText('Pourquoi ça compte')).toBeInTheDocument();
    expect(screen.getByText('méthodes de vote comparées')).toBeInTheDocument();
  });

  it('renders the historical elections section', () => {
    render(<HomePage />);
    expect(screen.getByText('Élections historiques analysées')).toBeInTheDocument();
    // Multiple election cards mention "Présidentielle"
    expect(screen.getAllByText(/Présidentielle/).length).toBeGreaterThanOrEqual(1);
  });

  it('shows spinner for dynamic stats initially', () => {
    render(<HomePage />);
    const spinners = document.querySelectorAll('.spinner-border');
    expect(spinners.length).toBeGreaterThan(0);
  });

  it('shows disagreeing methods count after API resolves', async () => {
    render(<HomePage />);
    // plurality→Alice, borda→Bob, irv→Alice → 1 method disagrees with plurality
    await waitFor(() => {
      expect(screen.getByText('1/3')).toBeInTheDocument();
    });
  });

  it('renders action card links to the right pages', () => {
    render(<HomePage />);
    const links = screen.getAllByRole('link');
    const hrefs = links.map((l) => l.getAttribute('href'));
    expect(hrefs).toContain('/scenario-builder');
    expect(hrefs).toContain('/simulation/compare');
    expect(hrefs).toContain('/constitutional-crisis');
  });
});
