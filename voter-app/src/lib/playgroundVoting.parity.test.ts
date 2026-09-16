import { describe, it, expect } from 'vitest';
import { ruleWinnerFromRanks, type Rule } from './playgroundVoting';
import fixtureJson from './__fixtures__/engineParity.json';

// Engine parity: the Playground computes winners client-side, but the repo's
// authoritative engine is the tested Python backend. These golden winners come
// from it (fast_api_voter/scripts/gen_engine_parity.py); here we assert the TS
// client returns the same winner on the same ranking profile — one source of
// truth, not two that silently drift.
//
// Only STRICT winners are in the fixture: each survives 200 candidate-relabel +
// ballot-shuffle trials, so a mismatch is a real algorithmic divergence, never a
// tie-break convention. Voter counts are odd → strict pairwise majorities.

interface Scenario {
  candidates: string[];
  ballots: string[][];
  winners: Record<string, string | null>;
}
const fixture = fixtureJson as { scenarios: Scenario[] };

const prepared = fixture.scenarios.map((sc) => {
  const idxOf: Record<string, number> = {};
  sc.candidates.forEach((name, i) => (idxOf[name] = i));
  return {
    m: sc.candidates.length,
    candidates: sc.candidates,
    ranks: sc.ballots.map((b) => b.map((name) => idxOf[name])),
    winners: sc.winners,
  };
});

const RULES = Object.keys(fixture.scenarios[0].winners) as Rule[];

function mismatchesFor(rule: Rule): string[] {
  const out: string[] = [];
  prepared.forEach((s, i) => {
    const expected = s.winners[rule];
    if (expected == null) return; // backend has no winner (e.g. Condorcet cycle)
    const got = s.candidates[ruleWinnerFromRanks(s.ranks, s.m, rule)];
    if (got !== expected) out.push(`#${i}: client=${got} backend=${expected}`);
  });
  return out;
}

// Methods whose client implementation does NOT match the authoritative backend
// on strict profiles — a real divergence this harness surfaced — pinned to the
// EXACT mismatch list, not a count: a different set of the same size is a new
// divergence, and reconciling one side turns the list stale, so neither slips by
// silently. Reconcile, regenerate (gen_engine_parity.py), then delete the entry.
const KNOWN_DIVERGENT: Partial<Record<Rule, string[]>> = {
  // Backend bug, not a modelling choice (PLAN_SURFACE_EXTERIEURE.md §2.E). The
  // client's winMajorityJudgment is the textbook Balinski–Laraki procedure:
  // strip the tied median grade until the candidates separate. The backend's
  // get_majority_judgment_winner ranks equal medians by p − q instead, which is
  // not the majority gauge (+p if p > q, else −q); all six below come from that
  // ordering, and the gauge picks the client's winner on each. Two further
  // backend gaps don't show up in this fixture: it strips at most once and only
  // the top two, and it compares p and q as floats, so an exact tie can be
  // decided by rounding.
  majority_judgment: [
    '#6: client=C backend=A',
    '#13: client=B backend=A',
    '#21: client=D backend=C',
    '#32: client=A backend=C',
    '#36: client=C backend=A',
    '#58: client=D backend=E',
  ],
};

describe('engine parity — client ruleWinnerFromRanks == backend golden winners', () => {
  it('has a non-trivial fixture', () => {
    expect(prepared.length).toBeGreaterThanOrEqual(40);
  });

  it.each(RULES)('%s matches the backend on every strict scenario', (rule) => {
    expect(mismatchesFor(rule)).toEqual(KNOWN_DIVERGENT[rule] ?? []);
  });
});

// ── Exhaustive small-profile domain (Lot 4.3, PLAN_SOLIDITE_TECHNIQUE.md) ──────
// Every possible ordinal profile for n<=3 candidates and m<=5 voters (481 total,
// see gen_engine_parity.py's generate_exhaustive_scenarios) — a PROOF over that
// whole bounded domain, not a sample of it. Unlike the random scenarios above,
// winners here are raw (not strict_winner-filtered): backend `None` must match
// client `-1` exactly, including every tied/degenerate case. That's deliberate —
// strict_winner's relabel-robustness filter would silently skip exactly the
// profiles where 4 of the 5 real bugs this exhaustive check found were hiding.
const exhaustive = (fixtureJson as { exhaustiveScenarios: Scenario[] }).exhaustiveScenarios;

const preparedExhaustive = exhaustive.map((sc) => {
  const idxOf: Record<string, number> = {};
  sc.candidates.forEach((name, i) => (idxOf[name] = i));
  return {
    m: sc.candidates.length,
    candidates: sc.candidates,
    ranks: sc.ballots.map((b) => b.map((name) => idxOf[name])),
    winners: sc.winners,
  };
});

const EXHAUSTIVE_RULES = Object.keys(exhaustive[0].winners) as Rule[];

function exhaustiveMismatchesFor(rule: Rule): string[] {
  const out: string[] = [];
  preparedExhaustive.forEach((s, i) => {
    const expected = s.winners[rule];
    const idx = ruleWinnerFromRanks(s.ranks, s.m, rule);
    const got = idx >= 0 ? s.candidates[idx] : null;
    if (got !== expected) out.push(`#${i}: client=${got} backend=${expected}`);
  });
  return out;
}

