import React from 'react';
import { render, screen } from '@testing-library/react';
import MonteCarloConvergencePanel from '../MonteCarloConvergencePanel';

// MonteCarloResults.test.tsx (the only existing caller-side test) stubs this
// component out entirely (`vi.mock('../MonteCarloConvergencePanel', () =>
// ({ default: () => null }))`), so its own render logic — including the
// regret/CI-stability axis tick formatting — had never actually run under
// any test before this file.
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  ComposedChart: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="regret-chart">{children}</div>
  ),
  AreaChart: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="agreement-chart">{children}</div>
  ),
  BarChart: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="ci-chart">{children}</div>
  ),
  Area: () => null,
  Bar: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  Line: () => null,
  Cell: () => null,
  Legend: () => null,
  ReferenceLine: () => null,
  Tooltip: () => null,
  CartesianGrid: () => null,
  // Real recharts computes its own tick values from the data range; the mock
  // calls the formatter directly so the 3-decimal regret/CI formatting
  // (never covered otherwise, since XAxis/YAxis are stubbed away) runs for real.
  XAxis: ({ tickFormatter }: { tickFormatter?: (value: number) => string }) =>
    tickFormatter ? <div data-testid="ci-x-tick">{tickFormatter(0.0214)}</div> : null,
  YAxis: ({ tickFormatter }: { tickFormatter?: (value: number) => string }) =>
    tickFormatter ? <div data-testid="regret-y-tick">{tickFormatter(0.05123)}</div> : null,
}));

const BASE_PROPS = {
  regretHistory: { plurality: [0.12, 0.08, 0.05], schulze: [0.05, 0.03, 0.01] },
  agreementHistory: [0.6, 0.75, 0.9],
  ciHalfLatest: { plurality: 0.021, schulze: 0.004 },
  iterationCheckpoints: [10, 30, 60],
  iteration: 60,
  isRunning: false,
};

describe('MonteCarloConvergencePanel', () => {
  it('renders nothing when there are no iteration checkpoints yet', () => {
    const { container } = render(
      <MonteCarloConvergencePanel {...BASE_PROPS} iterationCheckpoints={[]} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders the regret convergence chart with y-axis ticks fixed to 3 decimals', () => {
    render(<MonteCarloConvergencePanel {...BASE_PROPS} />);
    expect(screen.getByTestId('regret-chart')).toBeInTheDocument();
    // numericTickFormatter(v => v.toFixed(3)) applied to a raw axis value.
    expect(screen.getByTestId('regret-y-tick')).toHaveTextContent('0.051');
  });

  it('does not render the CI-stability chart before iteration 50', () => {
    render(<MonteCarloConvergencePanel {...BASE_PROPS} iteration={20} />);
    expect(screen.queryByTestId('ci-chart')).not.toBeInTheDocument();
  });

  it('renders the CI-stability chart with x-axis ticks fixed to 3 decimals once iteration >= 50', () => {
    render(<MonteCarloConvergencePanel {...BASE_PROPS} />);
    expect(screen.getByTestId('ci-chart')).toBeInTheDocument();
    expect(screen.getByTestId('ci-x-tick')).toHaveTextContent('0.021');
  });
});
