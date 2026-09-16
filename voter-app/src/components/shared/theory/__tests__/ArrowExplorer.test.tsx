import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import ArrowExplorer from '../ArrowExplorer';
import { makeTestQueryClient } from '../../../../test/queryWrapper';

vi.mock('../../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../../../api/client')) as unknown as {
  apiClient: { POST: jest.Mock };
};

vi.mock('recharts', () => {
  return {
    LineChart: ({ children }: any) => <div>{children}</div>,
    Line: ({ dataKey }: any) => <div data-testid={`line-${dataKey}`} />,
    XAxis: () => null,
    // Real recharts computes its own tick values from the data range; the
    // mock calls the formatter directly (same pattern as
    // MajorityTyrannyPanel.test.tsx / MonteCarloConvergencePanel.test.tsx)
    // so the 0-1 -> percentage rounding actually runs.
    YAxis: ({ tickFormatter }: { tickFormatter?: (v: number) => string }) =>
      tickFormatter ? <div data-testid="rate-y-tick">{tickFormatter(0.5)}</div> : null,
    CartesianGrid: () => null,
    Tooltip: ({ formatter }: { formatter?: (v: unknown, n: unknown) => unknown }) =>
      formatter ? <div data-testid="rate-tooltip">{formatter(0.5, 'x') as string}</div> : null,
    Legend: () => null,
    ReferenceLine: () => null,
    ResponsiveContainer: ({ children }: any) => (
      <div style={{ width: 400, height: 200 }}>{children}</div>
    ),
  };
});

// ── Fixtures ──────────────────────────────────────────────────────────────────

interface MockCounterexample {
  profile?: string[][];
  without_c?: string;
  with_c?: string;
  spoiler?: string;
  cycle?: string[];
  note?: string;
}
interface MockAxiomResult {
  violated: boolean;
  counterexample: MockCounterexample | null;
}

function makeArrowData(method = 'plurality') {
  return {
    data: {
      method,
      violations: {
        iia: {
          violated: true,
          counterexample: {
            profile: [
              ['A', 'C', 'B'],
              ['A', 'C', 'B'],
              ['A', 'C', 'B'],
              ['B', 'A', 'C'],
              ['B', 'A', 'C'],
              ['C', 'B', 'A'],
              ['C', 'B', 'A'],
            ],
            without_c: 'B',
            with_c: 'A',
            spoiler: 'C',
            note: 'Test note.',
          },
        },
        pareto: { violated: false, counterexample: null },
        transitivity: { violated: false, counterexample: null },
        non_dictatorship: { violated: false, counterexample: null },
      } as Record<string, MockAxiomResult>,
      arrow_summary: 'Test summary.',
      tradeoff_type: 'majority_focus',
    },
    error: undefined,
  };
}

function makeRateData(method = 'plurality') {
  return {
    data: {
      method,
      curve: [
        { n_candidates: 2, violation_rate: 0.0 },
        { n_candidates: 3, violation_rate: 0.45 },
        { n_candidates: 4, violation_rate: 0.58 },
        { n_candidates: 5, violation_rate: 0.65 },
      ],
    },
    error: undefined,
  };
}

