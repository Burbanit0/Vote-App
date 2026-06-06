import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import MajorityTyrannyPanel from '../MajorityTyrannyPanel';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../../api/client')) as unknown as {
  apiClient: { POST: jest.Mock };
};

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key.split('.').pop() ?? key,
  }),
}));

vi.mock('recharts', () => {
  const React = require('react');
  const stub = ({ children }: { children?: React.ReactNode }) =>
    React.createElement('div', { 'data-testid': 'recharts-stub' }, children);
  return {
    RadarChart: stub,
    Radar: stub,
    PolarGrid: stub,
    PolarAngleAxis: stub,
    LineChart: stub,
    Line: stub,
    XAxis: stub,
    YAxis: stub,
    CartesianGrid: stub,
    Tooltip: stub,
    Legend: stub,
    ResponsiveContainer: ({ children }: { children?: React.ReactNode }) =>
      React.createElement('div', null, children),
  };
});

const MOCK_DATA = {
  results: {
    simple_majority: {
      minority_win_rate: 0.0,
      minority_satisfaction: 0.0,
      majority_satisfaction: 1.0,
      total_welfare: 0.6,
      efficiency_loss: 0.5,
      tyranny_index: 1.0,
    },
    supermajority_2_3: {
      minority_win_rate: 1.0,
      minority_satisfaction: 1.0,
      majority_satisfaction: 0.0,
      total_welfare: 1.2,
      efficiency_loss: 0.01,
      tyranny_index: 0.0,
    },
    supermajority_3_4: {
      minority_win_rate: 1.0,
      minority_satisfaction: 1.0,
      majority_satisfaction: 0.0,
      total_welfare: 1.2,
      efficiency_loss: 0.01,
      tyranny_index: 0.0,
    },
    unanimous: {
      minority_win_rate: 1.0,
      minority_satisfaction: 1.0,
      majority_satisfaction: 0.0,
      total_welfare: 1.2,
      efficiency_loss: 0.01,
      tyranny_index: 0.0,
    },
    qv: {
      minority_win_rate: 0.6,
      minority_satisfaction: 0.6,
      majority_satisfaction: 0.5,
      total_welfare: 1.0,
      efficiency_loss: 0.2,
      tyranny_index: 0.4,
    },
    mj: {
      minority_win_rate: 0.0,
      minority_satisfaction: 0.0,
      majority_satisfaction: 1.0,
      total_welfare: 0.6,
      efficiency_loss: 0.5,
      tyranny_index: 1.0,
    },
  },
  tyranny_curve: [
    { majority_pct: 0.51, tyranny_by_rule: { simple_majority: 1.0, unanimous: 0.0 } },
    { majority_pct: 0.6, tyranny_by_rule: { simple_majority: 1.0, unanimous: 0.0 } },
    { majority_pct: 0.8, tyranny_by_rule: { simple_majority: 1.0, unanimous: 0.0 } },
  ],
  best_protector: 'unanimous',
  least_efficient: 'simple_majority',
  pedagogical_note: 'Tocqueville: la tyrannie de la majorité.',
};

/** openapi-fetch resolves to { data, error }. */
const ok = (d: unknown) => ({ data: d, error: undefined });

function renderPanel() {
  return render(
    <QueryClientProvider client={makeTestQueryClient()}>
      <MajorityTyrannyPanel />
    </QueryClientProvider>
  );
}

async function renderAndRun() {
  apiClient.POST.mockResolvedValueOnce(ok(MOCK_DATA));
  renderPanel();
  await act(async () => {
    fireEvent.click(screen.getByTestId('run-btn'));
  });
  await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
  await act(async () => {});
}

