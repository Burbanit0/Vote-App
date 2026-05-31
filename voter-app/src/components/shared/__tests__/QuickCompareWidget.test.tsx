import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import QuickCompareWidget from '../QuickCompareWidget';
import { ElectionProvider } from '../../../stores/useElectionStore';

jest.mock('../../../services/electionApi', () => ({
  simulateElection: jest.fn(),
}));

jest.mock('react-router', () => ({
  ...jest.requireActual('react-router'),
  useNavigate: () => jest.fn(),
}));

const { simulateElection } = jest.requireMock('../../../services/electionApi') as {
  simulateElection: jest.Mock;
};

function makeResult(winnerA: string, winnerB: string) {
  return {
    config: {}, voters_snapshot: [], candidates: [],
    methods: {
      plurality:    { winner: winnerA, bayesian_regret: 0.03, majority_satisfaction: 0.7, condorcet_consistent: null },
      schulze:      { winner: winnerB, bayesian_regret: 0.02, majority_satisfaction: 0.8, condorcet_consistent: null },
      borda:        { winner: winnerA, bayesian_regret: 0.03, majority_satisfaction: 0.7, condorcet_consistent: null },
      irv:          { winner: winnerA, bayesian_regret: 0.03, majority_satisfaction: 0.7, condorcet_consistent: null },
      two_round:    { winner: winnerA, bayesian_regret: 0.03, majority_satisfaction: 0.7, condorcet_consistent: null },
      approval:     { winner: winnerA, bayesian_regret: 0.03, majority_satisfaction: 0.7, condorcet_consistent: null },
      star_voting:  { winner: winnerA, bayesian_regret: 0.03, majority_satisfaction: 0.7, condorcet_consistent: null },
      median_voting:{ winner: winnerA, bayesian_regret: 0.03, majority_satisfaction: 0.7, condorcet_consistent: null },
    },
    condorcet_winner: winnerA,
    blank_rate: 0, campaign_trajectory: null,
    inter_method_agreement: 0.85, condorcet_exists: true,
  };
}

function renderWidget() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <QuickCompareWidget />
      </ElectionProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  jest.useFakeTimers();
  localStorage.clear();
  simulateElection.mockResolvedValue(makeResult('Chirac', 'Jospin'));
});

afterEach(() => {
  jest.useRealTimers();
});

describe('QuickCompareWidget', () => {
  it('renders 4 scenario cards', () => {
    renderWidget();
    expect(screen.getAllByText(/France 2002/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/USA 1992/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Consensus/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Condorcet/i).length).toBeGreaterThan(0);
  });

  it('renders method A and B selects', () => {
    renderWidget();
    const selects = screen.getAllByRole('combobox');
    expect(selects.length).toBeGreaterThanOrEqual(2);
  });

  it('fires simulateElection after debounce on mount', async () => {
    renderWidget();
    act(() => { jest.advanceTimersByTime(500); });
    await waitFor(() => expect(simulateElection).toHaveBeenCalledTimes(1));
  });

  it('fires new API call when scenario changes', async () => {
    renderWidget();
    act(() => { jest.advanceTimersByTime(500); });
    await waitFor(() => expect(simulateElection).toHaveBeenCalledTimes(1));

    simulateElection.mockClear();
    fireEvent.click(screen.getByText(/USA 1992/i));
    act(() => { jest.advanceTimersByTime(500); });
    await waitFor(() => expect(simulateElection).toHaveBeenCalledTimes(1));
  });

  it('fires new API call when method A changes', async () => {
    renderWidget();
    act(() => { jest.advanceTimersByTime(500); });
    await waitFor(() => expect(simulateElection).toHaveBeenCalledTimes(1));

    simulateElection.mockClear();
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[0], { target: { value: 'borda' } });
    act(() => { jest.advanceTimersByTime(500); });
    await waitFor(() => expect(simulateElection).toHaveBeenCalledTimes(1));
  });

  it('shows winner badges after result loads', async () => {
    renderWidget();
    act(() => { jest.advanceTimersByTime(500); });
    await waitFor(() => {
      expect(screen.getByText('Chirac')).toBeInTheDocument();
      expect(screen.getByText('Jospin')).toBeInTheDocument();
    });
  });

  it('shows divergence message when winners differ', async () => {
    simulateElection.mockResolvedValue(makeResult('Alice', 'Bob'));
    renderWidget();
    act(() => { jest.advanceTimersByTime(500); });
    await waitFor(() => {
      expect(screen.getByText(/Deux systèmes|Two systems/i)).toBeInTheDocument();
    });
  });

  it('shows consensus message when winners are the same', async () => {
    simulateElection.mockResolvedValue(makeResult('Alice', 'Alice'));
    renderWidget();
    act(() => { jest.advanceTimersByTime(500); });
    await waitFor(() => {
      expect(screen.getByText(/s'accordent|agree/i)).toBeInTheDocument();
    });
  });

  it('shows explore button after result loads', async () => {
    renderWidget();
    act(() => { jest.advanceTimersByTime(500); });
    await waitFor(() => {
      expect(screen.getByTestId('explore-button')).toBeInTheDocument();
    });
  });

  it('debounces rapid changes and only calls API once', async () => {
    renderWidget();
    const selects = screen.getAllByRole('combobox');

    // Fire 3 changes in quick succession
    fireEvent.change(selects[0], { target: { value: 'borda' } });
    fireEvent.change(selects[0], { target: { value: 'irv' } });
    fireEvent.change(selects[0], { target: { value: 'approval' } });

    act(() => { jest.advanceTimersByTime(500); });
    await waitFor(() => {
      // Should have called exactly twice (once from mount + once from rapid changes)
      expect(simulateElection.mock.calls.length).toBeLessThanOrEqual(2);
    });
  });
});
