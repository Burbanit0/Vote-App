# Truncated ballots and equal ranks: what each engine does today

> **status:** measured, not decided. Work order P3-5 of
> [`WORK_ORDERS_2026-11.md`](../plan/vote-app/WORK_ORDERS_2026-11.md), Phase 3 of
> [`PLAN_GLOBAL_2026-11.md`](../plan/vote-app/PLAN_GLOBAL_2026-11.md) (2026-11-15). Nothing here is a
> convention and no behaviour changed: it is what the two engines do now, so that the owner can say what
> each rule should do (question D4, below). **Every table cell is parsed and compared with a test's
> measurement**: `voter-app/src/lib/truncatedBallots.test.ts` (the client's side, and this page) against
> the fixture `voter-app/src/lib/__fixtures__/truncatedBallots.json`, which
> `fast_api_voter/scripts/gen_truncated_ballots.py` generates from the backend's own rules and
> `fast_api_voter/api/tests/test_truncated_ballots_fixture.py` keeps in step; the backend's readings
> are also pinned on literal ballots in `fast_api_voter/api/tests/test_truncated_ballots_as_is.py`. The
> prose around the tables is explanation, and is not machine-checked.

## What was measured

A **truncated ballot** is a ranking that lists only some of the candidates (a bullet vote `[A]`, a
two-place ballot `[B, C]`). An **equal rank** is a voter exactly as near to two candidates as to each
other. The two engines treat them differently.

1. **The "duel" probe**, on the 21 ordinal rules the engines share: `[[A], [A], [A], [B, C], [B, C]]`,
   three bullet votes for A and two ballots B then C; nobody ranks D. No rule is
   decided by a lot on the backend (the generator refuses a profile where one is), so each cell is a
   reading and not a draw. The client's cell lists every winner it gives over all 24 listings of the
   four candidates (`A, B, C, D` means the winner depends on the order the candidates are listed in).
2. **60 short-ballot profiles** of 5 to 9 ballots over A, B, C, D, each ballot ranking 1 to 4 of them.
   *Disagree on* counts the profiles where the two winners differ. These counts include ties each
   engine draws by lot (the client always at seed 0), so they size the gap; they do not say why.
3. **Equal ranks**: nine voters, several exactly equidistant from A and B or from C and D, turned
   into ballots by each engine's own way (the backend's `rankings_from_utilities`, the client's
   `computeRanks`), the candidates listed as given and reversed. One electorate only. *Follows the
   listing* says whether reversing the order changes the winner.
4. **The "field" probe**: `[[D, B], [C, D], [B, C]]`, a profile on which nobody ranks A.
5. **A cut score ballot** (five score rules): the backend's `project_ballot` ("rank_truncated", the top
   2 scored 1.0 and 0.5, the rest 0) on seven voters, handed to both engines as the same matrix, a
   matrix on which the winner is the same under every seed.
6. **A cut grade ballot** (approval, majority judgment): nine voters' 0 to 5 grades (multiples of 0.2),
   in full and cut to their top 1 and top 2, read as grades by majority judgment and as 0/1 approvals
   (grade 0.6 or more) by approval. Each engine derives these two from utility its own way
   (`CLAUDE.md`), so the ballot is shared as in the parity harness. The client has no truncation: it
   only forwards `ballot.truncate_at` to the backend's profile endpoint.
7. **Equal scores**: two candidates every voter grades alike, the field listed as given and reversed,
   for the seven non-ordinal rules.

## The 21 ordinal rules

