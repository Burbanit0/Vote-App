# EXP-025 — vLLM 0.32.0, and the order the schema's fields are sent in

- **Date**: 2026-10-18 · **Status**: 0.32.0 rejected (stay on 0.31.0); effective field order adopted in
  production (the owner, 2026-10-18) · **Real cost**: about six hours elapsed on the shared GPU, one
  server at a time (the 1h15 bump protocol, bank sessions for the cause, four for the order, a
  production-path chain of 45 minutes) · **Token cost**: not measured
- **Verdict in one sentence**: 0.32.0 changed what `disable_any_whitespace` means (compact JSON), which
  made the model write `"shifts":[]` after a concession in 41 of 45 cases; the bump is not worth it, but the
  investigation showed that the order the schema's fields reach the model in (OBS-050) decides what it
  writes, so production now sends them in an effective order, and that changes how the simulated society
  behaves.

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

## What production does now
`llm_client.effective_field_order` orders every object that carries a `motif`; `VllmJsonClient` sends the
schema in that order and keeps the rest of the body canonical (sorted). Objects without a `motif` (the
agents' turns) now go out in the order their class declares, which is what ADR-014 always said (`rationale`
first). The order is applied on the wire only, after the request hash is taken, so no request hash, golden or
replay log changed: the polity/LLM suite (`-k "polity or bakeoff or provenance or llm"`) gives 2175 passed, 45 skipped. `schema_wire` selects `"effective"`
(default), `"declared"` or `"sorted"` (the old bytes); the bake-off has the arms `declared_order`,
`effective_order` and `alphabetical_order`. `llm_client.py` joined `PROMPT_SOURCE_FILES`.

On stock 0.31.0 with the production path: the bank equals the earlier effective-order session on 178 of 191
answers (the 13 others are the long-thinking nondeterminism of OBS-020), 189 of 191 valid (both misses in
`chamber_deliberation`), and the live suite gives 11 passed, 1 xfailed, as before.

## The society behaves differently (OBS-051)
The bank cannot see it, and it is the largest effect. `pressure_action` decisions in the 2-year, 100-citizen
runs (act 0 nothing, 1 sign, 3 mobilise, 4 wait for the election):

| runs | decisions | 0 | 1 | 3 | 4 | elections / recalls |
|---|---:|---:|---:|---:|---:|---|
| alphabetical, 0.31.0 (six runs) | 115-222 each | 100% | 0 | 0 | 0 | 1 / 0 |
| effective order, 0.31.0 (three runs) | 114-217 each | 0-6% | 22-32% | 44-67% | 11-21% | 2-3 / 1-2 |
| earlier long runs (`phase10`, `phase11`, alphabetical) | 367-1671 each | 33-72% | ~14% | ~28% | ~2% | n/a |

On 40 identical chamber requests, 13 answers differ (`shifts` and `motif`). Every run recorded before
2026-10-18 was made with alphabetical bytes; the run provenance stamp changes with `llm_client.py`, so the
two are told apart, but they are not comparable decision by decision. The new order overshoots the old
long-run proportions: whether that is a better society or an over-active one is open.

## What it cost, and what to keep
- The 0.31.0 control was re-measured with today's flags (EAGLE-3), as for 0.31.0: the old results doc
  predates it.
- A shell `tail -15` in the chain cut the failing test's name; the full pytest output is now logged.
- **A declared order is a generation order only if the client keeps it.** That was the lesson of EXP-024;
  here the same fact moved a version bump from "parked" to "possible" and changed the society.
- **A version bump can change a flag's meaning without breaking anything.** The only thing that caught it
  was the frozen bank, family by family; the server-level checks all passed.
- A 45-case probe (the bank's `representative_response` through `_inline_refs`, temperature 0, count
  `stance == 1 and not shifts`) screens a new vLLM release in two minutes, before the 1h15 protocol.

## Where the evidence is
The raw sessions (bank sessions, the 2-year runs with their call logs and events, the scorecard, the chain
scripts and logs) are outside git, in `~/Documents/Dev/polity-runs/vllm032/`. The tables above are read off
them; the bake-off arms in `bakeoff_runner.py` reproduce the order sessions.

## Not settled
- Whether the new society is better: a phase-sized run (500 citizens, years) against `phase10`/`phase11` is
  the test, about two hours of GPU.
- The order effect is on one model, one seed, three 2-year runs. `motif` first may anchor the choice (a
  position effect); that mechanism is a guess.
- The agents' turns changed from alphabetical to declared order; none of their families is in the bank.
- 0.32.0 itself: stays parked. With the effective order it matches 0.31.0 on the bank without a patch, which
  re-opens it for the next release.
