import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import IdentityVotingPanel from '../IdentityVotingPanel';
import { makeTestQueryClient } from '../../../test/queryWrapper';

jest.mock('../../../api/client', () => ({
  apiClient: { GET: jest.fn(), POST: jest.fn(), PUT: jest.fn(), DELETE: jest.fn(), PATCH: jest.fn() },
  getAccessToken: jest.fn(() => null),
}));
const { apiClient } = jest.requireMock('../../../api/client') as { apiClient: { POST: jest.Mock } };

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key.split('.').pop() ?? key,
  }),
}));

jest.mock('recharts', () => {
  const React = require('react');
  const stub = ({ children }: { children?: React.ReactNode }) =>
    React.createElement('div', { 'data-testid': 'recharts-stub' }, children);
  return {
    BarChart: stub, Bar: stub, XAxis: stub, YAxis: stub,
    CartesianGrid: stub, Tooltip: stub, Legend: stub,
    LineChart: stub, Line: stub, ReferenceLine: stub, Cell: stub,
    ResponsiveContainer: ({ children }: { children?: React.ReactNode }) =>
      React.createElement('div', null, children),
  };
});

// ── Mock data ─────────────────────────────────────────────────────────────────

const MOCK_DATA_NO_CHANGE = {
  sincere_winner:  'Alice',
  identity_winner: 'Alice',
  mixed_winner:    'Alice',
  winner_changed:  false,
  group_results: [
    { group_name: 'Groupe A', affiliation: 'Alice', group_vote_pct: 0.82, ideology_match: 0.75, loyalty: 0.75, size_pct: 0.40 },
    { group_name: 'Groupe B', affiliation: 'Bob',   group_vote_pct: 0.65, ideology_match: 0.60, loyalty: 0.60, size_pct: 0.35 },
    { group_name: 'Groupe C', affiliation: 'Carol', group_vote_pct: 0.88, ideology_match: 0.70, loyalty: 0.80, size_pct: 0.25 },
  ],
  cross_pressured: { count: 42, abstention_rate: 0.08 },
  identity_weight_curve: [
    { weight: 0.0, winner: 'Alice', agreement_rate: 0.85 },
    { weight: 0.5, winner: 'Alice', agreement_rate: 0.75 },
    { weight: 1.0, winner: 'Alice', agreement_rate: 0.65 },
  ],
  pedagogical_note: 'Green 2002: voters adopt positions of their party.',
};

const MOCK_DATA_CHANGED = {
  ...MOCK_DATA_NO_CHANGE,
  mixed_winner:   'Carol',
  winner_changed: true,
};

/** openapi-fetch resolves to { data, error }. */
const ok = (d: unknown) => ({ data: d, error: undefined });

function renderPanel() {
  return render(
    <QueryClientProvider client={makeTestQueryClient()}>
      <IdentityVotingPanel />
    </QueryClientProvider>
  );
}

