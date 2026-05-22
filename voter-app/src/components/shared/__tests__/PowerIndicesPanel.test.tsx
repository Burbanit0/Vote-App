import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import axios from 'axios';
import PowerIndicesPanel from '../PowerIndicesPanel';

jest.mock('axios');
const mockAxios = axios as jest.Mocked<typeof axios>;

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
    ScatterChart: stub, Scatter: stub, XAxis: stub, YAxis: stub,
    CartesianGrid: stub, Tooltip: stub, ReferenceLine: stub,
    Cell: stub,
    ResponsiveContainer: ({ children }: { children?: React.ReactNode }) =>
      React.createElement('div', null, children),
  };
});

const MOCK_DATA = {
  total_seats: 100,
  majority_threshold: 51,
  parties: [
    { name: 'A', seats: 40, seat_pct: 0.40, shapley_index: 0.50, banzhaf_index: 0.50, power_ratio: 1.25, critical_count: 2, pivot_count: 4, is_pariah: false },
    { name: 'B', seats: 35, seat_pct: 0.35, shapley_index: 0.333, banzhaf_index: 0.333, power_ratio: 0.95, critical_count: 2, pivot_count: 2, is_pariah: false },
    { name: 'C', seats: 25, seat_pct: 0.25, shapley_index: 0.167, banzhaf_index: 0.167, power_ratio: 0.67, critical_count: 1, pivot_count: 1, is_pariah: false },
  ],
  viable_coalitions: [
    { parties: ['A', 'B'], seats: 75, minimal: true },
    { parties: ['A', 'C'], seats: 65, minimal: true },
    { parties: ['B', 'C'], seats: 60, minimal: false },
    { parties: ['A', 'B', 'C'], seats: 100, minimal: false },
  ],
  power_surprises: [] as string[],
  pedagogical_note: 'Test pedagogical note.',
};

const PARIAH_DATA = {
  ...MOCK_DATA,
  parties: [
    ...MOCK_DATA.parties.slice(0, 2),
    { name: 'P', seats: 30, seat_pct: 0.30, shapley_index: 0.0, banzhaf_index: 0.0, power_ratio: 0.0, critical_count: 0, pivot_count: 0, is_pariah: true },
  ],
  power_surprises: ['P : 30 sièges mais pouvoir=0 (paria)'],
};

async function renderAndRun(responseData = MOCK_DATA) {
  mockAxios.post.mockResolvedValueOnce({ data: responseData });
  render(<PowerIndicesPanel />);
  await act(async () => { fireEvent.click(screen.getByTestId('run-btn')); });
  await waitFor(() => expect(mockAxios.post).toHaveBeenCalledTimes(1));
  await act(async () => {});
}

