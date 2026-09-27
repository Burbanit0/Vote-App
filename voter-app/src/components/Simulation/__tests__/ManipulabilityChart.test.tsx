import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ManipulabilityChart from '../ManipulabilityChart';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
}));
const { apiClient } = (await import('../../../api/client')) as unknown as {
  apiClient: { GET: jest.Mock };
};

interface MockManipResult {
  method: string;
  manipulability_rate: number | null;
  average_gain: number;
  num_manipulators: number;
  num_sampled: number;
}

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  CartesianGrid: () => null,
  Cell: () => null,
  LabelList: () => null,
  ReferenceLine: () => null,
  // Real recharts computes its own tick values; the mock calls the
  // formatter directly so the `%`-suffix formatting is exercised.
  XAxis: ({ tickFormatter }: { tickFormatter?: (value: number) => string }) =>
    tickFormatter ? <div data-testid="manip-x-tick">{tickFormatter(37)}</div> : null,
  YAxis: () => null,
  // Real recharts calls `content` on hover with the active point's payload;
  // the mock invokes it directly (content here is the ManipTooltip
  // component reference itself) so its rate-based color/label thresholds
  // are exercised instead of only handing recharts an unused reference.
  Tooltip: ({
    content: Content,
  }: {
    content?: React.ComponentType<{ active?: boolean; payload?: { payload: MockManipResult }[] }>;
  }) =>
    Content ? (
      <Content
        active
        payload={[
          {
            payload: {
              method: 'borda',
              manipulability_rate: 12.3,
              average_gain: 0.8,
              num_manipulators: 24,
              num_sampled: 200,
            },
          },
        ]}
      />
    ) : null,
}));

function makeResult(rate: number) {
  return {
    method: 'plurality',
    manipulability_rate: rate,
    average_gain: 0.5,
    num_manipulators: Math.round((rate / 100) * 200),
    num_sampled: 200,
  };
}

const BASE_PARAMS = {
  num_candidates: 4,
  num_voters: 150,
  ideology_distribution: 'normal',
};

function renderChart() {
  return render(<ManipulabilityChart baseParams={BASE_PARAMS} />);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('ManipulabilityChart', () => {
  it('renders the analyze button before any run', () => {
    renderChart();
    expect(screen.getByRole('button', { name: /Analyser la manipulabilité/i })).toBeInTheDocument();
  });

  it('runs the analysis and renders the chart with formatted axis ticks', async () => {
    apiClient.GET.mockResolvedValue({
      data: { results: [makeResult(3), makeResult(45)] },
      error: undefined,
    });
    renderChart();
    fireEvent.click(screen.getByRole('button', { name: /Analyser la manipulabilité/i }));
    await waitFor(() => expect(screen.getByTestId('bar-chart')).toBeInTheDocument());
    // numericTickFormatter(v => `${v} %`) applied to a raw axis value of 37.
    expect(screen.getByTestId('manip-x-tick')).toHaveTextContent('37 %');
  });

  it('surfaces a failed analysis', async () => {
    // The API error path: the component shows the thrown Error's own message
    // (it used to route through a util that first looked for an axios-shaped
    // `response.data.error`, a shape nothing in this app throws).
    apiClient.GET.mockResolvedValue({ data: undefined, error: { detail: 'boom' } });
    renderChart();
    fireEvent.click(screen.getByRole('button', { name: /Analyser la manipulabilité/i }));
    await waitFor(() => expect(screen.getByText("Erreur lors de l'analyse")).toBeInTheDocument());
  });

  it('tooltip colour-codes the manipulability rate and renders its label and counts', async () => {
    apiClient.GET.mockResolvedValue({
      data: { results: [makeResult(3), makeResult(45)] },
      error: undefined,
    });
    renderChart();
    fireEvent.click(screen.getByRole('button', { name: /Analyser la manipulabilité/i }));
    await waitFor(() => expect(screen.getByTestId('bar-chart')).toBeInTheDocument());
    // The mocked Tooltip always feeds the ManipTooltip component a fixed
    // 12.3% / "borda" payload — real ManipTooltip logic classifies that as
    // "Modérée" (5% ≤ rate < 20%) and renders the sampled/manipulator counts.
    expect(screen.getByText(/12\.3 % — Modérée/)).toBeInTheDocument();
    expect(screen.getByText(/24 \/ 200 électeurs testés/)).toBeInTheDocument();
  });

  it('excludes methods with a null manipulability_rate from the chart', async () => {
    apiClient.GET.mockResolvedValue({
      data: {
        results: [
          makeResult(10),
          {
            method: 'schulze',
            manipulability_rate: null,
            average_gain: 0,
            num_manipulators: 0,
            num_sampled: 200,
          },
        ],
      },
      error: undefined,
    });
    renderChart();
    fireEvent.click(screen.getByRole('button', { name: /Analyser la manipulabilité/i }));
    await waitFor(() => expect(screen.getByTestId('bar-chart')).toBeInTheDocument());
    expect(screen.getByText(/1 méthode/)).toBeInTheDocument();
  });
});
