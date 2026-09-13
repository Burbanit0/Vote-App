import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { ruleWinnerFromRanks, type Rule } from './playgroundVoting';

/**
 * Property-based axiomatic tests for the client voting engine (Lot 4.4,
 * PLAN_SOLIDITE_TECHNIQUE.md). Hypothesis already does this for the Python
 * backend (`api/tests/test_voting_criteria_matrix.py`, Lot 4.1) -- this is
 * the other half of the parity contract getting the same treatment, using
 * fast-check directly against `ruleWinnerFromRanks`.
 *
 * **The satisfies/violates split starts from the Python matrix, but isn't
 * assumed to be correct.** Every "satisfies" claim below is actually run
 * here (not just copied), against a WIDER domain than the Python file uses:
 * n in [3,6] candidates (Python's own strategies hardcode exactly 4) and
 * m in [3,25] voters. Lot 4.3's exhaustive proof that this engine and the
 * backend agree EXACTLY for n<=4/m<=5 means anything wrong purely within
 * that box would already be caught there -- so this earns its keep on
 * everything outside it.
 *
 * **That wider net found three real, backend-confirmed corrections during
 * development**, none of them frontend-only quirks: `condorcet` (Copeland on
 * this engine, a different function from the Python matrix's identically-
 * named but non-comparable `get_condorcet_winner` key) and `baldwin` both
 * fail clone independence (baldwin only at n=6, outside Python's 4-candidate
 * search); `irv` and `coombs` both elect a Condorcet loser in cases Python's
 * fixed-4-candidate / fixed-200-example Hypothesis run never happened to
 * sample. All four are corrected in test_voting_criteria_matrix.py too --
 * see its module docstring for the full account. The lesson, not just the
 * fix: a property test that passed 200 times answered a real but narrower
 * question than "for all profiles", and a differently-shaped search (wider
 * candidate range, different tool, different random path) can still find
 * something it didn't cover.
 *
 * **Reproducibility.** fast-check pins a fresh random seed per run by
 * default; `SEED` below fixes one so this file doesn't become exactly the
 * kind of flaky-because-it's-still-exploring test the paragraph above
 * warns about. A fixed seed is not a promise that no fifth bug is out
 * there -- it promises this file finds the same three (now fixed) every
 * time, deterministically.
 *
 * **Scope.** Same 7 criteria as the Python matrix minus participation and
 * reversal symmetry (deliberately deferred there too, see its docstring).
 * "Violates" cases are pinned counterexamples: the ones shared with the
 * Python matrix are ported directly from it (verified to still reproduce
 * identically here); the four corrections above are new pinned examples
 * this file's own fast-check run produced, hand-verified against the
 * backend the same way.
 */

const ALL_METHODS: Rule[] = [
  'plurality',
  'two_round',
  'borda',
  'irv',
  'coombs',
  'condorcet',
  'minimax',
  'schulze',
  'bucklin',
  'nanson',
  'baldwin',
  'ranked_pairs',
  'kemeny',
  'black',
  'anti_plurality',
  'dowdall',
  'raynaud',
  'benham',
  'river',
  'smith_irv',
  'split_cycle',
];

it('the method registry is not stale', () => {
  expect(ALL_METHODS.length).toBe(21);
});

// ── Profile generation ──────────────────────────────────────────────────────
// n in [3,6] candidates, m in [3,25] voters, each voter's ranking a genuine
// random permutation (fc.shuffledSubarray with min=max=length shuffles the
// WHOLE array, verified against the installed fast-check version).
const range = (n: number): number[] => Array.from({ length: n }, (_, i) => i);

interface Profile {
  n: number;
  ranks: number[][];
}

const profileArb: fc.Arbitrary<Profile> = fc.integer({ min: 3, max: 6 }).chain((n) =>
  fc
    .array(fc.shuffledSubarray(range(n), { minLength: n, maxLength: n }), {
      minLength: 3,
      maxLength: 25,
    })
    .map((ranks) => ({ n, ranks }))
);

