import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import DistrictMap from '../DistrictMap';
import { ElectionProvider } from '../../../stores/useElectionStore';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../../api/client')) as unknown as { apiClient: { POST: jest.Mock } };

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
  error: undefined,
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
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <DistrictMap />
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

afterEach(() => {
  vi.useRealTimers();
});

describe('DistrictMap', () => {
  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /district/i })).toBeInTheDocument();
  });

  it('calls API on button click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/districts/),
      expect.any(Object)
    );
  });

  it('renders district grid SVG after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      expect(container.querySelector('[data-testid="district-grid"]')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('renders correct number of district rectangles', async () => {
    apiClient.POST.mockResolvedValue(makeData(10));
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      expect(container.querySelector('[data-testid="district-grid"]')).toBeInTheDocument();
    });
    vi.runAllTimers();
    const rects = container.querySelectorAll('[data-testid="district-grid"] rect');
    expect(rects.length).toBe(10);
  });

  it('shows FPTP winner badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      expect(screen.getAllByText(/FPTP.*Alice|Alice.*FPTP/i).length).toBeGreaterThan(0);
    });
    vi.runAllTimers();
  });

  it('shows distortion badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      expect(screen.getByTestId('distortion-badge')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('shows warning pedagogical message when FPTP and PR winners differ', async () => {
    apiClient.POST.mockResolvedValue(makeDivergentData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      // Warning alert appears when winners differ
      const alerts = document.querySelectorAll('.alert-warning');
      expect(alerts.length).toBeGreaterThan(0);
    });
    vi.runAllTimers();
  });

  it('renders two hémicycle SVGs', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      const svgs = container.querySelectorAll('svg');
      // district grid + 2 hémicycles = at least 3 SVGs
      expect(svgs.length).toBeGreaterThanOrEqual(3);
    });
    vi.runAllTimers();
  });

  it('shows error message on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument();
    });
  });

  it('shows replay button after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /district/i }));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /replay|rejouer/i })).toBeInTheDocument();
    });
    vi.runAllTimers();
  });
});
