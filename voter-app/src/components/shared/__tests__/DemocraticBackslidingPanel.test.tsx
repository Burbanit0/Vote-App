import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import DemocraticBackslidingPanel from '../DemocraticBackslidingPanel';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
}));
const { apiClient } = (await import('../../../api/client')) as unknown as {
  apiClient: { POST: jest.Mock };
};

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      if (opts?.n !== undefined) return `autocracy at #${opts.n}`;
      return key.split('.').pop() ?? key;
    },
  }),
}));

vi.mock('recharts', () => {
  const React = require('react');
  const stub = ({ children }: { children?: React.ReactNode }) =>
    React.createElement('div', { 'data-testid': 'recharts-stub' }, children);
  return {
    LineChart: stub,
    Line: stub,
    XAxis: stub,
    YAxis: stub,
    CartesianGrid: stub,
    Tooltip: stub,
    Legend: stub,
    ReferenceLine: stub,
    ResponsiveContainer: ({ children }: { children?: React.ReactNode }) =>
      React.createElement('div', { 'data-testid': 'timeline-chart' }, children),
  };
});

// ── Mock data helpers ─────────────────────────────────────────────────────────

function makeElection(n: number, quality: number, winner = 'Incumbent', pnr = false) {
  return {
    election_n: n,
    winner,
    vote_shares: { Incumbent: 0.55, Opposition: 0.45 },
    democratic_quality: quality,
    advantages: { gerrymandering_bonus: 0.05 * n, media_bias: 0, suppression_rate: 0 },
    guardrails_triggered: [] as string[],
    point_of_no_return: pnr,
  };
}

const MOCK_HEALTHY: object = {
  elections: [makeElection(1, 0.95), makeElection(2, 0.9), makeElection(3, 0.88)],
  autocracy_reached: false,
  autocracy_at_election: null,
  guardrails_effectiveness: {
    constitutional_court: 0,
    opposition_media: 0,
    international_pressure: 0,
    supermajority_required: 0,
  },
  tipping_points: [0.5, 0.8],
  pedagogical_note: 'Healthy democracy.',
};

const MOCK_AUTOCRACY: object = {
  elections: [
    makeElection(1, 0.85),
    makeElection(2, 0.65),
    makeElection(3, 0.4, 'Incumbent', true),
    makeElection(4, 0.18, 'Incumbent', true),
  ],
  autocracy_reached: true,
  autocracy_at_election: 4,
  guardrails_effectiveness: {
    constitutional_court: 0,
    opposition_media: 0,
    international_pressure: 0,
    supermajority_required: 0,
  },
  tipping_points: [0.3, 0.6],
  pedagogical_note: 'Autocracy reached.',
};

const MOCK_GUARDRAILS: object = {
  elections: [makeElection(1, 0.9), makeElection(2, 0.85), makeElection(3, 0.8)],
  autocracy_reached: false,
  autocracy_at_election: null,
  guardrails_effectiveness: {
    constitutional_court: 0.12,
    opposition_media: 0.08,
    international_pressure: 0,
    supermajority_required: 0,
  },
  tipping_points: [0.6, 1.0],
  pedagogical_note: 'Guardrails helped.',
};

/** openapi-fetch resolves to { data, error }. */
const ok = (d: unknown) => ({ data: d, error: undefined });

function renderPanel() {
  return render(
    <QueryClientProvider client={makeTestQueryClient()}>
      <DemocraticBackslidingPanel />
    </QueryClientProvider>
  );
}