const NUM_RUNS = 500;
// fast-check picks a fresh random seed every run by default -- great for
// exploration (it found 3 real bugs doing exactly that during development,
// see below), terrible for a committed test: a flaky failure that
// sometimes finds a genuinely new counterexample is still a flaky CI run.
// Pinned once development-time exploration was done, matching the
// Hypothesis `derandomize=True` lesson from Lot 4.1/4.2 -- this seed is not
// special, just fixed.
const SEED = 20260910;

// ── Ground-truth criteria helpers (independent of any method under test) ───

function condorcetWinner(ranks: number[][], n: number): number | null {
  for (let c = 0; c < n; c++) {
    let winner = true;
    for (let o = 0; o < n && winner; o++) {
      if (o === c) continue;
      let cOverO = 0;
      let oOverC = 0;
      for (const r of ranks) r.indexOf(c) < r.indexOf(o) ? cOverO++ : oOverC++;
      if (!(cOverO > oOverC)) winner = false;
    }
    if (winner) return c;
  }
  return null;
}

function condorcetLoser(ranks: number[][], n: number): number | null {
  for (let c = 0; c < n; c++) {
    let loser = true;
    for (let o = 0; o < n && loser; o++) {
      if (o === c) continue;
      let cOverO = 0;
      let oOverC = 0;
      for (const r of ranks) r.indexOf(c) < r.indexOf(o) ? cOverO++ : oOverC++;
      if (!(cOverO < oOverC)) loser = false;
    }
    if (loser) return c;
  }
  return null;
}

function majorityFirstChoice(ranks: number[][], n: number): number | null {
  const counts = new Array(n).fill(0);
  for (const r of ranks) counts[r[0]]++;
  for (let c = 0; c < n; c++) if (counts[c] * 2 > ranks.length) return c;
  return null;
}

function paretoDominated(ranks: number[][], n: number): Set<number> {
  const dominated = new Set<number>();
  for (let b = 0; b < n; b++) {
    for (let a = 0; a < n; a++) {
      if (a === b) continue;
      if (ranks.every((r) => r.indexOf(a) < r.indexOf(b))) {
        dominated.add(b);
        break;
      }
    }
  }
  return dominated;
}

function cloneAfter(ranks: number[][], target: number, cloneId: number): number[][] {
  return ranks.map((r) => {
    const i = r.indexOf(target);
    return [...r.slice(0, i + 1), cloneId, ...r.slice(i + 1)];
  });
}

function promoteToFirst(ranks: number[][], ballotIndex: number, candidate: number): number[][] {
  const r = ranks[ballotIndex];
  const promoted = [candidate, ...r.filter((c) => c !== candidate)];
  return ranks.map((row, i) => (i === ballotIndex ? promoted : row));
}

// ── 1. Condorcet winner ──────────────────────────────────────────────────────

const CONDORCET_WINNER_SATISFIES: Rule[] = [
  'condorcet',
  'minimax',
  'schulze',
  'nanson',
  'baldwin',
  'ranked_pairs',
  'kemeny',
  'black',
  'raynaud',
  'benham',
  'river',
  'smith_irv',
  'split_cycle',
];

describe('Condorcet winner criterion — if one exists, the method must elect it', () => {
  it.each(CONDORCET_WINNER_SATISFIES)('%s', (rule) => {
    fc.assert(
      fc.property(profileArb, ({ n, ranks }) => {
        const cw = condorcetWinner(ranks, n);
        if (cw === null) return true;
        return ruleWinnerFromRanks(ranks, n, rule) === cw;
      }),
      { numRuns: NUM_RUNS, seed: SEED }
    );
  });
});

// ── 2. Condorcet loser ───────────────────────────────────────────────────────

// `irv` is NOT copied from the Python matrix's classification here -- fixed
// there via test_condorcet_loser_irv_can_be_violated after this exact
// fast-check run found a real counterexample the Python file's own
// candidate-count-4-only fixtures could never generate (see its module
// docstring). Confirmed on the backend too, so this is a correction to a
// shared fact, not a frontend-only quirk.
const CONDORCET_LOSER_VIOLATES = new Set<Rule>([
  'plurality',
  'minimax',
  'bucklin',
  'anti_plurality',
  'dowdall',
  'irv',
  'coombs',
  'benham',
  'raynaud',
]);
const CONDORCET_LOSER_SATISFIES = ALL_METHODS.filter((r) => !CONDORCET_LOSER_VIOLATES.has(r));