describe('engine parity — EXHAUSTIVE small-profile domain (n<=3 candidates, m<=5 voters)', () => {
  it('covers the full n<=3, m<=5 domain', () => {
    expect(preparedExhaustive.length).toBe(481);
  });

  it.each(EXHAUSTIVE_RULES)('%s matches the backend on EVERY profile, ties and all', (rule) => {
    expect(exhaustiveMismatchesFor(rule)).toEqual([]);
  });
});

// ── Cardinal rules — per-voter score ballots, strict winners only. Three
// fixture sections share this shape and these checks:
// - cardinalScenarios: score / STAR / cumulative / maximin / nash over one
//   shared 0-5 score matrix.
// - approvalScenarios / majorityJudgmentScenarios: each engine derives those
//   two ballots from raw utility differently (see gen_engine_parity.py's
//   CARDINAL comment), so they're fed ballots at the exact values both sides
//   read identically instead — 0/1 approvals, and 0-5 MJ grades (divided by 5
//   below, since the client's MJ quantiser reads a [0, 1] score). That locks
//   the count, not the ballot derivation, which still differs.
interface CardinalScenario {
  candidates: string[];
  scores: number[][];
  winners: Record<string, string | null>;
}
const { cardinalScenarios, approvalScenarios, majorityJudgmentScenarios } = fixtureJson as Record<
  'cardinalScenarios' | 'approvalScenarios' | 'majorityJudgmentScenarios',
  CardinalScenario[]
>;

const prepareCardinal = (sc: CardinalScenario) => ({
  m: sc.candidates.length,
  candidates: sc.candidates,
  scores: sc.scores,
  // Ranks (best→worst) only satisfy ruleWinnerFromRanks' shape; cardinal rules read `scores`.
  ranks: sc.scores.map((row) => row.map((_, i) => i).sort((a, b) => row[b] - row[a])),
  winners: sc.winners,
});

// Enough strict winners that "no mismatches" means something: a backend change
// that nulls every winner would otherwise pass by comparing nothing.
const MIN_STRICT_WINNERS = 40;

// maximin is structurally far tie-ier than the other four cardinal rules: it
// picks the candidate whose WORST rating is highest, and with the 0-5 integer
// score range and n>=21 voters this file uses everywhere, a given candidate's
// worst rating lands on 0 with probability 1-(5/6)^21 ~= 98% -- so most
// scenarios have two or more candidates tied for the minimum, and it's that
// tie a shared position/key-order convention used to resolve (see
// strict_winner_cardinal's docstring in gen_engine_parity.py). Once
// shuffle_keys=True stopped letting that convention pass as "strict"
// (PLAN_SURFACE_EXTERIEURE.md §2.E), maximin's genuinely tie-free rate over
// the existing (m, n) grid measured at ~1.7% (1/60 in the committed fixture,
// corroborated by a standalone probe over hundreds of scenarios that put the
// true rate in the 1-3% range depending on (m, n)). Reaching the usual
// MIN_STRICT_WINNERS=40 would need ~2400 scenarios at that rate -- which, at
// this fixture's measured ~713 bytes/cardinal-scenario, would add >1.6MB and
// blow the committed fixture (already at 459KB) well past the repo's 500KB
// check-added-large-files pre-commit budget (only ~40KB / ~56 scenarios of
// headroom remain today). So maximin gets its own, much lower floor instead
// of quietly lowering the shared one, set to the exact count the (fully
// deterministic) generator currently produces: it only guards against the
// section going fully vacuous (a real regression), not against its
// naturally tiny, single-digit count moving by one or two on an unrelated
// change elsewhere in this generator.
const MIN_STRICT_WINNERS_MAXIMIN = 1;

describe.each([
  { section: 'shared score matrix', scenarios: cardinalScenarios.map(prepareCardinal) },
  { section: 'shared 0/1 approval ballot', scenarios: approvalScenarios.map(prepareCardinal) },
  {
    section: 'shared 0-5 grade ballot',
    scenarios: majorityJudgmentScenarios.map((sc) =>
      prepareCardinal({ ...sc, scores: sc.scores.map((row) => row.map((g) => g / 5)) })
    ),
  },
])('engine parity — cardinal rules over a $section', ({ scenarios }) => {
  it.each(Object.keys(scenarios[0].winners) as Rule[])(
    '%s matches the backend on every strict scenario',
    (rule) => {
      const mismatches: string[] = [];
      let compared = 0;
      scenarios.forEach((s, i) => {
        const expected = s.winners[rule];
        if (expected == null) return;
        compared += 1;
        const got = s.candidates[ruleWinnerFromRanks(s.ranks, s.m, rule, s.scores)];
        if (got !== expected) mismatches.push(`#${i}: client=${got} backend=${expected}`);
      });
      const minStrict = rule === 'maximin' ? MIN_STRICT_WINNERS_MAXIMIN : MIN_STRICT_WINNERS;
      expect(compared).toBeGreaterThanOrEqual(minStrict);
      expect(mismatches).toEqual(KNOWN_DIVERGENT[rule] ?? []);
    }
  );
});
