# Listing-order ties

> **status:** live — #662–#667 are fixed (PLAN_BEYOND_CI W5), and so are the lot's finaliser (#1066), the ranked rules (#1074), the workers' tallies (#1076), the lock order of ranked pairs and River (#1083), Kemeny-Young's equal rankings (#1088), the last aggregates, tallies and runners-up (#1090) and the last two orders (Hotelling's moves, identity voting's default groups) (#1092) (#926); what remains of the 2026-10-09 decision is below. (Set 2026-10-08; `docs/README.md` lists every plan.)

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

#667 did the score rules and #662 a voter's own ties; #1066 finalised the lot itself, and the
ranked-rules PR (#1074) did the first three bullets: where a ranked rule ends in a tie it cannot
separate, both engines draw by lot over the tied names, with the request's seed (below).
What that PR leaves, as #926's remainder, is in "Open".

**The lot** is `api/engine/utils/tie_lot.py` and its twin `voter-app/src/lib/tieLot.ts`:
FNV-1a (32-bit) over the UTF-8 bytes of the seed and the
tied names in code-point order, finalised with murmur3's fmix32; the index is that hash
modulo the number of tied names. Both test files pin the same draws, among them the same
64-seed sequences for 2, 3 and 5 names. A tie is equal up to float noise (1e-9 relative,
as `break_tie` reads one): the engines' logs and sums can differ in the last bits. The client draws over names when its caller passes
them (`ruleWinnerFromRanks`' `names`), and over indices otherwise.

**The lot's seed.** On the backend, every score rule takes a keyword `seed` (0 by default),
and so do `compare_all_methods`, `rule_winner` and `winner_from_utilities`. The endpoints
with a request seed pass it to their score rules, so a tie is drawn per request rather than
always the same way: `/simulate`, `/simulate-pipeline`, `/coalition`, `/primary`,
`/divergence`, `/campaign-sensitivity`, `/combined-effects`, `/demographic-turnout`,
`/compulsory-voting`, `/behavioral-biases`, `/nota`, `/ballot-complexity`,
`/electoral-fatigue`, `/choice-overload` (its majority judgment), `/polarization` (each trial
its own), `/affective-polarization`, `/abstention` and `/collective-will`. The strategic
probe reruns a rule with the same seed. `test_tie_lot.py` checks `/simulate` and
`/divergence` end to end.

Still at 0:
- **`/profile-simulate`**, on purpose: it feeds the playground, whose client engine still
  draws with 0. Threading `config.seed` through the client's ~20 analysis entry points
  (scorecard, sincerity, criteria, equilibrium, …) comes first, then this endpoint follows.
- **Endpoints without a seed:** the public v1 API, and `/simulations/monte-carlo` and its
  socket, which draw a fresh electorate each run.
- **A ranked rule called directly** with no `seed=`: it draws with 0. The engine's entry points
  (`compare_all_methods`, `rule_winner`, `winner_from_utilities`) and the workers pass the
  request's seed.
- **Polity's elections** (`domain/polity/`), out of scope as below: seeding them would change
  the archived runs' outcomes.

**A two-way tie no longer follows the seed's parity.** `draw` used to take FNV-1a modulo the
number of tied names, and FNV-1a's low bit is the parity of its input, so between two names the
draw alternated with the seed's last digit (Ann for seeds 1, 3, 5, 7 and Ben for 2, 4, 6, 8, on
twin candidates). Both engines now finalise it with fmix32, as the per-voter lot has since #663.
The pinned draws changed on both sides, and so did the parity fixture's score-rule draws and
the tied-electorate snapshot (the tied electorates in them are where a draw shows).

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
| #664 | The campaign and information models draw their noise from one stream per candidate (`tie_lot.streams`: the seed and the candidate's name), not from one shared stream in slot order; the workers pass the real candidates to `simulate_campaign` and read its shares by name, not by slot position |
| #663, #665 | A voter's nearest option, or favourite, when two tie: `tie_lot.nearest` (vectorised, for `argmin`/`argmax` rows) and `tie_lot.favourite` (the top of the voter's `ranking`), a lot seeded with the endpoint's seed and the voter. Issue voting (and its winner), party dynamics, the playground's sincere vote and desertion, Hotelling, `tech.py`, the theory workers, conviction voting, and the 22 sites that took a voter's favourite with `max(utilities, key=…)`. A voter's lot is finalised with fmix32 (`_voter_lot`): FNV-1a's low bit is only the parity of its input, which made a two-way tie alternate with the voter's index |
| #1066 | The rule-level lot (`tie_lot.draw`, `drawName` in `tieLot.ts`) is finalised with fmix32 on both engines, so a two-way draw falls both ways across seeds instead of alternating with the seed's parity; the pinned draws, the parity fixture's draws and the tied-electorate snapshot are regenerated |
| #1074 | The ranked rules draw an exact tie by the seeded lot on both engines, with the request's seed: plurality, two-round (its two finalists, then the runoff), Borda, Dowdall, positional, anti-plurality, approval, Bucklin, minimax, Copeland (Copeland score, then total wins, then the lot), Schulze, Nanson, Baldwin, Raynaud, Benham, Smith-IRV, Split Cycle (Borda, then the lot), ranked pairs and River (the sources / roots left); IRV and Coombs draw a full tie instead of returning no winner. `playgroundVoting.ts` draws over the same names; the parity fixture is regenerated |
| #1076 | The workers' aggregate tallies draw an exact tie by the request's seed instead of by name: the cascade, shy-voter (real and polled), NOTA (a tie goes to a candidate, drawn among those tied), liquid democracy, approval in the behavioral-biases and choice-overload workers, abstention and gerrymander (first choices), the compulsory-voting run, vote-steps approval, the Polis election, identity plurality, evaluative voting, quadratic voting (the winner, and a voter's odd leftover vote, now a per-voter lot), and random ballot's most probable winner in `compare_all_methods` |
| #1083 | The lock order of ranked pairs and River on equal margins and supports follows the seeded lot, not the names (backend) or the indices (client): `tie_lot.edge_key` and its twin `edgeKey` hash the seed and the majority's two names, and the equal majorities are locked in that order. The client sorts with the same key (hashed only for two majorities equal on both counts), at seed 0 like its other lots, so the engines agree at the backend's default seed. The parity fixture is regenerated |
| #1088 | Kemeny-Young's choice among equally good rankings, on the exact path (up to 10 candidates), is a draw by the seeded lot on both engines: several candidates can head an optimal ranking, every one that can is collected from the full set of the subset DP, and `tie_lot.draw` (`bestOf` on the client) picks one over their names with the request's seed, not the name-smallest (backend) or index-smallest (client). The client draws at seed 0 like its other lots. The parity fixture is regenerated |
| #1090 | Three aggregates that still followed the listing order or the names, now drawn by the seeded lot over the names: the epistocracy worker's tally winner (`tally.index(max(tally))`, first-listed), the Equal Shares completion's fallback when it has no rng (`sorted(..., key=(-approval, name))`; it takes a `seed`, and draws each place in turn), and the runners-up of `/primary`'s primaries and of its general election (the second place of a tie). The runner-up is now read off the first-preference counts, not their 4-place rounded shares |
| #1092 | Two orders that followed the listing but were not ties (owner decision D3). Hotelling's candidates best-respond one after another, each to the moves before it: the order is now drawn by the seeded lot over their names, a new one each round (seeded with the request's seed and the round); reversing the listing changed the final positions in 12 of 12 seeds, and now in none. Identity voting's three default groups were bound to the first, second and third listed candidates: each now backs the candidate nearest its centre (the axis the voters judge candidates on), an exact tie drawn by the lot, in the worker and in the Lab's panel (which always sent its own groups, bound to `candidates[i % n]`); the worker no longer raises with fewer than three candidates (the endpoint's schema still asks for three) |
| #662 | A voter's own tie (an indifferent voter, a truncated ballot's tail, twin candidates) is ordered by a lot seeded with the voter's id, so it falls differently from voter to voter and never by listing order: `tie_lot.ranking`, used by `project_ballot`, `rankings_from_utilities`, `compare_all_methods` (blank-vote path and Monte-Carlo twin included), `vote_ranked`, and the 19 worker sites that built a voter's ranking with the same stable sort |

## Open

#926 tracks what remains (the lot's finaliser, #1066, and the ranked rules' end-of-rule ties,
#1074, are in, each with the parity fixture regenerated):
- ties inside a rule that are not its final answer and still follow the names: above the exact
  cap (10 candidates: only polity reaches it, no request does), Kemeny-Young's KwikSort
  approximation takes the middle of the candidate list as its pivot and its caller sorts that
  list by name, so its answer follows the names. The client falls back to Borda there, so the
  two engines differ on purpose and neither draws. (The lock order of ranked pairs and River,
  and Kemeny-Young's exact path, are fixed: see the table. The elimination rules need
  nothing: IRV, Coombs, Nanson, Baldwin, Raynaud, Benham and Smith-IRV drop every candidate
  tied for last together, so a round has no tie to break; only a tie among the last survivors
  is left, and that is drawn.)
- Equal Shares' main loop: two candidates with the same per-voter price `rho` are elected by name
  (`c < best_c` in `get_equal_shares_result`), with or without an rng, and the same shape in the
  load-balancing rule above it (`c < best_candidate`). Found while doing P3-3; a lot there changes
  which candidate is elected first, so it is its own work order, not a completion tie;
- Hotelling's Borda objective ranks each voter's candidates with `argsort`, which breaks equal
  utilities by column index: with two candidates on exactly the same point, reversing the listing
  changes where they end up (plurality draws that tie per voter and approval has none). Found
  while doing P3-4; a per-voter lot in a numpy hot path is a design choice, so its own work order;
- Hotelling keeps only the first six candidates listed (`cand_specs[:6]`), though its schema
  accepts eight: the seventh and eighth are dropped by their position in the list. Found while
  doing P3-4; a cap that should choose its six by something other than the listing, or be raised;
- The client's own ranking of a voter's tie: `computeRanks` sorts by utility and leaves equal ones
  in candidate-index order, where the backend orders them by a lot seeded with the voter (#662).
  With voters exactly as near to two candidates as to each other, reversing the listing changes the
  client's winner in 21 of 21 ordinal rules and the backend's in none. Measured while doing P3-5
  (`docs/spec/truncated-ballots.md`, question D4.4); it needs a client twin of `tie_lot.ranking`;
- Hotelling's best-response loop reads each candidate's current score from the utilities taken at
  the start of the round, but tries its moves against the positions earlier candidates already
  moved to, and a candidate that finds no improving move is frozen for good (`converged_set`,
  never re-evaluated). Neither follows the listing now that the order is a lot, but both make the
  result depend on that order's draw. Found while doing P3-4; not a tie, not changed.

## By design

Not every tie broken by name is a bug. The theory page's apportionment comparison (`_hamilton` and
the four divisor methods in `theory/workers.py`) breaks an exact quotient tie by name, the first
party in sorted order, on purpose (owner decision D3, 2026-11-15): it shows the methods side by
side on one input, the endpoint has no seed field, and the paradox detectors re-run a method on a
perturbed input and compare, which a lot would make noisy. The order a request lists its parties
in never decides a seat: `test_apportionment_ties.py` pins that, listed both ways.

**Found while writing #666's test (2026-10-09).**
- The backend's ranked rules already break an aggregate tie by name
  (`min(scores, key=lambda c: (-scores[c], c))` in `simulation_ranked_utils.py`): the option
  parked above, on one side of the dual engine only. Fixed by #1074.
- With one voter indifferent between the two tied candidates, 30 of the 34 methods changed
  winner when the order was reversed: `compare_all_methods` ranked that voter by a stable sort
  over the listing order. Fixed by #662, with every other site that built a voter's ranking
  the same way.
- On an exact two-way tie, IRV and Coombs return no winner at all, where the invariant wants
  the lot. Fixed by #1074.
- Approval is left as it was by #667 (the score rules): a tie in the client's tally goes to
  the first-listed candidate (`argmax`), the backend's to the name. Fixed by #1074.

Out of scope: polity's own seat allocation (tracked as E1, fixed on the polity
branch) and `/choice-overload`, whose candidates are generated from the seed,
so there is no request order to depend on.

**Test pattern for a fix:** run the endpoint with the candidates reversed and
assert the same result (`api/tests/test_apportionment_ties.py`).