async function renderAndRun(responseData = MOCK_DATA_NO_CHANGE) {
  apiClient.POST.mockResolvedValueOnce(ok(responseData));
  renderPanel();
  await act(async () => { fireEvent.click(screen.getByTestId('run-btn')); });
  await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
  await act(async () => {});
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('IdentityVotingPanel', () => {
  beforeEach(() => jest.clearAllMocks());

  // ── Initial render ──────────────────────────────────────────────────────────

  it('renders Green quote on mount', () => {
    renderPanel();
    expect(screen.getByTestId('green-quote')).toBeInTheDocument();
  });

  it('renders preset buttons', () => {
    renderPanel();
    expect(screen.getByTestId('presets')).toBeInTheDocument();
    expect(screen.getByTestId('preset-usa2020')).toBeInTheDocument();
    expect(screen.getByTestId('preset-france2022')).toBeInTheDocument();
    expect(screen.getByTestId('preset-uk_brexit')).toBeInTheDocument();
  });

  it('renders group editor with default groups', () => {
    renderPanel();
    expect(screen.getByTestId('group-editor')).toBeInTheDocument();
    expect(screen.getByTestId('group-name-0')).toBeInTheDocument();
    expect(screen.getByTestId('group-name-1')).toBeInTheDocument();
    expect(screen.getByTestId('group-name-2')).toBeInTheDocument();
  });

  it('renders all controls', () => {
    renderPanel();
    expect(screen.getByTestId('run-btn')).toBeInTheDocument();
    expect(screen.getByTestId('voters-input')).toBeInTheDocument();
    expect(screen.getByTestId('seed-input')).toBeInTheDocument();
    expect(screen.getByTestId('identity-weight-slider')).toBeInTheDocument();
    expect(screen.getByTestId('cross-pressure-toggle')).toBeInTheDocument();
  });

  it('shows prompt alert before simulation', () => {
    renderPanel();
    expect(screen.getByTestId('prompt-alert')).toBeInTheDocument();
  });

  // ── Preset loading ──────────────────────────────────────────────────────────

  it('loads usa2020 preset and clears results', () => {
    renderPanel();
    fireEvent.click(screen.getByTestId('preset-usa2020'));
    // After loading preset, data is cleared
    expect(screen.getByTestId('prompt-alert')).toBeInTheDocument();
  });

  // ── API call ────────────────────────────────────────────────────────────────

  it('calls API with correct payload on run', async () => {
    await renderAndRun();
    const [url, init] = apiClient.POST.mock.calls[0];
    expect(url).toBe('/api/v2/theory/identity-voting');
    const payload = (init as { body: Record<string, unknown> }).body;
    expect(payload).toHaveProperty('candidates');
    expect(payload).toHaveProperty('num_voters');
    expect(payload).toHaveProperty('seed');
    expect(payload).toHaveProperty('identity_groups');
    expect(payload).toHaveProperty('identity_weight');
    expect(payload).toHaveProperty('cross_pressure');
  });

  // ── Results ─────────────────────────────────────────────────────────────────

  it('renders winner comparison after simulation', async () => {
    await renderAndRun();
    expect(screen.getByTestId('winner-comparison')).toBeInTheDocument();
  });

  it('renders cross-pressured stats', async () => {
    await renderAndRun();
    expect(screen.getByTestId('cross-pressured-stats')).toBeInTheDocument();
  });

  it('renders view switcher buttons', async () => {
    await renderAndRun();
    expect(screen.getByTestId('view-btn-groups')).toBeInTheDocument();
    expect(screen.getByTestId('view-btn-curve')).toBeInTheDocument();
    expect(screen.getByTestId('view-btn-table')).toBeInTheDocument();
  });

  it('shows groups view by default', async () => {
    await renderAndRun();
    expect(screen.getByTestId('groups-view')).toBeInTheDocument();
  });

  it('switches to curve view', async () => {
    await renderAndRun();
    fireEvent.click(screen.getByTestId('view-btn-curve'));
    expect(screen.getByTestId('curve-view')).toBeInTheDocument();
    expect(screen.queryByTestId('groups-view')).not.toBeInTheDocument();
  });

  it('switches to table view and shows group rows', async () => {
    await renderAndRun();
    fireEvent.click(screen.getByTestId('view-btn-table'));
    expect(screen.getByTestId('table-view')).toBeInTheDocument();
    expect(screen.getByTestId('table-row-0')).toBeInTheDocument();
    expect(screen.getByTestId('table-row-1')).toBeInTheDocument();
    expect(screen.getByTestId('table-row-2')).toBeInTheDocument();
  });

  it('renders real-world section and pedagogical note', async () => {
    await renderAndRun();
    expect(screen.getByTestId('realworld-section')).toBeInTheDocument();
    expect(screen.getByTestId('pedagogical-note')).toBeInTheDocument();
    expect(screen.getByTestId('pedagogical-note')).toHaveTextContent('Green');
  });

  // ── Winner changed alert ────────────────────────────────────────────────────

  it('shows winner-changed alert when winner changed', async () => {
    await renderAndRun(MOCK_DATA_CHANGED);
    expect(screen.getByTestId('winner-changed-alert')).toBeInTheDocument();
  });

  it('does NOT show winner-changed alert when winner same', async () => {
    await renderAndRun(MOCK_DATA_NO_CHANGE);
    expect(screen.queryByTestId('winner-changed-alert')).not.toBeInTheDocument();
  });

  // ── Error handling ──────────────────────────────────────────────────────────

  it('shows error alert on API failure', async () => {
    apiClient.POST.mockRejectedValueOnce(new Error('Network error'));
    renderPanel();
    await act(async () => { fireEvent.click(screen.getByTestId('run-btn')); });
    await waitFor(() => expect(screen.getByTestId('error-alert')).toBeInTheDocument());
  });
});
