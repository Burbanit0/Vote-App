import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import IntergenerationalPanel from '../IntergenerationalPanel';
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
    CartesianGrid: stub, Tooltip: stub, Legend: stub, Cell: stub,
    ResponsiveContainer: ({ children }: { children?: React.ReactNode }) =>
      React.createElement('div', null, children),
  };
});

// ── Mock data ──────────────────────────────────────────────────────────────────

function makeMechResult(adopted: boolean, votePct = 0.55) {
  return {
    adopted,
    vote_pct:          votePct,
    welfare_present:   adopted ? 0.6 : 0.4,
    welfare_future:    adopted ? 0.5 : 0.3,
    total_welfare_50y: adopted ? 0.55 : 0.35,
  };
}

const MOCK_DATA = {
  decisions_results: [
    {
      decision_name: 'Retraite',
      by_mechanism: {
        none:         makeMechResult(true,  0.62),
        proxy:        makeMechResult(true,  0.58),
        age_weighted: makeMechResult(false, 0.48),
        veto:         makeMechResult(false, 0.40),
      },
    },
    {
      decision_name: 'Education',
      by_mechanism: {
        none:         makeMechResult(true,  0.55),
        proxy:        makeMechResult(true,  0.60),
        age_weighted: makeMechResult(true,  0.65),
        veto:         makeMechResult(true,  0.70),
      },
    },
    {
      decision_name: 'Dette',
      by_mechanism: {
        none:         makeMechResult(true,  0.70),
        proxy:        makeMechResult(true,  0.60),
        age_weighted: makeMechResult(false, 0.45),
        veto:         makeMechResult(false, 0.30),
      },
    },
  ],
  mechanism_comparison: {
    none:         { adoption_rate: 1.00, present_bias: 0.40, future_welfare_gain:  0.00, intergenerational_gini: 0.25, avg_welfare_50y: 0.50 },
    proxy:        { adoption_rate: 0.90, present_bias: 0.25, future_welfare_gain:  0.05, intergenerational_gini: 0.20, avg_welfare_50y: 0.52 },
    age_weighted: { adoption_rate: 0.67, present_bias: 0.15, future_welfare_gain:  0.08, intergenerational_gini: 0.15, avg_welfare_50y: 0.55 },
    veto:         { adoption_rate: 0.50, present_bias: 0.05, future_welfare_gain:  0.12, intergenerational_gini: 0.10, avg_welfare_50y: 0.58 },
  },
  pedagogical_note: 'Rawls: veil of ignorance.',
};

/** openapi-fetch resolves to { data, error }. */
const ok = (d: unknown) => ({ data: d, error: undefined });

function renderPanel() {
  return render(
    <QueryClientProvider client={makeTestQueryClient()}>
      <IntergenerationalPanel />
    </QueryClientProvider>
  );
}

async function renderAndRun(responseData = MOCK_DATA) {
  apiClient.POST.mockResolvedValueOnce(ok(responseData));
  renderPanel();
  await act(async () => { fireEvent.click(screen.getByTestId('run-btn')); });
  await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
  await act(async () => {});
}

// ── Tests ──────────────────────────────────────────────────────────────────────

