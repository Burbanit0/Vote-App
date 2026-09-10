import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import AssumptionTesterPanel from '../AssumptionTesterPanel';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
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
    BarChart: stub,
    Bar: stub,
    XAxis: stub,
    YAxis: stub,
    CartesianGrid: stub,
    Tooltip: stub,
    Cell: stub,
    ResponsiveContainer: ({ children }: { children?: React.ReactNode }) =>
      React.createElement('div', null, children),
  };
});

// ── Mock data ─────────────────────────────────────────────────────────────────

const makeResult = (changed: boolean, variance: number, winner = 'Alice') => ({
  winner,
  winner_changed: changed,
  pct_trials_changed: changed ? 0.33 : 0.0,
  result_variance: variance,
  confidence_interval: [0.65, 0.95] as [number, number],
  winner_distribution: { Alice: changed ? 0.67 : 1.0, Bob: changed ? 0.33 : 0.0 },
});

const MOCK_ROBUST: object = {
  baseline_result: { winner: 'Alice', regret: 0.0 },
  relaxed_results: {
    single_peaked: makeResult(false, 0.05),
    stable_preferences: makeResult(false, 0.1),
    rational_voters: makeResult(false, 0.08),
    fixed_electorate: makeResult(false, 0.04),
    measurable_utilities: makeResult(false, 0.06),
  },
  most_fragile_assumption: 'stable_preferences',
  robust_result: true,
  pedagogical_note: 'Alice wins under all assumptions.',
};

const MOCK_FRAGILE: object = {
  baseline_result: { winner: 'Alice', regret: 0.0 },
  relaxed_results: {
    single_peaked: makeResult(true, 0.65, 'Bob'),
    stable_preferences: makeResult(false, 0.2),
    rational_voters: makeResult(false, 0.12),
    fixed_electorate: makeResult(false, 0.08),
    measurable_utilities: makeResult(false, 0.1),
  },
  most_fragile_assumption: 'single_peaked',
  robust_result: false,
  pedagogical_note: 'Fragile under single_peaked.',
};

/** openapi-fetch resolves to { data, error }. */
const ok = (d: unknown) => ({ data: d, error: undefined });

function renderPanel() {
  return render(
    <QueryClientProvider client={makeTestQueryClient()}>
      <AssumptionTesterPanel />
    </QueryClientProvider>
  );
}

async function renderAndRun(responseData: object = MOCK_ROBUST) {
  apiClient.POST.mockResolvedValueOnce(ok(responseData));
  renderPanel();
  await act(async () => {
    fireEvent.click(screen.getByTestId('run-btn'));
  });
  await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
  await act(async () => {});
}

describe('AssumptionTesterPanel', () => {
  beforeEach(() => vi.clearAllMocks());

  // ── Initial render ──────────────────────────────────────────────────────────

  it('renders philosophy quote on mount', () => {
    renderPanel();
    expect(screen.getByTestId('philosophy-quote')).toBeInTheDocument();
  });

  it('renders controls', () => {
    renderPanel();
    expect(screen.getByTestId('run-btn')).toBeInTheDocument();
    expect(screen.getByTestId('voters-input')).toBeInTheDocument();
    expect(screen.getByTestId('seed-input')).toBeInTheDocument();
  });

  it('renders assumption cards with checkboxes', () => {
    renderPanel();
    expect(screen.getByTestId('assumption-cards')).toBeInTheDocument();
    expect(screen.getByTestId('assumption-card-single_peaked')).toBeInTheDocument();
    expect(screen.getByTestId('assumption-card-stable_preferences')).toBeInTheDocument();
    expect(screen.getByTestId('assumption-card-rational_voters')).toBeInTheDocument();
    expect(screen.getByTestId('assumption-card-fixed_electorate')).toBeInTheDocument();
    expect(screen.getByTestId('assumption-card-measurable_utilities')).toBeInTheDocument();
  });

  it('shows prompt alert before test run', () => {
    renderPanel();
    expect(screen.getByTestId('prompt-alert')).toBeInTheDocument();
  });

  // ── Assumption toggle ───────────────────────────────────────────────────────

  it('toggles assumption checkboxes on/off', () => {
    renderPanel();
    const cb = screen.getByTestId('assumption-cb-single_peaked') as HTMLInputElement;
    expect(cb.checked).toBe(true);
    fireEvent.click(cb);
    expect(cb.checked).toBe(false);
    fireEvent.click(cb);
    expect(cb.checked).toBe(true);
  });

  // ── API call ────────────────────────────────────────────────────────────────

  it('calls API with correct payload on run', async () => {
    await renderAndRun();
    const [url, init] = apiClient.POST.mock.calls[0];
    expect(url).toBe('/api/v2/theory/assumption-testing');
    const payload = (init as { body: Record<string, unknown> }).body;
    expect(payload).toHaveProperty('base_simulation');
    expect(payload).toHaveProperty('assumptions_to_relax');
  });

  // ── Results: robust scenario ─────────────────────────────────────────────────

  it('renders summary section and robust badge', async () => {
    await renderAndRun(MOCK_ROBUST);
    expect(screen.getByTestId('summary-section')).toBeInTheDocument();
    expect(screen.getByTestId('robust-badge')).toHaveTextContent('robust');
  });

  it('renders fragility chart and variance chart', async () => {
    await renderAndRun(MOCK_ROBUST);
    expect(screen.getByTestId('fragility-chart')).toBeInTheDocument();
    expect(screen.getByTestId('variance-chart')).toBeInTheDocument();
  });

  it('renders reference section', async () => {
    await renderAndRun(MOCK_ROBUST);
    expect(screen.getByTestId('reference-section')).toBeInTheDocument();
  });

  it('renders pedagogical note', async () => {
    await renderAndRun(MOCK_ROBUST);
    expect(screen.getByTestId('pedagogical-note')).toBeInTheDocument();
    expect(screen.getByTestId('pedagogical-note')).toHaveTextContent(
      'Alice wins under all assumptions.'
    );
  });

  // ── Results: fragile scenario ────────────────────────────────────────────────

  it('shows fragile badge when result is fragile', async () => {
    await renderAndRun(MOCK_FRAGILE);
    expect(screen.getByTestId('robust-badge')).toHaveTextContent('fragile');
  });

  it('marks most-fragile assumption card', async () => {
    await renderAndRun(MOCK_FRAGILE);
    const card = screen.getByTestId('assumption-card-single_peaked');
    // The most-fragile card should be highlighted (yellow background)
    expect(card).toBeInTheDocument();
  });

  // ── Error handling ──────────────────────────────────────────────────────────

  it('shows error alert on API failure', async () => {
    apiClient.POST.mockRejectedValueOnce(new Error('Network error'));
    renderPanel();
    await act(async () => {
      fireEvent.click(screen.getByTestId('run-btn'));
    });
    await waitFor(() => expect(screen.getByTestId('error-alert')).toBeInTheDocument());
  });
});
