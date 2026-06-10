import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import EpistocracyPanel from '../EpistocracyPanel';
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
    t: (key: string, opts?: Record<string, unknown>) => {
      if (opts?.pct !== undefined) return `below random ${opts.pct}%`;
      return key.split('.').pop() ?? key;
    },
  }),
}));

vi.mock('recharts', () => {
  const React = require('react');
  const stub = ({ children }: { children?: React.ReactNode }) =>
    React.createElement('div', { 'data-testid': 'recharts-stub' }, children);
  return {
    BarChart: stub,
    Bar: stub,
    XAxis: stub,
    YAxis: stub,
    CartesianGrid: stub,
    Tooltip: stub,
    Legend: stub,
    LineChart: stub,
    Line: stub,
    ReferenceLine: stub,
    Cell: stub,
    ResponsiveContainer: ({ children }: { children?: React.ReactNode }) =>
      React.createElement('div', null, children),
  };
});

// ── Mock data ─────────────────────────────────────────────────────────────────

const MOCK_DATA = {
  voter_competence_stats: { mean: 0.6, biased_mean: 0.53, expert_count: 12 },
  results: {
    equal: { winner: 'B', bayesian_regret: 0.35, correct_choice_pct: 0.6, participates_pct: 1.0 },
    competence_weighted: {
      winner: 'B',
      bayesian_regret: 0.28,
      correct_choice_pct: 0.68,
      participates_pct: 1.0,
    },
    epistocratic: {
      winner: 'B',
      bayesian_regret: 0.2,
      correct_choice_pct: 0.78,
      participates_pct: 0.25,
    },
    lottery: {
      winner: 'B',
      bayesian_regret: 0.45,
      correct_choice_pct: 0.55,
      participates_pct: 1.0,
    },
  },
  democracy_vs_expert: { democracy_regret: 0.35, expert_regret: 0.18, omniscient_regret: 0.0 },
  condorcet_threshold: 0.5,
  pedagogical_note: 'Brennan 2016: against democracy.',
};

const BELOW_RANDOM_DATA = {
  ...MOCK_DATA,
  voter_competence_stats: { mean: 0.35, biased_mean: 0.28, expert_count: 2 },
};

/** openapi-fetch resolves to { data, error }. */
const ok = (d: unknown) => ({ data: d, error: undefined });

function renderPanel() {
  return render(
    <QueryClientProvider client={makeTestQueryClient()}>
      <EpistocracyPanel />
    </QueryClientProvider>
  );
}

async function renderAndRun(responseData = MOCK_DATA) {
  apiClient.POST.mockResolvedValueOnce(ok(responseData));
  renderPanel();
  await act(async () => {
    fireEvent.click(screen.getByTestId('run-btn'));
  });
  await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
  await screen.findByTestId('comparison-badges');
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('EpistocracyPanel', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders Caplan quote on mount', () => {
    renderPanel();
    expect(screen.getByTestId('caplan-quote')).toBeInTheDocument();
  });

  it('renders all controls', () => {
    renderPanel();
    expect(screen.getByTestId('run-btn')).toBeInTheDocument();
    expect(screen.getByTestId('voters-input')).toBeInTheDocument();
    expect(screen.getByTestId('seed-input')).toBeInTheDocument();
    expect(screen.getByTestId('dist-select')).toBeInTheDocument();
    expect(screen.getByTestId('caplan-bias-toggle')).toBeInTheDocument();
    expect(screen.getByTestId('comp-mean-slider')).toBeInTheDocument();
    expect(screen.getByTestId('threshold-slider')).toBeInTheDocument();
    expect(screen.getByTestId('expert-pct-slider')).toBeInTheDocument();
  });

  it('renders competence histogram on mount', () => {
    renderPanel();
    expect(screen.getByTestId('histogram-section')).toBeInTheDocument();
    expect(screen.getByTestId('competence-histogram')).toBeInTheDocument();
  });

  it('shows prompt alert before simulation', () => {
    renderPanel();
    expect(screen.getByTestId('prompt-alert')).toBeInTheDocument();
  });

  it('has three distribution options in select', () => {
    renderPanel();
    const select = screen.getByTestId('dist-select') as HTMLSelectElement;
    expect(select.options).toHaveLength(3);
  });

  it('calls API with correct payload on run', async () => {
    await renderAndRun();
    const [url, init] = apiClient.POST.mock.calls[0];
    expect(url).toBe('/api/v2/theory/epistocracy');
    const payload = (init as { body: Record<string, unknown> }).body;
    expect(payload).toHaveProperty('num_voters');
    expect(payload).toHaveProperty('seed');
    expect(payload).toHaveProperty('voter_competence_distribution');
    expect(payload).toHaveProperty('competence_params');
    expect(payload).toHaveProperty('epistocracy_threshold');
    expect(payload).toHaveProperty('candidates');
  });

  it('renders comparison badges after simulation', async () => {
    await renderAndRun();
    expect(screen.getByTestId('comparison-badges')).toBeInTheDocument();
  });

  it('renders view switcher buttons', async () => {
    await renderAndRun();
    expect(screen.getByTestId('view-btn-quality')).toBeInTheDocument();
    expect(screen.getByTestId('view-btn-table')).toBeInTheDocument();
  });

  it('shows quality view by default', async () => {
    await renderAndRun();
    expect(screen.getByTestId('quality-view')).toBeInTheDocument();
  });

  it('switches to table view and shows scheme rows', async () => {
    await renderAndRun();
    fireEvent.click(screen.getByTestId('view-btn-table'));
    expect(screen.getByTestId('table-view')).toBeInTheDocument();
    expect(screen.getByTestId('table-row-equal')).toBeInTheDocument();
    expect(screen.getByTestId('table-row-competence_weighted')).toBeInTheDocument();
    expect(screen.getByTestId('table-row-epistocratic')).toBeInTheDocument();
    expect(screen.getByTestId('table-row-lottery')).toBeInTheDocument();
  });

  it('renders arguments for/against section', async () => {
    await renderAndRun();
    expect(screen.getByTestId('arguments-section')).toBeInTheDocument();
  });

  it('renders pedagogical note', async () => {
    await renderAndRun();
    expect(screen.getByTestId('pedagogical-note')).toBeInTheDocument();
    expect(screen.getByTestId('pedagogical-note')).toHaveTextContent('Brennan');
  });

  it('shows below-random alert when biased_mean < 0.5', async () => {
    await renderAndRun(BELOW_RANDOM_DATA);
    expect(screen.getByTestId('below-random-alert')).toBeInTheDocument();
  });

  it('does NOT show below-random alert when biased_mean >= 0.5', async () => {
    await renderAndRun(MOCK_DATA);
    expect(screen.queryByTestId('below-random-alert')).not.toBeInTheDocument();
  });

  it('histogram stays visible when mean slider changes', () => {
    renderPanel();
    const slider = screen.getByTestId('comp-mean-slider');
    fireEvent.change(slider, { target: { value: '40' } });
    expect(screen.getByTestId('competence-histogram')).toBeInTheDocument();
  });

  it('shows error alert on API failure', async () => {
    apiClient.POST.mockRejectedValueOnce(new Error('Network error'));
    renderPanel();
    await act(async () => {
      fireEvent.click(screen.getByTestId('run-btn'));
    });
    await waitFor(() => expect(screen.getByTestId('error-alert')).toBeInTheDocument());
  });
});
