import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../hooks/useMetaTags', () => ({ useMetaTags: () => {} }));
vi.mock('../../services/assemblyApi', () => {
  // NB: declared inside the factory — vi.mock is hoisted above file-level consts.
  const sc = (
    p: number, pl: number, ev: number, mr: number, g: number, gr: number
  ) => ({
    proportionality: { mean: p, lo: p - 0.05, hi: p + 0.05 },
    pluralism: { mean: pl, lo: pl - 0.05, hi: pl + 0.05 },
    effective_votes: { mean: ev, lo: ev - 0.05, hi: ev + 0.05 },
    minority_representation: { mean: mr, lo: mr - 0.05, hi: mr + 0.05 },
    governability: { mean: g, lo: g - 0.05, hi: g + 0.05 },
    gerrymander_resistance: { mean: gr, lo: gr - 0.05, hi: gr + 0.05 },
  });
  return {
    runAssemblyScorecard: vi.fn().mockResolvedValue({
      replications: 24,
      structures: {
        // PR and FPTP trade off (proportionality vs governability); MMP is
        // strictly below PR on every axis → dominated.
        pr: sc(0.9, 0.9, 0.9, 0.9, 0.4, 0.9),
        fptp: sc(0.5, 0.5, 0.5, 0.5, 0.9, 0.6),
        mmp: sc(0.6, 0.6, 0.6, 0.6, 0.3, 0.6),
      },
    }),
    runAssembly: vi.fn().mockResolvedValue({
    structure: 'pr',
    assembly_size: 100,
    majority: 51,
    threshold_waived: false,
    parties: [],
    gallagher_index: 1.0,
    effective_parties_votes: 3.0,
    effective_parties_seats: 2.9,
    wasted_vote_share: 0.02,
    coalitions: [],
    }),
  };
});
vi.mock('../../services/profileApi', () => ({
  runProfileSimulate: vi.fn().mockResolvedValue({
    methods: { plurality: { winner: 'A' } },
    condorcet_winner: 'A',
    inter_method_agreement: 1,
    cycle_rate: 0.12,
    candidate_names: ['A', 'B'],
    display_points: [],
    candidate_points: null,
    num_voters: 300,
  }),
}));

import PlaygroundPage from '../PlaygroundPage';
import { useElectionStore, DEFAULT_PLAYGROUND, DEFAULT_CONFIG } from '../../stores/useElectionStore';

const LS_PG = 'votelab_playground';

beforeEach(() => {
  localStorage.clear();
  // Reset the module-singleton store to a known baseline between tests.
  useElectionStore.setState({ playground: { ...DEFAULT_PLAYGROUND }, config: { ...DEFAULT_CONFIG } });
});

