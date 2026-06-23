import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import PartyDynamicsPanel from '../PartyDynamicsPanel';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../../api/client')) as unknown as {
  apiClient: { POST: jest.Mock };
};

vi.mock('recharts', () => {
  const React = require('react');
  return {
    LineChart: ({ children }: any) => <div>{children}</div>,
    Line: ({ dataKey }: any) => <div data-testid={`line-${dataKey}`} />,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Legend: () => null,
    ReferenceLine: () => null,
    ResponsiveContainer: ({ children }: any) => (
      <div style={{ width: 400, height: 180 }}>{children}</div>
    ),
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(duverger = false) {
  const mkElection = (n: number, parties: string[], nEff: number) => ({
    election_n: n,
    active_parties: parties.length,
    parties: parties.map((name, i) => ({
      name,
      x: -0.8 + i * 0.4,
      y: 0,
      vote_pct: 100 / parties.length,
      seats: 100 / parties.length,
      survived: true,
    })),
    effective_parties: nEff,
    winner: parties[0],
    new_entrants: [],
    eliminated: n === 3 && duverger ? ['E'] : [],
  });

  const elections = [
    mkElection(1, ['A', 'B', 'C', 'D', 'E'], 5.0),
    mkElection(2, ['A', 'B', 'C', 'D', 'E'], 4.5),
    mkElection(
      3,
      duverger ? ['A', 'B', 'C', 'D'] : ['A', 'B', 'C', 'D', 'E'],
      duverger ? 3.2 : 4.8
    ),
  ];

  return {
    data: {
      elections,
      final_system: duverger ? 'tripartite' : 'fragmented',
      effective_parties_curve: elections.map((e) => e.effective_parties),
      duverger_confirmed: duverger,
      convergence_speed: duverger ? null : null,
      ideology_drift: [
        { party: 'A', initial_x: -0.8, final_x: -0.7 },
        { party: 'B', initial_x: -0.3, final_x: -0.2 },
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
        <PartyDynamicsPanel />
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

describe('PartyDynamicsPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByTestId('simulate-btn')).toBeInTheDocument();
  });

  it('shows preset selector', () => {
    renderPanel();
    expect(screen.getByTestId('preset-select')).toBeInTheDocument();
  });

  it('shows method selector', () => {
    renderPanel();
    expect(screen.getByTestId('method-select')).toBeInTheDocument();
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
      expect.stringMatching(/\/api\/(v2\/)?election\/party-dynamics/),
      expect.any(Object)
    );
    vi.runAllTimers();
  });

  it('renders ideology map SVG after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('ideology-map-svg')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('renders N_eff chart', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('n-eff-chart')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows final-system badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('final-system-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows duverger-confirmed badge', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('duverger-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows play button after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('play-btn')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows election slider after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('election-slider')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('advances election index when election slider changes', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => screen.getByTestId('election-slider'));
    fireEvent.change(screen.getByTestId('election-slider'), { target: { value: '2' } });
    expect(screen.getByTestId('election-slider')).toHaveValue('2');
    vi.runAllTimers();
  });

  it('tactical switch toggles correctly', () => {
    renderPanel();
    const sw = screen.getByTestId('tactical-switch');
    expect(sw).toBeChecked();
    fireEvent.click(sw);
    expect(sw).not.toBeChecked();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
