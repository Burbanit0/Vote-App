import React from 'react';
import { render, screen } from '@testing-library/react';
import StrategicImpactTab from '../StrategicImpactTab';

vi.mock('../../../hooks/useChartTheme', () => ({
  useChartTheme: () => ({
    isDark: false,
    gridStroke: '#e0e0e0',
    tickFill: '#666',
    tooltipStyle: {},
    refStroke: '#ccc',
  }),
}));

vi.mock('../simulationConstants', () => ({
  METHOD_LABELS: { plurality: 'Plurality', irv: 'IRV' },
  METHOD_LINE_COLORS: { plurality: '#e15759', irv: '#59a14f' },
}));

vi.mock('../../shared/EmptyChart', () => ({ default: ({ height }: { height?: number }) => (
  <div data-testid="empty-chart" />
) }));

// Recharts ResponsiveContainer needs a width mock in JSDOM
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => (
    <div style={{ width: 800, height: 440 }}>{children}</div>
  ),
  CartesianGrid: ({ strokeDasharray }: any) => <div data-testid="cartesian-grid" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  Line: () => <div data-testid="line" />,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  ReferenceLine: () => <div data-testid="ref-line" />,
  ReferenceArea: () => <div data-testid="ref-area" />,
}));

const mockData = [
  { strategic_pct: 0, methods: { plurality: 0.02, irv: 0.01 } },
  { strategic_pct: 20, methods: { plurality: 0.08, irv: 0.03 } },
  { strategic_pct: 40, methods: { plurality: 0.15, irv: 0.05 } },
];

describe('StrategicImpactTab', () => {
  it('renders card title', () => {
    render(
      <StrategicImpactTab strategicData={mockData} allMethodNames={['plurality', 'irv']} />
    );
    expect(screen.getByText(/Impact of strategic voting on Bayesian regret/)).toBeInTheDocument();
  });

  it('renders description text', () => {
    render(
      <StrategicImpactTab strategicData={mockData} allMethodNames={['plurality']} />
    );
    expect(screen.getByText(/vulnerable to tactical voting/)).toBeInTheDocument();
  });

  it('renders EmptyChart when no data', () => {
    render(<StrategicImpactTab strategicData={[]} allMethodNames={[]} />);
    expect(screen.getByTestId('empty-chart')).toBeInTheDocument();
  });

  it('renders chart when data is present', () => {
    render(
      <StrategicImpactTab strategicData={mockData} allMethodNames={['plurality', 'irv']} />
    );
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });
});
