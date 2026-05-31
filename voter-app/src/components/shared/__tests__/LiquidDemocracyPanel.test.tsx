import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import LiquidDemocracyPanel from '../LiquidDemocracyPanel';
import { ElectionProvider } from '../../../context/ElectionContext';
import { makeTestQueryClient } from '../../../test/queryWrapper';

jest.mock('../../../api/client', () => ({
  apiClient: { GET: jest.fn(), POST: jest.fn(), PUT: jest.fn(), DELETE: jest.fn(), PATCH: jest.fn() },
  getAccessToken: jest.fn(() => null),
}));
const { apiClient } = jest.requireMock('../../../api/client') as { apiClient: { POST: jest.Mock } };

// D3 mock — force simulation not available in JSDOM
jest.mock('d3', () => {
  const sel: any = {
    selectAll: jest.fn().mockReturnThis(),
    append:    jest.fn().mockReturnThis(),
    attr:      jest.fn().mockReturnThis(),
    style:     jest.fn().mockReturnThis(),
    data:      jest.fn().mockReturnThis(),
    join:      jest.fn().mockReturnThis(),
    remove:    jest.fn().mockReturnThis(),
    filter:    jest.fn().mockReturnThis(),
    on:        jest.fn().mockReturnThis(),
    text:      jest.fn().mockReturnThis(),
  };
  return {
    select:           jest.fn(() => sel),
    forceSimulation:  jest.fn(() => ({
      force: jest.fn().mockReturnThis(),
      on:    jest.fn((ev: string, cb: () => void) => { if (ev === 'tick') cb(); return {}; }),
      stop:  jest.fn(),
    })),
    forceLink:     jest.fn(() => ({ id: jest.fn().mockReturnThis(), distance: jest.fn().mockReturnThis(), links: jest.fn().mockReturnThis() })),
    forceManyBody: jest.fn(() => ({ strength: jest.fn().mockReturnThis() })),
    forceCenter:   jest.fn(() => ({})),
    forceCollide:  jest.fn(() => ({})),
  };
});

jest.mock('recharts', () => {
  const React = require('react');
  return {
    LineChart:           ({ children }: any) => <div data-testid="gini-line-chart">{children}</div>,
    Line:                () => null,
    XAxis:               () => null,
    YAxis:               () => null,
    CartesianGrid:       () => null,
    Tooltip:             () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 180 }}>{children}</div>,
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(winnerChanged = false) {
  return {
    data: {
      weighted_results: { Alice: 60, Bob: 25, Carol: 15 },
      direct_voters:    40,
      delegators:       60,
      super_voters: [
        { id: 5, weight: 15, x: -0.3, y: 0.1, choice: 'Alice' },
        { id: 12, weight: 8, x: 0.1, y: 0.2, choice: 'Bob' },
      ],
      delegation_graph: [
        { from: 0, to: 5 }, { from: 1, to: 5 }, { from: 2, to: 12 },
      ],
      cycles_detected:  4,
      cycle_voter_ids:  [20, 21, 22, 23],
      chain_stats:      { mean: 1.8, max: 3 },
      gini_curve: Array.from({ length: 11 }, (_, i) => ({
        probability: i / 10,
        gini:        i * 0.07,
      })),
      comparison: {
        liquid_winner:  winnerChanged ? 'Bob' : 'Alice',
        direct_winner:  'Alice',
        winner_changed: winnerChanged,
      },
      gini_voting_weight: 0.45,
      pedagogical_note:   'Test note.',
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <LiquidDemocracyPanel />
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

describe('LiquidDemocracyPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows delegation probability slider', () => {
    renderPanel();
    expect(screen.getByTestId('delegation-prob-slider')).toBeInTheDocument();
  });

  it('shows strategy selector', () => {
    renderPanel();
    expect(screen.getByTestId('strategy-select')).toBeInTheDocument();
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
      expect.stringMatching(/\/api\/(v2\/)?election\/liquid-democracy/),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('renders delegation graph SVG after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('delegation-graph-svg')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows direct and liquid winner badges', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('direct-winner-badge')).toBeInTheDocument();
      expect(screen.getByTestId('liquid-winner-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows comparison banner', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('comparison-banner')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows cycles badge when cycles detected', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('cycles-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows super-voters badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('super-voters-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows Gini badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('gini-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders Gini curve chart', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('gini-curve-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('danger border when winner changed', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const banner = screen.getByTestId('comparison-banner');
      expect(banner.className).toContain('border-danger');
    });
    jest.runAllTimers();
  });

  it('success border when winner unchanged', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const banner = screen.getByTestId('comparison-banner');
      expect(banner.className).toContain('border-success');
    });
    jest.runAllTimers();
  });

  it('debounced API call on slider change', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('delegation-prob-slider'), { target: { value: '0.8' } });
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