describe('PowerIndicesPanel', () => {
  beforeEach(() => jest.clearAllMocks());

  // ── Initial render ──────────────────────────────────────────────────────────

  it('renders preset buttons', () => {
    render(<PowerIndicesPanel />);
    expect(screen.getByTestId('preset-france2022')).toBeInTheDocument();
    expect(screen.getByTestId('preset-germany2021')).toBeInTheDocument();
    expect(screen.getByTestId('preset-pivot_paradox')).toBeInTheDocument();
  });

  it('renders party editor with default parties', () => {
    render(<PowerIndicesPanel />);
    expect(screen.getByTestId('party-editor')).toBeInTheDocument();
    expect(screen.getByTestId('party-name-0')).toBeInTheDocument();
    expect(screen.getByTestId('party-seats-0')).toBeInTheDocument();
  });

  it('renders run button and threshold input', () => {
    render(<PowerIndicesPanel />);
    expect(screen.getByTestId('run-btn')).toBeInTheDocument();
    expect(screen.getByTestId('threshold-input')).toBeInTheDocument();
  });

  it('shows prompt alert before calculation', () => {
    render(<PowerIndicesPanel />);
    expect(screen.getByTestId('prompt-alert')).toBeInTheDocument();
  });

  it('shows shapley and banzhaf checkboxes', () => {
    render(<PowerIndicesPanel />);
    expect(screen.getByTestId('cb-shapley')).toBeInTheDocument();
    expect(screen.getByTestId('cb-banzhaf')).toBeInTheDocument();
  });

  // ── Preset loading ──────────────────────────────────────────────────────────

  it('loads france2022 preset and populates parties', () => {
    render(<PowerIndicesPanel />);
    fireEvent.click(screen.getByTestId('preset-france2022'));
    // After preset, party names should update (multiple name inputs)
    const nameInputs = screen.getAllByTestId(/^party-name-/);
    expect(nameInputs.length).toBeGreaterThanOrEqual(4);
  });

  it('adds a party when add button clicked', () => {
    render(<PowerIndicesPanel />);
    const before = screen.getAllByTestId(/^party-name-/).length;
    fireEvent.click(screen.getByTestId('add-party-btn'));
    const after = screen.getAllByTestId(/^party-name-/).length;
    expect(after).toBe(before + 1);
  });

  // ── After calculation ───────────────────────────────────────────────────────

  it('calls API with correct payload on run', async () => {
    await renderAndRun();
    const [url, payload] = mockAxios.post.mock.calls[0];
    expect(url).toContain('/api/election/power-indices');
    expect(payload).toHaveProperty('parties');
    expect(payload).toHaveProperty('majority_threshold');
    expect(payload).toHaveProperty('calculate_shapley', true);
    expect(payload).toHaveProperty('calculate_banzhaf', true);
  });

  it('shows view switcher buttons after calculation', async () => {
    await renderAndRun();
    expect(screen.getByTestId('view-btn-scatter')).toBeInTheDocument();
    expect(screen.getByTestId('view-btn-hemi')).toBeInTheDocument();
    expect(screen.getByTestId('view-btn-coalitions')).toBeInTheDocument();
  });

  it('renders scatter view by default', async () => {
    await renderAndRun();
    expect(screen.getByTestId('scatter-view')).toBeInTheDocument();
  });

  it('switches to hemicycle view', async () => {
    await renderAndRun();
    fireEvent.click(screen.getByTestId('view-btn-hemi'));
    expect(screen.getByTestId('hemi-view')).toBeInTheDocument();
    expect(screen.getByTestId('power-hemicycle')).toBeInTheDocument();
    expect(screen.queryByTestId('scatter-view')).not.toBeInTheDocument();
  });

  it('switches to coalitions view and shows coalition rows', async () => {
    await renderAndRun();
    fireEvent.click(screen.getByTestId('view-btn-coalitions'));
    expect(screen.getByTestId('coalitions-view')).toBeInTheDocument();
    expect(screen.getByTestId('coalition-row-0')).toBeInTheDocument();
  });

  it('renders power table with party rows', async () => {
    await renderAndRun();
    expect(screen.getByTestId('power-table')).toBeInTheDocument();
    expect(screen.getByTestId('table-row-A')).toBeInTheDocument();
    expect(screen.getByTestId('table-row-B')).toBeInTheDocument();
    expect(screen.getByTestId('table-row-C')).toBeInTheDocument();
  });

  it('shows examples and pedagogical note sections', async () => {
    await renderAndRun();
    expect(screen.getByTestId('examples-section')).toBeInTheDocument();
    expect(screen.getByTestId('pedagogical-note')).toBeInTheDocument();
  });

  // ── Pariah behaviour ────────────────────────────────────────────────────────

  it('shows surprises section when power_surprises non-empty', async () => {
    await renderAndRun(PARIAH_DATA);
    expect(screen.getByTestId('surprises-section')).toBeInTheDocument();
  });

  it('does not show surprises section when power_surprises empty', async () => {
    await renderAndRun(MOCK_DATA);
    expect(screen.queryByTestId('surprises-section')).not.toBeInTheDocument();
  });

  // ── Error handling ──────────────────────────────────────────────────────────

  it('shows error alert on API failure', async () => {
    mockAxios.post.mockRejectedValueOnce(new Error('Network error'));
    render(<PowerIndicesPanel />);
    await act(async () => { fireEvent.click(screen.getByTestId('run-btn')); });
    await waitFor(() => expect(mockAxios.post).toHaveBeenCalled());
    await act(async () => {});
    expect(screen.getByTestId('error-alert')).toBeInTheDocument();
  });

  // ── Pariah toggle ───────────────────────────────────────────────────────────

  it('toggling pariah switch triggers re-calculation when data exists', async () => {
    mockAxios.post
      .mockResolvedValueOnce({ data: MOCK_DATA })
      .mockResolvedValueOnce({ data: PARIAH_DATA });

    render(<PowerIndicesPanel />);
    await act(async () => { fireEvent.click(screen.getByTestId('run-btn')); });
    await waitFor(() => expect(mockAxios.post).toHaveBeenCalledTimes(1));
    await act(async () => {});

    // Toggle pariah on first party
    fireEvent.click(screen.getByTestId('pariah-toggle-0'));
    await waitFor(() => expect(mockAxios.post).toHaveBeenCalledTimes(2));
    await act(async () => {});
  });
});