| Rule | Family | Duel probe: backend elects | client elects | Same? | 60 profiles: engines disagree on | Equal ranks: backend follows the listing | client follows the listing | Same winners? |
|---|---|---|---|---|---|---|---|---|
| `plurality` | rank-reading | A | A | yes | 0/60 | no | yes | no |
| `two_round` | rank-reading | A | A | yes | 0/60 | no | yes | no |
| `irv` | rank-reading | A | A | yes | 0/60 | no | yes | no |
| `bucklin` | rank-reading | A | A | yes | 0/60 | no | yes | no |
| `dowdall` | rank-reading | A | A | yes | 0/60 | no | yes | no |
| `coombs` | rank-reading | A | A | yes | 0/60 | no | yes | no |
| `anti_plurality` | veto | B | D | no | 1/60 | no | yes | no |
| `borda` | positional | B | A | no | 24/60 | no | yes | no |
| `nanson` | positional | B | A | no | 32/60 | no | yes | no |
| `baldwin` | positional | B | A | no | 33/60 | no | yes | no |
| `condorcet` | pairwise | A | A, B, C, D | no | 43/60 | no | yes | no |
| `minimax` | pairwise | A | A, B, C, D | no | 45/60 | no | yes | no |
| `schulze` | pairwise | A | A, B, C, D | no | 40/60 | no | yes | no |
| `ranked_pairs` | pairwise | A | A, B, C, D | no | 40/60 | no | yes | no |
| `kemeny` | pairwise | A | A, B, C, D | no | 41/60 | no | yes | no |
| `black` | pairwise | A | A, B, C, D | no | 37/60 | no | yes | no |
| `raynaud` | pairwise | A | A, B, C, D | no | 38/60 | no | yes | no |
| `benham` | pairwise | A | A, B, C, D | no | 38/60 | no | yes | no |
| `river` | pairwise | A | A, B, C, D | no | 40/60 | no | yes | no |
| `smith_irv` | pairwise | A | A, B, C, D | no | 34/60 | no | yes | no |
| `split_cycle` | pairwise | A | A, B, C, D | no | 36/60 | no | yes | no |

