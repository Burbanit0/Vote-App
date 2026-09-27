import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Laboratoire fiches read the shared electorate through the concern-split
// playground contexts (useStoreCtx / useInstrumentCtx / useScorecardCtx,
// PLAN_SURFACE_EXTERIEURE.md §2.J). These render each migrated fiche through
// the real catalog, inside a REAL PlaygroundProvider (no context mock), and
// check each wrapper hands its module populated values of the right shape
// from the slices it reads: a non-empty electorate, the configured candidate
// count, dims, the base seed, a resampler, the store's config/mode.
// What this does NOT catch: a swap between two same-shaped fields — e.g.
// pre-turnout `voters` passed where `votingVoters` belongs is indistinguishable
// here, since the default turnout model leaves them the same length. Reading a
// field from a context that doesn't carry it is caught earlier, by tsc.

vi.mock('../../../services/profileApi', () => ({
  runProfileSimulate: vi.fn().mockResolvedValue({
    methods: { plurality: { winner: 'A' } },
    condorcet_winner: 'A',
    inter_method_agreement: 1,
    cycle_rate: 0.1,
    candidate_names: ['A', 'B'],
    display_points: [],
    candidate_points: null,
    num_voters: 300,
    ballot_type: 'rank_truncated',
    ballot_expressiveness: 0.4,
    ballot_cognitive_load: 0.3,
    sample_ballot: { A: 1, B: 0.5 },
    winner_flips: [],
    incompatible_methods: [],
  }),
}));

// The four heavy modules the catalog's wrapper bodies render are stubbed to
// expose the props they received — the wrapper lines under test run for real;
// only the downstream compute is skipped.
vi.mock('../../playground/SincerityModule', () => ({
  default: (p: { voters: unknown[]; candidates: unknown[]; dims: number; you: unknown }) => (
    <div
      data-testid="stub-sincerity"
      data-voters={p.voters.length}
      data-candidates={p.candidates.length}
      data-dims={p.dims}
      data-has-you={String(p.you != null)}
    />
  ),
}));
vi.mock('../../playground/StrategicModule', () => ({
  default: (p: { config: { num_voters: number }; playground: { mode: string } }) => (
    <div
      data-testid="stub-strategic"
      data-num-voters={p.config.num_voters}
      data-mode={p.playground.mode}
    />
  ),
}));
vi.mock('../../playground/EquilibriumModule', () => ({
  default: (p: { voters: unknown[]; candidates: unknown[] }) => (
    <div
      data-testid="stub-equilibrium"
      data-voters={p.voters.length}
      data-candidates={p.candidates.length}
    />
  ),
}));
vi.mock('../../playground/VseModule', () => ({
  default: (p: { sampleAtSeed: unknown; baseSeed: number; candidates: unknown[] }) => (
    <div
      data-testid="stub-vse"
      data-sampler={typeof p.sampleAtSeed}
      data-base-seed={p.baseSeed}
      data-candidates={p.candidates.length}
    />
  ),
}));

// The four theory panels take the shared electorate as plain props (they used
// to take it as optional `lab*` props next to a `labMode` flag that was always
// true). Stubbed to expose what the catalog's wrappers actually hand them.
vi.mock('../../shared/mechanisms/EpistocracyPanel', () => ({
  default: (p: { candidates: unknown[]; numVoters: number; seed: number }) => (
    <div
      data-testid="stub-episto"
      data-candidates={p.candidates.length}
      data-num-voters={p.numVoters}
      data-seed={p.seed}
    />
  ),
}));
vi.mock('../../shared/mechanisms/IdentityVotingPanel', () => ({
  default: (p: { candidates: unknown[]; numVoters: number; seed: number }) => (
    <div
      data-testid="stub-identity"
      data-candidates={p.candidates.length}
      data-num-voters={p.numVoters}
      data-seed={p.seed}
    />
  ),
}));
vi.mock('../../shared/analysis/CollectiveWillPanel', () => ({
  default: (p: { candidates: unknown[]; numVoters: number; seed: number; ideology: string }) => (
    <div
      data-testid="stub-collective"
      data-candidates={p.candidates.length}
      data-num-voters={p.numVoters}
      data-seed={p.seed}
      data-ideology={p.ideology}
    />
  ),
}));
vi.mock('../../shared/analysis/AssumptionTesterPanel', () => ({
  default: (p: { candidates: unknown[]; numVoters: number; seed: number; ideology: string }) => (
    <div
      data-testid="stub-assumptions"
      data-candidates={p.candidates.length}
      data-num-voters={p.numVoters}
      data-seed={p.seed}
      data-ideology={p.ideology}
    />
  ),
}));