async function renderAndRun(responseData: object = MOCK_HEALTHY) {
  apiClient.POST.mockResolvedValueOnce(ok(responseData));
  renderPanel();
  await act(async () => {
    fireEvent.click(screen.getByTestId('run-btn'));
  });
  await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
  await act(async () => {});
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('DemocraticBackslidingPanel', () => {
  beforeEach(() => vi.clearAllMocks());

  // ── Initial render ──────────────────────────────────────────────────────────

  it('renders paradox quote on mount', () => {
    renderPanel();
    expect(screen.getByTestId('paradox-quote')).toBeInTheDocument();
  });

  it('renders all controls', () => {
    renderPanel();
    expect(screen.getByTestId('run-btn')).toBeInTheDocument();
    expect(screen.getByTestId('voters-input')).toBeInTheDocument();
    expect(screen.getByTestId('elections-input')).toBeInTheDocument();
    expect(screen.getByTestId('seed-input')).toBeInTheDocument();
    expect(screen.getByTestId('method-select')).toBeInTheDocument();
    expect(screen.getByTestId('intensity-slider')).toBeInTheDocument();
  });

  it('renders guardrails panel with all four toggles', () => {
    renderPanel();
    expect(screen.getByTestId('guardrails-panel')).toBeInTheDocument();
    expect(screen.getByTestId('guardrail-constitutional_court')).toBeInTheDocument();
    expect(screen.getByTestId('guardrail-opposition_media')).toBeInTheDocument();
    expect(screen.getByTestId('guardrail-international_pressure')).toBeInTheDocument();
    expect(screen.getByTestId('guardrail-supermajority_required')).toBeInTheDocument();
  });

  it('shows prompt alert before simulation', () => {
    renderPanel();
    expect(screen.getByTestId('prompt-alert')).toBeInTheDocument();
  });

  it('has three method options in select', () => {
    renderPanel();
    const select = screen.getByTestId('method-select') as HTMLSelectElement;
    expect(select.options).toHaveLength(3);
  });

  // ── API call ────────────────────────────────────────────────────────────────

  it('calls API with correct payload on run', async () => {
    await renderAndRun();
    const [url, init] = apiClient.POST.mock.calls[0];
    expect(url).toBe('/api/v2/theory/democratic-backsliding');
    const payload = (init as { body: Record<string, unknown> }).body;
    expect(payload).toHaveProperty('num_voters');
    expect(payload).toHaveProperty('num_elections');
    expect(payload).toHaveProperty('backsliding_method');
    expect(payload).toHaveProperty('backsliding_intensity');
    expect(payload).toHaveProperty('guardrails');
    expect(payload).toHaveProperty('guardrails.constitutional_court', false);
  });

  // ── Healthy democracy results ───────────────────────────────────────────────

  it('shows quality summary after simulation', async () => {
    await renderAndRun();
    expect(screen.getByTestId('quality-summary')).toBeInTheDocument();
  });

  it('renders timeline chart after simulation', async () => {
    await renderAndRun();
    expect(screen.getByTestId('timeline-chart')).toBeInTheDocument();
  });

  it('renders election cards for each election', async () => {
    await renderAndRun();
    expect(screen.getByTestId('election-card-1')).toBeInTheDocument();
    expect(screen.getByTestId('election-card-2')).toBeInTheDocument();
    expect(screen.getByTestId('election-card-3')).toBeInTheDocument();
  });

  it('renders advantages table with rows', async () => {
    await renderAndRun();
    expect(screen.getByTestId('advantages-section')).toBeInTheDocument();
    expect(screen.getByTestId('adv-row-1')).toBeInTheDocument();
    expect(screen.getByTestId('adv-row-3')).toBeInTheDocument();
  });

  it('shows pedagogical note', async () => {
    await renderAndRun();
    expect(screen.getByTestId('pedagogical-note')).toBeInTheDocument();
    expect(screen.getByTestId('pedagogical-note')).toHaveTextContent('Healthy democracy.');
  });

  it('does NOT show autocracy alert for healthy scenario', async () => {
    await renderAndRun();
    expect(screen.queryByTestId('autocracy-alert')).not.toBeInTheDocument();
  });

  // ── Autocracy scenario ──────────────────────────────────────────────────────

  it('shows autocracy alert when autocracy_reached=true', async () => {
    await renderAndRun(MOCK_AUTOCRACY);
    expect(screen.getByTestId('autocracy-alert')).toBeInTheDocument();
  });

  it('renders election cards for autocracy scenario', async () => {
    await renderAndRun(MOCK_AUTOCRACY);
    expect(screen.getByTestId('election-card-1')).toBeInTheDocument();
    expect(screen.getByTestId('election-card-4')).toBeInTheDocument();
  });

  // ── Guardrails effectiveness badges ────────────────────────────────────────

  it('shows effectiveness badge on active guardrail after simulation', async () => {
    apiClient.POST.mockResolvedValueOnce(ok(MOCK_GUARDRAILS));
    renderPanel();

    // Activate constitutional_court before running
    fireEvent.click(screen.getByTestId('guardrail-constitutional_court'));

    await act(async () => {
      fireEvent.click(screen.getByTestId('run-btn'));
    });
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalled());
    await act(async () => {});

    // The +12% badge should appear for constitutional_court
    expect(screen.getByText('+12%')).toBeInTheDocument();
  });

  // ── Guardrail toggle triggers recalculation ─────────────────────────────────

  it('toggling a guardrail recalculates when data already exists', async () => {
    apiClient.POST.mockResolvedValueOnce(ok(MOCK_HEALTHY)).mockResolvedValueOnce(
      ok(MOCK_GUARDRAILS)
    );

    renderPanel();
    await act(async () => {
      fireEvent.click(screen.getByTestId('run-btn'));
    });
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    await act(async () => {});

    fireEvent.click(screen.getByTestId('guardrail-constitutional_court'));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(2));
    await act(async () => {});
  });

  // ── Historical overlay toggles ──────────────────────────────────────────────

  it('renders historical overlay toggle badges', async () => {
    await renderAndRun();
    expect(screen.getByTestId('hist-toggle-hungary')).toBeInTheDocument();
    expect(screen.getByTestId('hist-toggle-turkey')).toBeInTheDocument();
    expect(screen.getByTestId('hist-toggle-venezuela')).toBeInTheDocument();
  });

  it('toggles historical overlay on click', async () => {
    await renderAndRun();
    const hungarybadge = screen.getByTestId('hist-toggle-hungary');
    fireEvent.click(hungarybadge);
    // Badge is still in DOM, just selected
    expect(hungarybadge).toBeInTheDocument();
    // Toggle off
    fireEvent.click(hungarybadge);
    expect(hungarybadge).toBeInTheDocument();
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
