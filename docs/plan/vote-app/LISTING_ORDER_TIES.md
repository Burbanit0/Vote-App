# Listing-order ties

**Invariant.** Reordering the candidates (or parties, or proposals) in a request
must not change the result. Where a rule reaches an exact tie, the tie is broken
by the endpoint's seeded lot (`break_tie` / `top_k` in
`api/engine/utils/simulation_multiwinner_utils.py`), never by position in the list.

A name tie-break was considered and **parked**: it swaps order-dependence for
name-dependence, and the client engine (`playgroundVoting.ts`) keeps listing
order, so it would split the dual engine. Decide it on both engines at once.

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

## Open

| Issue | Where | Mechanism |
|---|---|---|
| #667 | `simulation_score_utils.py` maximin / median voting | 0–5 score ballots tie often; `max()` and a stable sort keep listing order. Parity-locked: fix both engines. |
| #662 | `profile_engine.py` `project_ballot`, `compare_all_methods` rankings | Stable sort over request order resolves truncation ties. |
| #663 | Issue voting, party dynamics | Sign-collapsed platforms / 4-dp positions, then `argmax`/`argmin`. |
| #664 | `information_model.py`, `campaign_dynamics.py` | Noise drawn per candidate slot, not per candidate. |
| #665 | Playground, Hotelling, `tech.py`, theory workers, conviction voting | Raw `argmin`/`argmax`/`min()` for the nearest candidate. |
| #666 | `test_compare_all_methods_snapshot.py` | Golden is unanimous, so no tie-break regression can show. |

Out of scope: polity's own seat allocation (tracked as E1, fixed on the polity
branch) and `/choice-overload`, whose candidates are generated from the seed,
so there is no request order to depend on.

**Test pattern for a fix:** run the endpoint with the candidates reversed and
assert the same result (`api/tests/test_apportionment_ties.py`).
