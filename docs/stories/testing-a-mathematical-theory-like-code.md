# Testing a mathematical theory the way you test code

Most codebases that implement an algorithm never go near the mathematics
*about* that algorithm. The paper lives in a PDF, cited maybe once in a
docstring; the code lives in git, tested against whatever inputs the author
thought to write down. The two rarely touch. Vote Lab, a small sandbox
implementing 26 voting methods, does something unusual: the actual theorems
of social choice theory — Condorcet consistency, monotonicity, participation,
independence of clones, Pareto, unanimity — are executable test assertions,
run against every method the engine implements. Not analogies to the theory.
The theory itself, as code.

## A passing test and a failing test can both be correct

The starting move is a small inversion that's easy to miss: for each of 26
methods, the goal isn't just to check the criteria a method *should* satisfy
— it's to also assert the ones it's *known to violate*. A test proving that
Instant-Runoff Voting fails monotonicity is not a bug report. It's exactly
as valuable as a passing test, for two reasons at once: it documents a real,
citable property of the method, and it would catch an implementation bug the
moment IRV *accidentally* became monotone — which would mean it had quietly
stopped being IRV. Absence of a failure is sometimes the thing worth
guarding.

## When "I ran it 200 times" and "I proved it never happens" disagree

Building the matrix meant classifying, for 21 ranked methods against 7
criteria, which cells satisfy and which violate — and the project's own rule
was that no classification gets written down from memory or intuition; it
has to survive being discovered by fuzzing and then locked down as a
property-based test.

That rule caught something real during its own construction. An initial
exploration pass, sampling somewhere between 100 and 240 random ballot
profiles per cell, classified four methods as satisfying independence of
clones (`ranked_pairs`, `river`, `smith_irv`) or monotonicity (`nanson`) —
clean across every sample it tried. All four classifications were wrong. Once
the exploration was replaced with Hypothesis's actual shrinking search over
the full property — not a fixed sample, an open-ended search that keeps
narrowing toward the smallest failing case — all four methods turned out to
genuinely violate their criterion, but only on nearly-perfectly-tied,
degenerate profiles: pairwise margins or first-choice vote counts landing
exactly equal. Rare enough that low-sample random exploration walked right
past them every time; common enough that a real search, given permission to
keep looking, found them without much trouble.

The gap between "I tried it 200 times and saw nothing" and "this never
happens" turns out to be exactly where an incorrect classification hides —
and the only way to know which side of that gap you're on is to keep
searching until the tool itself, not your patience, decides to stop.

## An external referee changes what errors are even visible

Comparing your own two independent implementations against each other — the
project keeps a client engine and a backend engine in permanent lockstep,
by design — has a structural weakness: the two can be wrong in exactly the
same way, and agreement between them proves nothing about that shared
error. The fix was to bring in a referee that shares no code and no
assumptions: `pref_voting`, an academic library from Pacuit and Holliday,
run against 3,000 random ballot profiles across 3–4 candidates and 3–11
voters, for all 21 ordinal methods — comparing "is my winner a member of the
oracle's own winner set (including ties)" rather than exact equality, since
independent implementations legitimately break ties differently.

Eighteen of twenty-one methods matched perfectly: zero discrepancies. The
remaining four were each investigated by hand to a real conclusion, not
waved away as noise:

- **`dowdall`** produced one mismatch that turned out to be a bug in the
  *oracle*, not in Vote Lab. The disputed profile has two candidates in an
  exact tie — verified by hand in exact fractions (43/6) — but the oracle
  library's floating-point summation, adding terms in a different order,
  breaks that exact tie by a rounding epsilon and reports only one winner
  instead of two. Reproduced independently, confirmed, and left alone: there
  was nothing on this side to fix.
- **`baldwin`** (11 mismatches) and **`raynaud`** (27 mismatches) were real
  bugs. Both methods were eliminating only a single worst-ranked candidate
  per round instead of eliminating *every* candidate tied for worst — an
  inconsistency with how the engine's own `irv` and `nanson` implementations
  already handled ties. Fixed to match the project's existing convention
  (which also happens to be the oracle's), on both the backend and the
  client engine, with the parity fixture regenerated and the parity test
  green afterward.
- **`smith_irv`** produced the most mismatches (75) and hid two independent
  bugs at once: a dominance test that checked only "no one outside beats
  someone inside" instead of the correct "everyone inside beats everyone
  outside" — the two coincide except in the presence of pairwise ties, where
  the bug quietly certified a Smith set that was too small — and a second,
  separate error recomputing the Smith set from scratch on every elimination
  round instead of once, up front, on the full field (the actual definition
  of the method, confirmed against the oracle's own source). Fixing both
  produced a genuinely delightful reveal: once corrected, `smith_irv` turned
  out to actually *satisfy* independence of clones after all — the
  counterexample pinned down earlier in the axiom matrix had been an
  artifact of the bug, not a real mathematical property of the method. The
  matrix itself was updated, classification and explanation both, once the
  ground truth changed underneath it.

## Going past sampling entirely: a proof instead of a photograph

Even an exhaustive fuzzing campaign is still, by construction, a search over
a *finite* number of profiles, however large. The project's furthest step
replaced sampling with an actual proof: encoding vote tallies as symbolic
integer variables in the Z3 SMT solver and asking it to certify a property
for *every possible electorate*, not a sample of them. The result: minimax
and Schulze satisfy the Condorcet criterion for all electorates up to seven
candidates — full stop, no sample size caveat — decided by the solver in
under a minute.

The experiment's own risk assumption ("this might just fail — combinatorial
explosion, an encoding too heavy to solve") didn't materialize, but a
different, quieter risk did: a first encoding of IRV "proved" that IRV can
never elect a Condorcet loser — flatly contradicting a hand-verified
counterexample the fast-check property tests had already pinned down
earlier in the same effort. The encoding had silently dropped the engine's
actual tie-breaking rule (eliminate *every* candidate tied for worst, not
an arbitrary one), so Z3 had faithfully proven a true property of a
*different*, simpler rule that wasn't the one actually running in
production. Once the encoding was corrected and re-checked against the
already-known counterexample before trusting it with anything new, Z3 found
its own 7-ballot counterexample to the same claim — proven *minimal*, a
guarantee no amount of random sampling can offer by construction, no matter
how much of it you do.

## The shape of the whole effort

Put together, this is four distinct methods of finding out whether a piece
of social-choice theory is actually true of a specific 26-method
implementation: exhaustive small-case search, property-based fuzzing with a
real shrinking search (not fixed samples), an independent academic library
as referee, and formal proof over an unbounded universe of electorates. Each
one found something the others didn't, including in each other — the oracle
had its own bug, the fuzzing caught a hand-classification error, and the
formal encoding caught a mistake in its own first draft, checked against
work the fuzzing had already done. None of that is a sign the process
failed. It's what happens when the theory you're testing is only as honest
as the search that's allowed to try to break it — and here, unusually, the
theory and the tests are the same file.

---

*Sourced from [`PLAN_SOLIDITE_TECHNIQUE.md`](../../PLAN_SOLIDITE_TECHNIQUE.md)
(Lot 4.1, 4.2, and 4.6) and
[`docs/exploration/EXP-002-z3-formal-voting-proofs.md`](../exploration/EXP-002-z3-formal-voting-proofs.md).
The axiom matrix itself lives in
`fast_api_voter/api/tests/test_voting_criteria_matrix.py`; the oracle
cross-check and the fast-check property tests that first surfaced the
Condorcet-loser counterexample are documented inline in
`PLAN_SOLIDITE_TECHNIQUE.md`'s Lot 4.2 and 4.4 sections.*
