import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import STVPanel from '../STVPanel';
import { ElectionProvider } from '../../../stores/useElectionStore';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../../api/client')) as unknown as { apiClient: { POST: jest.Mock } };

// ── Fixture ───────────────────────────────────────────────────────────────────

const NAMES = ['Alice', 'Bob', 'Carol', 'Dave'];

function makeData() {
  return {
    data: {
      stv: {
        elected: ['Alice', 'Bob'],
        quota:   26,
        seats:   { Alice: 1, Bob: 1, Carol: 0, Dave: 0 },
        rounds: [
          {
            round: 0, action: 'elect', candidate: 'Alice',
            tallies:   { Alice: 0, Bob: 38, Carol: 22, Dave: 14 },
            transfers: { Bob: 9 },
          },
          {
            round: 1, action: 'eliminate', candidate: 'Dave',
            tallies:   { Bob: 43, Carol: 31 },
            transfers: {},
          },
          {
            round: 2, action: 'elect', candidate: 'Bob',
            tallies:   { Bob: 0, Carol: 31 },
            transfers: { Carol: 17 },
          },
        ],
      },
      dhondt: {
        seats:   { Alice: 1, Bob: 1, Carol: 0, Dave: 0 },
        elected: ['Alice', 'Bob'],
      },
      fptp: {
        seats:   { Alice: 1, Bob: 1, Carol: 0, Dave: 0 },
        elected: ['Alice', 'Bob'],
      },
      vote_shares:           { Alice: 0.40, Bob: 0.35, Carol: 0.15, Dave: 0.10 },
      num_seats:             2,
      quota:                 26,
      quota_type:            'droop',
      distortion_stv_dhondt: 0,
      distortion_stv_fptp:   0,
      candidates:            NAMES,
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <STVPanel />
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

describe('STVPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /STV|simuler/i })).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls API on button click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /STV|simuler/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/stv/),
      expect.any(Object),
    );
    vi.runAllTimers();
  });

  it('shows quota display after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /STV|simuler/i }));
    await waitFor(() => expect(screen.getByText(/26/)).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows STV round stepper', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /STV|simuler/i }));
    await waitFor(() => expect(screen.getByTestId('stv-round-0')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows elected badges for winners', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /STV|simuler/i }));
    await waitFor(() => {
      // After loading, advance to last step so all elected show
      const slider = screen.getByTestId('step-slider');
      fireEvent.change(slider, { target: { value: '2' } });
    });
    await waitFor(() => {
      expect(screen.getByTestId('elected-badge-Alice')).toBeInTheDocument();
      expect(screen.getByTestId('elected-badge-Bob')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('shows three hémicycle SVGs', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /STV|simuler/i }));
    await waitFor(() => {
      const svgs = container.querySelectorAll('svg');
      expect(svgs.length).toBeGreaterThanOrEqual(3);
    });
    vi.runAllTimers();
  });

  it('shows distortion badges', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /STV|simuler/i }));
    await waitFor(() => {
      expect(screen.getByTestId('distortion-stv-dhondt')).toBeInTheDocument();
      expect(screen.getByTestId('distortion-stv-fptp')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('step slider navigates rounds', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /STV|simuler/i }));
    await waitFor(() => expect(screen.getByTestId('step-slider')).toBeInTheDocument());
    fireEvent.change(screen.getByTestId('step-slider'), { target: { value: '1' } });
    await waitFor(() => expect(screen.getByTestId('stv-round-1')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /STV|simuler/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
