import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import PlottChaosPanel from '../PlottChaosPanel';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(condorcet = false) {
  const steps = [[-0.6, -0.6], [-0.1, 0.3], [0.6, 0.6]];
  const altSteps = [[-0.6, -0.6], [0.2, -0.4], [-0.6, -0.6]];
  return {
    data: {
      condorcet_winner_exists: condorcet,
      top_cycle: { size: condorcet ? 1 : 72, center: condorcet ? [0.1, 0.1] : [0.0, 0.0] },
      chaos_path: {
        from:      [-0.6, -0.6],
        to:        [0.6, 0.6],
        steps,
        num_steps: steps.length - 1,
      },
      alternative_path: {
        to:    [-0.6, -0.6],
        steps: altSteps,
      },
      voter_ideal_points: [
        [-0.5, 0.3], [0.4, -0.2], [0.1, 0.5], [-0.3, -0.4], [0.6, 0.1],
      ],
      pedagogical_note: 'Test note.',
    },
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <PlottChaosPanel />
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  jest.useFakeTimers();
});

afterEach(() => { jest.useRealTimers(); });

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('PlottChaosPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByTestId('simulate-btn')).toBeInTheDocument();
  });

  it('shows voters slider', () => {
    renderPanel();
    expect(screen.getByTestId('voters-slider')).toBeInTheDocument();
  });

  it('shows seed input', () => {
    renderPanel();
    expect(screen.getByTestId('seed-input')).toBeInTheDocument();
  });

  it('shows prompt before first run', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls axios.post on simulate click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringContaining('/api/theory/plott-chaos'),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('renders chaos map SVG after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('chaos-map-svg')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows no-condorcet badge for chaos scenario', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('condorcet-badge')).toBeInTheDocument());
    const badge = screen.getByTestId('condorcet-badge');
    expect(badge.className).toContain('bg-danger');
    jest.runAllTimers();
  });

  it('shows condorcet badge green when winner exists', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      const badge = screen.getByTestId('condorcet-badge');
      expect(badge.className).toContain('bg-success');
    });
    jest.runAllTimers();
  });

  it('shows top-cycle badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('top-cycle-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows path-steps badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('path-steps-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows play button after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('play-btn')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows show-alt-btn', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('show-alt-btn')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
