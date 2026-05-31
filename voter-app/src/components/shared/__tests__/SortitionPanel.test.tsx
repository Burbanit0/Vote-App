import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import SortitionPanel from '../SortitionPanel';
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
    RadarChart:       ({ children }: any) => <div>{children}</div>,
    Radar:            () => null,
    PolarGrid:        () => null,
    PolarAngleAxis:   () => null,
    LineChart:        ({ children }: any) => <div>{children}</div>,
    Line:             () => null,
    XAxis:            () => null,
    YAxis:            () => null,
    CartesianGrid:    () => null,
    Tooltip:          () => null,
    Legend:           () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 280 }}>{children}</div>,
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(consensus = false) {
  const mkAsm = (mean: number, rep: number) => ({
    members_ideology_mean: mean,
    representativity:      rep,
    diversity:             0.8,
    decision_regret:       0.2,
    gini_representation:   0.15,
    demographic_profile:   { age: 1.0, education: 0.6 },
  });

  return {
    data: {
      population: {
        mean_ideology: 0.02,
        gini_ideology: 0.58,
        demographics:  { mean_age_group: 1.0, mean_education_level: 0.6 },
      },
      assemblies: {
        elected:             mkAsm(0.22, 0.56),
        sortition_pure:      mkAsm(0.03, 0.94),
        sortition_stratified: mkAsm(0.02, 0.96),
      },
      variance: { elected: 0.012, sortition_pure: 0.004, sortition_stratified: 0.001 },
      winner_by_method: {
        elected:              'Bob',
        sortition_pure:       consensus ? 'Alice' : 'Alice',
        sortition_stratified: 'Alice',
      },
      consensus_possible: consensus,
      pedagogical_note:   'Test note.',
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <SortitionPanel />
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

describe('SortitionPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByTestId('simulate-btn')).toBeInTheDocument();
  });

  it('shows assembly size slider', () => {
    renderPanel();
    expect(screen.getByTestId('assembly-size-slider')).toBeInTheDocument();
  });

  it('shows realistic candidates switch', () => {
    renderPanel();
    expect(screen.getByTestId('realistic-switch')).toBeInTheDocument();
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
      expect.stringMatching(/\/api\/(v2\/)?election\/sortition/),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('shows ideology bars after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('ideology-bars')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders radar chart', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('radar-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders metrics table', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('metrics-table')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows historical examples section', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('examples-section')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows consensus badge when consensus=true', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('consensus-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows no-consensus badge when consensus=false', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('no-consensus-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('debounced re-simulation on slider change', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('assembly-size-slider'), { target: { value: '100' } });
    act(() => { jest.advanceTimersByTime(450); });
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(2));
    jest.runAllTimers();
  });

  it('debounced re-simulation on switch toggle after first run', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByTestId('realistic-switch'));
    act(() => { jest.advanceTimersByTime(450); });
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(2));
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
