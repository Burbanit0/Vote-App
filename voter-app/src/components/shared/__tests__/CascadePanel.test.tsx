import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import CascadePanel from '../CascadePanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

jest.mock('recharts', () => {
  const React = require('react');
  return {
    LineChart:           ({ children }: any) => <div data-testid="cascade-line-chart">{children}</div>,
    Line:                ({ name }: any) => <div data-testid={`line-${name ?? 'unknown'}`} />,
    XAxis:               () => null,
    YAxis:               () => null,
    CartesianGrid:       () => null,
    Tooltip:             () => null,
    Legend:              () => null,
    ReferenceLine:       () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 200 }}>{children}</div>,
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeSequence(n: number, cascadeAt: number | null) {
  return Array.from({ length: n }, (_, i) => {
    const sincere = i % 2 === 0 ? 'Alice' : 'Bob';
    const cascading = cascadeAt != null && i >= cascadeAt;
    const actual = cascading ? 'Carol' : sincere;
    return {
      voter_id:        i,
      sincere_choice:  sincere,
      actual_vote:     actual,
      followed_cascade: cascading && actual !== sincere,
    };
  });
}

function makeData(cascadeOccurred = false) {
  const seq = makeSequence(30, cascadeOccurred ? 10 : null);
  return {
    data: {
      sincere_winner:  'Alice',
      cascade_winner:  cascadeOccurred ? 'Carol' : 'Alice',
      cascade_occurred: cascadeOccurred,
      vote_sequence:   seq,
      cascade_start_at: cascadeOccurred ? 10 : null,
      cascade_strength_curve: Array.from({ length: 11 }, (_, i) => ({
        strength:     i / 10,
        winner:       i > 5 ? 'Carol' : 'Alice',
        cascade_rate: i * 0.08,
      })),
      comparison_runs: [
        { strength: 0.0, winner: 'Alice', cascade_rate: 0.0 },
        { strength: 0.5, winner: 'Alice', cascade_rate: 0.2 },
        { strength: 1.0, winner: 'Carol', cascade_rate: 0.7 },
      ],
      candidates: ['Alice', 'Bob', 'Carol'],
    },
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <CascadePanel />
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

describe('CascadePanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows cascade strength slider', () => {
    renderPanel();
    expect(screen.getByTestId('cascade-strength-slider')).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls axios.post on simulate click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringContaining('/api/election/cascade'),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('renders timeline SVG after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('cascade-timeline-svg')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows cascade-occurred badge when cascade changed winner', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('cascade-occurred-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows cascade winner badge red when cascade occurred', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const badge = screen.getByTestId('cascade-winner-badge');
      expect(badge.className).toContain('bg-danger');
    });
    jest.runAllTimers();
  });

  it('shows cascade winner badge green when no cascade', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const badge = screen.getByTestId('cascade-winner-badge');
      expect(badge.className).toContain('bg-success');
    });
    jest.runAllTimers();
  });

  it('shows cascade start badge when cascade_start_at is set', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('cascade-start-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders comparison badges for 0, 0.5, 1.0', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('comparison-badges')).toBeInTheDocument());
    await waitFor(() => {
      expect(screen.getByTestId('comparison-badge-0.0')).toBeInTheDocument();
      expect(screen.getByTestId('comparison-badge-0.5')).toBeInTheDocument();
      expect(screen.getByTestId('comparison-badge-1.0')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('renders strength curve chart', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('cascade-curve-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows cascade start line on SVG when cascade occurred', async () => {
    mockPost.mockResolvedValue(makeData(true));
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const line = container.querySelector('[data-testid="cascade-start-line"]');
      expect(line).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows follower rings for cascade-following voters', async () => {
    mockPost.mockResolvedValue(makeData(true));
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const rings = container.querySelectorAll('[data-testid="cascade-follower-ring"]');
      expect(rings.length).toBeGreaterThan(0);
    });
    jest.runAllTimers();
  });

  it('shows play button after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('play-button')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('slider triggers debounced API call', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('cascade-strength-slider'), { target: { value: '0.8' } });
    act(() => { jest.advanceTimersByTime(450); });
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(2));
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
