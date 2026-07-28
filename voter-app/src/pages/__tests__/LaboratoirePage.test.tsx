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
import { LAB_FAMILIES } from '../../components/lab/labCatalog';
import {
  useElectionStore,
  DEFAULT_PLAYGROUND,
  DEFAULT_CONFIG,
} from '../../stores/useElectionStore';

function renderLab(url = '/laboratoire') {
  return render(
    <MemoryRouter initialEntries={[url]}>
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

describe('LaboratoirePage — the bench', () => {
  it('opens on the family rail, the methods catalogue and ONE bench (the matrix)', () => {
    renderLab();
    for (const f of LAB_FAMILIES) {
      expect(screen.getByTestId(`lab-family-${f.id}`)).toBeInTheDocument();
    }
    expect(screen.getByTestId('lab-family-methods')).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByTestId('lab-bench')).toBeInTheDocument();
    expect(screen.queryByTestId('lab-bench-vs')).not.toBeInTheDocument();
    expect(screen.getByTestId('chip-lab-matrix')).toHaveAttribute('aria-pressed', 'true');
  });

  it('mounts nothing beyond the picked fiche — no stacked accordions anywhere', () => {
    renderLab();
    // Former anchor leaves are neither mounted nor even offered as chips while
    // another family's catalogue is open: content is data now, not 48 collapsed
    // panels waiting in the page.
    for (const id of ['mech-jury', 'sys-coalition', 'thy-sen', 'ana-montecarlo']) {
      expect(screen.queryByTestId(id)).not.toBeInTheDocument();
      expect(screen.queryByTestId(`chip-${id}`)).not.toBeInTheDocument();
    }
  });

  it('switching family swaps the catalogue but keeps the bench', () => {
    renderLab();
    fireEvent.click(screen.getByTestId('lab-family-theory'));
    expect(screen.getByTestId('chip-thy-sen')).toBeInTheDocument();
    expect(screen.getByTestId('chip-ana-montecarlo')).toBeInTheDocument();
    // The bench still shows the previously picked fiche.
    expect(screen.getByTestId('lab-bench')).toBeInTheDocument();
    expect(screen.queryByTestId('lab-bench-vs')).not.toBeInTheDocument();
  });

  // First lazy chunk clicked in the file → pays the cold dynamic-import cost,
  // which under Docker + v8 coverage can exceed the default timeout (same note
  // as the old accordion test carried).
  it('picking a chip puts that experiment on the bench', async () => {
    renderLab();
    fireEvent.click(screen.getByTestId('lab-family-theory'));
    fireEvent.click(screen.getByTestId('chip-thy-sen'));
    expect(screen.getByTestId('chip-thy-sen')).toHaveAttribute('aria-pressed', 'true');
    // The fiche header names the experiment; its panel loads into the bench.
    await waitFor(() => expect(screen.getByTestId('lab-bench')).toHaveTextContent(/Sen/), {
      timeout: 15000,
    });
  }, 20000);

  it('compare: arms the electorate picker, opens the SAME fiche on a second electorate, closes it', () => {
    renderLab();
    fireEvent.click(screen.getByTestId('lab-compare'));
    expect(screen.getByTestId('lab-elec-picker')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('lab-elec-polarized'));
    // The second column appears, labelled with the electorate it reads.
    expect(screen.getByTestId('lab-bench-vs')).toBeInTheDocument();
    expect(screen.getByTestId('lab-elec-label-vs')).toHaveTextContent(/Polaris/);
    fireEvent.click(screen.getByTestId('lab-compare-close'));
    expect(screen.queryByTestId('lab-bench-vs')).not.toBeInTheDocument();
  });

  it('deep-links: ?exp= selects the fiche AND its family; &vsElec= opens the electorate comparison', () => {
    renderLab('/laboratoire?exp=thy-sen&vsElec=polarized');
    expect(screen.getByTestId('lab-family-theory')).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByTestId('chip-thy-sen')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('lab-bench-vs')).toBeInTheDocument();
  });

  it('an unknown ?exp= falls back to the matrix instead of a blank bench', () => {
    renderLab('/laboratoire?exp=does-not-exist');
    expect(screen.getByTestId('lab-bench')).toBeInTheDocument();
    expect(screen.getByTestId('lab-family-methods')).toHaveAttribute('aria-checked', 'true');
  });

  it('the method gallery now covers common methods too, each with its everyday analogy', async () => {
    renderLab('/laboratoire?exp=lab-gallery');
    // A common method (IRV) — previously absent from the gallery — now has a card…
    const card = await waitFor(() => screen.getByTestId('gallery-irv'), { timeout: 15000 });
    // …carrying the "comme dans la vie" analogy line (tests run in English).
    expect(card).toHaveTextContent('Like real life:');
    expect(card).toHaveTextContent(/knockout game/);
  }, 20000);

  // Ported from the old accordion suite: the values panel's Lijphart dial must
  // survive the redesign (it now lives behind Règles & stratégie → Valeurs).
  it('the values fiche keeps the Lijphart dial and its granular escape hatch', async () => {
    useElectionStore.setState({
      playground: { ...DEFAULT_PLAYGROUND, mode: 'parliament' },
      config: { ...DEFAULT_CONFIG },
    });
    renderLab('/laboratoire?exp=lab-values');
    await waitFor(() => expect(screen.getByTestId('lens-item-pr')).toBeInTheDocument(), {
      timeout: 15000,
    });
    fireEvent.change(screen.getByTestId('lijphart-dial'), { target: { value: '0' } });
    expect(screen.getByTestId('lens-item-fptp')).toHaveTextContent('by your weights');
    fireEvent.change(screen.getByTestId('lijphart-dial'), { target: { value: '1' } });
    expect(screen.getByTestId('lens-item-pr')).toHaveTextContent('by your weights');

    fireEvent.click(screen.getByTestId('lens-granular-toggle'));
    expect(screen.queryByTestId('lijphart-dial')).not.toBeInTheDocument();
    expect(screen.getByTestId('weight-proportionality')).toBeInTheDocument();
  }, 20000);
});
