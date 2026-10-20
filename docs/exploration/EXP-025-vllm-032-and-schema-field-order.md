# EXP-025 — vLLM 0.32.0, and the order the schema's fields are sent in

- **Date**: 2026-10-18/19 · **Status**: 0.32.0 rejected (stay on 0.31.0); the "effective" order
  (`motif` first) rejected; the order is now a measured table (ADR-030), whose first
  four entries the owner set from the first sweep (2026-10-20) · **Real cost**: about nine hours of GPU over two
  days, one server at a time (the bump protocol, bank sessions for the cause and the order, a production-path
  chain, a 4-year live A/B) · **Token cost**: not measured
- **Verdict in one sentence**: 0.32.0 changed what `disable_any_whitespace` means (compact JSON), which
  made the model write `"shifts":[]` after a concession in 41 of 45 cases; chasing it showed that the order
  a schema's fields reach the model in (OBS-050) changes its answers a lot, that the order that looked
  logical made `pressure_action` blind, and that no order should be chosen without a ground-truth test, which
  ADR-030 now runs.

## Starting hypothesis
vLLM 0.32.0 (pushed 2026-10-18) lists no change that touches this stack. The bump protocol of
`vllm-bump-recipe` (a 0.31.0 control with today's flags, then 0.32.0: thinking budget, determinism, three
restarts, the live suite, three 2-year runs, the frozen bank) should show a null result, as 0.31.0 did.

## What the 0.32.0 protocol found
Nothing crashed. The server starts (healthy in 137 s cold), restarts and determinism pass, the thinking
budget is honoured (the results doc is byte-identical), the KV cache is unchanged (38,848 tokens, 2.37x).
The frozen bank, scored against the 0.31.0 control, did not pass:

| family | 0.31.0 | 0.32.0 |
|---|---:|---:|
| `representative_response` valid | 43/45 | **2/45** (41 discordant, all against 0.32.0, Holm p = 1e-11) |
| logprob gate | 16/16 aligned | 13/16 |
| live suite | 11 passed, 1 xfailed | 1 failed: the full-size `vote_cast` batch returned `blank=1` with a ranking |

All 41 failures are the same: `stance=1` (concession) with an empty `shifts` list, 31 tokens, on the same
request hash that gives real shifts (about 79 tokens) on 0.31.0.

**Cause, by bisection.** The two images differ in `xgrammar` (0.2.7 to 0.2.8) and `transformers` (5.17.0 to
5.19.0). An image with `xgrammar` 0.2.7 behaved the same as stock 0.32.0, the compiled grammar text is
identical, and the patched image below still has both new packages. The cause is vLLM PR #58067 (merged
2026-10-08, "Make disable_any_whitespace actually disable whitespace on xgrammar"): the flag now passes
`separators=(",", ":")`, so output is compact (`{"cid":6001,"shifts":[]`). Before, it only set
`any_whitespace=False` and xgrammar kept `", "` and `": "`. The compose file sets the flag (the 2026-09-06
whitespace-loop fix). The PR's own measurement is on `json_object` and says typed `json_schema` requests were
unaffected; on Qwen3-8B-AWQ with EAGLE-3 they are not.

| server | invalid (45 `representative_response` cases) | output |
|---|---:|---|
| 0.31.0 stock | 0 | spaced JSON |
| 0.32.0 stock | 33 | compact JSON |
| 0.32.0 + `xgrammar` 0.2.7 | 33 | compact JSON |
| 0.32.0 with the one `separators` line reverted | 0 | identical to 0.31.0, token for token |

The patched image scored on the full bank equals the 0.31.0 control (`representative_response` 43/45, logprob
gate 16/16, no paired difference above p = 0.125). So the whole regression is that line. Upstream calls
compact "strictly better"; no issue was filed.

## The order the fields are sent in
`sort_keys=True` on the request body reaches the schema, so every object's fields have always reached the
model alphabetically (OBS-050). Under compact JSON that put `shifts` before `stance`. Four bank sessions
(the bank stores its schemas sorted, so each arm rebuilds the order from the Pydantic classes):

