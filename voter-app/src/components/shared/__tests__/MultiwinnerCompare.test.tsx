import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import MultiwinnerCompare from '../MultiwinnerCompare';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

// ── Fixture ───────────────────────────────────────────────────────────────────

const NAMES = ['Alice', 'Bob', 'Carol', 'Dave'];

function makeData() {
  const makeMethod = (seats: Record<string, number>, distortion: number) => ({
    seats,
    elected:  Object.entries(seats).filter(([, s]) => s > 0).map(([c]) => c),
    distortion,
    seat_vs_votes: Object.fromEntries(NAMES.map(n => [n, {
      seats: seats[n] ?? 0,
      seat_pct: (seats[n] ?? 0) / 4,
      vote_pct: 0.25,
      delta: (seats[n] ?? 0) / 4 - 0.25,
    }])),
  });
  return {
    data: {
      candidates:             NAMES,
      num_seats:              4,
      vote_shares:            { Alice: 0.40, Bob: 0.30, Carol: 0.20, Dave: 0.10 },
      proportional_reference: { Alice: 2, Bob: 1, Carol: 1, Dave: 0 },
      best_method:  'spav',
      worst_method: 'fptp',
      methods: {
        stv:      makeMethod({ Alice: 2, Bob: 1, Carol: 1, Dave: 0 }, 0.04),
        dhondt:   makeMethod({ Alice: 2, Bob: 2, Carol: 0, Dave: 0 }, 0.10),
        spav:     makeMethod({ Alice: 2, Bob: 1, Carol: 1, Dave: 0 }, 0.04),
        phragmen: makeMethod({ Alice: 2, Bob: 1, Carol: 1, Dave: 0 }, 0.04),
        fptp:     makeMethod({ Alice: 4, Bob: 0, Carol: 0, Dave: 0 }, 0.30),
      },
    },
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <MultiwinnerCompare />
      </ElectionProvider>
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

describe('MultiwinnerCompare', () => {
  it('shows compare button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /comparer|compare/i })).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls axios.post on compare click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/multiwinner_compare/),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('renders 5 hémicycles after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => {
      const svgs = container.querySelectorAll('svg');
      expect(svgs.length).toBeGreaterThanOrEqual(5);
    });
    jest.runAllTimers();
  });

  it('shows distortion badges for each method', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => {
      expect(screen.getByTestId('distortion-badge-STV')).toBeInTheDocument();
      expect(screen.getByTestId('distortion-badge-FPTP')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows pedagogical note', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => {
      expect(screen.getByTestId('multiwinner-pedagogical')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('comparison table shows all 5 methods', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => {
      expect(screen.getAllByText('STV').length).toBeGreaterThan(0);
      expect(screen.getAllByText("D'Hondt").length).toBeGreaterThan(0);
      expect(screen.getAllByText('SPAV').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Phragmén').length).toBeGreaterThan(0);
      expect(screen.getAllByText('FPTP').length).toBeGreaterThan(0);
    });
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });

  it('best method badge is visible', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => {
      const bestBadge = screen.getAllByText(/proportionnel|PR/i);
      expect(bestBadge.length).toBeGreaterThan(0);
    });
    jest.runAllTimers();
  });
});