(`condorcet` is the client's name for Copeland's method, `kemeny` for the backend's `kemeny_young`.)

## The field probe

| Rule | Backend elects (across seeds) | Client elects | Same? |
|---|---|---|---|
| `anti_plurality` | B, C, D | A | no |
| `coombs` | B, C, D | A | no |

## The other seven rules

A cut ballot, five score rules (the backend's `rank_truncated` at 2 places, one matrix for both):

| Rule | Backend elects | Client elects | Same? |
|---|---|---|---|
| `score` | C | C | yes |
| `star` | C | C | yes |
| `cumulative` | C | C | yes |
| `maximin` | B | B | yes |
| `nash` | B | B | yes |

A ballot in full, cut to 1 place, cut to 2 places (approval and majority judgment, the shared ballot):

| Rule | Whole ballot | Top 1 | Top 2 | Both engines alike? |
|---|---|---|---|---|
| `approval` | C | D | B | yes |
| `majority_judgment` | C | D | B | yes |

Equal scores (A and B graded alike by everyone; listed, then reversed), the winner on each engine:

| Rule | Backend | Client | Same? |
|---|---|---|---|
| `score` | A, A | A, A | yes |
| `star` | A, A | A, A | yes |
| `cumulative` | A, A | A, A | yes |
| `maximin` | A, A | A, A | yes |
| `nash` | A, A | A, A | yes |
| `approval` | A, A | A, A | yes |
| `majority_judgment` | A, A | A, A | yes |

So on a ballot both engines are handed alike, the seven agree, and a tie in scores is drawn the same way
whichever way the candidates are listed. What differs for approval and majority judgment is the step
before: how each engine turns a voter's utility into the ballot, and that only the backend can cut it.
That step is not measured on this page.

## The readings, one family at a time

**Rank-reading rules** (plurality, two-round, IRV, Bucklin, Dowdall, Coombs): they read a ballot from its
top (Coombs, its last ranked candidate), and a short ballot ends where it ends. The engines agree on the
duel probe and on all 60 profiles. On the field probe Coombs is the exception, below.

**Veto** (anti-plurality): both engines veto the last *ranked* candidate. On the duel probe the backend
elects B (A is vetoed three times, C twice, B never) and the client D: with a field of four, D is never
vetoed either, and the tie between B and D is drawn by lot.

**Positional by length** (Borda, Nanson, Baldwin). The backend scores a ballot by its own length: a
ballot of `n` names gives position `p` the points `n - 1 - p`, so a bullet vote `[A]` gives A **zero**.
The client scores `m - 1 - rank` on a field of `m`, so the same bullet vote gives A `m - 1`. On the duel
probe's three bullet votes the backend elects B and the client A.

**Pairwise.** Seven rules call the backend's one duel count, `_pairwise_wins` (Copeland, Kemeny-Young,
Raynaud, ranked pairs, river, Smith-IRV, split cycle). Minimax and Schulze count duels themselves; Black
and Benham ask for a Condorcet winner and fall back (Black on Borda by ballot length, Benham on IRV).
On `[[A, B], [C]]` the shared count is:

- *backend*: an unranked candidate is **below every ranked one**, and a ballot that ranks neither of two
  candidates casts **no vote** in their duel (A beats B once, A beats C once, C beats A and B once;
  nothing between A and B from the second ballot);
- *client*: `pairwise()` gives an unranked candidate position 0, the **top**, and an exact tie in position
  goes to the later-listed candidate, so the counts are `[[0,1,0],[1,0,0],[2,2,0]]`: the unranked C beats
  A and B on both ballots, and A against B is decided by the listing. That is `pairwise()` assuming a
  full ranking, not a reading anyone chose. On the duel probe all eleven pairwise rules elect A on the
  backend and a different candidate, depending on how the field is listed, on the client.

**The field.** The backend reads the candidates off the ballots: a candidate that no ballot ranks is not
in the field. The client counts all `m`. On the field probe the backend's anti-plurality and Coombs elect
B, C or D (a lot decides some seeds) and never A; the client elects A in both, the candidate nobody ranks.

**Equal ranks.** Neither engine's rules ever see a tie: both turn equal utilities into a strict ranking
first. The backend orders a voter's own tie by a lot seeded with the voter (#662), so on this
electorate reversing the listing moves nothing in any of the 21 rules. The client's `computeRanks` sorts by
utility and leaves equal ones in candidate-index order, so the same voters elect a different winner when
the candidates are listed the other way, in all 21 rules. The fix of #662 was the backend's alone.

## Questions for the owner (D4)

These are the disagreements, and each blocks work order P3-6 (one convention). None has been answered.

1. **A candidate a ballot leaves out, in a duel.** Below every ranked candidate and no duel between two
   unranked ones (the backend)? Or abstention for both? The client's reading depends on the listing,
   which breaks the invariant of `LISTING_ORDER_TIES.md`, so it is not a candidate. Seven rules share the
   backend's count; Minimax and Schulze, and the fallbacks of Black (Borda) and Benham (IRV), would each
   need the same decision of their own.
2. **A candidate a ballot leaves out, in Borda-type points** (Borda, Nanson, Baldwin; Black falls back
   on Borda). Points by the ballot's own length (the backend: a bullet vote is worth nothing), by the field
   (the client: it is worth `m - 1`), or do the unranked share the leftover points evenly?
3. **The field.** The candidates the ballots name (the backend), or the candidates on offer (the client)?
   It decides whether a candidate nobody ranks can win, in anti-plurality and Coombs on the probes.
4. **A voter's own tie, on the client.** `computeRanks` follows the listing in all 21 rules, which breaks
   the invariant of `LISTING_ORDER_TIES.md` (it is recorded there as open): the same per-voter lot as the
   backend (which needs a client twin of `tie_lot.ranking`), or another way?
5. **Truncation on the client.** Does the client get truncated ballots at all? Today the playground's
   ballot type is only sent to the backend, so the live winner always reads full ballots.
6. **Equal scores.** Nothing to decide today: both engines draw a tie in scores the same way, and the
   listing does not move it. Recorded so that P3-6 does not reopen it.