| `representative_response` valid | 0.31.0 | 0.32.0 stock |
|---|---:|---:|
| alphabetical (production until now) | 43/45 | 2/45 |
| declared order (the classes' own: `cid, shifts, stance, motif`) | 44/45 | 13/45 |
| **effective order** (`cid, motif, stance, shifts`) | **45/45** | **43/45** |

Declared order is not enough: `ResponseDecision` declares `shifts` before `stance`. The effective order is
the id, then `motif` (its code constrains the decision: stance 3 needs motif 303/308, `salience_delta` 0 iff
motif 403), then the decision, then what hangs on it. `vote_cast` was 14/14 under both arms (13/14, 11/14
before); the logprob gate passed 16/16 on all four arms; accuracy moved nowhere significantly
(`candidacy_p500`, `pressure_act`, `vote_first_choice`, Holm). `chamber_deliberation` and
`campaign_positioning` lose one case each in some sessions; they flip between runs.

## The motif-first order on trial (2026-10-18/19)
It was put in production on the branch (commit `ddabeaf8`, never pushed): every decision as id, `motif`,
decision, dependents, and every other object (agents' turns, `PositionShift`) in its class's declared order.
Request hashes did not move (the order is applied after the hash), and on stock 0.31.0 the bank, the live
suite (11 passed, 1 xfailed) and the 2-year runs passed. Then:

**Ground truth said no.** On the frozen bank's truth families, 0.31.0 (better / worse units against
alphabetical, McNemar):

| | alphabetical | declared | motif first |
|---|---:|---:|---:|
| `pressure_act` (24) | 62.5% | **79.2%** (5 / 1, p 0.22) | 45.8% (4 / 8) |
| `vote_first_choice` (40) | 90.0% | **97.5%** (3 / 0, p 0.25) | 97.5% (3 / 0) |
| `candidacy_p500` (500) | 63.6% | **66.4%** (31 / 17, p 0.06) | 62.8% (0 / 4) |

With `motif` first, the model acted for 23 of the 24 pressure citizens, whatever their situation: 11 of the
12 who should act, and all 12 who should not. The declared order did nothing for all 12 who should not.
None of these differences survives Holm alone, but the declared order moves the same way on all three.

**The noise is not the explanation.** Two sessions sent the same bytes, on two server instances, give 0
different answers on pressure, candidacy, coalition, nomination, response and vote: every difference there
is the order. `positioning_poles` (9 of 10 differ), `chamber_poles` (2) and `reaction_scandal` (1) are too
noisy to say anything. The arms change key order only (same fields, types, bounds and required set), and
`prompt_source_sha256` only feeds `sweep_statistics.py`.

**Live, the society changed for the worse in three ways (OBS-051).** Exploration profile, p100, 15 seats,
4 years, seeds 1-3, both arms at once on one server (`~/Documents/Dev/polity-runs/order-ab`):

| measure | alphabetical | motif first + declared others | phase15 (older code), first 4 years |
|---|---|---|---|
| elections / recalls per run | 2 / 0 | 2 / 0 | 2 / 0 |
| pressure "nothing" share | 55% (41-72% per seed) | **0%** (0 of 1143) | 61% |
| forum mind-shift rate | 3.8-4.1% per seed | **0.0-1.1%** per seed | 6% |
| fallbacks | 0, 0, 0 | **5, 5, 5** (`chamber_deliberation`) | 0-5 |

The first comes from `motif` first on `PressureDecision` (its only change). The forum and chamber ones come
from the other half: `ForumTurn` and `PositionShift` in declared order (the chamber decision itself was sent
the same in both arms). Elections, recalls, occupancy and retries did not move.

## What production does now (ADR-030)
`llm_client.WIRE_ORDER` maps a decision class to the order its fields are sent in; anything it does not list
goes out alphabetically. It was empty until the first sweep (production's bytes equal to origin/polity's on all
16 schemas, checked); since 2026-10-20 it lists four decisions (below), and only those four schemas' bytes
differ. `scripts/check_schema_order.py` fills it: `isolation` (no GPU), `run` (two
control sessions and one per candidate on `case_bank_order.jsonl`: 144 pressure units, 160 vote units, 500
candidacy), `decide` (the pre-registered rule in `bakeoff_order.py`, written to
`check_schema_order_results.md`). `scripts/schema_order_live_ab.sh` and `schema_order_live_report.py` are the
live check: on the runs above, the report rejects the motif-first order for exactly the three regressions
found by hand.

## What it cost, and what to keep
- The 0.31.0 control was re-measured with today's flags (EAGLE-3), as for 0.31.0: the old results doc
  predates it.
- A shell `tail -15` in the chain cut the failing test's name; the full pytest output is now logged.
- **A declared order is a generation order only if the client keeps it.** That was the lesson of EXP-024;
  here the same fact moved a version bump from "parked" to "possible" and changed the society.
- **An order that reads as logical can be the worst one.** A reason code is a label, not reasoning: written
  first, it anchored the answer. The literature's "reasoning first" result is about free-text reasoning.
- **Look at the confusion matrix, not the distribution.** "Everyone acts" looked like a livelier society
  until the 24 ground-truth citizens showed the model had stopped reading their situation.
- **A version bump can change a flag's meaning without breaking anything.** The only thing that caught it
  was the frozen bank, family by family; the server-level checks all passed.
- A 45-case probe (the bank's `representative_response` through `_inline_refs`, temperature 0, count
  `stance == 1 and not shifts`) screens a new vLLM release in two minutes, before the 1h15 protocol.

## Where the evidence is
The raw sessions (bank sessions, the 2-year runs with their call logs and events, the scorecard, the chain
scripts and logs) are outside git, in `~/Documents/Dev/polity-runs/vllm032/` (bank sessions, 2-year runs) and
`~/Documents/Dev/polity-runs/order-ab/` (the 4-year live A/B). The tables above are read off
them; the bake-off arms in `bakeoff_runner.py` reproduce the order sessions.

## The first sweep (2026-10-20)
`check_schema_order.py` on vLLM 0.31.0: noise 0% on every decision type; no order passes the rule; the three
orders with `motif` before `act` are significantly worse on pressure (70-72/144 against 97, Holm p
0.003-0.009). The owner set `WIRE_ORDER` to the best-scoring orders of four decisions (ADR-030, "The first
table"): pressure `cid, target, act, motif`, candidacy `cid, outcome, motif`, vote `cid, blank, motif,
ranking`, response `cid, stance, shifts, motif`. Only those four schemas' bytes change; every agent turn and
nested object is sent as before. A rule fix came with it: arms sending a class the same order count once in
Holm (candidacy went from p 0.178 to 0.0595; no verdict changed).

**The table, re-run on a fresh server (2026-10-20).** Its requests are byte-identical to the sweep arms', and
it reproduces candidacy (332/500) and pressure (107/144) exactly, and the vote logprob gate (16/16 again,
both controls 13/16). Vote accuracy came out at 149/160, not 152: one thinking case ran away after the
restart (14,156 reasoning tokens against 2,183, no answer). So vote's +3 was one case of cross-instance
noise, which the two controls (same server instance) could not show; `check_schema_order.py run` now takes
`--restart-between-controls` so the next noise floor includes a restart.

**The table, live (2026-10-20).** `schema_order_live_ab.sh`: the 2026-10-18 control runs as `ctl-a`, a second
run of the same control code (`ctl-b`) and the table (`new`), seeds 1-3, 4 years
(`~/Documents/Dev/polity-runs/order-live`):

| measure | ctl-a | ctl-b | new |
|---|---:|---:|---:|
| elections / recalls per run | 2 / 0 | 2 / 0 | 2 / 0 |
| office occupancy | 0.941 | 0.941 | 0.941 |
| pressure "nothing" share | 54.6% | 69.3% | 55.3% |
| forum mind-shift rate | 3.9% | 5.0% | 4.8% |
| fallbacks | 0 | 15 | 5 |
| retry rate | 1.37% | 1.60% | 1.27% |

The table lies inside the two controls on every behaviour measure. The report first said FAIL, on retries,
because it held every measure to a two-sided range and the table had fewer retries than both controls:
fallbacks and retries are now one-sided (only an excess fails). The second control also shows that live noise
is wide (pressure inaction 55% to 69% on the same code) and that 15 chamber fallbacks happen on the control
code too: OBS-051's fallbacks were noise. Judged against both controls, the motif-first order still fails, on
pressure inaction (0%) and forum mind-shift (0.6%).

## Not settled
- Whether the four orders are a real gain: none is significant alone; the live check and the next sweep say.
  Vote's accuracy lead was noise; its gate gain reproduces.
- The agents' turns and nested objects: no ground truth, so they stay alphabetical; a forum opinion-change
  family would let the sweep cover them.
- 0.32.0: stays parked. Re-test it with whatever `WIRE_ORDER` the sweep picks: under compact JSON the
  `ResponseDecision` order is the one that matters (`stance` before `shifts` gave 43/45, declared 13/45).
