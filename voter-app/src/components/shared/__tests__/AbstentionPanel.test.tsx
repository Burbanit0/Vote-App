import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import AbstentionPanel from '../AbstentionPanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

jest.mock('recharts', () => {
  const React = require('react');
  return {
    LineChart:           ({ children }: any) => <div data-testid="line-chart">{children}</div>,
    Line:                ({ name }: any) => <div data-testid={`line-${name ?? 'unknown'}`} />,
    XAxis:               () => null,
    YAxis:               () => null,
    Tooltip:             () => null,
    Legend:              () => null,
    ReferenceLine:       () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 200 }}>{children}</div>,
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeRound(rnd: number, turnout: number, hasAbstained = false) {
  const abstentionMap = [
    { id: 0, x: -0.3, y: 0.1, preferred: 'Alice', abstained: hasAbstained && rnd > 0, prob_abstention: hasAbstained ? 0.35 : 0 },
    { id: 1, x:  0.4, y: -0.1, preferred: 'Bob',   abstained: false,                  prob_abstention: 0.05 },
    { id: 2, x:  0.0, y:  0.3, preferred: 'Carol',  abstained: false,                  prob_abstention: 0.10 },
  ];
  return {
    round:            rnd,
    turnout,
    vote_shares:      { Alice: 0.45, Bob: 0.35, Carol: 0.20 },
    winner_fptp:      'Alice',
    winner_condorcet: 'Alice',
    abstention_map:   abstentionMap,
  };
}

function makeData(winnerChanged = false) {
  return {
    data: {
      rounds: [
        makeRound(0, 1.0, false),
        makeRound(1, 0.85, true),
        makeRound(2, 0.72, true),
        makeRound(3, 0.65, true),
      ],
      sincere_winner:  'Alice',
      final_winner:    winnerChanged ? 'Bob' : 'Alice',
      winner_changed:  winnerChanged,
      turnout_by_camp: { Alice: 0.65, Bob: 0.90, Carol: 0.80 },
      candidates:      [{ name: 'Alice' }, { name: 'Bob' }, { name: 'Carol' }],
    },
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <AbstentionPanel />
      </ElectionProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  jest.useFakeTimers();
});

afterEach(() => {
  jest.useRealTimers();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('AbstentionPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('shows demob and influence sliders', () => {
    renderPanel();
    expect(screen.getByTestId('demob-slider')).toBeInTheDocument();
    expect(screen.getByTestId('influence-slider')).toBeInTheDocument();
  });

  it('calls axios.post on button click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    // Accept either /api/election/abstention (Flask v1) or
    // /api/v2/election/abstention (FastAPI v2 — default since Phase 3 batch 2).
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/abstention/),
      expect.any(Object),
    );
  });

  it('renders ideology map SVG after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('abstention-map-svg')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders abstained voters as grey dots', async () => {
    mockPost.mockResolvedValue(makeData());
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('abstention-map-svg')).toBeInTheDocument());
    // Advance to round 1 where there are abstained voters
    fireEvent.change(screen.getByTestId('round-slider'), { target: { value: '1' } });
    act(() => { jest.runAllTimers(); });
    const abstainedDots = container.querySelectorAll('[data-testid="abstained-voter"]');
    expect(abstainedDots.length).toBeGreaterThan(0);
    jest.runAllTimers();
  });

  it('shows green comparison band when winner unchanged', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const band = screen.getByTestId('winner-comparison-band');
      expect(band).toBeInTheDocument();
      // jsdom converts hex to rgb() — check green hue
      expect(band.style.background).toMatch(/f0fff4|rgb\(240,\s*255,\s*244\)/);
    });
    jest.runAllTimers();
  });

  it('shows red comparison band when winner changed', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const band = screen.getByTestId('winner-comparison-band');
      expect(band.style.background).toMatch(/fff3f3|rgb\(255,\s*243,\s*243\)/);
    });
    jest.runAllTimers();
  });

  it('renders turnout line chart', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('turnout-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows camp turnout badges', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('camp-turnout-Alice')).toBeInTheDocument();
      expect(screen.getByTestId('camp-turnout-Bob')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows play/pause button', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('play-button')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
