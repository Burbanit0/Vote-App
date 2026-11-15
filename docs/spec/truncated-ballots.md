# Truncated ballots and equal ranks: what each engine does today

> **status:** measured, not decided. Work order P3-5 of
> [`WORK_ORDERS_2026-11.md`](../plan/vote-app/WORK_ORDERS_2026-11.md), Phase 3 of
> [`PLAN_GLOBAL_2026-11.md`](../plan/vote-app/PLAN_GLOBAL_2026-11.md) (2026-11-15). Nothing here is a
> convention and no behaviour changed: it is what the two engines do now, so that the owner can say what
> each rule should do (question D4, below). **Every number is checked by a test that ran**:
> `fast_api_voter/api/tests/test_truncated_ballots_as_is.py` (the backend's readings) and
> `voter-app/src/lib/truncatedBallots.test.ts` (the client's, and this page's table), against the
> fixture `voter-app/src/lib/__fixtures__/truncatedBallots.json`, which
> `fast_api_voter/scripts/gen_truncated_ballots.py` generates from the backend's own rules.

## What was measured

A **truncated ballot** is a ranking that lists only some of the candidates (a bullet vote `[A]`, a
two-place ballot `[B, C]`). An **equal rank** is a voter exactly as near to two candidates as to each
other. The two engines treat them differently, and neither is the same as the other.

1. **Short ballots**, on the 21 ordinal rules the engines share: 60 fixed profiles of 5 to 9 ballots
   over the candidates A, B, C, D, each ballot ranking 1 to 4 of them. The backend's rule gets the
   ballots as lists of names; the client's gets the same ballots as lists of indices
   (`ruleWinnerFromRanks`). *Disagree on* counts the profiles on which the two winners differ.
2. **Equal ranks**, on the same 21 rules: nine voters, several exactly equidistant from A and B or
   from C and D, taken through each engine's own way of turning utilities into ballots (the backend's
   `rankings_from_utilities`, the client's `computeRanks`), with the candidates listed as given and in
   the reverse order. *Follows the listing* says whether reversing the order changes the winner.
3. **A truncated score ballot**, on the five score rules: the backend's `project_ballot`
   ("rank_truncated", the top 2 scored 1.0 and 0.5, the rest 0), the same matrix on both engines.

## The 21 ordinal rules

| Rule | Family | Short ballots: engines disagree on | Same? | Equal ranks: backend follows the listing | Equal ranks: client follows the listing | Same? |
|---|---|---|---|---|---|---|
| `plurality` | rank-reading | 0/60 | yes | no | yes | no |
| `two_round` | rank-reading | 0/60 | yes | no | yes | no |
| `irv` | rank-reading | 0/60 | yes | no | yes | no |
| `bucklin` | rank-reading | 0/60 | yes | no | yes | no |
| `dowdall` | rank-reading | 0/60 | yes | no | yes | no |
| `coombs` | rank-reading | 0/60 | yes | no | yes | no |
| `anti_plurality` | veto | 1/60 | no | no | yes | no |
| `borda` | positional by length | 24/60 | no | no | yes | no |
| `nanson` | positional by length | 32/60 | no | no | yes | no |
| `baldwin` | positional by length | 33/60 | no | no | yes | no |
| `condorcet` | pairwise | 43/60 | no | no | yes | no |
| `minimax` | pairwise | 45/60 | no | no | yes | no |
| `schulze` | pairwise | 40/60 | no | no | yes | no |
| `ranked_pairs` | pairwise | 40/60 | no | no | yes | no |
| `kemeny` | pairwise | 41/60 | no | no | yes | no |
| `black` | pairwise | 37/60 | no | no | yes | no |
| `raynaud` | pairwise | 38/60 | no | no | yes | no |
| `benham` | pairwise | 38/60 | no | no | yes | no |
| `river` | pairwise | 40/60 | no | no | yes | no |
| `smith_irv` | pairwise | 34/60 | no | no | yes | no |
| `split_cycle` | pairwise | 36/60 | no | no | yes | no |

(`condorcet` is the client's name for Copeland's method, `kemeny` for the backend's `kemeny_young`.)

## The other seven rules

| Rule | A truncated ballot | Backend | Client | Same? |
|---|---|---|---|---|
| `score` | a score vector with 0 for the unranked | elects A | elects A | yes |
| `star` | the same | elects C | elects C | yes |
| `cumulative` | the same | elects A | elects A | yes |
| `maximin` | the same | elects A | elects A | yes |
| `nash` | the same | elects C | elects C | yes |
| `approval` | the voter's utility, projected | elects A on 1-place ballots, C on 2 and 3 | no truncation | not comparable |
| `majority_judgment` | the voter's utility, projected | elects A on 1-place ballots, C on 2 and 3 | no truncation | not comparable |

The five score rules count the zeros the same way on both engines (they are parity-locked). Approval
and majority judgment each derive their ballot from utility their own way (`CLAUDE.md`), and the
client has no truncation at all (`ballot.truncate_at` is only forwarded to the backend's profile
endpoint): on six voters whose full-information winner is C, the backend elects A when every ballot
has one place, and C with two or three.

## The readings, one family at a time

**Rank-reading rules** (plurality, two-round, IRV, Bucklin, Dowdall, Coombs): they read a ballot from
its top (or its last ranked candidate), and a short ballot just ends where it ends. The two engines
agreed on all 60 profiles.

**Veto** (anti-plurality): both engines veto the last *ranked* candidate. They disagreed on one
profile, for a different reason: see "the field", below.

**Positional by length** (Borda, Nanson, Baldwin). The backend scores a ballot by its own length: a
ballot of `n` names gives position `p` the points `n − 1 − p`, so a bullet vote `[A]` gives A **zero**.
The client scores `m − 1 − rank` on a field of `m`, so the same bullet vote gives A `m − 1`, and an
unranked candidate gets nothing. On `[[A], [B, C]]` the backend elects B, the client A.

**Pairwise** (Copeland, minimax, Schulze, ranked pairs, Kemeny, Black, Raynaud, Benham, river,
Smith-IRV, split cycle: all read one shared duel count). On `[[A, B], [C]]`:
- *backend*: an unranked candidate is **below every ranked one**, and a ballot that ranks neither of
  two candidates casts **no vote** in their duel (`A` beats `B` once, `A` beats `C` once, `C` beats
  both `A` and `B` once; nothing between A and B from the second ballot);
- *client*: an unranked candidate is given position 0, the **top**, and an exact tie in position
  goes to the later-listed candidate, so the duel counts are `[[0,1,0],[1,0,0],[2,2,0]]`: the unranked
  C beats A and B on both ballots, and A against B is decided by the listing. It is a by-product of
  `pairwise()` assuming a full ranking, not a reading anyone chose.

**The field.** The backend reads the candidates off the ballots: a candidate that no ballot ranks is
not in the field. The client counts all `m`. On `[[D], [B], [C, B], [D, C, B], [D]]` nobody ranks A:
anti-plurality on the backend never considers it and elects C; on the client A is never vetoed and
wins.

**Equal ranks.** Neither engine's rules ever see a tie: both turn equal utilities into a strict
ranking first. The backend orders a voter's own tie by a lot seeded with the voter (#662), so
reversing the listing moves nothing (0 of 21 rules). The client's `computeRanks` sorts by utility and
leaves equal ones in candidate-index order, so the same voters elect a different winner when the
candidates are listed the other way, in **all 21** rules. The fix of #662 was the backend's alone.

## Questions for the owner (D4)

These are the disagreements, and each blocks work order P3-6 (one convention). None has been answered.

1. **A candidate a ballot leaves out, in a duel.** Below every ranked candidate and no duel between
   two unranked ones (the backend)? Or abstention for both? The client's reading is an accident and
   not a candidate. This fixes eleven rules at once, since they share one duel count.
2. **A candidate a ballot leaves out, in Borda-type points** (Borda, Nanson, Baldwin). Points by the
   ballot's own length (the backend: a bullet vote is worth nothing), by the field (the client: it is
   worth `m − 1`), or the unranked share the leftover points evenly?
3. **The field.** The candidates the ballots name (the backend), or the candidates on offer (the
   client)? It decides whether a candidate nobody ranks can win.
4. **A voter's own tie, on the client.** `computeRanks` should not follow the listing: the same
   per-voter lot as the backend (which needs a client twin of `tie_lot.ranking`), or another way?
   This one is a bug under the invariant of `LISTING_ORDER_TIES.md`, so the question is how, not
   whether.
5. **Truncation on the client.** Does the client get truncated ballots at all? Today the playground's
   ballot type is only sent to the backend, so the live winner always reads full ballots.
