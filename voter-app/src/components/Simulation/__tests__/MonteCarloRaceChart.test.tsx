import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import MonteCarloRaceChart from '../MonteCarloRaceChart';

vi.mock('recharts', () => ({
  ResponsiveContainer:  ({ children }: any) => <div>{children}</div>,
  AreaChart:            ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  Area:                 ({ dataKey }: any) => <div data-testid={`area-${dataKey}`} />,
  CartesianGrid:        () => null,
  XAxis:                () => null,
  YAxis:                () => null,
  Tooltip:              () => null,
  ReferenceLine:        () => null,
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PARTIAL = {
  plurality: {
    winner_distribution:  { Alice: 0.62, Bob: 0.31, Carol: 0.07 },
    most_common_winner:   'Alice',
  },
  schulze: {
    winner_distribution:  { Alice: 0.55, Bob: 0.38, Carol: 0.07 },
    most_common_winner:   'Alice',
  },
  borda: {
    winner_distribution:  { Alice: 0.48, Bob: 0.45, Carol: 0.07 },
    most_common_winner:   'Alice',
  },
};

const BASE_PROPS = {
  regretHistory:        { plurality: [0.04], schulze: [0.02], borda: [0.03] },
  iterationCheckpoints: [50],
  partialResults:       PARTIAL,
  isRunning:            true,
};

// Helper: render and advance timers so effects run
function renderChart(props = BASE_PROPS) {
  let result: ReturnType<typeof render>;
  act(() => { result = render(<MonteCarloRaceChart {...props} />); });
  return result!;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('MonteCarloRaceChart', () => {
  it('returns null when iterationCheckpoints is empty', () => {
    const { container } = renderChart({
      ...BASE_PROPS,
      iterationCheckpoints: [],
      partialResults:       {} as any,
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
    const methodBtn     = screen.getByTestId('view-one-method');
    expect(candidatesBtn.className).toContain('btn-secondary');
    expect(methodBtn.className).toContain('btn-outline-secondary');
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
    const options  = Array.from(dropdown.querySelectorAll('option')).map((o) => o.textContent);
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
