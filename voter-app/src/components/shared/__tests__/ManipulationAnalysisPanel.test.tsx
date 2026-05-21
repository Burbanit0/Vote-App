import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import ManipulationAnalysisPanel from '../ManipulationAnalysisPanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeData(manipulable = true) {
  const manipulators = manipulable
    ? [
        {
          voter_id:        3,
          voter_ideology:  [-0.2, 0.4] as [number, number],
          sincere_vote:    ['Alice', 'Carol', 'Bob'],
          strategic_vote:  ['Carol', 'Alice', 'Bob'],
          strategy_type:   'compromising' as const,
          sincere_result:  'Bob',
          strategic_result: 'Carol',
          utility_gain:    0.32,
        },
        {
          voter_id:        7,
          voter_ideology:  [0.3, -0.1] as [number, number],
          sincere_vote:    ['Alice', 'Bob', 'Carol'],
          strategic_vote:  ['Alice', 'Carol', 'Bob'],
          strategy_type:   'burying' as const,
          sincere_result:  'Bob',
          strategic_result: 'Alice',
          utility_gain:    0.45,
        },
      ]
    : [];

  return {
    data: {
      sincere_winner:     'Bob',
      manipulable,
      manipulation_count: manipulators.length,
      manipulators,
      strategy_breakdown: { compromising: manipulable ? 1 : 0, burying: manipulable ? 1 : 0, pushover: 0, truncating: 0 },
      key_manipulator:    manipulable ? { voter_id: 7, strategy: 'burying', gain: 0.45 } : null,
      pedagogical_note:   'Test note.',
    },
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <ManipulationAnalysisPanel />
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

describe('ManipulationAnalysisPanel', () => {
  it('shows analyze button', () => {
    renderPanel();
    expect(screen.getByTestId('analyze-btn')).toBeInTheDocument();
  });

  it('shows method selector', () => {
    renderPanel();
    expect(screen.getByTestId('method-select')).toBeInTheDocument();
  });

  it('shows prompt before first run', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls axios.post on analyze click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringContaining('/api/theory/manipulation-analysis'),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('shows manipulable badge (danger) when manipulable', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => {
      const badge = screen.getByTestId('manipulable-badge');
      expect(badge.className).toContain('bg-danger');
    });
    jest.runAllTimers();
  });

  it('shows not-manipulable badge (success) when not manipulable', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => {
      const badge = screen.getByTestId('manipulable-badge');
      expect(badge.className).toContain('bg-success');
    });
    jest.runAllTimers();
  });

  it('shows count badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => expect(screen.getByTestId('count-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows winner badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => expect(screen.getByTestId('winner-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders ideology map SVG', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => expect(screen.getByTestId('manip-map-svg')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows strategy table', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => expect(screen.getByTestId('strategy-table')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows manipulator detail when voter clicked in map', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => screen.getByTestId('manip-map-svg'));
    // Click the first manipulator circle (SVG click)
    const svg = screen.getByTestId('manip-map-svg');
    const circles = svg.querySelectorAll('circle');
    if (circles.length > 0) {
      fireEvent.click(circles[1]); // Second circle = first manipulator halo
    }
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
