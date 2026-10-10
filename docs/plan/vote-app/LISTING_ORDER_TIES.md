# Listing-order ties

> **status:** live — issues #662–#665 are open; #666 is their test and #667 is fixed (PLAN_BEYOND_CI W5). (Set 2026-10-08; `docs/README.md` lists every plan.)

**Invariant.** Reordering the candidates (or parties, or proposals) in a request
must not change the result. Where a rule reaches an exact tie, the tie is broken
by the endpoint's seeded lot (`break_tie` / `top_k` in
`api/engine/utils/simulation_multiwinner_utils.py`), never by position in the list.

**Decided 2026-10-09 (owner): the seeded lot, on both engines.** A name tie-break was
rejected: it swaps order-dependence for name-dependence (a candidate named Aaron wins
every tie). So:
- the backend's ranked rules move off their name tie-break, `(-score, name)`;
- IRV and Coombs draw instead of returning no winner on a full tie;
- the client engine (`playgroundVoting.ts`) gets the same draw, so parity holds and the
  fixture is regenerated;
- #667 and #662 implement it, and the strict xfails in `test_compare_all_methods_snapshot.py`
  flip as they do.

**The lot** is `api/engine/utils/tie_lot.py` and its twin `voter-app/src/lib/tieLot.ts`:
FNV-1a (32-bit) over the UTF-8 bytes of the seed (0 unless a caller passes one) and the
tied names in code-point order; the index is the hash modulo the number of tied names.
Both test files pin the same draws. A tie is equal up to float noise (1e-9 relative,
as `break_tie` reads one): the engines' logs and sums can differ in the last bits. The client draws over names when its caller passes
them (`ruleWinnerFromRanks`' `names`), and over indices otherwise.

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

## Open

| Issue | Where | Mechanism |
|---|---|---|
| #662 | `profile_engine.py` `project_ballot`, `compare_all_methods` rankings | Stable sort over request order resolves truncation ties. |
| #663 | Issue voting, party dynamics | Sign-collapsed platforms / 4-dp positions, then `argmax`/`argmin`. |
| #664 | `information_model.py`, `campaign_dynamics.py` | Noise drawn per candidate slot, not per candidate. |
| #665 | Playground, Hotelling, `tech.py`, theory workers, conviction voting | Raw `argmin`/`argmax`/`min()` for the nearest candidate. |

**Found while writing #666's test (2026-10-09).**
- The backend's ranked rules already break an aggregate tie by name
  (`min(scores, key=lambda c: (-scores[c], c))` in `simulation_ranked_utils.py`): the option
  parked above, on one side of the dual engine only.
- With one voter indifferent between the two tied candidates, 30 of the 34 methods change
  winner when the order is reversed: `compare_all_methods` ranks that voter by a stable sort
  over the listing order (#662).
- On an exact two-way tie, IRV and Coombs return no winner at all, where the invariant wants
  the lot. No issue tracks this yet.

Out of scope: polity's own seat allocation (tracked as E1, fixed on the polity
branch) and `/choice-overload`, whose candidates are generated from the seed,
so there is no request order to depend on.

**Test pattern for a fix:** run the endpoint with the candidates reversed and
assert the same result (`api/tests/test_apportionment_ties.py`).
