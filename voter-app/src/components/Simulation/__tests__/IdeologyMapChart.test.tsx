import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import IdeologyMapChart from '../IdeologyMapChart';

vi.mock('../../../services/simulationCompareApi', () => ({
  getIdeologyMap: vi.fn(),
}));

const { getIdeologyMap } = (await import('../../../services/simulationCompareApi')) as unknown as {
  getIdeologyMap: jest.Mock;
};

const MOCK_RESULT = {
  voters: [
    { id: 0, x: -0.5, y: -0.2, utility_winner_a: 0.7, utility_winner_b: 0.4, prefers_a: true },
    { id: 1, x: 0.3, y: 0.1, utility_winner_a: 0.3, utility_winner_b: 0.6, prefers_a: false },
  ],
  candidates: [
    { name: 'Alice', x: -0.5, y: 0.0, party: 'Liberal' },
    { name: 'Bob', x: 0.5, y: 0.0, party: 'Conservative' },
  ],
  winner_a: 'Alice',
  winner_b: 'Bob',
  method_a: 'plurality',
  method_b: 'schulze',
  condorcet_winner: 'Alice',
  pct_better_off_with_a: 0.5,
  pct_better_off_with_b: 0.5,
};

beforeEach(() => {
  vi.clearAllMocks();
  getIdeologyMap.mockResolvedValue(MOCK_RESULT);
});

describe('IdeologyMapChart', () => {
  // Helper: render and wait until the initial API call's state updates have settled
  async function renderAndSettle(candidates = ['Alice', 'Bob']) {
    const result = render(<IdeologyMapChart defaultCandidates={candidates} />);
    await waitFor(() => expect(getIdeologyMap).toHaveBeenCalled());
    await act(async () => {}); // flush setMapData / setLoading microtasks
    return result;
  }

  it('renders method selects and voter slider', async () => {
    await renderAndSettle();
    const selects = screen.getAllByRole('combobox');
    expect(selects.length).toBeGreaterThanOrEqual(2);
  });

  it('renders the SVG canvas', async () => {
    const { container } = await renderAndSettle();
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('calls getIdeologyMap on mount with correct default methods', async () => {
    await renderAndSettle();
    const params = getIdeologyMap.mock.calls[0][0];
    expect(params.method_a).toBe('plurality');
    expect(params.method_b).toBe('schulze');
    expect(params.candidates).toHaveLength(2);
  });

  it('re-fetches when method A select changes', async () => {
    await renderAndSettle();

    const [selectA] = screen.getAllByRole('combobox');
    fireEvent.change(selectA, { target: { value: 'borda' } });

    await waitFor(() => expect(getIdeologyMap).toHaveBeenCalledTimes(2));
    await act(async () => {}); // flush state from second fetch
    const params = getIdeologyMap.mock.calls[1][0];
    expect(params.method_a).toBe('borda');
  });

  it('renders winner info after data loads', async () => {
    await renderAndSettle();
    await waitFor(() => {
      const elements = screen.getAllByText(/plurality/i);
      expect(elements.length).toBeGreaterThan(0);
    });
  });

  it('shows "show losers" toggle (unchecked by default)', async () => {
    await act(async () => {
      render(<IdeologyMapChart defaultCandidates={['Alice', 'Bob']} />);
    });
    const toggle = document.getElementById('show-losers-toggle') as HTMLInputElement;
    expect(toggle).toBeInTheDocument();
    expect(toggle).not.toBeChecked();
  });

  it('checking "show losers" toggle changes its state', async () => {
    await act(async () => {
      render(<IdeologyMapChart defaultCandidates={['Alice', 'Bob']} />);
    });
    const toggle = document.getElementById('show-losers-toggle') as HTMLInputElement;
    fireEvent.click(toggle);
    expect(toggle).toBeChecked();
  });

  it('Voronoi toggle is OFF by default', async () => {
    await act(async () => {
      render(<IdeologyMapChart defaultCandidates={['Alice', 'Bob']} />);
    });
    const toggle = document.getElementById('show-voronoi-toggle') as HTMLInputElement;
    expect(toggle).toBeInTheDocument();
    expect(toggle).not.toBeChecked();
  });

  it('activating Voronoi toggle renders SVG region paths', async () => {
    const { container } = await renderAndSettle();

    // No voronoi paths before toggle
    expect(container.querySelector('[data-testid^="voronoi-region"]')).toBeNull();

    const toggle = document.getElementById('show-voronoi-toggle') as HTMLInputElement;
    fireEvent.click(toggle);

    // After toggle: paths should appear for 2 candidates
    await waitFor(() => {
      const paths = container.querySelectorAll('[data-testid^="voronoi-region"]');
      expect(paths.length).toBeGreaterThan(0);
    });
  });

  it('Voronoi legend shows candidate badges when toggle is ON', async () => {
    await renderAndSettle();

    // Before toggle: candidate name badges from the voronoi legend are absent
    // (they'd only appear inside the legend div, not as star labels)
    const toggle = document.getElementById('show-voronoi-toggle') as HTMLInputElement;
    expect(toggle).not.toBeChecked();

    fireEvent.click(toggle);
    expect(toggle).toBeChecked();

    // After toggle: legend section renders (contains candidate name badges)
    await waitFor(() => {
      expect(screen.getAllByText('Alice').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Bob').length).toBeGreaterThan(0);
    });
  });

  it('renders regenerate button', async () => {
    await act(async () => {
      render(<IdeologyMapChart defaultCandidates={['Alice', 'Bob']} />);
    });
    expect(screen.getByText(/Régénérer|Regenerate/i)).toBeInTheDocument();
  });

  it('clicking regenerate triggers a new API call with different seed', async () => {
    await renderAndSettle();
    const seedBefore = getIdeologyMap.mock.calls[0][0].seed;

    fireEvent.click(screen.getByText(/Régénérer|Regenerate/i));

    await waitFor(() => expect(getIdeologyMap).toHaveBeenCalledTimes(2));
    await act(async () => {});
    const seedAfter = getIdeologyMap.mock.calls[1][0].seed;
    expect(seedAfter).not.toBe(seedBefore);
  });

  it('passes defaultCandidates as initial candidate positions', async () => {
    render(<IdeologyMapChart defaultCandidates={['Alice', 'Bob', 'Carol']} />);
    await waitFor(() => expect(getIdeologyMap).toHaveBeenCalledTimes(1));
    await act(async () => {});
    const params = getIdeologyMap.mock.calls[0][0];
    expect(params.candidates).toHaveLength(3);
    expect(params.candidates.map((c: any) => c.name)).toEqual(['Alice', 'Bob', 'Carol']);
  });
});
