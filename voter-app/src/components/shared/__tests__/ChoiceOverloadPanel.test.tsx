import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import ChoiceOverloadPanel from '../ChoiceOverloadPanel';
import { ElectionProvider } from '../../../context/ElectionContext';
import { makeTestQueryClient } from '../../../test/queryWrapper';

jest.mock('../../../api/client', () => ({
  apiClient: { GET: jest.fn(), POST: jest.fn(), PUT: jest.fn(), DELETE: jest.fn(), PATCH: jest.fn() },
  getAccessToken: jest.fn(() => null),
}));
const { apiClient } = jest.requireMock('../../../api/client') as { apiClient: { POST: jest.Mock } };

jest.mock('recharts', () => {
  const React = require('react');
  return {
    LineChart:           ({ children }: any) => <div>{children}</div>,
    BarChart:            ({ children }: any) => <div>{children}</div>,
    Line:                ({ dataKey }: any) => <div data-testid={`line-${dataKey}`} />,
    Bar:                 ({ dataKey }: any) => <div data-testid={`bar-${dataKey}`} />,
    Cell:                () => null,
    XAxis:               () => null,
    YAxis:               () => null,
    CartesianGrid:       () => null,
    Tooltip:             () => null,
    Legend:              () => null,
    ReferenceLine:       () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 220 }}>{children}</div>,
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

const COUNTS = [2, 3, 5, 7, 10];
const METHODS = ['plurality', 'approval', 'borda', 'majority_judgment'];

function makeData() {
  return {
    data: {
      results_by_n: COUNTS.map((n, i) => ({
        num_candidates:         n,
        mean_voter_regret:      n <= 5 ? 0 : 0.01 + i * 0.01,
        heuristic_voters:       n <= 5 ? 0 : 0.4,
        winner_by_method:       Object.fromEntries(METHODS.map((m) => [m, 'Alice'])),
        condorcet_winner:       'Alice',
        methods_elect_condorcet: Object.fromEntries(METHODS.map((m) => [m, true])),
      })),
      regret_curve: COUNTS.map((n, i) => ({ n_candidates: n, regret: n <= 5 ? 0 : 0.01 * i })),
      most_robust_method:   'majority_judgment',
      least_robust_method:  'plurality',
      overload_threshold:   5,
      heuristic_weights:    { notoriety: 0.2, primacy: 0.1, partisan: 0.2 },
      pedagogical_note:     'Test note.',
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <ChoiceOverloadPanel />
        </ElectionProvider>
      </QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  jest.useFakeTimers();
});

afterEach(() => { jest.useRealTimers(); });

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ChoiceOverloadPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows all four sliders', () => {
    renderPanel();
    expect(screen.getByTestId('threshold-slider')).toBeInTheDocument();
    expect(screen.getByTestId('notoriety-slider')).toBeInTheDocument();
    expect(screen.getByTestId('primacy-slider')).toBeInTheDocument();
    expect(screen.getByTestId('partisan-slider')).toBeInTheDocument();
  });

  it('shows prompt before first run', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls API on simulate click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/choice-overload/),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('renders line chart after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('overload-line-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders heuristic bar chart', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('heuristic-bar-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders method table', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('method-table')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows most-robust badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('most-robust-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows least-robust badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('least-robust-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('debounced re-simulation on notoriety slider change', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('notoriety-slider'), { target: { value: '0.35' } });
    act(() => { jest.advanceTimersByTime(450); });
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(2));
    jest.runAllTimers();
  });

  it('debounced re-simulation on threshold slider change', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('threshold-slider'), { target: { value: '7' } });
    act(() => { jest.advanceTimersByTime(450); });
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(2));
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
