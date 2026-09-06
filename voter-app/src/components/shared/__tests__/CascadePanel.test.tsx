import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import CascadePanel from '../CascadePanel';
import { ElectionProvider } from '../../../stores/useElectionStore';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
}));
const { apiClient } = (await import('../../../api/client')) as unknown as {
  apiClient: { POST: jest.Mock };
};

vi.mock('recharts', () => {
  const React = require('react');
  return {
    LineChart: ({ children }: any) => <div data-testid="cascade-line-chart">{children}</div>,
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

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeSequence(n: number, cascadeAt: number | null) {
  return Array.from({ length: n }, (_, i) => {
    const sincere = i % 2 === 0 ? 'Alice' : 'Bob';
    const cascading = cascadeAt != null && i >= cascadeAt;
    const actual = cascading ? 'Carol' : sincere;
    return {
      voter_id: i,
      sincere_choice: sincere,
      actual_vote: actual,
      followed_cascade: cascading && actual !== sincere,
    };
  });
}

function makeData(cascadeOccurred = false) {
  const seq = makeSequence(30, cascadeOccurred ? 10 : null);
  return {
    data: {
      sincere_winner: 'Alice',
      cascade_winner: cascadeOccurred ? 'Carol' : 'Alice',
      cascade_occurred: cascadeOccurred,
      vote_sequence: seq,
      cascade_start_at: cascadeOccurred ? 10 : null,
      cascade_strength_curve: Array.from({ length: 11 }, (_, i) => ({
        strength: i / 10,
        winner: i > 5 ? 'Carol' : 'Alice',
        cascade_rate: i * 0.08,
      })),
      comparison_runs: [
        { strength: 0.0, winner: 'Alice', cascade_rate: 0.0 },
        { strength: 0.5, winner: 'Alice', cascade_rate: 0.2 },
        { strength: 1.0, winner: 'Carol', cascade_rate: 0.7 },
      ],
      candidates: ['Alice', 'Bob', 'Carol'],
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <CascadePanel />
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

describe('CascadePanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows cascade strength slider', () => {
    renderPanel();
    expect(screen.getByTestId('cascade-strength-slider')).toBeInTheDocument();
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
      expect.stringMatching(/\/api\/(v2\/)?election\/cascade/),
      expect.any(Object)
    );
    vi.runAllTimers();
  });

  it('renders timeline SVG after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('cascade-timeline-svg')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows cascade-occurred badge when cascade changed winner', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('cascade-occurred-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows cascade winner badge red when cascade occurred', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const badge = screen.getByTestId('cascade-winner-badge');
      expect(badge.className).toContain('bg-[#dc3545]');
    });
    vi.runAllTimers();
  });

  it('shows cascade winner badge green when no cascade', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const badge = screen.getByTestId('cascade-winner-badge');
      expect(badge.className).toContain('bg-[#198754]');
    });
    vi.runAllTimers();
  });

  it('shows cascade start badge when cascade_start_at is set', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('cascade-start-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('renders comparison badges for 0, 0.5, 1.0', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('comparison-badges')).toBeInTheDocument());
    await waitFor(() => {
      expect(screen.getByTestId('comparison-badge-0.0')).toBeInTheDocument();
      expect(screen.getByTestId('comparison-badge-0.5')).toBeInTheDocument();
      expect(screen.getByTestId('comparison-badge-1.0')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('renders strength curve chart', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('cascade-curve-chart')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows cascade start line on SVG when cascade occurred', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const line = container.querySelector('[data-testid="cascade-start-line"]');
      expect(line).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('shows follower rings for cascade-following voters', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const rings = container.querySelectorAll('[data-testid="cascade-follower-ring"]');
      expect(rings.length).toBeGreaterThan(0);
    });
    vi.runAllTimers();
  });

  it('shows play button after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('play-button')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('slider triggers debounced API call', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('cascade-strength-slider'), { target: { value: '0.8' } });
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
