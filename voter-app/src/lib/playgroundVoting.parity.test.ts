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
      expect(compared).toBeGreaterThanOrEqual(MIN_STRICT_WINNERS);
      expect(mismatches).toEqual(KNOWN_DIVERGENT[rule] ?? []);
    }
  );
});

// ── Exhaustive cardinal domains (approval, majority judgment) ─────────────────
// generate_exhaustive_approval_scenarios / generate_exhaustive_majority_judgment_scenarios
// in gen_engine_parity.py extend the same exhaustive-domain proof used above
// for the ordinal rules (n<=3 candidates, every profile, not a sample) to the
// two rules that read `scores` instead of `ranks`. Same deal as that block:
// winners are RAW (ties/no-winner → null, not filtered out by strict_winner),
// so a mismatch is a real algorithmic divergence, not a tie-break artefact.
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
const { exhaustiveApprovalScenarios, exhaustiveMajorityJudgmentScenarios } = fixtureJson as Record<
  'exhaustiveApprovalScenarios' | 'exhaustiveMajorityJudgmentScenarios',
  CardinalScenario[]
>;

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
