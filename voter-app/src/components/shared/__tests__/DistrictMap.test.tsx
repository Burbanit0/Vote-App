import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import DistrictMap from '../DistrictMap';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

const makeData = (numDistricts = 10) => ({
  data: {
    num_districts: numDistricts,
    districts: Array.from({ length: numDistricts }, (_, i) => ({
      id:              i,
      ideology_center: (i - numDistricts / 2) * 0.1,
      winner_fptp:     i < numDistricts * 0.6 ? 'Alice' : 'Bob',
      vote_shares:     { Alice: 0.55, Bob: 0.31, Carol: 0.14 },
    })),
    parliament_fptp:         { Alice: 6, Bob: 4, Carol: 0 },
    parliament_proportional: { Alice: 5, Bob: 3, Carol: 2 },
    national_vote_share:     { Alice: 0.55, Bob: 0.31, Carol: 0.14 },
    distortion:              0.14,
    condorcet_winner_national: 'Alice',
    fptp_winner:             'Alice',
    proportional_winner:     'Alice',
  },
});

const makeDivergentData = () => {
  const d = makeData(10);
  d.data.fptp_winner         = 'Alice';
  d.data.proportional_winner = 'Bob';
  d.data.distortion          = 0.22;
  return d;
};

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <DistrictMap />
      </ElectionProvider>
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

describe('DistrictMap', () => {
  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /district/i })).toBeInTheDocument();
  });

  it('calls axios.post on button click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/districts/),
      expect.any(Object)
    );
  });

  it('renders district grid SVG after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      expect(container.querySelector('[data-testid="district-grid"]')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('renders correct number of district rectangles', async () => {
    mockPost.mockResolvedValue(makeData(10));
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      expect(container.querySelector('[data-testid="district-grid"]')).toBeInTheDocument();
    });
    jest.runAllTimers();
    const rects = container.querySelectorAll('[data-testid="district-grid"] rect');
    expect(rects.length).toBe(10);
  });

  it('shows FPTP winner badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      expect(screen.getAllByText(/FPTP.*Alice|Alice.*FPTP/i).length).toBeGreaterThan(0);
    });
    jest.runAllTimers();
  });

  it('shows distortion badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      expect(screen.getByTestId('distortion-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows warning pedagogical message when FPTP and PR winners differ', async () => {
    mockPost.mockResolvedValue(makeDivergentData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      // Warning alert appears when winners differ
      const alerts = document.querySelectorAll('.alert-warning');
      expect(alerts.length).toBeGreaterThan(0);
    });
    jest.runAllTimers();
  });

  it('renders two hémicycle SVGs', async () => {
    mockPost.mockResolvedValue(makeData());
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      const svgs = container.querySelectorAll('svg');
      // district grid + 2 hémicycles = at least 3 SVGs
      expect(svgs.length).toBeGreaterThanOrEqual(3);
    });
    jest.runAllTimers();
  });

  it('shows error message on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument();
    });
  });

  it('shows replay button after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /replay|rejouer/i })).toBeInTheDocument();
    });
    jest.runAllTimers();
  });
});
