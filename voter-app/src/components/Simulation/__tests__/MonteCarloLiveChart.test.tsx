import React from 'react';
import { render, screen } from '@testing-library/react';
import MonteCarloLiveChart from '../MonteCarloLiveChart';

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart: ({ children }: any) => <div>{children}</div>,
  Bar: ({ children }: any) => <div>{children}</div>,
  CartesianGrid: () => <div />,
  Cell: () => <div />,
  Tooltip: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
}));

vi.mock('../../../hooks/useChartTheme', () => ({
  useChartTheme: () => ({
    isDark: false,
    gridStroke: '#e0e0e0',
    tickFill: '#333',
    tooltipStyle: {},
  }),
}));

const baseProps = {
  isRunning: false,
  progress: 0,
  iteration: 0,
  total: 0,
  condorcetRate: 0,
  partialResults: {},
  error: null,
  onStop: vi.fn(),
};

describe('MonteCarloLiveChart', () => {
  it('returns null when idle (not running, iteration 0)', () => {
    const { container } = render(<MonteCarloLiveChart {...baseProps} />);
    expect(container.innerHTML).toBe('');
  });

  it('shows spinner and stop button when running', () => {
    render(
      <MonteCarloLiveChart
        {...baseProps}
        isRunning={true}
        iteration={10}
        total={100}
        progress={10}
      />
    );
    expect(screen.getByText(/Monte Carlo running/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Stop/ })).toBeInTheDocument();
  });

  it('shows error alert when error is present', () => {
    render(
      <MonteCarloLiveChart
        {...baseProps}
        error="Something went wrong"
      />
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('shows complete badge when done', () => {
    render(
      <MonteCarloLiveChart
        {...baseProps}
        iteration={100}
        total={100}
        progress={100}
      />
    );
    expect(screen.getByText(/Complete/)).toBeInTheDocument();
  });

  it('shows condorcet rate when > 0', () => {
    render(
      <MonteCarloLiveChart
        {...baseProps}
        iteration={50}
        total={100}
        progress={100}
        condorcetRate={0.75}
      />
    );
    expect(screen.getByText(/75\.0%/)).toBeInTheDocument();
  });

  it('renders chart when partial results exist', () => {
    render(
      <MonteCarloLiveChart
        {...baseProps}
        iteration={50}
        total={100}
        progress={50}
        condorcetRate={0.8}
        isRunning={true}
        partialResults={{
          plurality: {
            winner_distribution: { Alice: 0.6, Bob: 0.4 },
            most_common_winner: 'Alice',
          },
        }}
      />
    );
    expect(screen.getByText(/Monte Carlo running/)).toBeInTheDocument();
    expect(screen.getByText(/80\.0%/)).toBeInTheDocument();
  });
});
