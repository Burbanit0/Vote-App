import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import ElectionLabPage from '../ElectionLabPage';
import { ElectionProvider } from '../../stores/useElectionStore';

jest.mock('../../services/electionApi', () => ({
  simulateElection:   jest.fn(),
  interpretElection:  jest.fn(),
}));

jest.mock('../../components/Simulation/IdeologyMapChart',    () => () => <div data-testid="ideology-map" />);
jest.mock('../../components/Simulation/VoteStepAnimator',    () => () => <div data-testid="vote-step" />);
jest.mock('../../components/Simulation/MonteCarloResults',   () => () => <div data-testid="monte-carlo" />);
jest.mock('../../components/Simulation/ManipulabilityChart', () => () => <div data-testid="manipulability" />);

const { simulateElection, interpretElection } = jest.requireMock('../../services/electionApi') as {
  simulateElection:  jest.Mock;
  interpretElection: jest.Mock;
};

const MOCK_RESULT = {
  config:                  {},
  voters_snapshot:         [],
  candidates:              [{ name: 'Alice', x: -0.5, y: 0.0, party: 'Liberal' }],
  methods: {
    plurality: { winner: 'Alice', bayesian_regret: 0.02, majority_satisfaction: 0.8, condorcet_consistent: true },
    schulze:   { winner: 'Alice', bayesian_regret: 0.01, majority_satisfaction: 0.85, condorcet_consistent: true },
  },
  condorcet_winner:        'Alice',
  blank_rate:              0,
  campaign_trajectory:     null,
  inter_method_agreement:  1.0,
  condorcet_exists:        true,
};

function renderPage() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <ElectionLabPage />
      </ElectionProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  simulateElection.mockResolvedValue(MOCK_RESULT);
  interpretElection.mockResolvedValue({
    headline: 'Test headline', condorcet_analysis: 'Condorcet ok',
    divergence_reason: '', method_groups: [], best_by_regret: 'schulze',
    worst_by_regret: 'plurality', blank_analysis: null,
    pedagogical_note: 'Note', key_facts: [],
  });
  localStorage.clear();
});

describe('ElectionLabPage', () => {
  it('renders the title and simulate button', () => {
    renderPage();
    expect(screen.getAllByText(/Election Lab/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Simuler|Simulate/i).length).toBeGreaterThan(0);
  });

  it('renders parameter accordion sections', () => {
    renderPage();
    // Use getAllBy because the LabCentralView (added in Sprint 2) reuses these
    // labels in the active-modules badge bar.
    expect(screen.getAllByText(/Candidats|Candidates/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Électorat|Electorate/i).length).toBeGreaterThan(0);
  });

  it('clicking Simulate calls simulateElection', async () => {
    renderPage();
    const btn = screen.getAllByText(/Simuler|Simulate/i).find(
      (el) => el.closest('button') !== null
    );
    expect(btn).toBeTruthy();
    fireEvent.click(btn!.closest('button')!);
    await waitFor(() => expect(simulateElection).toHaveBeenCalledTimes(1));
  });

  it('shows results tab after simulation', async () => {
    renderPage();
    const btn = screen.getAllByText(/Simuler|Simulate/i).find(
      (el) => el.closest('button') !== null
    );
    fireEvent.click(btn!.closest('button')!);
    await waitFor(() => expect(screen.getAllByText(/plurality/i).length).toBeGreaterThan(0));
  });

  it('applying scenario france2022 loads 5 candidates', async () => {
    renderPage();
    const scenarioBtn = screen.getByText(/Scénario|Scenario/i);
    fireEvent.click(scenarioBtn);
    const france = await screen.findByText(/France 2022/i);
    fireEvent.click(france);
    // The accordion should show Macron, Le Pen, etc.
    await waitFor(() => {
      const inputs = screen.getAllByDisplayValue(/Macron|Le Pen|Mélenchon/i);
      expect(inputs.length).toBeGreaterThan(0);
    });
  });

  it('noResults alert shown before simulation', () => {
    renderPage();
    expect(screen.getByText(/Configurez|Configure/i)).toBeInTheDocument();
  });
});
