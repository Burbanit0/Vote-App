import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../hooks/useMetaTags', () => ({ useMetaTags: () => {} }));
vi.mock('../../services/assemblyApi', () => {
  const sc = (p: number, pl: number, ev: number, mr: number, g: number, gr: number) => ({
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
      congruence: {
        electorate_median: [0, 0],
        assembly_position: [0.05, 0],
        governing_position: null,
        assembly_gap: 0.05,
        governing_gap: null,
      },
      mirror: [
        { region: 'left_lib', electorate_share: 0.25, assembly_share: 0.25 },
        { region: 'left_cons', electorate_share: 0.25, assembly_share: 0.25 },
        { region: 'right_lib', electorate_share: 0.25, assembly_share: 0.25 },
        { region: 'right_cons', electorate_share: 0.25, assembly_share: 0.25 },
      ],
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
    ballot_type: 'rank_truncated',
    ballot_expressiveness: 0.4,
    ballot_cognitive_load: 0.3,
    sample_ballot: { A: 1, B: 0.5, C: 0 },
    winner_flips: ['irv', 'borda'],
    incompatible_methods: ['star_voting'],
  }),
}));

import { MemoryRouter, Routes, Route } from 'react-router';
import LaboratoirePage from '../LaboratoirePage';
import {
  useElectionStore,
  DEFAULT_PLAYGROUND,
  DEFAULT_CONFIG,
} from '../../stores/useElectionStore';

function renderLab() {
  return render(
    <MemoryRouter initialEntries={['/laboratoire']}>
      <Routes>
        <Route path="/laboratoire" element={<LaboratoirePage />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  localStorage.clear();
  useElectionStore.setState({
    playground: { ...DEFAULT_PLAYGROUND },
    config: { ...DEFAULT_CONFIG },
  });
});

describe('LaboratoirePage', () => {
  it('renders every themed section, collapsed, on first paint', () => {
    renderLab();
    for (const key of [
      'ballot',
      'strategy',
      'values',
      'mechanisms',
      'systems',
      'campaign',
      'temporal',
      'behavioral',
      'analysis',
      'theory',
      'results',
    ]) {
      expect(screen.getByTestId(`lab-${key}-toggle`)).toBeInTheDocument();
    }
    expect(screen.queryByTestId('mech-jury')).not.toBeInTheDocument();
  });

  // First lazy section clicked in the file → pays the cold dynamic-import cost,
  // which under Docker + v8 coverage can exceed the default 5 s test timeout. Give
  // both the test and the wait a generous budget (the sibling tests run warm).
  it('the mechanisms section reveals its leaves lazily', async () => {
    renderLab();
    fireEvent.click(screen.getByTestId('lab-mechanisms-toggle'));
    expect(await screen.findByTestId('mech-jury', {}, { timeout: 15000 })).toBeInTheDocument();
    expect(screen.getByTestId('mech-sortition')).toBeInTheDocument();
    expect(screen.getByTestId('mech-identity')).toBeInTheDocument();
  }, 20000);

  it('the systems section reveals its leaves lazily', async () => {
    renderLab();
    fireEvent.click(screen.getByTestId('lab-systems-toggle'));
    expect(await screen.findByTestId('sys-coalition', {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByTestId('sys-pipeline')).toBeInTheDocument();
  });

  it('the results section reveals its leaves lazily', async () => {
    renderLab();
    fireEvent.click(screen.getByTestId('lab-results-toggle'));
    expect(await screen.findByTestId('res-table', {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByTestId('res-animation')).toBeInTheDocument();
  });

  it('the theory section reveals its leaves lazily', async () => {
    renderLab();
    fireEvent.click(screen.getByTestId('lab-theory-toggle'));
    expect(await screen.findByTestId('thy-sen', {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByTestId('thy-judgment')).toBeInTheDocument();
    expect(screen.getByTestId('thy-polis')).toBeInTheDocument();
  });

  it('the analysis section reveals its leaves lazily', async () => {
    renderLab();
    fireEvent.click(screen.getByTestId('lab-analysis-toggle'));
    expect(await screen.findByTestId('ana-montecarlo', {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByTestId('ana-manipulability')).toBeInTheDocument();
    expect(screen.getByTestId('ana-combined')).toBeInTheDocument();
  });

  it('the values section moves the spotlight with the Lijphart dial and has a granular escape hatch', async () => {
    useElectionStore.setState({
      playground: { ...DEFAULT_PLAYGROUND, mode: 'parliament' },
      config: { ...DEFAULT_CONFIG },
    });
    renderLab();
    fireEvent.click(screen.getByTestId('lab-values-toggle'));
    await waitFor(() => expect(screen.getByTestId('lens-item-pr')).toBeInTheDocument(), {
      timeout: 5000,
    });
    fireEvent.change(screen.getByTestId('lijphart-dial'), { target: { value: '0' } });
    expect(screen.getByTestId('lens-item-fptp')).toHaveTextContent('by your weights');
    fireEvent.change(screen.getByTestId('lijphart-dial'), { target: { value: '1' } });
    expect(screen.getByTestId('lens-item-pr')).toHaveTextContent('by your weights');

    fireEvent.click(screen.getByTestId('lens-granular-toggle'));
    expect(screen.queryByTestId('lijphart-dial')).not.toBeInTheDocument();
    expect(screen.getByTestId('weight-proportionality')).toBeInTheDocument();
  });
});
