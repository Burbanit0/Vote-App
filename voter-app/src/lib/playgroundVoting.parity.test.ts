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
// on strict profiles — a real divergence this harness surfaced. Tracked debt:
// reconcile each (fix the client engine to the tested backend), then delete it
// from this set. See gen_engine_parity.py to regenerate the golden winners.
const KNOWN_DIVERGENT = new Set<Rule>([]);

describe('engine parity — client ruleWinnerFromRanks == backend golden winners', () => {
  it('has a non-trivial fixture', () => {
    expect(prepared.length).toBeGreaterThanOrEqual(40);
  });

  it.each(RULES.filter((r) => !KNOWN_DIVERGENT.has(r)))(
    '%s matches the backend on every strict scenario',
    (rule) => {
      expect(mismatchesFor(rule)).toEqual([]);
    }
  );

  // Keep the debt honest: if a known-divergent method now agrees (0 mismatches),
  // this fails so the method gets promoted out of KNOWN_DIVERGENT; if a NEW method
  // starts diverging, its locked test above fails — neither slips by silently.
  if (KNOWN_DIVERGENT.size > 0) {
    it.each([...KNOWN_DIVERGENT])(
      '%s is still a tracked divergence (reconcile, then unlist)',
      (rule) => {
        expect(mismatchesFor(rule).length).toBeGreaterThan(0);
      }
    );
  }
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

// ── Cardinal rules (score / STAR / cumulative / maximin / nash) — same
// per-voter score matrix on both engines. Approval and majority judgment are
// handled separately below: an arbitrary shared score matrix isn't a fair
// comparison for them (each engine derives/quantises those two ballots
// differently from a raw utility score — see gen_engine_parity.py's CARDINAL
// comment), so those two scenarios feed ballots at the exact values both
// sides are guaranteed to interpret identically instead.
interface CardinalScenario {
  candidates: string[];
  scores: number[][];
  winners: Record<string, string | null>;
}
const cardinal = (fixtureJson as { cardinalScenarios: CardinalScenario[] }).cardinalScenarios;

const preparedCardinal = cardinal.map((sc) => ({
  m: sc.candidates.length,
  candidates: sc.candidates,
  scores: sc.scores,
  // Ranks (best→worst) only satisfy ruleWinnerFromRanks' shape; cardinal rules read `scores`.
  ranks: sc.scores.map((row) => row.map((_, i) => i).sort((a, b) => row[b] - row[a])),
  winners: sc.winners,
}));

const CARDINAL_RULES = Object.keys(cardinal[0].winners) as Rule[];

describe('engine parity — cardinal rules over a shared score matrix', () => {
  it.each(CARDINAL_RULES)('%s matches the backend on every strict scenario', (rule) => {
    const mismatches: string[] = [];
    preparedCardinal.forEach((s, i) => {
      const expected = s.winners[rule];
      if (expected == null) return;
      const got = s.candidates[ruleWinnerFromRanks(s.ranks, s.m, rule, s.scores)];
      if (got !== expected) mismatches.push(`#${i}: client=${got} backend=${expected}`);
    });
    expect(mismatches).toEqual([]);
  });
});

// ── Approval / Majority Judgment — ballots pinned to the exact values both
// engines are guaranteed to quantise identically (0.0/1.0 for approval;
// multiples of 1/5 for MJ's 6-level grade), so a mismatch here is a real
// divergence in the winner-selection algorithm, not the (known, documented)
// difference in how each engine would derive that ballot from raw utility.
interface SingleWinnerScenario {
  candidates: string[];
  scores: number[][];
  winner: string | null;
}

function singleWinnerMismatches(scenarios: SingleWinnerScenario[], rule: Rule): string[] {
  const mismatches: string[] = [];
  scenarios.forEach((sc, i) => {
    if (sc.winner == null) return; // no relabel-stable winner on the backend either
    const m = sc.candidates.length;
    // ranks only satisfy ruleWinnerFromRanks' shape; approval/MJ read `scores`.
    const ranks = sc.scores.map((row) => row.map((_, j) => j).sort((a, b) => row[b] - row[a]));
    const idx = ruleWinnerFromRanks(ranks, m, rule, sc.scores);
    const got = idx >= 0 ? sc.candidates[idx] : null;
    if (got !== sc.winner) mismatches.push(`#${i}: client=${got} backend=${sc.winner}`);
  });
  return mismatches;
}

const approvalScenarios = (fixtureJson as { approvalScenarios: SingleWinnerScenario[] })
  .approvalScenarios;
const majorityJudgmentScenarios = (
  fixtureJson as { majorityJudgmentScenarios: SingleWinnerScenario[] }
).majorityJudgmentScenarios;

describe('engine parity — approval (shared 0/1 approval ballot)', () => {
  it('matches the backend on every strict scenario', () => {
    expect(singleWinnerMismatches(approvalScenarios, 'approval')).toEqual([]);
  });
});

describe('engine parity — majority judgment (shared grade/5 ballot)', () => {
  // KNOWN DIVERGENCE (tracked, not silently accepted — PLAN_SURFACE_EXTERIEURE.md
  // §2.E). The backend's tie-break (median → majority-gauge p−q → ONE extra
  // median-strip step, get_majority_judgment_winner) is a heuristic
  // approximation of the textbook Balinski–Laraki procedure — repeatedly
  // strip one instance of the tied median grade and recompare until
  // distinguished — which is what the client's winMajorityJudgment actually
  // implements (no gauge at all). The two agree except when the backend's
  // single extra step doesn't fully resolve a tie the full iterative strip
  // would have: confirmed on exactly 3/60 scenarios here (#22, #50, #59) —
  // e.g. #22, candidates tied on median=4, backend's gauge ranks them
  // p−q=−0.238 vs −0.286 (picks the first), the client's iterative strip
  // picks the other. This needs a human call on which convention the
  // backend should implement (or whether the "single step suffices" backend
  // docstring claim should be corrected) — not a silent client-side patch.
  const MJ_KNOWN_MISMATCH_COUNT = 3;

  it('matches the backend except for the tracked tie-break divergence above', () => {
    const mismatches = singleWinnerMismatches(majorityJudgmentScenarios, 'majority_judgment');
    expect(mismatches.length).toBe(MJ_KNOWN_MISMATCH_COUNT);
  });
});
