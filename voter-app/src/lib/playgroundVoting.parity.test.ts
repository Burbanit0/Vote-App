import { describe, it, expect } from 'vitest';
import { KEMENY_EXACT_CAP, ruleWinnerFromRanks, type Rule } from './playgroundVoting';
import fixtureJson from './__fixtures__/engineParity.json';

// Engine parity: the Playground computes winners client-side, but the repo's
// authoritative engine is the tested Python backend. These golden winners come
// from it (fast_api_voter/scripts/gen_engine_parity.py); here we assert the TS
// client returns the same winner on the same ranking profile — one source of
// truth, not two that silently drift.
//
// The SAMPLED blocks hold STRICT winners only: each survives 200 candidate-relabel
// + ballot-shuffle trials, so a mismatch there is a real algorithmic divergence,
// never a tie-break convention. The exhaustive blocks further down record raw
// winners, ties included, so they do pin the tie-break convention (see
// `ruleWinnerFromRanks`). Voter counts are odd → strict pairwise majorities.

interface Scenario {
  candidates: string[];
  ballots: string[][];
  winners: Record<string, string | null>;
}
const fixture = fixtureJson as { scenarios: Scenario[]; _kemenyExactCap: number };

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
//
// Currently empty and should stay that way — `majority_judgment` was the one
// entry (fix/majority-judgment-gauge, following PLAN_SURFACE_EXTERIEURE.md
// §2.E): the backend ranked equal medians by p − q instead of running the real
// Balinski–Laraki procedure (repeatedly strip the tied median grade and
// recompare). get_majority_judgment_winner now ports the client's
// winMajorityJudgment directly (see `_mj_winner` in simulation_score_utils.py);
// 0 mismatches on regeneration.
const KNOWN_DIVERGENT: Partial<Record<Rule, string[]>> = {};

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

// Shared by every exhaustive block below (ordinal here, approval/majority-
// judgment further down): raw winner vs. raw winner, ties/no-winner (null)
// included, no strict_winner-style filtering. `scores` is optional — the
// ordinal shape below doesn't have it, ruleWinnerFromRanks falls back to
// `ranks` alone; the cardinal shapes further down always pass it.
function exhaustiveMismatchesFor<
  T extends {
    m: number;
    candidates: string[];
    ranks: number[][];
    winners: Record<string, string | null>;
    scores?: number[][];
  },
