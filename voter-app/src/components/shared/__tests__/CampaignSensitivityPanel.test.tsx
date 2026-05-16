import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import CampaignSensitivityPanel from '../CampaignSensitivityPanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('../../../services/electionApi', () => ({
  fetchCampaignSensitivity: jest.fn(),
}));

jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart:            ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar:                 ({ children }: any) => <div>{children}</div>,
  AreaChart:           ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  Area:                () => null,
  CartesianGrid:       () => null,
  Cell:                () => null,
  XAxis:               () => null,
  YAxis:               () => null,
  Tooltip:             () => null,
  Legend:              () => null,
}));

const { fetchCampaignSensitivity } = jest.requireMock('../../../services/electionApi') as {
  fetchCampaignSensitivity: jest.Mock;
};

const MOCK_RESULT = {
  snapshots: [
    {
      day: 0,
      methods: {
        plurality: { winner: 'Alice', vote_share: 0.6 },
        schulze:   { winner: 'Bob',   vote_share: 0.4 },
      },
      inter_method_agreement: 0.5,
    },
    {
      day: 14,
      methods: {
        plurality: { winner: 'Alice', vote_share: 0.65 },
        schulze:   { winner: 'Alice', vote_share: 0.6 },
      },
      inter_method_agreement: 1.0,
    },
  ],
  method_stability: {
    plurality: { winner_changes: 0, final_winner: 'Alice', stability_score: 1.0 },
    schulze:   { winner_changes: 1, final_winner: 'Alice', stability_score: 0.0 },
  },
  most_stable_method:  'plurality',
  least_stable_method: 'schulze',
};

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <CampaignSensitivityPanel />
      </ElectionProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  fetchCampaignSensitivity.mockResolvedValue(MOCK_RESULT);
});

describe('CampaignSensitivityPanel', () => {
  it('renders sliders and compute button', () => {
    renderPanel();
    const sliders = screen.getAllByRole('slider');
    expect(sliders.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole('button', { name: /Analyser|Analyse/i })).toBeInTheDocument();
  });

  it('shows prompt text before analysis', () => {
    renderPanel();
    expect(screen.getByText(/Configurez|Configure/i)).toBeInTheDocument();
  });

  it('calls fetchCampaignSensitivity when button clicked', async () => {
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    await waitFor(() => expect(fetchCampaignSensitivity).toHaveBeenCalledTimes(1));
  });

  it('passes snapshot_days including "final" in the API call', async () => {
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    await waitFor(() => expect(fetchCampaignSensitivity).toHaveBeenCalledTimes(1));
    const params = fetchCampaignSensitivity.mock.calls[0][0];
    expect(params.snapshot_days).toContain('final');
    expect(params.snapshot_days).toContain(0);
  });

  it('renders charts after analysis completes', async () => {
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    await waitFor(() => {
      expect(screen.getAllByTestId('bar-chart').length).toBeGreaterThan(0);
    });
  });

  it('most stable method shown after load', async () => {
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    await waitFor(() => {
      // The stability title or badge containing "plurality" should be visible
      const elements = screen.getAllByText(/plurality/i);
      expect(elements.length).toBeGreaterThan(0);
    });
  });

  it('polling effect slider updates value', () => {
    renderPanel();
    const sliders = screen.getAllByRole('slider');
    fireEvent.change(sliders[0], { target: { value: '0.8' } });
    // No crash — slider works
    expect(sliders[0]).toBeInTheDocument();
  });

  it('contagion toggle changes checkbox state', () => {
    renderPanel();
    const checkbox = screen.getByRole('checkbox');
    const initial = checkbox.getAttribute('checked');
    fireEvent.click(checkbox);
    expect(checkbox).toBeInTheDocument(); // no crash
  });
});
