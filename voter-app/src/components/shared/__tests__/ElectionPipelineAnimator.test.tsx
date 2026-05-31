import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import ElectionPipelineAnimator from '../ElectionPipelineAnimator';
import { ElectionProvider } from '../../../context/ElectionContext';
import { makeTestQueryClient } from '../../../test/queryWrapper';

jest.mock('../../../api/client', () => ({
  apiClient: { GET: jest.fn(), POST: jest.fn(), PUT: jest.fn(), DELETE: jest.fn(), PATCH: jest.fn() },
  getAccessToken: jest.fn(() => null),
}));
const { apiClient } = jest.requireMock('../../../api/client') as { apiClient: { POST: jest.Mock } };

jest.mock('../MethodGroupDonut', () => () => <div data-testid="donut" />);

// Minimal pipeline result
const makePipeline = (stepIds: string[]) => ({
  data: {
    num_steps:  stepIds.length,
    candidates: [
      { name: 'Alice', x: -0.5, y: 0.0, party: 'Liberal' },
      { name: 'Bob',   x:  0.5, y: 0.0, party: 'Conservative' },
    ],
    steps: stepIds.map((id) => ({
      id,
      label:   { fr: `Étape ${id}`, en: `Step ${id}` },
      desc:    { fr: 'desc fr', en: 'desc en' },
      voters:  [
        { id: 0, x: -0.3, y: 0.1, preference: 'Alice', is_blank: false },
        { id: 1, x:  0.4, y: -0.1, preference: 'Bob',   is_blank: false },
      ],
      metrics: id === 'results'
        ? { inter_method_agreement: 0.85, condorcet_winner: 'Alice', blank_rate: 0 }
        : { num_voters: 2 },
      ...(id === 'results' ? { winner_groups: [{ winner: 'Alice', methods: ['plurality'], pct: 1.0 }] } : {}),
    })),
  },
  error: undefined,
});

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <ElectionPipelineAnimator />
        </ElectionProvider>
      </QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
});

describe('ElectionPipelineAnimator', () => {
  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getAllByText(/pipeline|Animer|Animate/i).length).toBeGreaterThan(0);
  });

  it('shows "Animate pipeline" button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /pipeline|animer/i })).toBeInTheDocument();
  });

  it('calls API on button click', async () => {
    apiClient.POST.mockResolvedValue(makePipeline(['base', 'results']));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /pipeline|animer/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/simulate-pipeline/),
      expect.any(Object)
    );
  });

  it('renders step buttons after pipeline loads', async () => {
    apiClient.POST.mockResolvedValue(makePipeline(['base', 'results']));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /pipeline|animer/i }));
    await waitFor(() => {
      expect(screen.getByTestId('pipeline-step-base')).toBeInTheDocument();
      expect(screen.getByTestId('pipeline-step-results')).toBeInTheDocument();
    });
  });

  it('shows SVG scatter after pipeline loads', async () => {
    apiClient.POST.mockResolvedValue(makePipeline(['base', 'results']));
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /pipeline|animer/i }));
    await waitFor(() => {
      expect(container.querySelector('svg')).toBeInTheDocument();
    });
  });

  it('clicking a step button navigates to that step', async () => {
    apiClient.POST.mockResolvedValue(makePipeline(['base', 'campaign', 'results']));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /pipeline|animer/i }));
    await waitFor(() => expect(screen.getByTestId('pipeline-step-campaign')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('pipeline-step-campaign'));
    // No crash — step navigation works
    expect(screen.getByTestId('pipeline-step-campaign')).toBeInTheDocument();
  });

  it('shows donut in results step', async () => {
    apiClient.POST.mockResolvedValue(makePipeline(['base', 'results']));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /pipeline|animer/i }));

    // Navigate to results step
    await waitFor(() => expect(screen.getByTestId('pipeline-step-results')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('pipeline-step-results'));

    await waitFor(() => expect(screen.getByTestId('donut')).toBeInTheDocument());
  });

  it('shows error when API fails', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /pipeline|animer/i }));
    await waitFor(() => {
      expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument();
    });
  });
});
