import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import NOTAPanel from '../NOTAPanel';
import { ElectionProvider } from '../../../stores/useElectionStore';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../../api/client')) as unknown as {
  apiClient: { POST: jest.Mock };
};

vi.mock('recharts', () => {
  const React = require('react');
  return {
    LineChart: ({ children }: any) => <div data-testid="nota-line-chart">{children}</div>,
    Line: ({ name }: any) => <div data-testid={`line-${name ?? 'unknown'}`} />,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Legend: () => null,
    ReferenceLine: () => null,
    ResponsiveContainer: ({ children }: any) => (
      <div style={{ width: 400, height: 200 }}>{children}</div>
    ),
  };
});

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeData(valid = true, notaPct = 0.15, winner: string | null = 'Alice') {
  return {
    data: {
      nota_pct: notaPct,
      election_valid: valid,
      winner,
      nota_curve: Array.from({ length: 20 }, (_, i) => ({
        threshold: i * 0.05,
        nota_pct: Math.min(1, i * 0.05),
        nota_wins: i * 0.05 >= 0.5,
        winner: i * 0.05 >= 0.5 ? null : 'Alice',
      })),
      method_comparison: {
        plurality: { winner: 'Alice', nota_pct: notaPct, election_valid: valid },
        approval: { winner: 'Alice', nota_pct: notaPct * 0.5, election_valid: true },
        borda: { winner: 'Alice', nota_pct: notaPct * 0.95, election_valid: valid },
        irv: { winner: 'Alice', nota_pct: notaPct * 0.95, election_valid: valid },
        schulze: { winner: 'Alice', nota_pct: notaPct * 0.9, election_valid: valid },
        majority_judgment: { winner: 'Alice', nota_pct: notaPct * 0.7, election_valid: valid },
      },
      pedagogical_note: 'Test note.',
      nota_rule: 'invalidate',
      nota_threshold: 0.3,
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <NOTAPanel />
        </ElectionProvider>
      </QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('NOTAPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows threshold slider', () => {
    renderPanel();
    expect(screen.getByTestId('nota-threshold-slider')).toBeInTheDocument();
  });

  it('shows rule selector', () => {
    renderPanel();
    expect(screen.getByTestId('nota-rule-select')).toBeInTheDocument();
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
      expect.stringMatching(/\/api\/(v2\/)?election\/nota/),
      expect.any(Object)
    );
    vi.runAllTimers();
  });

  it('shows NOTA percentage badge after load', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('nota-pct-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows election-valid badge when election valid', async () => {
    apiClient.POST.mockResolvedValue(makeData(true, 0.1, 'Alice'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('election-valid-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows election-invalid alert when election invalid', async () => {
    apiClient.POST.mockResolvedValue(makeData(false, 0.6, null));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('election-invalid-alert')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('does NOT show invalid alert when threshold is low (election valid)', async () => {
    // Slider at 0 / low nota_pct → no invalid badge
    apiClient.POST.mockResolvedValue(makeData(true, 0.0, 'Alice'));
    renderPanel();
    // Set slider to 0
    fireEvent.change(screen.getByTestId('nota-threshold-slider'), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('election-valid-badge')).toBeInTheDocument());
    expect(screen.queryByTestId('election-invalid-alert')).not.toBeInTheDocument();
    vi.runAllTimers();
  });

  it('shows tipping point badge when nota exceeds 50%', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('tipping-point-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('renders nota curve chart', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('nota-curve-chart')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('renders method comparison table', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('method-comparison-table')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('has a row for each tracked method', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      for (const meth of [
        'plurality',
        'approval',
        'borda',
        'irv',
        'schulze',
        'majority_judgment',
      ]) {
        expect(screen.getByTestId(`method-row-${meth}`)).toBeInTheDocument();
      }
    });
    vi.runAllTimers();
  });

  it('shows nota-elected alert when NOTA wins with winner_take_all rule', async () => {
    apiClient.POST.mockResolvedValue(makeData(true, 0.6, 'NOTA'));
    renderPanel();
    fireEvent.change(screen.getByTestId('nota-rule-select'), {
      target: { value: 'winner_take_all' },
    });
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('nota-elected-alert')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('debounced re-simulation on slider change', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('nota-threshold-slider'), { target: { value: '0.7' } });
    act(() => {
      vi.advanceTimersByTime(450);
    });
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(2));
    vi.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