>(scenarios: T[], rule: Rule): string[] {
  const out: string[] = [];
  scenarios.forEach((s, i) => {
    const expected = s.winners[rule];
    const idx = ruleWinnerFromRanks(s.ranks, s.m, rule, s.scores);
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
    expect(exhaustiveMismatchesFor(preparedExhaustive, rule)).toEqual([]);
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

// ── Exhaustive cardinal domains (approval, majority judgment, maximin) ────────
// generate_exhaustive_approval_scenarios / generate_exhaustive_majority_judgment_scenarios /
// generate_exhaustive_maximin_scenarios in gen_engine_parity.py extend the same
// exhaustive-domain proof used above for the ordinal rules (n<=3 candidates,
// every profile, not a sample) to the three rules that read `scores` instead
// of `ranks`. Same deal as that block: winners are RAW (ties/no-winner →
// null, not filtered out by strict_winner), so a mismatch is a real
// algorithmic divergence, not a tie-break artefact.
//
// Domain sizes (see gen_engine_parity.py's docstrings for the measured
// combinations_with_replacement counts behind these numbers):
// - approval: every non-degenerate profile for n<=3 candidates, m<=5 voters —
//   481 profiles, exactly the same shape as the ordinal exhaustive domain
//   (2^n - 2 non-degenerate ballot subsets happens to equal n! for n in {2,3}).
// - majority_judgment: coarsened to 3 grades (0/2/5 of the 0-5 scale — see
//   MJ_EXHAUSTIVE_GRADES' comment for why that loses no algorithmic coverage),
//   n<=3 candidates, m<=5 voters for n=2 (2,001 profiles) and m<=3 for n=3
//   (4,059 profiles) — the full 6-grade domain explodes combinatorially at
//   n=3 well before m=5, the same way ordinal n=4 does.
// - maximin: the SAME 3-grade coarsening and n/m bounds as majority_judgment
//   (MAXIMIN_EXHAUSTIVE_GRADES' comment in gen_engine_parity.py has the
//   independent verification — both code-reading and a throwaway empirical
//   check — that maximin has the same order-only-comparison property that
//   makes the coarsening lossless), so the same 6,060-profile domain
//   (2,001 for n=2 + 4,059 for n=3). Unlike MJ, maximin's ballots are fed to
//   the engines UNSCALED (raw grade ints, not divided by 5): neither side's
//   maximin implementation compares a score against a fixed threshold, only
//   against each other, so no rescale is needed here — contrast with the
//   `/ 5` map below for majority_judgment.
//
//   Maximin gets a DIFFERENT check shape than approval/majority_judgment,
//   below — it is the one rule here whose own tie-break has no principled,
//   shared convention to lock. get_maximin_score_winner (backend) and
//   winMaximin (client) each deterministically pick ONE candidate among
//   those tied for the best worst-case score, but by genuinely different
//   mechanisms — backend: `_score_candidates`'s first-encountered dict-key
//   order; client: lowest array index — that only ever coincide here
//   because this generator's ballots happen to always be built in canonical
//   candidate order (see generate_exhaustive_maximin_scenarios' docstring in
//   gen_engine_parity.py for the full story, including the empirical
//   measurement that reversing per-voter dict key order flips the backend's
//   own recorded pick on 3,312/6,060 = 54.7% of this exact domain). Asserting
//   raw winner identity on every profile the way approval/MJ do would just be
//   asserting that shared construction accident, not real cross-engine
//   agreement — so this section instead asserts the two things that ARE
//   real: every profile's client pick is a genuine maximin winner (a member
//   of `maximinTiedWinners`, the analytically-true tied-for-best set,
//   computed independently of either engine), and client/backend/tied-set
//   agree exactly on the ~45.3% of profiles where that set has just one
//   member — i.e. every profile where the rule actually has an unambiguous
//   answer, with no tie-break convention involved to disagree about.
const {
  exhaustiveApprovalScenarios,
  exhaustiveMajorityJudgmentScenarios,
  exhaustiveMaximinScenarios,
} = fixtureJson as Record<
  'exhaustiveApprovalScenarios' | 'exhaustiveMajorityJudgmentScenarios',
  CardinalScenario[]
> &
  Record<'exhaustiveMaximinScenarios', (CardinalScenario & { maximinTiedWinners: string[] })[]>;

describe('engine parity — EXHAUSTIVE approval domain (n<=3 candidates, m<=5 voters)', () => {
  const prepared = exhaustiveApprovalScenarios.map(prepareCardinal);

  it('covers the full non-degenerate n<=3, m<=5 domain', () => {
    expect(prepared).toHaveLength(481);
  });

  it('approval matches the backend on EVERY profile, ties and all', () => {
    expect(exhaustiveMismatchesFor(prepared, 'approval')).toEqual([]);
  });
});

describe('engine parity — EXHAUSTIVE majority-judgment domain (3 grades, n<=3)', () => {
  const prepared = exhaustiveMajorityJudgmentScenarios.map((sc) =>
    prepareCardinal({ ...sc, scores: sc.scores.map((row) => row.map((g) => g / 5)) })
  );

  it('covers the full 3-grade domain (m<=5 for n=2, m<=3 for n=3)', () => {
    expect(prepared).toHaveLength(6060);
  });

  it('majority_judgment matches the backend on EVERY profile, ties and all', () => {
    expect(exhaustiveMismatchesFor(prepared, 'majority_judgment')).toEqual([]);
  });
});

describe('engine parity — EXHAUSTIVE maximin domain (3 grades, n<=3)', () => {
  const prepared = exhaustiveMaximinScenarios.map((sc) => ({
    ...prepareCardinal(sc),
    maximinTiedWinners: sc.maximinTiedWinners,
  }));

  it('covers the full 3-grade domain (m<=5 for n=2, m<=3 for n=3)', () => {
    expect(prepared).toHaveLength(6060);
  });

  // Real, order-independent claim #1: the client NEVER picks a candidate that
  // isn't genuinely tied for the best worst-case score, on any of the 6,060
  // profiles — i.e. it always computes a real maximin winner, whether or not
  // that profile happens to have a tie. This does not assume or require any
  // particular tie-break convention; it only requires the underlying min/max
  // computation itself to be correct.
  it('client always returns a genuine maximin winner (member of the analytically-true tied set)', () => {
    const violations: string[] = [];
    prepared.forEach((s, i) => {
      const idx = ruleWinnerFromRanks(s.ranks, s.m, 'maximin', s.scores);
      const got = s.candidates[idx];
      if (!s.maximinTiedWinners.includes(got)) {
        violations.push(
          `#${i}: client picked ${got}, not in the true tied set ${JSON.stringify(s.maximinTiedWinners)}`
        );
      }
    });
    expect(violations).toEqual([]);
  });

  // Real, order-independent claim #2: on every profile where the tied set has
  // exactly one member — the rule has an unambiguous answer, no tie-break
  // convention involved at all — client and backend agree exactly. Reuses
  // exhaustiveMismatchesFor (it only needs `winners.maximin`, which for a
  // singleton tied set always equals that one candidate — enforced by the
  // generator's own assertion when the fixture was built).
  it('client matches the backend exactly on every profile with a UNIQUE analytically-true winner', () => {
    const unambiguous = prepared.filter((s) => s.maximinTiedWinners.length === 1);
    // Measured ~2,748/6,060 (45.3%) unambiguous profiles in this domain — floor
    // set well below that so a small, legitimate shift elsewhere in the
    // generator doesn't flake this, while still catching the check going
    // vacuous (a real regression).
    expect(unambiguous.length).toBeGreaterThanOrEqual(2000);
    expect(exhaustiveMismatchesFor(unambiguous, 'maximin')).toEqual([]);
  });
});

// An engine-boundary invariant the scenario comparisons above structurally
// cannot check, learned the hard way on fix/kemeny-exact-and-neutral.
describe('kemeny engine boundary', () => {
  // The caps must be equal or the two engines silently answer different
  // algorithms above whichever is lower — backend KwikSort, client Borda. No
  // fixture scenario can catch that: the widest is 8 candidates, and a scenario
  // above the cap would be comparing Borda against KwikSort by construction. So
  // the generator emits the backend's value and this pins the client to it.
  it('the client exact cap equals the backend _KY_EXACT_CAP', () => {
    expect(KEMENY_EXACT_CAP).toBe(fixture._kemenyExactCap);
  });
});