describe('Condorcet loser criterion — must never elect the Condorcet loser', () => {
  it.each(CONDORCET_LOSER_SATISFIES)('%s', (rule) => {
    fc.assert(
      fc.property(profileArb, ({ n, ranks }) => {
        const cl = condorcetLoser(ranks, n);
        if (cl === null) return true;
        return ruleWinnerFromRanks(ranks, n, rule) !== cl;
      }),
      { numRuns: NUM_RUNS, seed: SEED }
    );
  });

  it('irv can be violated (found by fast-check, hand-verified against the backend too)', () => {
    // C loses both of its pairwise contests (a genuine Condorcet loser), but
    // A and B tie for fewest first-preferences and are eliminated TOGETHER,
    // leaving C -- who nobody's second choice could rescue A or B ahead of
    // -- as the sole survivor. Needed exactly 3 candidates, a count the
    // Python matrix's fixed-4-candidate fixtures never generate.
    const ranks = [
      [2, 1, 0],
      [2, 0, 1],
      [0, 1, 2],
      [2, 0, 1],
      [1, 0, 2],
      [1, 0, 2],
      [0, 1, 2],
    ];
    expect(condorcetLoser(ranks, 3)).toBe(2);
    expect(ruleWinnerFromRanks(ranks, 3, 'irv')).toBe(2);
  });

  it('coombs can be violated (found by fast-check, hand-verified against the backend too)', () => {
    // Unlike irv above, this needed no new candidate count -- 4 candidates,
    // already well inside the Python matrix's own tested domain -- just an
    // 11-ballot profile its 200 fixed Hypothesis examples never happened to
    // sample. A true answer to a narrower question, not a false signal.
    const ranks = [
      [1, 3, 2, 0],
      [0, 3, 2, 1],
      [1, 2, 3, 0],
      [3, 0, 2, 1],
      [1, 3, 0, 2],
      [2, 1, 3, 0],
      [0, 3, 2, 1],
      [0, 1, 2, 3],
      [3, 0, 1, 2],
      [0, 1, 2, 3],
      [2, 3, 1, 0],
    ];
    expect(condorcetLoser(ranks, 4)).toBe(2);
    expect(ruleWinnerFromRanks(ranks, 4, 'coombs')).toBe(2);
  });

  it('benham can be violated (found by fast-check, hand-verified against the backend too)', () => {
    // Same family as coombs above: 4 candidates, a 6-ballot profile the
    // Python matrix's fixed Hypothesis examples never happened to sample.
    const ranks = [
      [2, 0, 3, 1],
      [1, 3, 0, 2],
      [3, 2, 0, 1],
      [2, 0, 3, 1],
      [1, 2, 3, 0],
      [3, 2, 0, 1],
    ];
    expect(condorcetLoser(ranks, 4)).toBe(1);
    expect(ruleWinnerFromRanks(ranks, 4, 'benham')).toBe(1);
  });

  it('raynaud can be violated (found by fast-check, hand-verified against the backend too)', () => {
    const ranks = [
      [3, 1, 0, 2],
      [1, 2, 3, 0],
      [2, 0, 3, 1],
    ];
    expect(condorcetLoser(ranks, 4)).toBe(0);
    expect(ruleWinnerFromRanks(ranks, 4, 'raynaud')).toBe(0);
  });
});

// ── 3. Majority ──────────────────────────────────────────────────────────────

// `dowdall` is NOT copied from the Python matrix's classification here --
// fixed there via test_majority_criterion_dowdall_can_be_violated after
// this exact fast-check run found a real (very rare -- an exact score tie)
// counterexample. Confirmed on the backend too.
const MAJORITY_VIOLATES = new Set<Rule>(['borda', 'anti_plurality', 'dowdall']);
const MAJORITY_SATISFIES = ALL_METHODS.filter((r) => !MAJORITY_VIOLATES.has(r));

