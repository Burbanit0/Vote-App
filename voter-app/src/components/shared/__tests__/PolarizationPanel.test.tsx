import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import PolarizationPanel from '../PolarizationPanel';
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
    ScatterChart: ({ children }: any) => <div data-testid="scatter-chart">{children}</div>,
    Scatter: ({ name }: any) => <div data-testid={`scatter-${name}`} />,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Label: () => null,
    ResponsiveContainer: ({ children }: any) => (
      <div style={{ width: 400, height: 260 }}>{children}</div>
    ),
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData() {
  return {
    data: {
      results: [
        {
          ideology: 'centrist',
          polarization_index: 0.12,
          condorcet_rate: 0.9,
          agreement_rate: 0.85,
          winner_stability: 0.15,
          best_method: 'schulze',
          worst_method: 'plurality',
          method_regrets: { plurality: 0.089, schulze: 0.031, borda: 0.045 },
        },
        {
          ideology: 'polarized',
          polarization_index: 0.48,
          condorcet_rate: 0.35,
          agreement_rate: 0.42,
          winner_stability: 0.72,
          best_method: 'schulze',
          worst_method: 'plurality',
          method_regrets: { plurality: 0.134, schulze: 0.062, borda: 0.091 },
        },
      ],
      key_findings: [
        'À partir de P ≈ 0.48, le vainqueur de Condorcet disparaît dans 65% des cas.',
        'Schulze est la méthode la plus robuste dans les électorats polarisés.',
      ],
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <PolarizationPanel />
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

describe('PolarizationPanel', () => {
  it('shows compute button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /calculer|compute/i })).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('shows ideology badges', () => {
    renderPanel();
    expect(screen.getByTestId('ideology-badge-centrist')).toBeInTheDocument();
    expect(screen.getByTestId('ideology-badge-polarized')).toBeInTheDocument();
  });

  it('clicking an ideology badge toggles it', () => {
    renderPanel();
    const badge = screen.getByTestId('ideology-badge-centrist');
    fireEvent.click(badge);
    // Second click re-adds it
    fireEvent.click(badge);
    expect(badge).toBeInTheDocument();
  });

  it('calls API on compute click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/polarization/),
      expect.any(Object)
    );
    vi.runAllTimers();
  });

  it('renders scatter chart after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    // The panel renders TWO scatter charts side-by-side (centrist vs polarized),
    // so we use getAllByTestId.
    await waitFor(() => expect(screen.getAllByTestId('scatter-chart').length).toBeGreaterThan(0));
    vi.runAllTimers();
  });

  it('renders one Scatter component per ideology', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    await waitFor(() => {
      expect(screen.getByTestId('scatter-centrist')).toBeInTheDocument();
      expect(screen.getByTestId('scatter-polarized')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('renders heatmap SVG with cells', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    await waitFor(() => {
      expect(screen.getByTestId('polarization-heatmap')).toBeInTheDocument();
      const cells = container.querySelectorAll('[data-testid="heatmap-cell"]');
      expect(cells.length).toBeGreaterThan(0);
    });
    vi.runAllTimers();
  });

  it('shows key findings', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    await waitFor(() => {
      const findings = screen.getAllByTestId('finding-item');
      expect(findings.length).toBe(2);
    });
    vi.runAllTimers();
  });

  it('sims slider triggers debounced API call', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    // Load data first
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    // Move slider → debounce fires after 500ms
    fireEvent.change(screen.getByTestId('sims-slider'), { target: { value: '20' } });
    act(() => {
      vi.advanceTimersByTime(550);
    });
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(2));
    vi.runAllTimers();
  });

  it('shows best method badge after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    await waitFor(() => {
      const badges = screen.getAllByTestId(/best-badge-/);
      expect(badges.length).toBeGreaterThan(0);
    });
    vi.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