function renderExplorer() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ArrowExplorer />
      </QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ArrowExplorer', () => {
  it.each(['analyze-btn', 'method-select', 'axiom-filter-section'])(
    'shows %s on first render',
    (testid) => {
      renderExplorer();
      expect(screen.getByTestId(testid)).toBeInTheDocument();
    }
  );

  it('shows axiom filter checkboxes', () => {
    renderExplorer();
    expect(screen.getByTestId('axiom-check-iia')).toBeInTheDocument();
    expect(screen.getByTestId('axiom-check-pareto')).toBeInTheDocument();
    expect(screen.getByTestId('axiom-check-transitivity')).toBeInTheDocument();
    expect(screen.getByTestId('axiom-check-non_dictatorship')).toBeInTheDocument();
  });

  it('calls both API endpoints on analyze click', async () => {
    apiClient.POST.mockResolvedValueOnce(makeArrowData()).mockResolvedValueOnce(makeRateData());
    renderExplorer();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(2));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?theory\/arrow/),
      expect.any(Object)
    );
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?theory\/iia-rate/),
      expect.any(Object)
    );
    vi.runAllTimers();
  });

  it.each(['arrow-pentagon', 'counterexample-iia', 'iia-rate-chart'])(
    'shows %s after analysis',
    async (testid) => {
      apiClient.POST.mockResolvedValueOnce(makeArrowData()).mockResolvedValueOnce(makeRateData());
      renderExplorer();
      fireEvent.click(screen.getByTestId('analyze-btn'));
      await waitFor(() => expect(screen.getByTestId(testid)).toBeInTheDocument(), {
        timeout: 8000,
      });
      vi.runAllTimers();
    }
  );

  it('shows axiom comparison matrix', () => {
    renderExplorer();
    expect(screen.getByTestId('axiom-matrix')).toBeInTheDocument();
  });

  it('shows compatible-methods when axioms are checked', () => {
    renderExplorer();
    // Check one axiom
    fireEvent.click(screen.getByTestId('axiom-check-iia'));
    expect(screen.getByTestId('compatible-methods')).toBeInTheDocument();
  });

  it('lists the matching methods when at least one is compatible', () => {
    renderExplorer();
    // Every KNOWN_VIOLATIONS entry has pareto: false (unviolated), so
    // checking only this axiom must yield a non-empty compatible list --
    // unlike 'iia' alone (every entry violates it), which never does.
    fireEvent.click(screen.getByTestId('axiom-check-pareto'));
    const box = screen.getByTestId('compatible-methods');
    expect(box).toBeInTheDocument();
    expect(box.textContent).toContain('plurality');
  });

  it('shows Arrow impossibility message when all axioms checked', () => {
    renderExplorer();
    // Check all axioms
    ['iia', 'pareto', 'transitivity', 'non_dictatorship'].forEach((ax) => {
      fireEvent.click(screen.getByTestId(`axiom-check-${ax}`));
    });
    expect(screen.getByTestId('compatible-methods')).toBeInTheDocument();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderExplorer();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });

  it('falls back to a generic violated message when the backend sends no counterexample', async () => {
    const data = makeArrowData();
    data.data.violations.pareto = { violated: true, counterexample: null };
    apiClient.POST.mockResolvedValueOnce(data).mockResolvedValueOnce(makeRateData());
    renderExplorer();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => expect(screen.getByTestId('counterexample-iia')).toBeInTheDocument(), {
      timeout: 8000,
    });
    expect(screen.getByText(/violatedGeneric|violated/i)).toBeInTheDocument();
    vi.runAllTimers();
  });

  it('renders a cycle counterexample for a transitivity violation', async () => {
    const data = makeArrowData();
    data.data.violations.transitivity = {
      violated: true,
      counterexample: { cycle: ['A', 'B', 'C'], note: 'Condorcet cycle.' },
    };
    apiClient.POST.mockResolvedValueOnce(data).mockResolvedValueOnce(makeRateData());
    renderExplorer();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(
      () => expect(screen.getByTestId('counterexample-transitivity')).toBeInTheDocument(),
      { timeout: 8000 }
    );
    expect(screen.getByText('A > B > C')).toBeInTheDocument();
    vi.runAllTimers();
  });

  it('re-runs the analysis for whichever method is selected', async () => {
    apiClient.POST.mockResolvedValue(makeArrowData('schulze'));
    renderExplorer();
    fireEvent.change(screen.getByTestId('method-select'), { target: { value: 'schulze' } });
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() =>
      expect(apiClient.POST).toHaveBeenCalledWith(
        expect.stringMatching(/\/api\/(v2\/)?theory\/arrow/),
        expect.objectContaining({ body: expect.objectContaining({ method: 'schulze' }) })
      )
    );
    vi.runAllTimers();
  });

  it('feeds the IIA-rate chart axis/tooltip formatters real values', async () => {
    apiClient.POST.mockResolvedValueOnce(makeArrowData()).mockResolvedValueOnce(makeRateData());
    renderExplorer();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => expect(screen.getByTestId('iia-rate-chart')).toBeInTheDocument(), {
      timeout: 8000,
    });
    expect(screen.getByTestId('rate-y-tick')).toHaveTextContent('50%');
    expect(screen.getByTestId('rate-tooltip')).toHaveTextContent('50%');
    vi.runAllTimers();
  });
});
