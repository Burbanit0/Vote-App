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

// The page navigates (drill-downs to the Lab), so render it under a router with
// a probe route standing in for /election-lab.
function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/playground']}>
      <Routes>
        <Route path="/playground" element={<PlaygroundPage />} />
        <Route path="/election-lab" element={<div data-testid="lab-probe" />} />
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

  it('mode toggle swaps the canvas, reveals assembly knobs, and persists', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('mode-toggle-parliament'));

    expect(screen.getByTestId('canvas-parliament')).toBeInTheDocument();
    expect(screen.queryByTestId('leader-canvas')).not.toBeInTheDocument();
    // Assembly-only knob appears in parliament mode.
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
    fireEvent.change(screen.getByLabelText('Dimensions de l’espace'), { target: { value: '3' } });

    expect(useElectionStore.getState().playground.space.dims).toBe(3);
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).space.dims).toBe(3);
  });

  it('the dimension knob reshapes the leader canvas (1-D line, 3-D z controls)', () => {
    renderPage();
    const dimsSelect = screen.getByLabelText('Dimensions de l’espace');
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

  it('the flip button toggles the mode and shows the flip caption', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('flip-button'));
    expect(useElectionStore.getState().playground.mode).toBe('parliament');
    expect(screen.getByTestId('flip-caption')).toHaveTextContent('Mêmes électeurs');
    // Replayable in the other direction.
    fireEvent.click(screen.getByTestId('flip-button'));
    expect(useElectionStore.getState().playground.mode).toBe('leader');
    expect(screen.getByTestId('flip-caption')).toBeInTheDocument();
  });

  it('the campaign scrubber advances the day label and disables candidate edits', () => {
    renderPage();
    fireEvent.change(screen.getByTestId('campaign-slider'), { target: { value: '0.5' } });
    expect(screen.getByTestId('campaign-scrubber')).toHaveTextContent('J15');
    expect(screen.getByTestId('campaign-scrubber')).toHaveTextContent('revenez à J0');
  });

  it('shake-the-assumptions renders win-rate bands that sum to ~100%', async () => {
    renderPage();
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
    renderPage();
    fireEvent.click(screen.getByTestId('mode-toggle-parliament'));
    fireEvent.click(screen.getByTestId('duverger-toggle'));
    expect(useElectionStore.getState().playground.assembly.strategic_desertion).toBe(true);
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).assembly.strategic_desertion).toBe(
      true
    );
  });

  // ── P5: scorecard + values lens ──────────────────────────────────────────

  it('leader mode renders the banded scorecard and the values lens over the 6 rules', async () => {
    renderPage();
    await waitFor(
      () => expect(screen.getByTestId('axis-condorcet_efficiency').textContent).toMatch(/\d+\s?%/),
      { timeout: 5000 }
    );
    expect(screen.getByTestId('values-panel')).toBeInTheDocument();
    expect(screen.getByTestId('lens-item-condorcet')).toBeInTheDocument();
    expect(screen.getByTestId('lens-item-plurality')).toBeInTheDocument();
  });

  it('parliament mode shows the structure scorecard from the backend with bands', async () => {
    renderPage();
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

  // ── FA-1 : la couche bulletin ─────────────────────────────────────────────

  it('the ballot selector persists and reveals the truncation slider', () => {
    renderPage();
    fireEvent.change(screen.getByTestId('ballot-select'), {
      target: { value: 'rank_truncated' },
    });
    expect(useElectionStore.getState().playground.ballot.type).toBe('rank_truncated');
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).ballot.type).toBe('rank_truncated');
    fireEvent.change(screen.getByTestId('ballot-truncate'), { target: { value: '2' } });
    expect(useElectionStore.getState().playground.ballot.truncate_at).toBe(2);
  });

  it('shows the sample ballot, the expressiveness/load trade-off and the winner flips', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('ballot-preview')).toBeInTheDocument());
    expect(screen.getByTestId('ballot-preview').textContent).toContain('A 1');
    expect(screen.getByTestId('ballot-tradeoff')).toHaveTextContent('Expressivité');
    expect(screen.getByTestId('ballot-tradeoff')).toHaveTextContent('Charge cognitive');
    expect(screen.getByTestId('ballot-flips')).toHaveTextContent('2 méthodes');
    expect(screen.getByTestId('ballot-flips')).toHaveTextContent('irv, borda');
  });

  // ── FC-1 : manipulation, principe vs pratique ────────────────────────────

  it('the hardness readout shows the complexity flag for the selected rule', () => {
    renderPage();
    expect(screen.getByTestId('manip-hardness')).toHaveTextContent('Gibbard–Satterthwaite');
    expect(screen.getByTestId('manip-hardness')).toHaveTextContent('P (calcul trivial)');
    // Switch to IRV → the NP-hardness flag and its citation appear.
    fireEvent.change(screen.getByTestId('rule-select'), { target: { value: 'irv' } });
    expect(screen.getByTestId('manip-hardness')).toHaveTextContent('NP-difficile');
    expect(screen.getByTestId('manip-hardness')).toHaveTextContent('Bartholdi–Orlin');
    // The worked example compares plurality vs IRV on this electorate.
    expect(screen.getByTestId('manip-hardness')).toHaveTextContent('Exemple');
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
    fireEvent.change(screen.getByTestId('turnout-select'), { target: { value: 'alienation' } });
    expect(useElectionStore.getState().playground.turnout.model).toBe('alienation');
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).turnout.model).toBe('alienation');
    fireEvent.change(screen.getByTestId('turnout-intensity'), { target: { value: '0.9' } });
    // The live participation read-out appears and reports below 100%.
    const rate = screen.getByTestId('turnout-rate').textContent ?? '';
    const pct = Number((rate.match(/(\d+)\s?%/) ?? [])[1]);
    expect(pct).toBeLessThan(100);
  });

  it('the sincere-vote module is collapsed in leader mode and opens with a live verdict', () => {
    renderPage();
    expect(screen.getByTestId('module-sincerity')).toBeInTheDocument();
    expect(screen.queryByTestId('sincerity-module')).not.toBeInTheDocument();
    // The "you" marker is only on the map while the module is open.
    expect(screen.queryByTestId('you-marker')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('module-sincerity-toggle'));
    expect(screen.getByTestId('sincerity-module')).toBeInTheDocument();
    expect(screen.getByTestId('you-marker')).toBeInTheDocument();
    // Live (no button): the headline + bloc control render immediately.
    expect(screen.getByTestId('sincerity-headline')).toHaveTextContent('/15 méthodes');
    expect(screen.getByTestId('sincerity-bloc')).toBeInTheDocument();
    // The electorate sweep is on-demand and renders a per-method ranking.
    expect(screen.queryByTestId('sincerity-scan')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('sincerity-scan-run'));
    expect(screen.getByTestId('sincerity-scan')).toHaveTextContent('minimise le vote utile');
  });

  it('the strategic-vulnerability module is collapsed in leader mode, opens on demand', () => {
    renderPage();
    expect(screen.getByTestId('module-strategic')).toBeInTheDocument();
    expect(screen.queryByTestId('strategic-module')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('module-strategic-toggle'));
    expect(screen.getByTestId('strategic-module')).toBeInTheDocument();
    expect(screen.getByTestId('strategic-run')).toBeInTheDocument();
  });

  it('the advanced modules are collapsed by default and open on demand', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('mode-toggle-parliament'));
    expect(screen.getByTestId('module-structural')).toBeInTheDocument();
    expect(screen.queryByTestId('structural-panel')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('module-structural-toggle'));
    expect(screen.getByTestId('structural-panel')).toBeInTheDocument();
  });

  it('the identity dial moves the spotlight along the frontier', async () => {
    renderPage();
    fireEvent.click(screen.getByTestId('mode-toggle-parliament'));
    await waitFor(() => expect(screen.getByTestId('lens-item-pr')).toBeInTheDocument(), {
      timeout: 5000,
    });
    // Majoritarian end → governability wins → FPTP spotlighted.
    fireEvent.change(screen.getByTestId('lijphart-dial'), { target: { value: '0' } });
    expect(screen.getByTestId('lens-item-fptp')).toHaveTextContent('selon vos pondérations');
    // Consensualist end → proportional axes win → PR spotlighted.
    fireEvent.change(screen.getByTestId('lijphart-dial'), { target: { value: '1' } });
    expect(screen.getByTestId('lens-item-pr')).toHaveTextContent('selon vos pondérations');
  });

  it('the granular escape hatch reveals the sliders and a touch switches modes', async () => {
    renderPage();
    // Dial mode by default: granular sliders not rendered.
    expect(screen.getByTestId('lijphart-dial')).toBeInTheDocument();
    expect(screen.queryByTestId('weight-condorcet_efficiency')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('lens-granular-toggle'));
    expect(screen.queryByTestId('lijphart-dial')).not.toBeInTheDocument();
    expect(screen.getByTestId('weight-condorcet_efficiency')).toBeInTheDocument();
  });

  // ── Drill-downs Playground → Lab (shared electorate) ─────────────────────

  it('a scorecard axis drill-down navigates to the matching Lab tab', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('drill-strategic_resistance'));
    expect(screen.getByTestId('lab-probe')).toBeInTheDocument();
  });

  it('the cycle-rate read-out drills into the Lab', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('drill-ctl-manipulability'));
    expect(screen.getByTestId('lab-probe')).toBeInTheDocument();
  });

  it('the Duverger toggle drills into party dynamics', () => {
    renderPage();
    fireEvent.click(screen.getByTestId('mode-toggle-parliament'));
    fireEvent.click(screen.getByTestId('drill-ctl-party-dynamics'));
    expect(screen.getByTestId('lab-probe')).toBeInTheDocument();
  });

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
    fireEvent.click(screen.getByTestId('electorate-preset-fragmented'));

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
    // 2-D by default: no z sub-list.
    expect(screen.queryByTestId('community-z-list')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Dimensions de l’espace'), { target: { value: '3' } });
    expect(screen.getByTestId('community-z-list')).toBeInTheDocument();
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
});
