import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import JuryTheoremPanel from '../JuryTheoremPanel';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../../api/client')) as unknown as { apiClient: { POST: jest.Mock } };

vi.mock('recharts', () => {
  const React = require('react');
  return {
    LineChart:           ({ children }: any) => <div data-testid="line-chart">{children}</div>,
    Line:                ({ dataKey, name }: any) => <div data-testid={`line-${dataKey ?? name}`} />,
    BarChart:            ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
    Bar:                 ({ children }: any) => <div>{children}</div>,
    Cell:                () => null,
    XAxis:               () => null,
    YAxis:               () => null,
    Tooltip:             () => null,
    Legend:              () => null,
    ReferenceLine:       () => null,
    CartesianGrid:       () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 300 }}>{children}</div>,
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(bestMethod = 'schulze'): { data: any; error: undefined } {
  const methods = {
    plurality: { accuracy: 0.85, beats_majority: true,  beats_theory: false },
    borda:     { accuracy: 0.88, beats_majority: true,  beats_theory: false },
    irv:       { accuracy: 0.87, beats_majority: true,  beats_theory: false },
    approval:  { accuracy: 0.89, beats_majority: true,  beats_theory: false },
    schulze:   { accuracy: 0.92, beats_majority: true,  beats_theory: true  },
  };

  const curvePoints = Array.from({ length: 20 }, (_, i) => ({
    competence:  0.51 + i * (0.48 / 19),
    theoretical: 0.51 + i * 0.02,
    plurality:   0.52 + i * 0.02,
    borda:       0.53 + i * 0.02,
    irv:         0.52 + i * 0.02,
    approval:    0.53 + i * 0.02,
    schulze:     0.54 + i * 0.02,
  }));

  return {
    data: {
      theoretical_accuracy: 0.89,
      methods,
      best_method:          bestMethod,
      worst_method:         'plurality',
      voter_competence:     0.70,
      num_voters:           100,
      competence_curve:     curvePoints,
      pedagogical_note:     'Avec P=0.7 et 100 électeurs, la théorie prédit 89%. Schulze atteint 92%.',
      pedagogical_note_en:  'With P=0.7 and 100 voters, theory predicts 89%. Schulze reaches 92%.',
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <JuryTheoremPanel />
      </QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('JuryTheoremPanel', () => {
  it('renders simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows competence slider', () => {
    renderPanel();
    expect(screen.getByTestId('competence-slider')).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls API on button click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/jury/),
      expect.objectContaining({ body: expect.objectContaining({ voter_competence: 0.70 }) }),
    );
  });

  it('renders competence curve LineChart after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('competence-curve-chart')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('renders accuracy BarChart after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('accuracy-bar-chart')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows theory accuracy badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('theory-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows best method badge', async () => {
    apiClient.POST.mockResolvedValue(makeData('schulze'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const badge = screen.getByTestId('best-method-badge');
      expect(badge.textContent).toContain('schulze');
    });
    vi.runAllTimers();
  });

  it('shows method-level badges', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('method-badge-plurality')).toBeInTheDocument();
      expect(screen.getByTestId('method-badge-schulze')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('shows pedagogical note', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('pedagogical-note')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('competence slider triggers debounced API call', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();

    // Initial data load first
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));

    // Slider change → debounce → API call after DEBOUNCE_MS
    fireEvent.change(screen.getByTestId('competence-slider'), { target: { value: '0.8' } });
    // Before debounce fires: no extra call yet
    expect(apiClient.POST).toHaveBeenCalledTimes(1);

    // Advance fake timers past debounce
    act(() => { vi.advanceTimersByTime(450); });
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(2));
    expect((apiClient.POST.mock.calls[1][1] as { body: Record<string, unknown> }).body).toMatchObject({ voter_competence: 0.8 });
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
