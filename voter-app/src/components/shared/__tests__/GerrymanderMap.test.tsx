import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import GerrymanderMap from '../GerrymanderMap';
import { ElectionProvider } from '../../../stores/useElectionStore';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../../api/client')) as unknown as { apiClient: { POST: jest.Mock } };

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(gerryIndex = 0.6) {
  return {
    data: {
      districts: [
        { id: 0, num_voters: 55, winner: 'Alice', vote_shares: { Alice: 0.7, Bob: 0.3 } },
        { id: 1, num_voters: 45, winner: 'Bob',   vote_shares: { Alice: 0.2, Bob: 0.8 } },
      ],
      voters: [
        { id: 0, x: -0.3, y: 0.2, preferred: 'Alice' },
        { id: 1, x:  0.4, y: -0.1, preferred: 'Bob' },
        { id: 2, x: -0.1, y: 0.1,  preferred: 'Alice' },
      ],
      parliament_gerrymander: { Alice: 2, Bob: 0 },
      parliament_proportional:{ Alice: 1, Bob: 1 },
      national_vote_share:    { Alice: 0.55, Bob: 0.45 },
      distortion:             0.25,
      gerrymander_index:      gerryIndex,
      winner:                 'Alice',
      candidates:             ['Alice', 'Bob'],
      num_seats:              2,
    },
    error: undefined,
  };
}

function renderMap() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <GerrymanderMap />
        </ElectionProvider>
      </QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  vi.useFakeTimers();
});

afterEach(() => { vi.useRealTimers(); });

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('GerrymanderMap', () => {
  it('renders the SVG grid', () => {
    renderMap();
    expect(screen.getByTestId('gerrymander-grid')).toBeInTheDocument();
  });

  it('renders 100 grid cells (10×10)', () => {
    const { container } = renderMap();
    const cells = container.querySelectorAll('[data-testid="grid-cell"]');
    expect(cells.length).toBe(100);
  });

  it('shows simulate button', () => {
    renderMap();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderMap();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('clicking a cell cycles its district id', () => {
    const { container } = renderMap();
    const cell = container.querySelectorAll('[data-testid="grid-cell"]')[0];
    const initialDistrict = cell.getAttribute('data-district');
    fireEvent.click(cell);
    // After one click, district should be (initialDistrict + 1) % numDist
    const newDistrict = container.querySelectorAll('[data-testid="grid-cell"]')[0].getAttribute('data-district');
    expect(newDistrict).not.toBeNull();
    // District changes (wraps around mod numDist)
    expect(Number(newDistrict)).toBe((Number(initialDistrict) + 1) % 5);
  });

  it('auto-redistribute button redraws grid', () => {
    renderMap();
    const btn = screen.getByRole('button', { name: /équitable|fair/i });
    fireEvent.click(btn);
    // Grid should still have 100 cells — no crash
    expect(screen.getByTestId('gerrymander-grid')).toBeInTheDocument();
  });

  it('gerrymander optimal button works', () => {
    renderMap();
    const btn = screen.getByRole('button', { name: /optimal/i });
    fireEvent.click(btn);
    expect(screen.getByTestId('gerrymander-grid')).toBeInTheDocument();
  });

  it('calls API on simulate click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderMap();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/gerrymander/),
      expect.any(Object),
    );
    vi.runAllTimers();
  });

  it('renders voter dots after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    const { container } = renderMap();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const dots = container.querySelectorAll('[data-testid="voter-dot"]');
      expect(dots.length).toBeGreaterThan(0);
    });
    vi.runAllTimers();
  });

  it('shows two hémicycle SVGs', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    const { container } = renderMap();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      // Grid SVG + 2 hémicycles = 3 total
      const svgs = container.querySelectorAll('svg');
      expect(svgs.length).toBeGreaterThanOrEqual(3);
    });
    vi.runAllTimers();
  });

  it('shows distortion badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderMap();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('distortion-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows warning alert when gerrymander_index > 0.2', async () => {
    apiClient.POST.mockResolvedValue(makeData(0.6));
    renderMap();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('gerrymander-alert')).toBeInTheDocument());
    const alert = screen.getByTestId('gerrymander-alert');
    expect(alert.className).toContain('bg-amber-100');
    vi.runAllTimers();
  });

  it('shows success alert when gerrymander_index ≤ 0.2', async () => {
    apiClient.POST.mockResolvedValue(makeData(0.05));
    renderMap();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('gerrymander-alert')).toBeInTheDocument());
    const alert = screen.getByTestId('gerrymander-alert');
    expect(alert.className).toContain('bg-green-100');
    vi.runAllTimers();
  });

  it('shows gerrymander index progress bar', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderMap();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('gerry-index-bar')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderMap();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
