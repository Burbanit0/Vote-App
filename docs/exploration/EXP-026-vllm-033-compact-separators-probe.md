# EXP-026 — vLLM 0.33.0: the probe that fails for the same one line as 0.32.0

- **Date**: 2026-11-15 UTC (the evening of 2026-11-14 local; 02:24Z to about 03:10Z) · **Status**: 0.33.0 rejected for now (the pin stays on v0.31.0, the owner's standing choice; the ways forward are listed below and left to the owner) · **Real cost**: about 45 minutes of the local GPU, one image pull of about 35 GB and two derived images (all three deleted afterwards), no rented compute · **Token cost**: not measured
- **Verdict in one sentence**: 0.33.0 still sends `separators=(",", ":")` when `disable_any_whitespace` is set, and with the field order production now uses, that turns 48 valid answers out of 50 on a 2-minute probe into 0 out of 50; one reverted line gives back 0.31.0's answers byte for byte. The order that passed on 0.32.0 in October was never shipped, and the result contradicts the explanation EXP-025 and ADR-030 gave for it ("`stance` before `shifts`"): production's order has `stance` before `shifts` and collapses all the same.

## Starting hypothesis
0.33.0 (pushed 2026-11-02) might be adoptable. EXP-025 had shown that the only thing wrong with 0.32.0 was one line (compact JSON), and that one field order made stock 0.32.0 match 0.31.0 on 2026-10-18 (43/45 against 43/45): the hand-picked "effective" order `cid, motif, stance, shifts`, which was then rejected for what it did to `pressure_action` and never shipped. EXP-025 and ADR-030 both read that pass as "`stance` before `shifts`", and ADR-030's table (2026-10-20) gives `ResponseDecision` the order `cid, stance, shifts, motif`, which has `stance` before `shifts` too; that table was never run on 0.32.0. The 0.33.0 release notes list changes on our exact path: grammar masks under speculative decoding (#52477), lookahead block hashes for EAGLE prefix caching on by default (#61589), a truthful `finish_reason` (#59324, #61574), a new special-token filter in the xgrammar JSON compiler, PyTorch 2.14, CUDA 13.0 only. `backend_xgrammar.py` still passes `separators=(",", ":")` when `disable_any_whitespace` is set (vLLM PR #58067), and `StructuredOutputsConfig` has no setting for it. What I expected before running: production's order, having `stance` before `shifts`, would absorb the compact-JSON change, and the open question was whether the other changes (speculation, caching, the filter) would move anything. The first half was wrong.

## Protocol
All runs: `python scripts/run_bakeoff.py --label <label> --families response_sweep --out <dir>/bank`, from `fast_api_voter/`, on the code of origin/polity at `ff2dbaf1`, the same bank (`bank_sha256` identical in the five sessions), temperature 0. One server at a time, the production flags (`docker-compose.llm.yml`: Qwen3-8B-AWQ, `--structured-outputs-config '{"backend": "xgrammar", "disable_any_whitespace": true}'`, EAGLE-3 draft length 3, 16,384 context, 0.88 memory).

The `response_sweep` family is 45 `representative_response` cases (50 scored answers with the 5 reruns), plus the 6 `logprob_gate` rows the session always runs. That is 56 scored rows and 64 calls (the rest are 2 warm-ups and 6 one-token budget probes): 59 distinct requests. It is the two-minute probe EXP-025 recommended before the 1h15 protocol.

1. Stock `vllm/vllm-openai:v0.33.0`, then the usual bump chain (`chain.sh`: probe, thinking budget, determinism, ...). The chain was stopped by hand at its third step, because the probe had failed.
2. A 0.31.0 control on the same code and cases (`docker-compose.llm.031.yml`, the production file).
3. Three one-variable arms on 0.33.0, each built to test one suspect:
   - no `--speculative-config` (no EAGLE-3, so no grammar-under-speculation path);
   - an image where the JSON compiler's special-token filter is bypassed (`tokenizer_info = full_vocab_tokenizer_info`, one replace in `backend_xgrammar.py`);
   - an image where `separators = (",", ":") if self.disable_any_whitespace else None` is replaced by `separators = None` (the 0.31.0 behaviour, one line).

## What it found
Valid answers on `response_sweep` (50 scored answers; the validator is the production `ResponseBatch` one):

| server | valid | what the model wrote |
|---|---:|---|
| v0.31.0 (current pin) | 48/50 | spaced JSON, real shifts |
| stock v0.33.0 | **0/50** | compact JSON, `"shifts":[]` every time |
| 0.33.0, no EAGLE-3 | 0/50 | same |
| 0.33.0, special-token filter bypassed | 0/50 | same |
| 0.33.0, `separators = None` (one line) | **48/50** | identical to 0.31.0 |

- **Every failure is the same.** All 50 answers on stock 0.33.0 are `"stance":1` (40) or `"stance":2` (10) with `"shifts":[]`, and the validator rejects each ("stance=1 (concession) requires at least one shift"). Example raw content: `{"decisions":[{"cid":6007,"stance":1,"shifts":[],"motif":301}]}`. Completion length is 31-32 tokens (mean 31.2) against 36-87 on 0.31.0 (mean 79.7): the model stops after writing the empty list. The two cases invalid on 0.31.0 are the same two cases as on the patched arm.
- **The patched arm is the control.** With the one line reverted, the 6 logprob rows and 45 cases give the same answers and the same validity as 0.31.0 on all 56 scored rows (51 distinct cases). The text of all 58 answers that carry one (56 decisions and 2 warm-ups; the 6 one-token budget probes return none) is byte-identical to 0.31.0. Prompt token counts are identical on all 64 calls (59 distinct requests) between 0.31.0 and 0.33.0, so the prompt did not move: only the output spacing did. One honest nuance: the reasoning text (not the answer) differs on 3 of the 6 thinking `vote_cast` calls (19 to 734 fewer reasoning tokens on 0.33.0 + patch), with the same final answer; the cause was not investigated.
- **The other suspects are cleared for this probe, not in general.** EAGLE-3 off and the new filter bypassed each give 0/50. Lookahead block hashes (#61589), the `finish_reason` changes and PyTorch 2.14 were not isolated; they are moot for this family because the one-line revert alone restores everything, but they were not tested on any other.
- **`logprob_gate`: 6/6 valid on every arm.** Compact JSON does not hurt the vote batch here.

**What this says about the order, and what it corrects.** Four orders of `ResponseDecision` have now met compact JSON:

| order | vLLM | valid |
|---|---|---:|
| alphabetical `cid, motif, shifts, stance` (production in October) | 0.32.0 | 2/45 |
| declared `cid, shifts, stance, motif` | 0.32.0 | 13/45 |
| "effective" `cid, motif, stance, shifts` (rejected, never shipped) | 0.32.0 | 43/45 |
| ADR-030's table `cid, stance, shifts, motif` (production since #967) | 0.33.0 | **0/50** |

EXP-025 ("`stance` before `shifts` gave 43/45, declared 13/45") and ADR-030 ("`stance` before `shifts` (what decided vLLM 0.32)") predicted that the last row would pass. It does not: `stance` before `shifts` is not what protects. What the one passing order has and the others lack is `motif` before both and `shifts` last; whether that is the cause was not tested. The rows are also on two vLLM versions: the October order was not run on 0.33.0, and production's order was not run on 0.32.0, so "the same line, another order" is an inference across versions, supported by the one-line revert restoring everything on 0.33.0. Those two statements in EXP-025 and ADR-030 are left as written (they are dated records); this note is their correction. The order is part of the prompt, and ADR-030's was chosen against one spacing.

**Other readings on 0.33.0.**
- Healthy 140 s after start (137 s for 0.32.0).
- KV cache 31,600 tokens (1.93x). The 0.31.0 control started the same day logged 30,656 (1.87x); that line was read from the server log at the time and was not saved to a file. 0.32.0 logged 30,656 and 38,848 (2.37x) on 2026-10-18 in two GPU-memory states, so the number moves with the state of the GPU, and 0.33.0 is not smaller.
- Thinking budget honoured: 256 asked, 256 reasoning tokens; 64 asked, 64; unbudgeted 1,034 against 972 recorded in the pinned results doc, all finish `stop`, all answers decode.

## What was not run
Said plainly, because a probe is not a bump protocol: determinism within a run and across a restart, the three restarts, the live suite, the 2-year A/B runs, the full bank, `check_schema_order.py` on 0.33.0, and October's passing order (`cid, motif, stance, shifts`) on 0.33.0. Only `response_sweep` and `logprob_gate` were run on 0.33.0 (and the thinking-budget script). The 0.33.0 result is therefore "fails the first gate", not "fails everything": nothing was measured on the other families.

Not probed either: the agents' turns (no ground-truth family exists for them). With the scenario profile (`llm.crowd: false`) the nine crowd decisions, `representative_response` among them, are decided by rules and never reach the model, so this regression concerns the flagship and exploration profiles, not the scenario one.

## What it cost
About 45 minutes of the local GPU (server starts of about 2 minutes each, probes of 78 to 112 s each, plus the builds), one image pull, two derived images (a `FROM` plus one Python replace each); all three images were deleted afterwards. No rented compute. No CI time, no code change, nothing merged. The next bump will cost the two-minute probe again.

## Options left to the owner
None decided, except "stay on 0.31.0 for now".
1. **Stay on 0.31.0.** Free. The pin is already running and the probe is the gate for the next release; the cost is that each release adds more to catch up with.
2. **Re-run `check_schema_order.py isolation|run|decide` on stock 0.33.0**, which ADR-030 asks for on a version change. Several GPU sessions (two controls plus one per candidate order); the duration was not measured here. It may pick another order, which changes simulated behaviour and couples the table to the vLLM version.
3. **A derived image with the one-line revert.** Byte-identical to 0.31.0 on the probe; a thin `Dockerfile`, but the replace has to be reapplied (and its anchor checked) at every bump, and it keeps a local fork of one file.
4. **`disable_any_whitespace: false`.** No patch, but the whitespace loop of 2026-09-06 (a non-terminating whitespace run after certain field orders) is exactly what the flag was added for; that failure would have to be re-measured on 0.33.0 under today's orders first.
5. **An upstream request for a separators setting** (drafted below, not filed). Free to file, with no schedule.

## Upstream request (drafted, not filed)
> **Title:** Allow choosing the JSON separators when `disable_any_whitespace` is set (xgrammar backend)
>
> Since #58067, `disable_any_whitespace` makes the xgrammar backend pass `separators=(",", ":")`, so every structured output is compact JSON. Before, the flag only disabled arbitrary whitespace and the grammar kept the default `", "` and `": "`. Compact output is cheaper, and the PR's measurement shows no loss on its own case.
>
> A deployment may nevertheless depend on the previous spacing: what a model writes next depends on the token sequence it has just written, and `"shifts": []` and `"shifts":[]` are different sequences. On Qwen3-8B-AWQ with EAGLE-3, a 45-case probe of a schema with a decision field followed by a list went from 48 valid answers out of 50 (v0.31.0) to 0 out of 50 (v0.33.0): the model now closes the list empty every time. Reverting the one `separators` line gives answers byte-identical to v0.31.0 on that probe. Only the spacing changed (prompt token counts are identical; speculative decoding and the special-token filter were ruled out).
>
> **Ask:** a `separators` (or `compact_separators`) field on `StructuredOutputsConfig`, defaulting to the current behaviour so nothing changes for anyone who does not set it, so that a deployment can keep the spacing its prompts and measured behaviour were built on.

## What I take from it (transferable)
- **A two-minute probe on the one family that broke last time is the right first gate.** It caught the regression in under two minutes, before any of the hour-long protocol was spent. Keep one cheap probe per known failure and run it before the long protocol.
- **A configuration chosen on one version is a measurement of that version.** The field order was measured on 0.31.0's spacing; another order passed on 0.32.0 in October and today's fails on 0.33.0. "Passed once" is a property of the whole stack (model, server, flag, order), not of the order.
- **An explanation read off one passing arm is a hypothesis.** "`stance` before `shifts`" fitted three rows and went into an ADR as the reason; the fourth row refutes it. I repeated it as a fact when I predicted this bump would pass.
- **Silent default changes are the dangerous kind.** Nothing crashed, the server was healthy, the thinking budget was honoured, the logprob gate passed 6/6; only a ground-truth family showed the model had stopped writing its answers. A server-level health check cannot see that.
- **Isolate the cause with one-variable arms before choosing between options.** Three arms, 45 minutes: speculation off (0/50), filter off (0/50), one line reverted (48/50, byte-identical). That turns "0.33.0 is broken" into "one line of 0.33.0 changed the spacing".
- **Say what a probe does not cover.** Everything not run is listed above; a pass on this probe would not have been a pass on the bump, and the failure only blocks it.

## Where the evidence is
Outside git, in `~/Documents/Dev/polity-runs/vllm033/`: `chain.sh` and `chain.log` (the stopped chain), `bank/probe-031`, `probe-033`, `probe-033-nospec`, `probe-033-nofilter`, `probe-033-sepdefault` (each with `results.jsonl`, `llm_calls.jsonl`, `session.json`), `probe-nofilter/Dockerfile` and `probe-sepdefault/Dockerfile` (the two derived images), the compose files, `thinking033/` (the thinking-budget run). The tables above are read off them. The PR numbers and the release-note claims come from the vLLM repository as read on 2026-11-15.
