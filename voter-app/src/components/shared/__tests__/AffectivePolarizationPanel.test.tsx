import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import AffectivePolarizationPanel from '../AffectivePolarizationPanel';
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
    LineChart: ({ children }: any) => <div data-testid="affect-line-chart">{children}</div>,
    Line: ({ name }: any) => <div data-testid={`line-${name ?? 'unknown'}`} />,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Legend: () => null,
    ReferenceLine: () => null,
    ResponsiveContainer: ({ children }: any) => (
      <div style={{ width: 400, height: 220 }}>{children}</div>
    ),
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(winnerChanged = false) {
  const sincere = { plurality: 'Carol', borda: 'Carol', schulze: 'Carol' };
  const affective = winnerChanged
    ? { plurality: 'Alice', borda: 'Carol', schulze: 'Bob' }
    : { ...sincere };

  return {
    data: {
      sincere_results: sincere,
      affective_results: affective,
      winner_changed: winnerChanged,
      condorcet_violation: winnerChanged,
      sincere_cw: 'Carol',
      affective_cw: winnerChanged ? null : 'Carol',
      method_sensitivity: { plurality: winnerChanged ? 0.6 : 0.0, borda: 0.1, schulze: 0.3 },
      affect_curve: Array.from({ length: 11 }, (_, i) => ({
        hostility: i / 10,
        condorcet_rate: 1 - i * 0.05,
        agreement_rate: 1 - i * 0.08,
      })),
      candidate_camps: { Alice: 'left', Bob: 'right', Carol: 'centre' },
      voters: [
        { id: 0, x: -0.5, y: 0.1, camp: 'left', sincere_pref: 'Alice', affective_pref: 'Alice' },
        { id: 1, x: 0.5, y: -0.1, camp: 'right', sincere_pref: 'Bob', affective_pref: 'Bob' },
        { id: 2, x: 0.0, y: 0.1, camp: 'centre', sincere_pref: 'Carol', affective_pref: 'Alice' },
      ],
      candidates: [
        { name: 'Alice', x: -0.6 },
        { name: 'Bob', x: 0.6 },
        { name: 'Carol', x: 0.0 },
      ],
      pedagogical_note: 'Test note.',
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <AffectivePolarizationPanel />
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

describe('AffectivePolarizationPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows hostility slider', () => {
    renderPanel();
    expect(screen.getByTestId('hostility-slider')).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls API on simulate click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/affective-polarization/),
      expect.any(Object)
    );
    vi.runAllTimers();
  });

  it('renders ideology map SVG after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('affect-map-svg')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows winner-changed badge when winner changed', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const badge = screen.getByTestId('winner-changed-badge');
      expect(badge.className).toContain('bg-[#dc3545]');
    });
    vi.runAllTimers();
  });

  it('shows green badge when winner unchanged', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const badge = screen.getByTestId('winner-changed-badge');
      expect(badge.className).toContain('bg-[#198754]');
    });
    vi.runAllTimers();
  });

  it('shows condorcet violation badge', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('condorcet-violation-badge')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('renders affect curve chart', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('affect-curve-chart')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows changed-voter dots on the map', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const changed = container.querySelectorAll('[data-testid="changed-voter"]');
      expect(changed.length).toBeGreaterThan(0);
    });
    vi.runAllTimers();
  });

  it('slider triggers debounced API call', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('hostility-slider'), { target: { value: '0.8' } });
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
