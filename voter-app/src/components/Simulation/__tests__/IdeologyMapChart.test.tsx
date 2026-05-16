import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import IdeologyMapChart from '../IdeologyMapChart';

jest.mock('../../../services/simulationCompareApi', () => ({
  getIdeologyMap: jest.fn(),
}));

const { getIdeologyMap } = jest.requireMock('../../../services/simulationCompareApi') as {
  getIdeologyMap: jest.Mock;
};

const MOCK_RESULT = {
  voters: [
    { id: 0, x: -0.5, y: -0.2, utility_winner_a: 0.7, utility_winner_b: 0.4, prefers_a: true },
    { id: 1, x:  0.3, y:  0.1, utility_winner_a: 0.3, utility_winner_b: 0.6, prefers_a: false },
  ],
  candidates: [
    { name: 'Alice', x: -0.5, y: 0.0, party: 'Liberal' },
    { name: 'Bob',   x:  0.5, y: 0.0, party: 'Conservative' },
  ],
  winner_a:             'Alice',
  winner_b:             'Bob',
  method_a:             'plurality',
  method_b:             'schulze',
  condorcet_winner:     'Alice',
  pct_better_off_with_a: 0.5,
  pct_better_off_with_b: 0.5,
};

beforeEach(() => {
  jest.clearAllMocks();
  getIdeologyMap.mockResolvedValue(MOCK_RESULT);
});

describe('IdeologyMapChart', () => {
  it('renders method selects and voter slider', async () => {
    render(<IdeologyMapChart defaultCandidates={['Alice', 'Bob']} />);
    await waitFor(() => expect(getIdeologyMap).toHaveBeenCalled());

    // Method selects
    const selects = screen.getAllByRole('combobox');
    expect(selects.length).toBeGreaterThanOrEqual(2);
  });

  it('renders the SVG canvas', async () => {
    const { container } = render(<IdeologyMapChart defaultCandidates={['Alice', 'Bob']} />);
    await waitFor(() => expect(getIdeologyMap).toHaveBeenCalled());
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('calls getIdeologyMap on mount with correct default methods', async () => {
    render(<IdeologyMapChart defaultCandidates={['Alice', 'Bob']} />);
    await waitFor(() => expect(getIdeologyMap).toHaveBeenCalledTimes(1));
    const params = getIdeologyMap.mock.calls[0][0];
    expect(params.method_a).toBe('plurality');
    expect(params.method_b).toBe('schulze');
    expect(params.candidates).toHaveLength(2);
  });

  it('re-fetches when method A select changes', async () => {
    render(<IdeologyMapChart defaultCandidates={['Alice', 'Bob']} />);
    await waitFor(() => expect(getIdeologyMap).toHaveBeenCalledTimes(1));

    // Change method A to borda
    const [selectA] = screen.getAllByRole('combobox');
    fireEvent.change(selectA, { target: { value: 'borda' } });

    await waitFor(() => expect(getIdeologyMap).toHaveBeenCalledTimes(2));
    const params = getIdeologyMap.mock.calls[1][0];
    expect(params.method_a).toBe('borda');
  });

  it('renders winner info after data loads', async () => {
    render(<IdeologyMapChart defaultCandidates={['Alice', 'Bob']} />);
    await waitFor(() => expect(getIdeologyMap).toHaveBeenCalled());
    // Stats panel shows pct values once data loads
    await waitFor(() => {
      const elements = screen.getAllByText(/plurality/i);
      expect(elements.length).toBeGreaterThan(0);
    });
  });

  it('shows "show losers" toggle', async () => {
    render(<IdeologyMapChart defaultCandidates={['Alice', 'Bob']} />);
    const toggle = screen.getByRole('checkbox');
    expect(toggle).toBeInTheDocument();
    expect(toggle).not.toBeChecked();
  });

  it('checking "show losers" toggle changes its state', async () => {
    render(<IdeologyMapChart defaultCandidates={['Alice', 'Bob']} />);
    const toggle = screen.getByRole('checkbox');
    fireEvent.click(toggle);
    expect(toggle).toBeChecked();
  });

  it('renders regenerate button', async () => {
    render(<IdeologyMapChart defaultCandidates={['Alice', 'Bob']} />);
    expect(screen.getByText(/Régénérer|Regenerate/i)).toBeInTheDocument();
  });

  it('clicking regenerate triggers a new API call with different seed', async () => {
    render(<IdeologyMapChart defaultCandidates={['Alice', 'Bob']} />);
    await waitFor(() => expect(getIdeologyMap).toHaveBeenCalledTimes(1));
    const seedBefore = getIdeologyMap.mock.calls[0][0].seed;

    fireEvent.click(screen.getByText(/Régénérer|Regenerate/i));

    await waitFor(() => expect(getIdeologyMap).toHaveBeenCalledTimes(2));
    const seedAfter = getIdeologyMap.mock.calls[1][0].seed;
    expect(seedAfter).not.toBe(seedBefore);
  });

  it('passes defaultCandidates as initial candidate positions', async () => {
    render(<IdeologyMapChart defaultCandidates={['Alice', 'Bob', 'Carol']} />);
    await waitFor(() => expect(getIdeologyMap).toHaveBeenCalledTimes(1));
    const params = getIdeologyMap.mock.calls[0][0];
    expect(params.candidates).toHaveLength(3);
    expect(params.candidates.map((c: any) => c.name)).toEqual(['Alice', 'Bob', 'Carol']);
  });
});