describe('Majority criterion — a strict first-choice majority must win', () => {
  it.each(MAJORITY_SATISFIES)('%s', (rule) => {
    fc.assert(
      fc.property(profileArb, ({ n, ranks }) => {
        const maj = majorityFirstChoice(ranks, n);
        if (maj === null) return true;
        return ruleWinnerFromRanks(ranks, n, rule) === maj;
      }),
      { numRuns: NUM_RUNS, seed: SEED }
    );
  });

  it('dowdall can be violated (found by fast-check, hand-verified against the backend too)', () => {
    // B has an outright majority of first-place votes (5 of 9), but ties A
    // exactly on Dowdall score (19/3 each, in exact fractions) and loses
    // the alphabetical tie-break -- same family as Borda's already-known
    // majority weakness, just rarer (needs an exact score tie).
    const ranks = [
      [0, 2, 1],
      [1, 0, 2],
      [0, 2, 1],
      [1, 0, 2],
      [0, 2, 1],
      [1, 0, 2],
      [0, 2, 1],
      [1, 0, 2],
      [1, 2, 0],
    ];
    expect(majorityFirstChoice(ranks, 3)).toBe(1);
    expect(ruleWinnerFromRanks(ranks, 3, 'dowdall')).toBe(0);
  });
});

// ── 4. Unanimity ─────────────────────────────────────────────────────────────
// Hand-built profile (full agreement is rare among random permutations),
// mirrors the Python matrix's fixture exactly (candidate B = index 1).

describe('Unanimity — if every voter ranks the same candidate first, they win', () => {
  const ranks = [
    [1, 0, 2, 3],
    [1, 2, 0, 3],
    [1, 3, 2, 0],
    [1, 0, 3, 2],
    [1, 2, 3, 0],
  ];
  it.each(ALL_METHODS)('%s', (rule) => {
    expect(ruleWinnerFromRanks(ranks, 4, rule)).toBe(1);
  });
});

// ── 5. Pareto efficiency ─────────────────────────────────────────────────────

const PARETO_VIOLATES = new Set<Rule>(['anti_plurality']);
const PARETO_SATISFIES = ALL_METHODS.filter((r) => !PARETO_VIOLATES.has(r));

describe('Pareto efficiency — a candidate ranked below another on every ballot must lose', () => {
  it.each(PARETO_SATISFIES)('%s', (rule) => {
    fc.assert(
      fc.property(profileArb, ({ n, ranks }) => {
        const dominated = paretoDominated(ranks, n);
        if (dominated.size === 0) return true;
        return !dominated.has(ruleWinnerFromRanks(ranks, n, rule));
      }),
      { numRuns: NUM_RUNS, seed: SEED }
    );
  });

  it('anti_plurality can be violated (pinned, ported from the Python matrix)', () => {
    // C is preferred to A on every single ballot; anti-plurality only
    // tallies LAST-place votes, ignoring first-place preferences entirely.
    const ranks = [
      [1, 2, 0, 3], // B C A D
      [2, 0, 3, 1], // C A D B
      [2, 1, 0, 3], // C B A D
    ];
    expect(ranks.every((r) => r.indexOf(2) < r.indexOf(0))).toBe(true);
    expect(ruleWinnerFromRanks(ranks, 4, 'anti_plurality')).toBe(0);
  });
});

// ── 6. Clone independence ────────────────────────────────────────────────────

// `condorcet` and `baldwin` are NOT copied from the Python matrix's own
// clone-independence classification -- for good reason in each case:
//
// - The Python matrix's "condorcet" key is get_condorcet_winner, the raw
//   strict criterion (trivially clone-"independent" in the sense that
//   testing it against itself is closer to tautology). The client's
//   "condorcet" RULE is a genuinely different function -- Copeland's method
//   (RULE_LABELS calls it "Condorcet (Copeland)") -- and Copeland's
//   win-minus-loss score is a textbook example of a scoring rule cloning can
//   manipulate. Confirmed here with a real counterexample, independently of
//   anything the Python file classified.
// - `baldwin` WAS classified as clone-independent in the Python matrix
//   (Lot 4.1/4.2) -- but that classification came from Hypothesis fuzzing
//   over a hardcoded 4-candidate pool (`_CANDS4`). fast-check's wider net (up
//   to 6 candidates here) found a genuine counterexample at n=6 that no
//   4-candidate search could ever see, and it reproduces identically on the
//   backend (see the corrected classification and pinned example added to
//   test_voting_criteria_matrix.py, Lot 4.4 follow-up). A real gap in an
//   earlier lot's methodology, not a frontend-only issue.
const CLONE_INDEPENDENCE_VIOLATES = new Set<Rule>([
  'borda',
  'coombs',
  'bucklin',
  'nanson',
  'kemeny',
  'black',
  'anti_plurality',
  'dowdall',
  'split_cycle',
  'ranked_pairs',
  'river',
  'condorcet',
  'baldwin',
]);
const CLONE_INDEPENDENCE_SATISFIES = ALL_METHODS.filter((r) => !CLONE_INDEPENDENCE_VIOLATES.has(r));

