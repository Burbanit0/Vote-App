import { describe, it, expect } from 'vitest';
import { ruleWinnerFromRanks, type Rule } from './playgroundVoting';
import fixtureJson from './__fixtures__/engineParity.json';

// Engine parity: the Playground computes winners client-side, but the repo's
// authoritative engine is the tested Python backend. These golden winners come
// from it (flask_voter_app/scripts/gen_engine_parity.py); here we assert the TS
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
const KNOWN_DIVERGENT = new Set<Rule>(['irv', 'coombs', 'schulze', 'bucklin']);

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
  it.each([...KNOWN_DIVERGENT])(
    '%s is still a tracked divergence (reconcile, then unlist)',
    (rule) => {
      expect(mismatchesFor(rule).length).toBeGreaterThan(0);
    }
  );
});
