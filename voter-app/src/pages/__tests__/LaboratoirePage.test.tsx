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

import { MemoryRouter, Routes, Route, useLocation } from 'react-router';
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
    // Each column's content-error link names the fiche and the electorate it reads.
    const wheres = screen
      .getAllByTestId('report-content-error')
      .map((a) => new URL(a.getAttribute('href')!).searchParams.get('where')!);
    expect(wheres).toHaveLength(2);
    expect(wheres.every((w) => w.startsWith('lab:lab-matrix @ '))).toBe(true);
    expect(wheres[1]).toMatch(/Polaris/);
    fireEvent.click(screen.getByTestId('lab-compare-close'));
    expect(screen.queryByTestId('lab-bench-vs')).not.toBeInTheDocument();
  });

  it('deep-links: ?exp= selects the fiche AND its family; &vsElec= opens the electorate comparison', () => {
    // A fiche that reads the electorate's composition (the values lab), so it has a second column.
    renderLab('/laboratoire?exp=lab-values&vsElec=polarized');
    expect(screen.getByTestId('lab-family-rules')).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByTestId('chip-lab-values')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('lab-bench-vs')).toBeInTheDocument();
  });

  describe('Compare is offered where it changes something', () => {
    it('on a fiche that reads the electorate: the button, and the electorate it reads', () => {
      renderLab('/laboratoire?exp=lab-matrix');
      expect(screen.getByTestId('lab-compare')).toBeInTheDocument();
      expect(screen.getByTestId('lab-elec-label-primary')).toHaveTextContent('Current electorate');
      expect(screen.queryByTestId('lab-elec-note')).not.toBeInTheDocument();
    });

    it('on a fiche that ignores it: no button, and the label says why', () => {
      renderLab('/laboratoire?exp=thy-sen');
      expect(screen.queryByTestId('lab-compare')).not.toBeInTheDocument();
      expect(screen.getByTestId('lab-elec-label-primary')).toHaveTextContent(
        'Same on any electorate mix'
      );
      // The reason is text on the page, not a tooltip a keyboard or a phone never shows.
      expect(screen.getByTestId('lab-elec-note')).toHaveTextContent(/comparing electorates/);
    });

    it('reports a content error from such a fiche without naming an electorate it does not read', () => {
      renderLab('/laboratoire?exp=thy-sen');
      const where = new URL(
        screen.getByTestId('report-content-error').getAttribute('href')!
      ).searchParams.get('where');
      expect(where).toBe('lab:thy-sen @ electorate-independent');
    });

    it('forgets an armed picker when the bench moves on: it does not come back by itself', () => {
      renderLab('/laboratoire?exp=lab-matrix');
      fireEvent.click(screen.getByTestId('lab-compare'));
      expect(screen.getByTestId('lab-elec-picker')).toBeInTheDocument();
      fireEvent.click(screen.getByTestId('lab-family-theory'));
      fireEvent.click(screen.getByTestId('chip-thy-sen'));
      fireEvent.click(screen.getByTestId('lab-family-methods'));
      fireEvent.click(screen.getByTestId('chip-lab-matrix'));
      expect(screen.queryByTestId('lab-elec-picker')).not.toBeInTheDocument();
    });

    it('ignores a stale &vsElec= on such a fiche: the two columns would be the same', () => {
      renderLab('/laboratoire?exp=thy-sen&vsElec=polarized');
      expect(screen.getByTestId('chip-thy-sen')).toHaveAttribute('aria-pressed', 'true');
      expect(screen.queryByTestId('lab-bench-vs')).not.toBeInTheDocument();
      expect(screen.queryByTestId('lab-elec-picker')).not.toBeInTheDocument();
    });

    it('closes the second column when the bench moves to a fiche that ignores the electorate', () => {
      renderLab('/laboratoire?exp=lab-values&vsElec=polarized');
      expect(screen.getByTestId('lab-bench-vs')).toBeInTheDocument();
      fireEvent.click(screen.getByTestId('lab-family-theory'));
      fireEvent.click(screen.getByTestId('chip-thy-sen'));
      expect(screen.queryByTestId('lab-bench-vs')).not.toBeInTheDocument();
      expect(screen.queryByTestId('lab-compare')).not.toBeInTheDocument();
    });

    it('and leaves no stale &vsElec= in the link of a fiche that ignores the electorate', () => {
      let search = '';
      const Probe: React.FC = () => {
        search = useLocation().search;
        return null;
      };
      render(
        <MemoryRouter initialEntries={['/laboratoire?exp=lab-values&vsElec=polarized']}>
          <Routes>
            <Route
              path="/laboratoire"
              element={
                <>
                  <LaboratoirePage />
                  <Probe />
                </>
              }
            />
          </Routes>
        </MemoryRouter>
      );
      expect(search).toContain('vsElec=polarized');
      fireEvent.click(screen.getByTestId('lab-family-theory'));
      fireEvent.click(screen.getByTestId('chip-thy-sen'));
      expect(search).toBe('?exp=thy-sen');
    });

    it('keeps the second column when the bench moves to another fiche that reads it', () => {
      renderLab('/laboratoire?exp=lab-values&vsElec=polarized');
      fireEvent.click(screen.getByTestId('lab-family-methods'));
      fireEvent.click(screen.getByTestId('chip-lab-matrix'));
      expect(screen.getByTestId('lab-bench-vs')).toBeInTheDocument();
    });
  });

  describe('search', () => {
    const search = (q: string) =>
      fireEvent.change(screen.getByTestId('lab-search'), { target: { value: q } });

    it('looks across every family at once, and stands in for the catalogue while it holds words', () => {
      renderLab();
      // The methods catalogue is open: the jury fiche (systems family) is not offered...
      expect(screen.queryByTestId('chip-mech-jury')).not.toBeInTheDocument();
      search('jury');
      // ...until the search finds it, wherever it lives.
      expect(screen.getByTestId('lab-search-results')).toBeInTheDocument();
      expect(screen.getByTestId('chip-mech-jury')).toBeInTheDocument();
      expect(screen.queryByTestId('chip-lab-matrix')).not.toBeInTheDocument();
      expect(screen.getByTestId('lab-search-count')).toHaveTextContent(/fiche/);
    });

    it('says so when nothing matches, with what was typed', () => {
      renderLab();
      search('zzzz');
      expect(screen.getByTestId('lab-search-empty')).toHaveTextContent('No fiche matches “zzzz”.');
      // Said aloud too: the live region carries it, not only the visible line.
      expect(screen.getByTestId('lab-search-count')).toHaveTextContent('No fiche matches “zzzz”.');
      expect(screen.queryByTestId('lab-search-results')?.querySelector('button')).toBeNull();
    });

    it('matches on the group and family names too, not only the fiche title', () => {
      renderLab();
      search('abstention');
      // "Blank vote & abstention" is a family: every fiche in it is a result.
      expect(screen.getByTestId('chip-thy-blank')).toBeInTheDocument();
      expect(screen.getByTestId('chip-blank-divergence')).toBeInTheDocument();
    });

    it('a result opens its fiche and brings its family along; closing the search lands on it', () => {
      renderLab();
      search('jury');
      fireEvent.click(screen.getByTestId('chip-mech-jury'));
      // Escape in the box clears it, and the catalogue of the fiche's family is back, fiche pressed.
      fireEvent.keyDown(screen.getByTestId('lab-search'), { key: 'Escape' });
      expect(screen.queryByTestId('lab-search-results')).not.toBeInTheDocument();
      expect(screen.getByTestId('lab-family-systems')).toHaveAttribute('aria-checked', 'true');
      expect(screen.getByTestId('chip-mech-jury')).toHaveAttribute('aria-pressed', 'true');
    });

    it('picking a family clears the search', () => {
      renderLab();
      search('jury');
      fireEvent.click(screen.getByTestId('lab-family-theory'));
      expect(screen.getByTestId('lab-search')).toHaveValue('');
      expect(screen.queryByTestId('lab-search-results')).not.toBeInTheDocument();
      expect(screen.getByTestId('chip-thy-sen')).toBeInTheDocument();
    });

    it('while results stand in for the catalogue, no family is shown as the one being read', () => {
      renderLab();
      expect(screen.getByTestId('lab-family-methods')).toHaveAttribute('aria-checked', 'true');
      search('jury');
      for (const f of LAB_FAMILIES) {
        expect(screen.getByTestId(`lab-family-${f.id}`)).toHaveAttribute('aria-checked', 'false');
      }
    });

    it('names the family of each result, where several families sit together', () => {
      renderLab();
      search('jury');
      expect(screen.getByTestId('chip-mech-jury')).toHaveTextContent('Systems & mechanisms');
    });

    it('keeps the search on any other key: only Escape clears it', () => {
      renderLab();
      search('jury');
      fireEvent.keyDown(screen.getByTestId('lab-search'), { key: 'a' });
      expect(screen.getByTestId('lab-search')).toHaveValue('jury');
      expect(screen.getByTestId('chip-mech-jury')).toBeInTheDocument();
    });

    it('a lone accent is no search', () => {
      renderLab();
      search('\u0301');
      expect(screen.queryByTestId('lab-search-results')).not.toBeInTheDocument();
      expect(screen.getByTestId('chip-lab-matrix')).toBeInTheDocument();
    });

    it('a blank box is no search: the family catalogue stays', () => {
      renderLab();
      search('   ');
      expect(screen.queryByTestId('lab-search-results')).not.toBeInTheDocument();
      expect(screen.getByTestId('chip-lab-matrix')).toBeInTheDocument();
    });
  });

  it('an unknown ?exp= falls back to the matrix instead of a blank bench', () => {
    renderLab('/laboratoire?exp=does-not-exist');
    expect(screen.getByTestId('lab-bench')).toBeInTheDocument();
    expect(screen.getByTestId('lab-family-methods')).toHaveAttribute('aria-checked', 'true');
  });

  it('the blank-vote fiche opens the reflection: three silences + the four-regime verdicts', async () => {
    renderLab('/laboratoire?exp=thy-blank');
    await waitFor(() => expect(screen.getByTestId('blank-vote-panel')).toBeInTheDocument(), {
      timeout: 15000,
    });
    // Act 1 — the three silences.
    expect(screen.getByTestId('silence-blanc')).toBeInTheDocument();
    // Act 2 — one verdict card per regime, and the "blank wins" preset flips
    // the competitive regime to a re-run.
    fireEvent.click(screen.getByTestId('blank-preset-blankLeads'));
    expect(screen.getByTestId('lens-card-competitive')).toHaveTextContent(/reopens|Do it again/);
  }, 20000);

  it('the blank-vote fiche can switch to the real Playground electorate instead of the hand-set mixer', async () => {
    renderLab('/laboratoire?exp=thy-blank');
    await waitFor(() => expect(screen.getByTestId('blank-vote-panel')).toBeInTheDocument(), {
      timeout: 15000,
    });
    // Manual mode: abstract A/B/C sliders, editable.
    expect(screen.getByTestId('blank-cand-0')).toBeInTheDocument();
    expect(screen.queryByText(DEFAULT_CONFIG.candidates[0].name)).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('blank-real-toggle'));

    // Real mode: the actual Playground candidates, read-only (no more sliders),
    // plus a computed blank share for whoever's too far from all of them.
    expect(screen.getByTestId('blank-real-toggle')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.queryByTestId('blank-cand-0')).not.toBeInTheDocument();
    for (const c of DEFAULT_CONFIG.candidates) {
      expect(screen.getByText(c.name)).toBeInTheDocument();
    }
    expect(screen.getByTestId('blank-real-share')).toHaveTextContent(/%$/);

    // Toggling back restores the hand-set mixer untouched.
    fireEvent.click(screen.getByTestId('blank-real-toggle'));
    expect(screen.getByTestId('blank-cand-0')).toBeInTheDocument();
  }, 20000);

  it('the regime atlas globe renders dots and toggles its colour lens', async () => {
    renderLab('/laboratoire?exp=sys-atlas');
    await waitFor(() => expect(screen.getByTestId('regime-globe')).toBeInTheDocument(), {
      timeout: 15000,
    });
    // At least some regimes are plotted on the front hemisphere.
    expect(screen.getAllByTestId(/^atlas-dot-/).length).toBeGreaterThan(0);
    // The lens toggle flips from method to blank.
    expect(screen.getByTestId('atlas-lens-method')).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(screen.getByTestId('atlas-lens-blank'));
    expect(screen.getByTestId('atlas-lens-blank')).toHaveAttribute('aria-pressed', 'true');
  }, 20000);

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
