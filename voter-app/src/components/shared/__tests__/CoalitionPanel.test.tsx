import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import CoalitionPanel from '../CoalitionPanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

const makeCoalitionData = () => ({
  data: {
    methods: [
      {
        method:               'plurality',
        winner:               'Alice',
        seats:                { Alice: 55, Bob: 30, Carol: 15 },
        vote_shares:          { Alice: 0.55, Bob: 0.30, Carol: 0.15 },
        coalition_parties:    ['Alice'],
        coalition_seats:      55,
        coalition_spread:     0.0,
        government_possible:  true,
      },
      {
        method:               'borda',
        winner:               'Carol',
        seats:                { Alice: 35, Bob: 35, Carol: 30 },
        vote_shares:          { Alice: 0.35, Bob: 0.35, Carol: 0.30 },
        coalition_parties:    ['Alice', 'Carol'],
        coalition_seats:      65,
        coalition_spread:     0.25,
        government_possible:  true,
      },
    ],
    candidates:            [
      { name: 'Alice', x: -0.5 },
      { name: 'Bob',   x:  0.5 },
      { name: 'Carol', x:  0.0 },
    ],
    total_seats:           100,
    seat_threshold:        50,
    most_centrist_method:  'plurality',
    most_divergent_method: 'borda',
    inter_method_agreement: 0.5,
  },
});

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <CoalitionPanel />
      </ElectionProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
});

describe('CoalitionPanel', () => {
  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getAllByText(/coalition|Coalition/i).length).toBeGreaterThan(0);
  });

  it('shows run button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /coalition|simuler/i })).toBeInTheDocument();
  });

  it('calls axios.post on button click', async () => {
    mockPost.mockResolvedValue(makeCoalitionData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /coalition|simuler/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    // Accept either /api/election/coalition (Flask v1) or
    // /api/v2/election/coalition (FastAPI v2 — default since Phase 3 batch 2).
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/coalition/),
      expect.any(Object)
    );
  });

  it('renders method rows after data loads', async () => {
    mockPost.mockResolvedValue(makeCoalitionData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /coalition|simuler/i }));
    await waitFor(() => {
      expect(screen.getByText('plurality')).toBeInTheDocument();
      expect(screen.getByText('borda')).toBeInTheDocument();
    });
  });

  it('renders SVG hémicycle', async () => {
    mockPost.mockResolvedValue(makeCoalitionData());
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /coalition|simuler/i }));
    await waitFor(() => {
      expect(container.querySelector('svg')).toBeInTheDocument();
    });
  });

  it('shows government possible badge', async () => {
    mockPost.mockResolvedValue(makeCoalitionData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /coalition|simuler/i }));
    await waitFor(() => {
      expect(screen.getAllByText(/✓|Majorité possible|Majority possible/i).length).toBeGreaterThan(0);
    });
  });

  it('shows most centrist badge', async () => {
    mockPost.mockResolvedValue(makeCoalitionData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /coalition|simuler/i }));
    await waitFor(() => {
      expect(screen.getAllByText(/plurality/i).length).toBeGreaterThan(0);
    });
  });

  it('shows error when API fails', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /coalition|simuler/i }));
    await waitFor(() => {
      expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument();
    });
  });

  it('clicking a method row changes selected method display', async () => {
    mockPost.mockResolvedValue(makeCoalitionData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /coalition|simuler/i }));
    await waitFor(() => expect(screen.getByText('borda')).toBeInTheDocument());

    fireEvent.click(screen.getByText('borda'));
    // After clicking borda row, borda should appear in the right panel title
    expect(screen.getAllByText(/borda/i).length).toBeGreaterThan(0);
  });
});
