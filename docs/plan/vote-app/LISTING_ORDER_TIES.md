# Listing-order ties

> **status:** live — issue #664 is open; #666 is the test, and #667, #662, #663 and #665 are fixed (PLAN_BEYOND_CI W5). (Set 2026-10-08; `docs/README.md` lists every plan.)

**Invariant.** Reordering the candidates (or parties, or proposals) in a request
must not change the result. Where a rule reaches an exact tie, the tie is broken
by a seeded lot, never by position in the list: the endpoint's (`break_tie` / `top_k` in
`api/engine/utils/simulation_multiwinner_utils.py`), or for the single-winner rules
shared by both engines, the portable lot below.

**Decided 2026-10-09 (owner): the seeded lot, on both engines.** A name tie-break was
rejected: it swaps order-dependence for name-dependence (a candidate named Aaron wins
every tie). So:
- the backend's ranked rules move off their name tie-break, `(-score, name)`;
- IRV and Coombs draw instead of returning no winner on a full tie;
- the client engine (`playgroundVoting.ts`) gets the same draw, so parity holds and the
  fixture is regenerated;
- #667 and #662 implement it, and the strict xfails in `test_compare_all_methods_snapshot.py`
  flip as they do.

#667 did the score rules and #662 a voter's own ties. **Still to do from this decision:**
the ranked rules' aggregate tie-break (first bullet), IRV and Coombs on a full tie (second),
and the client's ordinal rules with them (third): 21 parity-locked rules, so one PR with the
fixture regenerated. No issue tracks it yet.

**The lot** is `api/engine/utils/tie_lot.py` and its twin `voter-app/src/lib/tieLot.ts`:
FNV-1a (32-bit) over the UTF-8 bytes of the seed and the
tied names in code-point order; the index is the hash modulo the number of tied names.
Both test files pin the same draws. A tie is equal up to float noise (1e-9 relative,
as `break_tie` reads one): the engines' logs and sums can differ in the last bits. The client draws over names when its caller passes
them (`ruleWinnerFromRanks`' `names`), and over indices otherwise. No caller passes a seed yet,
so it is 0 everywhere: the draw is reproducible and free of listing order, but a given
set of tied names always draws the same one. Threading the request's or trial's seed
through is still to do; it needs a parameter on `compare_all_methods` and the client.

## Fixed

| PR | What |
|---|---|
| #638 | Apportionment quotient ties (D'Hondt, Sainte-Laguë) by lot |
| #640 | Hamilton: exact integer remainders |
| #643 | Multi-winner rows (FPTP top-N, Equal Shares completion, coalition anchor) |
| #657 | Utilities no longer rounded to 4 dp before ranking (invented per-voter ties) |
| #659 | Playground assembly, structural fairness, no-show favourite |
| #661 | Profile engine's strategic transform no longer invents a first-place tie |
| #660 | (related) Redis cache no longer serves a previous build's results |
| #666 | `compare_all_methods` gets tied electorates: a snapshot, and a listing-order test per method in `test_compare_all_methods_snapshot.py`. Strict xfails mark what #662 and #667 still owe, so each fix has a test that flips |
| #667 | The score rules draw an exact tie by the seeded lot, on both engines: score, STAR (a tie for a finalist place; a tied runoff goes to the higher score, then the lot), majority judgment (once every grade is compared), cumulative, maximin, Nash, median voting, mean-median hybrid, variance-based |
| #663, #665 | A voter's nearest option, or favourite, when two tie: `tie_lot.nearest` (vectorised, for `argmin`/`argmax` rows) and `tie_lot.favourite` (the top of the voter's `ranking`), a lot seeded with the endpoint's seed and the voter. Issue voting (and its winner), party dynamics, the playground's sincere vote and desertion, Hotelling, `tech.py`, the theory workers, conviction voting, and the 22 sites that took a voter's favourite with `max(utilities, key=…)`. A voter's lot is finalised with fmix32 (`_voter_lot`): FNV-1a's low bit is only the parity of its input, which made a two-way tie alternate with the voter's index |
| #662 | A voter's own tie (an indifferent voter, a truncated ballot's tail, twin candidates) is ordered by a lot seeded with the voter's id, so it falls differently from voter to voter and never by listing order: `tie_lot.ranking`, used by `project_ballot`, `rankings_from_utilities`, `compare_all_methods` (blank-vote path and Monte-Carlo twin included), `vote_ranked`, and the 19 worker sites that built a voter's ranking with the same stable sort |

## Open

| Issue | Where | Mechanism |
|---|---|---|
| #664 | `information_model.py`, `campaign_dynamics.py` | Noise drawn per candidate slot, not per candidate. |

**Found while writing #666's test (2026-10-09).**
- The backend's ranked rules already break an aggregate tie by name
  (`min(scores, key=lambda c: (-scores[c], c))` in `simulation_ranked_utils.py`): the option
  parked above, on one side of the dual engine only.
- With one voter indifferent between the two tied candidates, 30 of the 34 methods changed
  winner when the order was reversed: `compare_all_methods` ranked that voter by a stable sort
  over the listing order. Fixed by #662, with every other site that built a voter's ranking
  the same way.
- On an exact two-way tie, IRV and Coombs return no winner at all, where the invariant wants
  the lot. No issue tracks this yet.
- Approval is left as it was by #667 (the score rules): a tie in the client's tally goes to
  the first-listed candidate (`argmax`), the backend's to the name. No issue tracks this yet.

Out of scope: polity's own seat allocation (tracked as E1, fixed on the polity
branch) and `/choice-overload`, whose candidates are generated from the seed,
so there is no request order to depend on.

**Test pattern for a fix:** run the endpoint with the candidates reversed and
assert the same result (`api/tests/test_apportionment_ties.py`).