describe('Clone independence — cloning a candidate must not change the winner', () => {
  it.each(CLONE_INDEPENDENCE_SATISFIES)('%s', (rule) => {
    fc.assert(
      fc.property(profileArb, ({ n, ranks }) => {
        const winner = ruleWinnerFromRanks(ranks, n, rule);
        if (winner < 0) return true;
        for (let target = 0; target < n; target++) {
          const cloned = cloneAfter(ranks, target, n); // clone gets the next index
          const newWinner = ruleWinnerFromRanks(cloned, n + 1, rule);
          if (target === winner) {
            if (newWinner !== winner && newWinner !== n) return false;
          } else if (newWinner !== winner) {
            return false;
          }
        }
        return true;
      }),
      { numRuns: NUM_RUNS, seed: SEED }
    );
  });

  it('borda can be violated (pinned, ported from the Python matrix)', () => {
    const ranks = [
      [1, 2, 0], // B C A
      [2, 0, 1], // C A B
      [2, 1, 0], // C B A
      [1, 2, 0], // B C A
      [0, 1, 2], // A B C
      [0, 1, 2],
      [0, 1, 2],
    ];
    expect(ruleWinnerFromRanks(ranks, 3, 'borda')).toBe(1); // B
    const cloned = [
      [1, 2, 0, 3], // B C A A*
      [2, 0, 3, 1], // C A A* B
      [2, 1, 0, 3], // C B A A*
      [1, 2, 0, 3],
      [0, 3, 1, 2], // A A* B C
      [0, 3, 1, 2],
      [0, 3, 1, 2],
    ];
    expect(ruleWinnerFromRanks(cloned, 4, 'borda')).toBe(0); // A
  });

  it.each(['ranked_pairs', 'river'] as const)(
    '%s can be violated (pinned, ported from the Python matrix)',
    (rule) => {
      // A 3-voter Condorcet cycle with all three pairwise margins exactly
      // tied at 2-1 -- the textbook clone-independence proof for Tideman's
      // ranked-pairs family assumes generic (non-tied) margins, so it
      // doesn't cover this degenerate case. The Python original clones C and
      // names the clone "A*" specifically because this counterexample is
      // tie-break-order-sensitive: "A*" sorts alphabetically right after A
      // (a prefix comparison), not last -- so the clone here is index 1
      // (A=0, clone=1, B=2, C=3, D=4), not index n. Using index n (sorting
      // after D) doesn't reproduce the violation; this is a
      // deliberately-positioned counterexample, not a generic clone.
      const ranks = [
        [0, 2, 1, 3], // A C B D
        [1, 0, 2, 3], // B A C D
        [2, 1, 0, 3], // C B A D
      ];
      expect(ruleWinnerFromRanks(ranks, 4, rule)).toBe(1); // B
      // Clone C (index 2) -> "A*"; renumber so A=0, clone=1, B=2, C=3, D=4.
      const cloned = [
        [0, 3, 1, 2, 4], // A C A* B D
        [2, 0, 3, 1, 4], // B A C A* D
        [3, 1, 2, 0, 4], // C A* B A D
      ];
      expect(ruleWinnerFromRanks(cloned, 5, rule)).toBe(0); // A
    }
  );

  it('condorcet (Copeland) can be violated (found by fast-check, hand-verified)', () => {
    // Copeland's win-minus-loss score is a textbook example of a rule
    // clones can manipulate: original winner is candidate 2, but cloning
    // non-winner candidate 4 shifts the net-score balance enough to hand
    // victory to candidate 4 itself -- not even its own clone.
    const ranks = [
      [1, 4, 2, 0, 3],
      [4, 3, 2, 1, 0],
      [2, 3, 1, 0, 4],
    ];
    expect(ruleWinnerFromRanks(ranks, 5, 'condorcet')).toBe(2);
    const cloned = cloneAfter(ranks, 4, 5);
    expect(ruleWinnerFromRanks(cloned, 6, 'condorcet')).toBe(4);
  });

  it('baldwin can be violated (found by fast-check, hand-verified against the backend too)', () => {
    // Lot 4.1/4.2's Hypothesis-based classification of baldwin as clone-
    // independent came from a hardcoded 4-candidate search space
    // (`_CANDS4` in test_voting_criteria_matrix.py) -- this 6-candidate
    // counterexample was outside anything that search could find. It
    // reproduces identically on the backend (get_baldwin_winner), which is
    // why the Python matrix's classification was corrected alongside this
    // test rather than treating it as a client-only quirk.
    const ranks = [
      [0, 1, 3, 4, 2, 5],
      [2, 5, 3, 1, 0, 4],
      [3, 0, 2, 5, 4, 1],
      [0, 2, 4, 3, 5, 1],
      [2, 3, 4, 1, 5, 0],
      [2, 5, 3, 1, 4, 0],
      [3, 1, 0, 2, 5, 4],
      [3, 1, 0, 4, 5, 2],
      [1, 0, 2, 4, 5, 3],
    ];
    expect(ruleWinnerFromRanks(ranks, 6, 'baldwin')).toBe(2);
    const cloned = cloneAfter(ranks, 3, 6);
    expect(ruleWinnerFromRanks(cloned, 7, 'baldwin')).toBe(3);
  });
});

