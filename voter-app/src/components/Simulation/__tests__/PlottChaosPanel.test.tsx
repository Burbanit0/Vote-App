import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import PlottChaosPanel from '../PlottChaosPanel';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../../api/client')) as unknown as {
  apiClient: { POST: jest.Mock };
};

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(condorcet = false) {
  const steps = [
    [-0.6, -0.6],
    [-0.1, 0.3],
    [0.6, 0.6],
  ];
  const altSteps = [
    [-0.6, -0.6],
    [0.2, -0.4],
    [-0.6, -0.6],
  ];
  return {
    data: {
      condorcet_winner_exists: condorcet,
      top_cycle: { size: condorcet ? 1 : 72, center: condorcet ? [0.1, 0.1] : [0.0, 0.0] },
      chaos_path: {
        from: [-0.6, -0.6],
        to: [0.6, 0.6],
        steps,
        num_steps: steps.length - 1,
      },
      alternative_path: {
        to: [-0.6, -0.6],
        steps: altSteps,
      },
      voter_ideal_points: [
        [-0.5, 0.3],
        [0.4, -0.2],
        [0.1, 0.5],
        [-0.3, -0.4],
        [0.6, 0.1],
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
        <PlottChaosPanel />
      </QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

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

  it('calls API on simulate click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?theory\/plott-chaos/),
      expect.any(Object)
    );
    vi.runAllTimers();
  });

  it('renders chaos map SVG after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('chaos-map-svg')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows no-condorcet badge for chaos scenario', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('condorcet-badge')).toBeInTheDocument());
    const badge = screen.getByTestId('condorcet-badge');
    expect(badge.className).toContain('bg-[#dc3545]');
    vi.runAllTimers();
  });

  it('shows condorcet badge green when winner exists', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      const badge = screen.getByTestId('condorcet-badge');
      expect(badge.className).toContain('bg-[#198754]');
    });
    vi.runAllTimers();
  });

  it('shows top-cycle badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('top-cycle-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows path-steps badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('path-steps-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows play button after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('play-btn')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows show-alt-btn', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('show-alt-btn')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