describe('IntergenerationalPanel', () => {
  beforeEach(() => jest.clearAllMocks());

  // ── Initial render ──────────────────────────────────────────────────────────

  it('renders key message on mount', () => {
    renderPanel();
    expect(screen.getByTestId('key-message')).toBeInTheDocument();
  });

  it('renders decision editor with default decisions', () => {
    renderPanel();
    expect(screen.getByTestId('decision-editor')).toBeInTheDocument();
    expect(screen.getByTestId('decision-name-0')).toBeInTheDocument();
    expect(screen.getByTestId('decision-name-1')).toBeInTheDocument();
  });

  it('renders controls: voters, age dist sliders, seed, run', () => {
    renderPanel();
    expect(screen.getByTestId('run-btn')).toBeInTheDocument();
    expect(screen.getByTestId('voters-input')).toBeInTheDocument();
    expect(screen.getByTestId('seed-input')).toBeInTheDocument();
    expect(screen.getByTestId('age-dist-0')).toBeInTheDocument();
    expect(screen.getByTestId('age-dist-1')).toBeInTheDocument();
    expect(screen.getByTestId('age-dist-2')).toBeInTheDocument();
  });

  it('shows prompt alert before simulation', () => {
    renderPanel();
    expect(screen.getByTestId('prompt-alert')).toBeInTheDocument();
  });

  // ── Decision editor interactions ────────────────────────────────────────────

  it('adds a decision when add button is clicked', () => {
    renderPanel();
    const before = screen.getAllByTestId(/^decision-name-/).length;
    fireEvent.click(screen.getByTestId('add-decision-btn'));
    const after = screen.getAllByTestId(/^decision-name-/).length;
    expect(after).toBe(before + 1);
  });

  // ── API call ────────────────────────────────────────────────────────────────

  it('calls API with correct payload on run', async () => {
    await renderAndRun();
    const [url, init] = apiClient.POST.mock.calls[0];
    expect(url).toBe('/api/v2/theory/intergenerational');
    const payload = (init as { body: Record<string, unknown> }).body;
    expect(payload).toHaveProperty('decisions');
    expect(payload).toHaveProperty('num_voters');
    expect(payload).toHaveProperty('age_distribution');
    expect(payload).toHaveProperty('seed');
  });

  // ── Results ─────────────────────────────────────────────────────────────────

  it('renders 4 hemicycles after simulation', async () => {
    await renderAndRun();
    expect(screen.getByTestId('hemicycles-section')).toBeInTheDocument();
    expect(screen.getByTestId('hemicycle-none')).toBeInTheDocument();
    expect(screen.getByTestId('hemicycle-proxy')).toBeInTheDocument();
    expect(screen.getByTestId('hemicycle-age_weighted')).toBeInTheDocument();
    expect(screen.getByTestId('hemicycle-veto')).toBeInTheDocument();
  });

  it('renders view switcher buttons', async () => {
    await renderAndRun();
    expect(screen.getByTestId('view-btn-comparison')).toBeInTheDocument();
    expect(screen.getByTestId('view-btn-welfare')).toBeInTheDocument();
    expect(screen.getByTestId('view-btn-table')).toBeInTheDocument();
  });

  it('shows comparison view by default', async () => {
    await renderAndRun();
    expect(screen.getByTestId('comparison-view')).toBeInTheDocument();
  });

  it('switches to welfare view', async () => {
    await renderAndRun();
    fireEvent.click(screen.getByTestId('view-btn-welfare'));
    expect(screen.getByTestId('welfare-view')).toBeInTheDocument();
    expect(screen.queryByTestId('comparison-view')).not.toBeInTheDocument();
  });

  it('switches to table view and shows mechanism rows', async () => {
    await renderAndRun();
    fireEvent.click(screen.getByTestId('view-btn-table'));
    expect(screen.getByTestId('table-view')).toBeInTheDocument();
    expect(screen.getByTestId('table-row-none')).toBeInTheDocument();
    expect(screen.getByTestId('table-row-proxy')).toBeInTheDocument();
    expect(screen.getByTestId('table-row-age_weighted')).toBeInTheDocument();
    expect(screen.getByTestId('table-row-veto')).toBeInTheDocument();
  });

  it('renders per-decision breakdown', async () => {
    await renderAndRun();
    expect(screen.getByTestId('decisions-breakdown')).toBeInTheDocument();
    expect(screen.getByTestId('decision-result-0')).toBeInTheDocument();
    expect(screen.getByTestId('decision-result-1')).toBeInTheDocument();
    expect(screen.getByTestId('decision-result-2')).toBeInTheDocument();
  });

  it('renders examples section and pedagogical note', async () => {
    await renderAndRun();
    expect(screen.getByTestId('examples-section')).toBeInTheDocument();
    expect(screen.getByTestId('pedagogical-note')).toBeInTheDocument();
    expect(screen.getByTestId('pedagogical-note')).toHaveTextContent('Rawls');
  });

  // ── Error handling ──────────────────────────────────────────────────────────

  it('shows error alert on API failure', async () => {
    apiClient.POST.mockRejectedValueOnce(new Error('Network error'));
    renderPanel();
    await act(async () => { fireEvent.click(screen.getByTestId('run-btn')); });
    await waitFor(() => expect(screen.getByTestId('error-alert')).toBeInTheDocument());
  });
});
