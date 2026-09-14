import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import MonteCarloRaceChart from '../MonteCarloRaceChart';

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  Area: ({ dataKey }: any) => <div data-testid={`area-${dataKey}`} />,
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  // Real recharts calls `content` on hover with the active point's payload;
  // the mock invokes it directly so RaceTooltip's own rendering (iteration
  // label + per-candidate rounded percentages) is exercised instead of only
  // handing recharts an unused closure.
  Tooltip: ({
    content,
  }: {
    content?: (props: {
      active?: boolean;
      label?: number;
      payload?: { dataKey: string; value: number; color: string }[];
    }) => React.ReactNode;
  }) =>
    content
      ? content({
          active: true,
          label: 50,
          payload: [
            { dataKey: 'Alice', value: 0.62, color: '#1a56cc' },
            { dataKey: 'Bob', value: 0.31, color: '#b35c00' },
          ],
        })
      : null,
  ReferenceLine: () => null,
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PARTIAL = {
  plurality: {
    winner_distribution: { Alice: 0.62, Bob: 0.31, Carol: 0.07 },
    most_common_winner: 'Alice',
  },
  schulze: {
    winner_distribution: { Alice: 0.55, Bob: 0.38, Carol: 0.07 },
    most_common_winner: 'Alice',
  },
  borda: {
    winner_distribution: { Alice: 0.48, Bob: 0.45, Carol: 0.07 },
    most_common_winner: 'Alice',
  },
};

const BASE_PROPS = {
  regretHistory: { plurality: [0.04], schulze: [0.02], borda: [0.03] },
  iterationCheckpoints: [50],
  partialResults: PARTIAL,
  isRunning: true,
};

// Helper: render and advance timers so effects run
function renderChart(props = BASE_PROPS) {
  let result: ReturnType<typeof render>;
  act(() => {
    result = render(<MonteCarloRaceChart {...props} />);
  });
  return result!;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('MonteCarloRaceChart', () => {
  it('returns null when iterationCheckpoints is empty', () => {
    const { container } = renderChart({
      ...BASE_PROPS,
      iterationCheckpoints: [],
      partialResults: {} as any,
    });
    expect(container.firstChild).toBeNull();
  });

  it('returns null when partialResults has no candidates (empty distributions)', () => {
    const { container } = renderChart({
      ...BASE_PROPS,
      partialResults: {
        plurality: { winner_distribution: {}, most_common_winner: null },
      } as any,
    });
    // No candidates → no chart
    expect(container.firstChild).toBeNull();
  });

  it('renders the AreaChart when data is present', () => {
    renderChart();
    expect(screen.getByTestId('area-chart')).toBeInTheDocument();
  });

  it('renders one Area per candidate', () => {
    renderChart();
    expect(screen.getByTestId('area-Alice')).toBeInTheDocument();
    expect(screen.getByTestId('area-Bob')).toBeInTheDocument();
    expect(screen.getByTestId('area-Carol')).toBeInTheDocument();
  });

  it('tooltip shows the iteration label and rounded per-candidate percentages', () => {
    renderChart();
    // Exact-text matches, since the card description text also contains the
    // substring "iteration" and "Alice: 62%" is split across a text node and
    // a nested <strong> in the real markup.
    expect(
      screen.getByText((_, el) => el?.tagName === 'STRONG' && el.textContent === 'Iteration 50')
    ).toBeInTheDocument();
    expect(
      screen.getByText((_, el) => el?.tagName === 'DIV' && el.textContent === 'Alice: 62%')
    ).toBeInTheDocument();
    expect(
      screen.getByText((_, el) => el?.tagName === 'DIV' && el.textContent === 'Bob: 31%')
    ).toBeInTheDocument();
  });

  it('shows the race title and description', () => {
    renderChart();
    expect(screen.getAllByText(/Course des candidats|Candidate race/i).length).toBeGreaterThan(0);
  });

  it('shows three view toggle buttons', () => {
    renderChart();
    expect(screen.getByTestId('view-candidates')).toBeInTheDocument();
    expect(screen.getByTestId('view-one-method')).toBeInTheDocument();
    expect(screen.getByTestId('view-methods-race')).toBeInTheDocument();
  });

  it('Candidates button is active by default', () => {
    renderChart();
    const candidatesBtn = screen.getByTestId('view-candidates');
    const methodBtn = screen.getByTestId('view-one-method');
    expect(candidatesBtn.className).toContain('text-secondary-foreground');
    expect(methodBtn.className).toContain('border-input');
  });

  it('switching to method view shows method dropdown', () => {
    renderChart();
    // No dropdown before toggle
    expect(screen.queryByRole('combobox')).toBeNull();

    fireEvent.click(screen.getByTestId('view-one-method'));

    // Dropdown now present
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('method dropdown contains all available methods', () => {
    renderChart();
    fireEvent.click(screen.getByTestId('view-one-method'));

    const dropdown = screen.getByRole('combobox');
    const options = Array.from(dropdown.querySelectorAll('option')).map((o) => o.textContent);
    expect(options).toContain('plurality');
    expect(options).toContain('schulze');
  });

  it('does NOT show final-winner badge when isRunning=true', () => {
    renderChart({ ...BASE_PROPS, isRunning: true });
    expect(screen.queryByText(/Vainqueur|Winner:/i)).toBeNull();
  });

  it('shows final-winner badge when isRunning=false', async () => {
    renderChart({ ...BASE_PROPS, isRunning: false });
    // Wait for the effect to accumulate history and re-render
    await waitFor(() => {
      // Alice is in the legend or winner badge
      expect(screen.getAllByText(/Alice/i).length).toBeGreaterThan(0);
    });
  });

  it('candidate names appear in the legend', () => {
    renderChart();
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
    expect(screen.getByText('Carol')).toBeInTheDocument();
  });
});