import { ALL_EXPERIMENTS } from '../labCatalog';
import { PlaygroundProvider } from '../../playground/PlaygroundController';
import { DEFAULT_CONFIG } from '../../../stores/useElectionStore';

function renderFiche(id: string) {
  const exp = ALL_EXPERIMENTS.find((e) => e.id === id);
  if (!exp) throw new Error(`no catalog entry ${id}`);
  const { Body } = exp;
  return render(
    <PlaygroundProvider>
      <React.Suspense fallback={<div>loading</div>}>
        <Body />
      </React.Suspense>
    </PlaygroundProvider>
  );
}

const CANDIDATES = String(DEFAULT_CONFIG.candidates.length);

describe('Laboratoire fiches read the right playground context slices', () => {
  it('strat-sincerity: live voters + candidates from the instrument, dims from the store', async () => {
    renderFiche('strat-sincerity');
    const stub = await screen.findByTestId('stub-sincerity');
    expect(Number(stub.getAttribute('data-voters'))).toBeGreaterThan(0);
    expect(stub).toHaveAttribute('data-candidates', CANDIDATES);
    expect(stub).toHaveAttribute('data-dims', '2');
    expect(stub).toHaveAttribute('data-has-you', 'true');
  });

  it('strat-vuln: config + playground from the store', async () => {
    renderFiche('strat-vuln');
    const stub = await screen.findByTestId('stub-strategic');
    expect(stub).toHaveAttribute('data-num-voters', String(DEFAULT_CONFIG.num_voters));
    expect(stub).toHaveAttribute('data-mode', 'leader');
  });

  it('strat-equilibrium: live voters + candidates from the instrument', async () => {
    renderFiche('strat-equilibrium');
    const stub = await screen.findByTestId('stub-equilibrium');
    expect(Number(stub.getAttribute('data-voters'))).toBeGreaterThan(0);
    expect(stub).toHaveAttribute('data-candidates', CANDIDATES);
  });

  it('anchor-vse: the resampler + base seed + candidates from the instrument', async () => {
    renderFiche('anchor-vse');
    const stub = await screen.findByTestId('stub-vse');
    expect(stub).toHaveAttribute('data-sampler', 'function');
    expect(stub).toHaveAttribute('data-base-seed', String(DEFAULT_CONFIG.seed));
    expect(stub).toHaveAttribute('data-candidates', CANDIDATES);
  });

  it.each([
    ['mech-epistocracy', 'stub-episto'],
    ['mech-identity', 'stub-identity'],
  ])('%s: the shared electorate reaches the panel as plain props', async (id, testid) => {
    renderFiche(id);
    const stub = await screen.findByTestId(testid);
    expect(stub).toHaveAttribute('data-candidates', CANDIDATES);
    expect(stub).toHaveAttribute('data-num-voters', String(DEFAULT_CONFIG.num_voters));
    expect(stub).toHaveAttribute('data-seed', String(DEFAULT_CONFIG.seed));
  });

  it.each([
    ['ana-collective', 'stub-collective'],
    ['ana-assumptions', 'stub-assumptions'],
  ])('%s: the electorate and the ideology reach the panel', async (id, testid) => {
    renderFiche(id);
    const stub = await screen.findByTestId(testid);
    expect(stub).toHaveAttribute('data-candidates', CANDIDATES);
    expect(stub).toHaveAttribute('data-num-voters', String(DEFAULT_CONFIG.num_voters));
    expect(stub).toHaveAttribute('data-seed', String(DEFAULT_CONFIG.seed));
    expect(stub).toHaveAttribute('data-ideology', DEFAULT_CONFIG.ideology);
  });

  it('lab-duel renders against the real instrument context', async () => {
    renderFiche('lab-duel');
    expect(await screen.findByTestId('duel-verdict')).toBeInTheDocument();
  });

  it('lab-ballot renders against the real store + scorecard contexts', async () => {
    renderFiche('lab-ballot');
    expect(await screen.findByTestId('ballot-select')).toBeInTheDocument();
  });
});