// ── 7. Monotonicity ──────────────────────────────────────────────────────────

const MONOTONICITY_VIOLATES = new Set<Rule>([
  'two_round',
  'irv',
  'coombs',
  'baldwin',
  'raynaud',
  'benham',
  'smith_irv',
  'nanson',
]);
const MONOTONICITY_SATISFIES = ALL_METHODS.filter((r) => !MONOTONICITY_VIOLATES.has(r));

describe('Monotonicity — ranking the winner higher must never make them lose', () => {
  it.each(MONOTONICITY_SATISFIES)('%s', (rule) => {
    fc.assert(
      fc.property(profileArb, ({ n, ranks }) => {
        const winner = ruleWinnerFromRanks(ranks, n, rule);
        if (winner < 0) return true;
        for (let i = 0; i < ranks.length; i++) {
          if (ranks[i][0] === winner) continue;
          const modified = promoteToFirst(ranks, i, winner);
          return ruleWinnerFromRanks(modified, n, rule) === winner;
        }
        return true;
      }),
      { numRuns: NUM_RUNS, seed: SEED }
    );
  });

  it('smith_irv can be violated (pinned, ported from the Python matrix)', () => {
    const ranks = [
      [3, 0, 2, 1], // D A C B
      [2, 0, 3, 1], // C A D B
      [3, 1, 2, 0], // D B C A
      [1, 2, 0, 3], // B C A D
      [0, 3, 2, 1], // A D C B
      [3, 2, 1, 0], // D C B A
      [1, 2, 0, 3],
      [0, 3, 2, 1],
      [1, 0, 3, 2], // B A D C
    ];
    expect(ruleWinnerFromRanks(ranks, 4, 'smith_irv')).toBe(0); // A
    const modified = promoteToFirst(ranks, 0, 0);
    expect(ruleWinnerFromRanks(modified, 4, 'smith_irv')).toBe(1); // B
  });

  it('nanson can be violated (pinned, ported from the Python matrix)', () => {
    const ranks = [
      [2, 3, 1, 0], // C D B A
      [2, 0, 3, 1], // C A D B
      [1, 3, 0, 2], // B D A C
      [3, 2, 1, 0], // D C B A
      [1, 3, 0, 2],
      [2, 0, 1, 3], // C A B D
      [3, 0, 2, 1], // D A C B
      [1, 0, 3, 2], // B A D C
    ];
    expect(ruleWinnerFromRanks(ranks, 4, 'nanson')).toBe(3); // D
    const modified = promoteToFirst(ranks, 0, 3);
    expect(ruleWinnerFromRanks(modified, 4, 'nanson')).toBe(1); // B
  });
});