describe('MajorityTyrannyPanel', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders controls and run button', () => {
    renderPanel();
    expect(screen.getByTestId('run-btn')).toBeInTheDocument();
    expect(screen.getByTestId('voters-input')).toBeInTheDocument();
    expect(screen.getByTestId('majority-slider')).toBeInTheDocument();
    expect(screen.getByTestId('intensity-slider')).toBeInTheDocument();
    expect(screen.getByTestId('decisions-input')).toBeInTheDocument();
    expect(screen.getByTestId('seed-input')).toBeInTheDocument();
  });

  it('shows tocqueville quote on mount', () => {
    renderPanel();
    expect(screen.getByTestId('tocqueville-quote')).toBeInTheDocument();
  });

  it('shows rule toggles for all 6 rules', () => {
    renderPanel();
    const allRules = [
      'simple_majority',
      'supermajority_2_3',
      'supermajority_3_4',
      'unanimous',
      'qv',
      'mj',
    ];
    allRules.forEach((r) => {
      expect(screen.getByTestId(`rule-badge-${r}`)).toBeInTheDocument();
    });
  });

  it('shows prompt alert before simulation', () => {
    renderPanel();
    expect(screen.getByTestId('prompt-alert')).toBeInTheDocument();
  });

  it('calls API with correct payload on run', async () => {
    await renderAndRun();
    const [url, init] = apiClient.POST.mock.calls[0];
    expect(url).toBe('/api/v2/theory/majority-tyranny');
    const payload = (init as { body: Record<string, unknown> }).body;
    expect(payload).toHaveProperty('num_voters');
    expect(payload).toHaveProperty('majority_pct');
    expect(payload).toHaveProperty('minority_intensity');
    expect(payload).toHaveProperty('num_decisions');
    expect(payload).toHaveProperty('seed');
    expect(payload).toHaveProperty('decision_rules');
  });

  it('renders summary badges after simulation', async () => {
    await renderAndRun();
    expect(screen.getByTestId('best-protector-badge')).toBeInTheDocument();
    expect(screen.getByTestId('least-efficient-badge')).toBeInTheDocument();
  });

  it('renders view switcher buttons', async () => {
    await renderAndRun();
    expect(screen.getByTestId('view-btn-radar')).toBeInTheDocument();
    expect(screen.getByTestId('view-btn-curve')).toBeInTheDocument();
    expect(screen.getByTestId('view-btn-table')).toBeInTheDocument();
  });

  it('shows radar view by default after simulation', async () => {
    await renderAndRun();
    expect(screen.getByTestId('radar-view')).toBeInTheDocument();
  });

  it('switches to curve view on click', async () => {
    await renderAndRun();
    fireEvent.click(screen.getByTestId('view-btn-curve'));
    expect(screen.getByTestId('curve-view')).toBeInTheDocument();
    expect(screen.queryByTestId('radar-view')).not.toBeInTheDocument();
  });

  it('switches to table view and shows rule rows', async () => {
    await renderAndRun();
    fireEvent.click(screen.getByTestId('view-btn-table'));
    expect(screen.getByTestId('table-view')).toBeInTheDocument();
    expect(screen.getByTestId('row-simple_majority')).toBeInTheDocument();
    expect(screen.getByTestId('row-unanimous')).toBeInTheDocument();
  });

  it('shows safeguards section', async () => {
    await renderAndRun();
    expect(screen.getByTestId('safeguards-section')).toBeInTheDocument();
  });

  it('shows pedagogical note', async () => {
    await renderAndRun();
    expect(screen.getByTestId('pedagogical-note')).toBeInTheDocument();
  });

  it('shows error alert on API failure', async () => {
    apiClient.POST.mockRejectedValueOnce(new Error('Network error'));
    renderPanel();
    await act(async () => {
      fireEvent.click(screen.getByTestId('run-btn'));
    });
    await waitFor(() => expect(screen.getByTestId('error-alert')).toBeInTheDocument());
  });

  it('toggles a rule off and back on', () => {
    renderPanel();
    const badge = screen.getByTestId('rule-badge-qv');
    // Click to deactivate (keeps at least 1 active so it deactivates)
    fireEvent.click(badge);
    fireEvent.click(badge); // Toggle back
    expect(badge).toBeInTheDocument();
  });
});
