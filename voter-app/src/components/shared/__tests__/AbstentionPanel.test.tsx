import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import AbstentionPanel from '../AbstentionPanel';
import { ElectionProvider } from '../../../stores/useElectionStore';
import { makeTestQueryClient } from '../../../test/queryWrapper';

// Mock the typed openapi-fetch client; real react-query drives the state
// transitions. $api (openapi-react-query) calls apiClient.POST(path, { body }).
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
    LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
    Line: ({ name }: any) => <div data-testid={`line-${name ?? 'unknown'}`} />,
    XAxis: () => null,
    YAxis: () => null,
    Tooltip: () => null,
    Legend: () => null,
    ReferenceLine: () => null,
    ResponsiveContainer: ({ children }: any) => (
      <div style={{ width: 400, height: 200 }}>{children}</div>
    ),
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeRound(rnd: number, turnout: number, hasAbstained = false) {
  const abstentionMap = [
    {
      id: 0,
      x: -0.3,
      y: 0.1,
      preferred: 'Alice',
      abstained: hasAbstained && rnd > 0,
      prob_abstention: hasAbstained ? 0.35 : 0,
    },
    { id: 1, x: 0.4, y: -0.1, preferred: 'Bob', abstained: false, prob_abstention: 0.05 },
    { id: 2, x: 0.0, y: 0.3, preferred: 'Carol', abstained: false, prob_abstention: 0.1 },
  ];
  return {
    round: rnd,
    turnout,
    vote_shares: { Alice: 0.45, Bob: 0.35, Carol: 0.2 },
    winner_fptp: 'Alice',
    winner_condorcet: 'Alice',
    abstention_map: abstentionMap,
  };
}

function makeData(winnerChanged = false) {
  return {
    rounds: [
      makeRound(0, 1.0, false),
      makeRound(1, 0.85, true),
      makeRound(2, 0.72, true),
      makeRound(3, 0.65, true),
    ],
    sincere_winner: 'Alice',
    final_winner: winnerChanged ? 'Bob' : 'Alice',
    winner_changed: winnerChanged,
    turnout_by_camp: { Alice: 0.65, Bob: 0.9, Carol: 0.8 },
    candidates: [{ name: 'Alice' }, { name: 'Bob' }, { name: 'Carol' }],
  };
}

/** openapi-fetch resolves to { data, error }. */
const ok = (d: unknown) => ({ data: d, error: undefined });

function renderPanel() {
  return render(
    <QueryClientProvider client={makeTestQueryClient()}>
      <MemoryRouter>
        <ElectionProvider>
          <AbstentionPanel />
        </ElectionProvider>
      </MemoryRouter>
    </QueryClientProvider>
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

describe('AbstentionPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('shows demob and influence sliders', () => {
    renderPanel();
    expect(screen.getByTestId('demob-slider')).toBeInTheDocument();
    expect(screen.getByTestId('influence-slider')).toBeInTheDocument();
  });

  it('calls the API on button click', async () => {
    apiClient.POST.mockResolvedValue(ok(makeData()));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      '/api/v2/election/abstention',
      expect.objectContaining({ body: expect.any(Object) })
    );
  });

  it('renders ideology map SVG after data loads', async () => {
    apiClient.POST.mockResolvedValue(ok(makeData()));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('abstention-map-svg')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('renders abstained voters as grey dots', async () => {
    apiClient.POST.mockResolvedValue(ok(makeData()));
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('abstention-map-svg')).toBeInTheDocument());
    fireEvent.change(screen.getByTestId('round-slider'), { target: { value: '1' } });
    act(() => {
      vi.runAllTimers();
    });
    const abstainedDots = container.querySelectorAll('[data-testid="abstained-voter"]');
    expect(abstainedDots.length).toBeGreaterThan(0);
    vi.runAllTimers();
  });

  it('shows green comparison band when winner unchanged', async () => {
    apiClient.POST.mockResolvedValue(ok(makeData(false)));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const band = screen.getByTestId('winner-comparison-band');
      expect(band).toBeInTheDocument();
      expect(band.style.background).toMatch(/f0fff4|rgb\(240,\s*255,\s*244\)/);
    });
    vi.runAllTimers();
  });

  it('shows red comparison band when winner changed', async () => {
    apiClient.POST.mockResolvedValue(ok(makeData(true)));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const band = screen.getByTestId('winner-comparison-band');
      expect(band.style.background).toMatch(/fff3f3|rgb\(255,\s*243,\s*243\)/);
    });
    vi.runAllTimers();
  });

  it('renders turnout line chart', async () => {
    apiClient.POST.mockResolvedValue(ok(makeData()));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('turnout-chart')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows camp turnout badges', async () => {
    apiClient.POST.mockResolvedValue(ok(makeData()));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('camp-turnout-Alice')).toBeInTheDocument();
      expect(screen.getByTestId('camp-turnout-Bob')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('shows play/pause button', async () => {
    apiClient.POST.mockResolvedValue(ok(makeData()));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('play-button')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
