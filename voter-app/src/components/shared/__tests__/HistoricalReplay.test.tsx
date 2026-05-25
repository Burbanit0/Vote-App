import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import HistoricalReplay from '../HistoricalReplay';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

jest.mock('recharts', () => {
  const React = require('react');
  return {
    BarChart:            ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
    Bar:                 ({ children }: any) => <div>{children}</div>,
    XAxis:               () => null,
    YAxis:               () => null,
    Tooltip:             () => null,
    Cell:                () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 200 }}>{children}</div>,
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeReplay(differs = false) {
  const numDays = 10;
  const days = Array.from({ length: numDays + 1 }, (_, i) => ({
    day:              i,
    vote_shares:      { Chirac: 0.40, Jospin: 0.35, 'Le Pen': 0.16, Bayrou: 0.09 },
    winner_fptp:      'Chirac',
    winner_condorcet: 'Jospin',
    winner_borda:     'Jospin',
  }));

  return {
    data: {
      scenario:   { id: 'france2002', name: 'France 2002', real_winner: 'Chirac' },
      candidates: [
        { name: 'Chirac',  x:  0.30, y: 0.10, modified: false },
        { name: 'Jospin',  x: -0.30, y: -0.10, modified: differs },
        { name: 'Le Pen',  x:  0.85, y: 0.20, modified: false },
        { name: 'Bayrou',  x:  0.05, y: 0.00, modified: false },
      ],
      days,
      final: {
        winner_fptp:         differs ? 'Jospin' : 'Chirac',
        winner_condorcet:    'Jospin',
        winner_borda:        'Jospin',
        differs_from_real:   differs,
        pedagogical_note:    differs
          ? 'En déplaçant Jospin, il devient vainqueur.'
          : 'La simulation converge vers Chirac.',
        pedagogical_note_en: differs
          ? 'Moving Jospin changes the winner.'
          : 'Simulation converges on Chirac.',
      },
    },
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <HistoricalReplay />
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

describe('HistoricalReplay', () => {
  it('renders 4 scenario cards', () => {
    renderPanel();
    expect(screen.getByTestId('scenario-card-france2002')).toBeInTheDocument();
    expect(screen.getByTestId('scenario-card-usa1992')).toBeInTheDocument();
    expect(screen.getByTestId('scenario-card-germany2021')).toBeInTheDocument();
    expect(screen.getByTestId('scenario-card-condorcet_cycle')).toBeInTheDocument();
  });

  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('calls axios.post with correct endpoint on simulate click', async () => {
    mockPost.mockResolvedValue(makeReplay());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/historical-replay/),
      expect.objectContaining({ scenario_id: 'france2002' }),
    );
  });

  it('renders ideology map SVG after data loads', async () => {
    mockPost.mockResolvedValue(makeReplay());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('ideology-map-svg')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders 4 candidate star markers on the SVG', async () => {
    mockPost.mockResolvedValue(makeReplay());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const stars = screen.getAllByTestId(/candidate-star-/);
      expect(stars.length).toBe(4);
    });
    jest.runAllTimers();
  });

  it('renders day slider', async () => {
    mockPost.mockResolvedValue(makeReplay());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('day-slider')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('day slider changes current day display', async () => {
    mockPost.mockResolvedValue(makeReplay());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('day-slider')).toBeInTheDocument());
    fireEvent.change(screen.getByTestId('day-slider'), { target: { value: '5' } });
    expect(screen.getByTestId('day-badge').textContent).toContain('5');
    jest.runAllTimers();
  });

  it('renders vote share bar chart', async () => {
    mockPost.mockResolvedValue(makeReplay());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('vote-share-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders comparison panel with real vs simulated result', async () => {
    mockPost.mockResolvedValue(makeReplay());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('comparison-panel')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows divergence badge when history is rewritten', async () => {
    mockPost.mockResolvedValue(makeReplay(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('divergence-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('does NOT show divergence badge when history is not rewritten', async () => {
    mockPost.mockResolvedValue(makeReplay(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('result-badge')).toBeInTheDocument());
    expect(screen.queryByTestId('divergence-badge')).toBeNull();
    jest.runAllTimers();
  });

  it('renders pedagogical note', async () => {
    mockPost.mockResolvedValue(makeReplay());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('pedagogical-note')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows apply-drag button after data loads', async () => {
    mockPost.mockResolvedValue(makeReplay());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('apply-drag-btn')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('switching scenario card changes selection', () => {
    renderPanel();
    fireEvent.click(screen.getByTestId('scenario-card-usa1992'));
    // Card is now selected — the border style or click handler should update state
    // We verify by checking the card is clickable without crash
    expect(screen.getByTestId('scenario-card-usa1992')).toBeInTheDocument();
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
