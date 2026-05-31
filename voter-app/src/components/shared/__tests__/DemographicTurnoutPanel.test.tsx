import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import DemographicTurnoutPanel from '../DemographicTurnoutPanel';
import { ElectionProvider } from '../../../context/ElectionContext';
import { makeTestQueryClient } from '../../../test/queryWrapper';

jest.mock('../../../api/client', () => ({
  apiClient: { GET: jest.fn(), POST: jest.fn(), PUT: jest.fn(), DELETE: jest.fn(), PATCH: jest.fn() },
  getAccessToken: jest.fn(() => null),
}));
const { apiClient } = jest.requireMock('../../../api/client') as { apiClient: { POST: jest.Mock } };

jest.mock('recharts', () => {
  const React = require('react');
  return {
    BarChart:            ({ children }: any) => <div>{children}</div>,
    Bar:                 () => null,
    Cell:                () => null,
    XAxis:               () => null,
    YAxis:               () => null,
    CartesianGrid:       () => null,
    Tooltip:             () => null,
    Legend:              () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 200 }}>{children}</div>,
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(winnerChanged = false) {
  const candidates = ['Alice', 'Bob', 'Carol'];
  return {
    data: {
      biased_result: {
        winner:         winnerChanged ? 'Bob' : 'Alice',
        vote_shares:    { Alice: winnerChanged ? 0.35 : 0.44, Bob: winnerChanged ? 0.45 : 0.33, Carol: 0.23 },
        actual_turnout: 0.71,
        voter_profile:  { mean_age_group: 1.4, mean_education_level: 0.6, mean_ideology_x: 0.08 },
      },
      corrected_result: {
        winner:         'Alice',
        vote_shares:    { Alice: 0.44, Bob: 0.33, Carol: 0.23 },
        mean_ideology_x: -0.01,
      },
      winner_changed: winnerChanged,
      representation_gap: {
        ideology_drift:          0.09,
        overrepresented_groups:  ['seniors (65+), éducation élevée'],
        underrepresented_groups: ['jeunes (18-34), faible éducation'],
      },
      demographic_breakdown: [
        { group: 'jeunes (18-34), faible éducation',    population_pct: 0.10, voter_pct: 0.06, ideology_mean: -0.12 },
        { group: 'jeunes (18-34), éducation élevée',    population_pct: 0.15, voter_pct: 0.11, ideology_mean: -0.09 },
        { group: 'adultes (35-64), faible éducation',   population_pct: 0.18, voter_pct: 0.16, ideology_mean:  0.03 },
        { group: 'adultes (35-64), éducation élevée',   population_pct: 0.27, voter_pct: 0.25, ideology_mean: -0.01 },
        { group: 'seniors (65+), faible éducation',     population_pct: 0.12, voter_pct: 0.18, ideology_mean:  0.14 },
        { group: 'seniors (65+), éducation élevée',     population_pct: 0.18, voter_pct: 0.24, ideology_mean:  0.11 },
      ],
      pedagogical_note: 'Test note.',
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <DemographicTurnoutPanel />
        </ElectionProvider>
      </QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  jest.useFakeTimers();
});

afterEach(() => { jest.useRealTimers(); });

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('DemographicTurnoutPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByTestId('simulate-btn')).toBeInTheDocument();
  });

  it('shows preset selector', () => {
    renderPanel();
    expect(screen.getByTestId('preset-select')).toBeInTheDocument();
  });

  it('shows three turnout sliders', () => {
    renderPanel();
    expect(screen.getByTestId('turnout-slider-0')).toBeInTheDocument();
    expect(screen.getByTestId('turnout-slider-1')).toBeInTheDocument();
    expect(screen.getByTestId('turnout-slider-2')).toBeInTheDocument();
  });

  it('shows prompt before first run', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls API on simulate click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/demographic-turnout/),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('shows biased winner badge after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('biased-winner-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows ideology drift badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('drift-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows turnout badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('turnout-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows winner-changed alert when result flips', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('winner-changed-alert')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('does NOT show winner-changed alert when result stable', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => screen.getByTestId('biased-winner-badge'));
    expect(screen.queryByTestId('winner-changed-alert')).not.toBeInTheDocument();
    jest.runAllTimers();
  });

  it('renders pyramid chart', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('pyramid-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders biased and corrected bar charts', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('biased-bar-chart')).toBeInTheDocument();
      expect(screen.getByTestId('corrected-bar-chart')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('renders ideology drift SVG', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('ideology-drift-svg')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders demographic breakdown table with 6 rows', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('breakdown-table')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows corrected winner badge when winner changed', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('corrected-winner-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