describe('PlaygroundPage (P0 shell)', () => {
  it('renders and shows the leader canvas by default', () => {
    render(<PlaygroundPage />);
    expect(screen.getByTestId('playground-page')).toBeInTheDocument();
    expect(screen.getByTestId('leader-canvas')).toBeInTheDocument();
    expect(screen.queryByTestId('canvas-parliament')).not.toBeInTheDocument();
  });

  it('mode toggle swaps the canvas, reveals assembly knobs, and persists', () => {
    render(<PlaygroundPage />);
    fireEvent.click(screen.getByTestId('mode-toggle-parliament'));

    expect(screen.getByTestId('canvas-parliament')).toBeInTheDocument();
    expect(screen.queryByTestId('leader-canvas')).not.toBeInTheDocument();
    // Assembly-only knob appears in parliament mode.
    expect(screen.getByLabelText('Structure')).toBeInTheDocument();

    expect(useElectionStore.getState().playground.mode).toBe('parliament');
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).mode).toBe('parliament');
  });

  it('a preset mutates shared electorate + playground state and persists', () => {
    render(<PlaygroundPage />);
    fireEvent.click(screen.getByTestId('preset-fragmented'));

    const { playground, config } = useElectionStore.getState();
    expect(playground.mode).toBe('parliament');
    expect(config.candidates).toHaveLength(6);
    expect(config.num_voters).toBe(600);
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).mode).toBe('parliament');
    // The canvas reflects the preset's mode.
    expect(screen.getByTestId('canvas-parliament')).toBeInTheDocument();
  });

  it('a knob change (dimensions) persists to the store', () => {
    render(<PlaygroundPage />);
    fireEvent.change(screen.getByLabelText('Dimensions de l’espace'), { target: { value: '3' } });

    expect(useElectionStore.getState().playground.space.dims).toBe(3);
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).space.dims).toBe(3);
  });

  it('surfaces the cycle-rate read-out from the profile engine', async () => {
    render(<PlaygroundPage />);
    await waitFor(() => expect(screen.getByTestId('cycle-rate')).toHaveTextContent('12 %'));
  });

  // ── P4: the dynamic layer ────────────────────────────────────────────────

  it('the flip button toggles the mode and shows the flip caption', () => {
    render(<PlaygroundPage />);
    fireEvent.click(screen.getByTestId('flip-button'));
    expect(useElectionStore.getState().playground.mode).toBe('parliament');
    expect(screen.getByTestId('flip-caption')).toHaveTextContent('Mêmes électeurs');
    // Replayable in the other direction.
    fireEvent.click(screen.getByTestId('flip-button'));
    expect(useElectionStore.getState().playground.mode).toBe('leader');
    expect(screen.getByTestId('flip-caption')).toBeInTheDocument();
  });

  it('the campaign scrubber advances the day label and disables candidate edits', () => {
    render(<PlaygroundPage />);
    fireEvent.change(screen.getByTestId('campaign-slider'), { target: { value: '0.5' } });
    expect(screen.getByTestId('campaign-scrubber')).toHaveTextContent('J15');
    expect(screen.getByTestId('campaign-scrubber')).toHaveTextContent('revenez à J0');
  });

  it('shake-the-assumptions renders win-rate bands that sum to ~100%', async () => {
    render(<PlaygroundPage />);
    fireEvent.click(screen.getByTestId('shake-toggle'));
    await waitFor(
      () => expect(screen.getByTestId('shake-bands')).toHaveTextContent('ré-échantillonnages'),
      { timeout: 5000 }
    );
    const text = screen.getByTestId('shake-bands').textContent ?? '';
    const pcts = [...text.matchAll(/(\d+)\s?%/g)].map((m) => Number(m[1]));
    // headline % + one per candidate; the per-candidate rates sum to ~100.
    const perCandidate = pcts.slice(1);
    const sum = perCandidate.reduce((s, p) => s + p, 0);
    expect(sum).toBeGreaterThanOrEqual(97);
    expect(sum).toBeLessThanOrEqual(103);
  });

  it('the Duverger toggle persists strategic desertion in the store', () => {
    render(<PlaygroundPage />);
    fireEvent.click(screen.getByTestId('mode-toggle-parliament'));
    fireEvent.click(screen.getByTestId('duverger-toggle'));
    expect(useElectionStore.getState().playground.assembly.strategic_desertion).toBe(true);
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).assembly.strategic_desertion).toBe(
      true
    );
  });

  // ── P5: scorecard + values lens ──────────────────────────────────────────

  it('leader mode renders the banded scorecard and the values lens over the 6 rules', async () => {
    render(<PlaygroundPage />);
    await waitFor(
      () =>
        expect(
          screen.getByTestId('axis-condorcet_efficiency').textContent
        ).toMatch(/\d+\s?%/),
      { timeout: 5000 }
    );
    expect(screen.getByTestId('values-panel')).toBeInTheDocument();
    expect(screen.getByTestId('lens-item-condorcet')).toBeInTheDocument();
    expect(screen.getByTestId('lens-item-plurality')).toBeInTheDocument();
  });

  it('parliament mode shows the structure scorecard from the backend with bands', async () => {
    render(<PlaygroundPage />);
    fireEvent.click(screen.getByTestId('mode-toggle-parliament'));
    await waitFor(
      () => expect(screen.getByTestId('axis-proportionality')).toHaveTextContent('90 %'),
      { timeout: 5000 }
    );
    // The three structures appear in the lens; with the mocked axes FPTP and PR
    // trade off (neither dominates), while MMP is dominated by PR.
    expect(screen.getByTestId('lens-item-mmp')).toHaveTextContent('écarté (dominé)');
    expect(screen.getByTestId('lens-item-pr')).not.toHaveTextContent('écarté');
  });
});
