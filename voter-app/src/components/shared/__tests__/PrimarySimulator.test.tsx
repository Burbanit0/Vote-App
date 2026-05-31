import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import PrimarySimulator from '../PrimarySimulator';
import { ElectionProvider } from '../../../context/ElectionContext';
import { makeTestQueryClient } from '../../../test/queryWrapper';

jest.mock('../../../api/client', () => ({
  apiClient: { GET: jest.fn(), POST: jest.fn(), PUT: jest.fn(), DELETE: jest.fn(), PATCH: jest.fn() },
  getAccessToken: jest.fn(() => null),
}));
const { apiClient } = jest.requireMock('../../../api/client') as { apiClient: { POST: jest.Mock } };

// Mock Recharts to avoid SVG measurement issues in jsdom
jest.mock('recharts', () => {
  const React = require('react');
  return {
    BarChart:          ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
    Bar:               ({ children }: any) => <div>{children}</div>,
    XAxis:             () => null,
    YAxis:             () => null,
    Tooltip:           () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 300 }}>{children}</div>,
    Cell:              () => null,
  };
});

const makeData = (winnerChanged = false) => ({
  data: {
    primaries: [
      {
        party:               'Left',
        winner:              'Marc',
        runner_up:           'Sophie',
        distortion:          0.25,
        winner_pos:          -0.75,
        party_center:        -0.5,
        vote_shares:         { Marc: 0.6, Sophie: 0.4 },
        num_primary_voters:  50,
      },
      {
        party:               'Right',
        winner:              'Paul',
        runner_up:           'Elise',
        distortion:          0.25,
        winner_pos:          0.75,
        party_center:        0.5,
        vote_shares:         { Paul: 0.55, Elise: 0.45 },
        num_primary_voters:  50,
      },
      {
        party:               'Centre',
        winner:              'Anna',
        runner_up:           'Tom',
        distortion:          0.0,
        winner_pos:          0.0,
        party_center:        0.0,
        vote_shares:         { Anna: 0.65, Tom: 0.35 },
        num_primary_voters:  30,
      },
    ],
    general_ballot:           ['Marc', 'Paul', 'Anna'],
    general_winner:           winnerChanged ? 'Marc' : 'Anna',
    general_runner_up:        winnerChanged ? 'Anna' : 'Marc',
    general_vote_shares:      { Marc: 0.38, Paul: 0.35, Anna: 0.27 },
    median_voter_distance:    0.18,
    without_primaries_winner: winnerChanged ? 'Anna' : 'Anna',
  },
  error: undefined,
});

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <PrimarySimulator />
        </ElectionProvider>
      </QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
});

describe('PrimarySimulator', () => {
  it('shows run button before simulation', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls API with correct URL on click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/primary/),
      expect.any(Object)
    );
  });

  it('renders Phase 1 primaries section after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('primaries-section')).toBeInTheDocument();
    });
  });

  it('renders Phase 2 general election section', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('general-section')).toBeInTheDocument();
    });
  });

  it('shows general winner badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('general-winner-badge')).toBeInTheDocument();
    });
  });

  it('shows drift badge when distortion > 0.1', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('drift-badge')).toBeInTheDocument();
    });
  });

  it('shows per-party drift badge when distortion > 0.1', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('drift-badge-Left')).toBeInTheDocument();
      expect(screen.getByTestId('drift-badge-Right')).toBeInTheDocument();
    });
  });

  it('shows ideology axis SVG', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('ideology-axis')).toBeInTheDocument();
    });
  });

  it('shows warning alert when primaries change the winner', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const alerts = document.querySelectorAll('.alert-warning');
      expect(alerts.length).toBeGreaterThan(0);
    });
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument();
    });
  });

  it('renders bar charts for primary results', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      // 3 primaries + 1 general = 4 bar charts
      expect(screen.getAllByTestId('bar-chart').length).toBeGreaterThanOrEqual(3);
    });
  });
});
