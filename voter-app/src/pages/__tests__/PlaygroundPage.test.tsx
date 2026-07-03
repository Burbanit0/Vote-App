import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../hooks/useMetaTags', () => ({ useMetaTags: () => {} }));
vi.mock('../../services/assemblyApi', () => {
  // NB: declared inside the factory — vi.mock is hoisted above file-level consts.
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
import PlaygroundPage from '../PlaygroundPage';
import {
  useElectionStore,
  DEFAULT_PLAYGROUND,
  DEFAULT_CONFIG,
} from '../../stores/useElectionStore';

const LS_PG = 'votelab_playground';

// Rendered under a router (the page uses router context).
function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/playground']}>
      <Routes>
        <Route path="/playground" element={<PlaygroundPage />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  localStorage.clear();
  // Reset the module-singleton store to a known baseline between tests.
  useElectionStore.setState({
    playground: { ...DEFAULT_PLAYGROUND },
    config: { ...DEFAULT_CONFIG },
  });
});

describe('PlaygroundPage (P0 shell)', () => {
  it('renders and shows the leader canvas by default', () => {
    renderPage();
    expect(screen.getByTestId('playground-page')).toBeInTheDocument();
    expect(screen.getByTestId('leader-canvas')).toBeInTheDocument();
    expect(screen.queryByTestId('canvas-parliament')).not.toBeInTheDocument();
  });

  it('the lens switch is present once a moment past Électorat is active, with no heavy overlay mounted', () => {
    renderPage();
    // Électorat hides the rule UI — no method has been chosen yet.
    expect(screen.queryByTestId('lens-switch')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('moment-bilan'));
    // The cheap lens control is there from here on; the default 'winner' lens means
    // the probability overlay (and its compute) stays unmounted until selected.
    expect(screen.getByTestId('lens-switch')).toBeInTheDocument();
    expect(screen.getByTestId('lens-winner')).toHaveAttribute('aria-checked', 'true');
    expect(screen.queryByTestId('problens')).not.toBeInTheDocument();
    expect(screen.queryByTestId('lottery-bars')).not.toBeInTheDocument();
  });

  it('switching to the probability lens renders the lottery on the central map', async () => {
    renderPage();
    fireEvent.click(screen.getByTestId('moment-method'));
    fireEvent.click(screen.getByTestId('lens-probability'));
    expect(screen.getByTestId('lottery-bars')).toBeInTheDocument();
    expect(screen.queryByTestId('winregion')).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('problens')).toBeInTheDocument());
  });

  it('switching to the manipulation lens tints voters and states the G-S boundary', async () => {
    renderPage();
    fireEvent.click(screen.getByTestId('moment-method'));
    fireEvent.click(screen.getByTestId('lens-manipulation'));
    expect(screen.queryByTestId('winregion')).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('manip-voters')).toBeInTheDocument());
    expect(screen.getByTestId('manip-summary')).toHaveTextContent(/Gibbard/);
  });

  it('switching to the criteria lens renders the empirical methods × criteria matrix', async () => {
    renderPage();
    fireEvent.click(screen.getByTestId('moment-method'));
    fireEvent.click(screen.getByTestId('lens-criteria'));
    expect(screen.queryByTestId('winregion')).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('criteria-matrix')).toBeInTheDocument());
  });

  it('mode toggle swaps the canvas, reveals assembly knobs, and persists', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('mode-toggle-parliament'));

    expect(screen.getByTestId('canvas-parliament')).toBeInTheDocument();
    expect(screen.queryByTestId('leader-canvas')).not.toBeInTheDocument();
    // Assembly-only knob lives in the Méthode moment.
    fireEvent.click(screen.getByTestId('moment-method'));
    expect(screen.getByLabelText('Structure')).toBeInTheDocument();

    expect(useElectionStore.getState().playground.mode).toBe('parliament');
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).mode).toBe('parliament');
  });

  it('a preset mutates shared electorate + playground state and persists', () => {
    renderPage();
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
    renderPage();
    fireEvent.click(screen.getByTestId('electorate-advanced-toggle'));
    fireEvent.change(screen.getByLabelText('Dimensions of the space'), { target: { value: '3' } });

    expect(useElectionStore.getState().playground.space.dims).toBe(3);
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).space.dims).toBe(3);
  });

  it('the dimension knob reshapes the leader canvas (1-D line, 3-D z controls)', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('electorate-advanced-toggle'));
    const dimsSelect = screen.getByLabelText('Dimensions of the space');
    // 2-D by default: no z controls, canvas tagged dims=2.
    expect(screen.getByTestId('leader-canvas')).toHaveAttribute('data-dims', '2');
    expect(screen.queryByTestId('z-controls')).not.toBeInTheDocument();
    // 1-D → the canvas collapses to a line.
    fireEvent.change(dimsSelect, { target: { value: '1' } });
    expect(screen.getByTestId('leader-canvas')).toHaveAttribute('data-dims', '1');
    // 3-D → per-candidate z sliders appear.
    fireEvent.change(dimsSelect, { target: { value: '3' } });
    expect(screen.getByTestId('leader-canvas')).toHaveAttribute('data-dims', '3');
    expect(screen.getByTestId('z-controls')).toBeInTheDocument();
  });

  it('surfaces the cycle-rate read-out from the profile engine', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('cycle-rate')).toHaveTextContent('12 %'));
  });

  // ── P4: the dynamic layer ────────────────────────────────────────────────

  it('the persistent mode toggle flips leader↔parliament and shows the flip caption', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('mode-toggle-parliament'));
    expect(useElectionStore.getState().playground.mode).toBe('parliament');
    expect(screen.getByTestId('flip-caption')).toHaveTextContent('Same voters');
    // Replayable in the other direction.
    fireEvent.click(screen.getByTestId('mode-toggle-leader'));
    expect(useElectionStore.getState().playground.mode).toBe('leader');
    expect(screen.getByTestId('flip-caption')).toBeInTheDocument();
  });

  it('shake-the-assumptions renders win-rate bands that sum to ~100%', async () => {
    renderPage();
    fireEvent.click(screen.getByTestId('shake-toggle'));
    await waitFor(() => expect(screen.getByTestId('shake-bands')).toHaveTextContent('resamples'), {
      timeout: 5000,
    });
    const text = screen.getByTestId('shake-bands').textContent ?? '';
    // Each candidate row renders its win rate with a Wilson margin as "rate±half%".
    const perCandidate = [...text.matchAll(/(\d+)±\d+%/g)].map((m) => Number(m[1]));
    expect(perCandidate.length).toBeGreaterThanOrEqual(2);
    const sum = perCandidate.reduce((s, p) => s + p, 0);
    expect(sum).toBeGreaterThanOrEqual(97);
    expect(sum).toBeLessThanOrEqual(103);
  });

  it('the Duverger toggle persists strategic desertion in the store', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('mode-toggle-parliament'));
    fireEvent.click(screen.getByTestId('moment-strategy'));
    fireEvent.click(screen.getByTestId('duverger-toggle'));
    expect(useElectionStore.getState().playground.assembly.strategic_desertion).toBe(true);
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).assembly.strategic_desertion).toBe(
      true
    );
  });

  // ── P5: scorecard + values lens ──────────────────────────────────────────

  it('leader mode summarises winners and opens the per-method robustness table', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('moment-bilan'));
    // The verdict synthesis is always visible…
    expect(screen.getByTestId('bilan-verdict')).toBeInTheDocument();
    // …the detailed per-method table lives behind the robustness disclosure.
    expect(screen.queryByTestId('bilan-method-table')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('module-robustness-toggle'));
    expect(screen.getByTestId('bilan-method-table')).toBeInTheDocument();
  });

  it('parliament mode shows the structure scorecard from the backend with bands', async () => {
    renderPage();
    fireEvent.click(screen.getByTestId('mode-toggle-parliament'));
    fireEvent.click(screen.getByTestId('moment-bilan'));
    await waitFor(
      () => expect(screen.getByTestId('axis-proportionality')).toHaveTextContent('90 %'),
      { timeout: 5000 }
    );
  });

  // ── Method moment: multi-select rule checkboxes ──────────────────────────

  it('the method moment shows rule checkboxes and toggling updates the set', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('moment-method'));
    const pluralityCheck = screen.getByTestId('rule-check-plurality').querySelector('input')!;
    expect(pluralityCheck.checked).toBe(true);
    fireEvent.click(pluralityCheck);
    expect(pluralityCheck.checked).toBe(false);
    // Select-all restores it
    fireEvent.click(screen.getByTestId('rules-select-all'));
    expect(pluralityCheck.checked).toBe(true);
  });

  // ── FC-1 : manipulation, principe vs pratique ────────────────────────────

  it('the hardness readout shows the complexity flag for the selected rule', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('moment-strategy'));
    expect(screen.getByTestId('manip-hardness')).toHaveTextContent('Gibbard–Satterthwaite');
    expect(screen.getByTestId('manip-hardness')).toHaveTextContent('P (trivial)');
    // Switch to IRV → the NP-hardness flag and its citation appear.
    fireEvent.change(screen.getByTestId('rule-select'), { target: { value: 'irv' } });
    expect(screen.getByTestId('manip-hardness')).toHaveTextContent('NP-hard');
    expect(screen.getByTestId('manip-hardness')).toHaveTextContent('Bartholdi–Orlin');
    // The worked example compares plurality vs IRV on this electorate.
    expect(screen.getByTestId('manip-hardness')).toHaveTextContent('Example');
  });

  // ── FA-2 : la lentille Lijphart ───────────────────────────────────────────

  it('parliament mode renders the democracy map with the three live structures', async () => {
    renderPage();
    fireEvent.click(screen.getByTestId('mode-toggle-parliament'));
    // Advanced modules ship collapsed (progressive disclosure) — open it first.
    await waitFor(() => expect(screen.getByTestId('module-democracy-toggle')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('module-democracy-toggle'));
    await waitFor(() => expect(screen.getByTestId('democracy-map')).toBeInTheDocument(), {
      timeout: 5000,
    });
    expect(screen.getByTestId('dm-pr')).toBeInTheDocument();
    expect(screen.getByTestId('dm-fptp')).toBeInTheDocument();
  });

  // ── Réalisme électoral : participation / abstention ──────────────────────

  it('the turnout control persists and the live rate drops under abstention', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('moment-strategy'));
    fireEvent.change(screen.getByTestId('turnout-select'), { target: { value: 'alienation' } });
    expect(useElectionStore.getState().playground.turnout.model).toBe('alienation');
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).turnout.model).toBe('alienation');
    fireEvent.change(screen.getByTestId('turnout-intensity'), { target: { value: '0.9' } });
    const rate = screen.getByTestId('turnout-rate').textContent ?? '';
    const pct = Number((rate.match(/(\d+)\s?%/) ?? [])[1]);
    expect(pct).toBeLessThan(100);
  });

  it('the advanced modules are collapsed by default and open on demand', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('mode-toggle-parliament'));
    expect(screen.getByTestId('module-structural')).toBeInTheDocument();
    expect(screen.queryByTestId('structural-panel')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('module-structural-toggle'));
    expect(screen.getByTestId('structural-panel')).toBeInTheDocument();
  });

  // The Lijphart dial + values/Pareto lens moved to /laboratoire (see
  // LaboratoirePage.test.tsx) — same PlaygroundController state, different surface.

  // ── Composer l'électorat : moteur d'électorat ─────────────────────────────

  it('the electorate composer ships collapsed and opens on demand', () => {
    renderPage();
    expect(screen.getByTestId('module-electorate')).toBeInTheDocument();
    expect(screen.queryByTestId('electorate-composer')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('module-electorate-toggle'));
    expect(screen.getByTestId('electorate-composer')).toBeInTheDocument();
    // Defaults to the simple gaussian; community editing is hidden until composed.
    expect(screen.queryByTestId('community-list')).not.toBeInTheDocument();
  });

  it('switching to a composed electorate persists, reveals blocs and a colour legend', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('module-electorate-toggle'));
    fireEvent.click(screen.getByTestId('electorate-mode-composed'));

    expect(useElectionStore.getState().playground.electorate.mode).toBe('composed');
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).electorate.mode).toBe('composed');
    expect(screen.getByTestId('community-list')).toBeInTheDocument();
    // The leader cloud is now coloured by community → a legend appears.
    expect(screen.getByTestId('electorate-legend')).toBeInTheDocument();
  });

  it('a composed preset and add/remove community mutate the store', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('module-electorate-toggle'));
    fireEvent.click(screen.getByTestId('electorate-mode-composed'));
    fireEvent.change(screen.getByTestId('electorate-preset-select'), {
      target: { value: 'fragmented' },
    });

    const e1 = useElectionStore.getState().playground.electorate;
    expect(e1.mode).toBe('composed');
    const n = e1.communities.length;
    fireEvent.click(screen.getByTestId('community-add'));
    expect(useElectionStore.getState().playground.electorate.communities).toHaveLength(n + 1);
  });

  it('the sample controls (voter count, seed, ideology) update the shared config', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('module-electorate-toggle'));
    // Voter count + seed apply in both modes (simple by default).
    fireEvent.change(screen.getByTestId('electorate-num-voters'), { target: { value: '750' } });
    expect(useElectionStore.getState().config.num_voters).toBe(750);
    fireEvent.change(screen.getByTestId('electorate-seed'), { target: { value: '1234' } });
    expect(useElectionStore.getState().config.seed).toBe(1234);
    // Re-roll changes the seed to something else (new electorate draw).
    fireEvent.click(screen.getByTestId('electorate-seed-reroll'));
    expect(useElectionStore.getState().config.seed).not.toBe(1234);
    // Ideology is a simple-mode-only knob (composed overrides it).
    fireEvent.change(screen.getByTestId('electorate-ideology'), { target: { value: 'polarized' } });
    expect(useElectionStore.getState().config.ideology).toBe('polarized');
    fireEvent.click(screen.getByTestId('electorate-mode-composed'));
    expect(screen.queryByTestId('electorate-ideology')).not.toBeInTheDocument();
  });

  it('the measurement-noise slider persists to the electorate', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('module-electorate-toggle'));
    fireEvent.click(screen.getByTestId('electorate-mode-composed'));
    fireEvent.change(screen.getByTestId('electorate-noise'), { target: { value: '0.5' } });
    expect(useElectionStore.getState().playground.electorate.noise).toBe(0.5);
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).electorate.noise).toBe(0.5);
  });

  it('per-community z sliders appear only when the map is in 3-D', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('module-electorate-toggle'));
    fireEvent.click(screen.getByTestId('electorate-mode-composed'));
    // 2-D by default: no z sliders.
    expect(screen.queryByTestId('community-z-g')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('electorate-advanced-toggle'));
    fireEvent.change(screen.getByLabelText('Dimensions of the space'), { target: { value: '3' } });
    expect(screen.getByTestId('community-z-g')).toBeInTheDocument();
  });

  it('importing a JSON composition replaces the electorate (données d’entrée)', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('module-electorate-toggle'));
    fireEvent.click(screen.getByTestId('electorate-mode-composed'));
    const payload = JSON.stringify({
      correlation: 0.5,
      noise: 0.2,
      communities: [
        { id: 'x', label: 'Importé', x: -0.4, y: 0.1, spread: 0.2, weight: 2, turnout: 0.7 },
      ],
    });
    fireEvent.change(screen.getByTestId('electorate-json'), { target: { value: payload } });
    fireEvent.click(screen.getByTestId('electorate-import'));

    const e = useElectionStore.getState().playground.electorate;
    expect(e.mode).toBe('composed');
    expect(e.correlation).toBe(0.5);
    expect(e.noise).toBe(0.2);
    expect(e.communities).toHaveLength(1);
    expect(e.communities[0].label).toBe('Importé');
  });

  it('a malformed import surfaces an error and leaves the electorate intact', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('module-electorate-toggle'));
    fireEvent.click(screen.getByTestId('electorate-mode-composed'));
    const before = useElectionStore.getState().playground.electorate.communities.length;
    fireEvent.change(screen.getByTestId('electorate-json'), { target: { value: '{ not json' } });
    fireEvent.click(screen.getByTestId('electorate-import'));
    expect(screen.getByTestId('electorate-json-error')).toBeInTheDocument();
    expect(useElectionStore.getState().playground.electorate.communities).toHaveLength(before);
  });

  // ── FORM-LOCK: the absorbed Lab phenomena must never deteriorate the core ──
  // The deep Lab families (mechanisms, systems, results, analysis, theory) now
  // live entirely on /laboratoire (see LaboratoirePage.test.tsx) — the playground
  // mounts none of them, at any moment.

  it('form-lock: no Lab module is mounted on first paint', () => {
    renderPage();
    // The two-mode core is intact and visible.
    expect(screen.getByTestId('leader-canvas')).toBeInTheDocument();
    expect(screen.getByTestId('cycle-rate')).toBeInTheDocument();
    // The old terminal catch-all is gone.
    expect(screen.queryByTestId('module-advanced')).not.toBeInTheDocument();
    for (const panel of ['mech-jury', 'ana-montecarlo', 'res-table', 'sys-coalition', 'thy-sen']) {
      expect(screen.queryByTestId(panel)).not.toBeInTheDocument();
    }
  });

  it('campaign is folded in as moment ④, with no loose mechanics on the static moments', () => {
    renderPage();
    // No legacy campaign mechanics leak onto the snapshot moments.
    for (const id of [
      'campaign-scrubber',
      'campaign-slider',
      'launch-campaign',
      'behavior-realism-link',
      'module-temporal',
      'anchor-campaign',
    ]) {
      expect(screen.queryByTestId(id)).not.toBeInTheDocument();
    }
    // The journey rail carries the four moments; the core canvas is on the default one.
    expect(screen.getByTestId('moment-rail')).toBeInTheDocument();
    for (const m of ['electorate', 'method', 'strategy', 'campaign', 'bilan']) {
      expect(screen.getByTestId(`moment-${m}`)).toBeInTheDocument();
    }
    expect(screen.getByTestId('leader-canvas')).toBeInTheDocument();
    // Entering the campaign moment swaps the static instrument for the timeline.
    fireEvent.click(screen.getByTestId('moment-campaign'));
    expect(screen.getByTestId('moment-campaign-panel')).toBeInTheDocument();
    expect(screen.queryByTestId('leader-canvas')).not.toBeInTheDocument();
  });
});
