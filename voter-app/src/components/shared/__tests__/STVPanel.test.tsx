import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import STVPanel from '../STVPanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

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
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <STVPanel />
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

describe('STVPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /STV|simuler/i })).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls axios.post on button click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /STV|simuler/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringContaining('/api/election/stv'),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('shows quota display after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /STV|simuler/i }));
    await waitFor(() => expect(screen.getByText(/26/)).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows STV round stepper', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /STV|simuler/i }));
    await waitFor(() => expect(screen.getByTestId('stv-round-0')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows elected badges for winners', async () => {
    mockPost.mockResolvedValue(makeData());
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
    jest.runAllTimers();
  });

  it('shows three hémicycle SVGs', async () => {
    mockPost.mockResolvedValue(makeData());
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /STV|simuler/i }));
    await waitFor(() => {
      const svgs = container.querySelectorAll('svg');
      expect(svgs.length).toBeGreaterThanOrEqual(3);
    });
    jest.runAllTimers();
  });

  it('shows distortion badges', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /STV|simuler/i }));
    await waitFor(() => {
      expect(screen.getByTestId('distortion-stv-dhondt')).toBeInTheDocument();
      expect(screen.getByTestId('distortion-stv-fptp')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('step slider navigates rounds', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /STV|simuler/i }));
    await waitFor(() => expect(screen.getByTestId('step-slider')).toBeInTheDocument());
    fireEvent.change(screen.getByTestId('step-slider'), { target: { value: '1' } });
    await waitFor(() => expect(screen.getByTestId('stv-round-1')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /STV|simuler/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
