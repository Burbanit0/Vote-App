# Root cause found and fixed: `disable_any_whitespace` resolves the sort_keys truncation bug

Follow-up to the completed sort_keys truncation sweep
(`check_vllm_pressure_action_sort_keys_truncation_results.md`,
`check_vllm_response_coalition_sort_keys_truncation_results.md`,
`check_vllm_remaining_decisions_sort_keys_truncation_results.md` — 2 of 9 decision types broken
outright under vLLM's shipped config, a 3rd broken under the unsorted ordering). Those documents
mapped the bug's footprint empirically without touching `sort_keys` (explicitly out of scope, per
this investigation's standing discipline) or isolating the underlying vLLM mechanism. This
document does the latter — investigating the vLLM/xgrammar side, not the project's own
`sort_keys` code.

## The mechanism

Every failure had the same shape: valid tokens through the second-to-last field, then `\n   `
(newline + spaces) repeated hundreds of times, never reaching the last field or closing the JSON
object, burning the entire token budget. vLLM's engine startup log names its structured-output
config explicitly: `StructuredOutputsConfig(backend='auto', disable_any_whitespace=False, ...)`.
xgrammar (the backend `auto` resolves to here) compiles a schema into a grammar that, by default,
allows arbitrary whitespace between JSON tokens — exactly the kind of flexibility a
greedy/temperature=0 decoder can get stuck exploiting: emitting more whitespace is always
grammar-legal, so once the sampler's argmax lands there, nothing forces it back out.
`disable_any_whitespace=True` removes that flexibility from the compiled grammar.

## The mechanism, confirmed with token-level evidence

The paragraph above explains WHAT the fix removes; this section confirms WHY it was needed, via a
temporary diagnostic instance (default config, `disable_any_whitespace=False`, a bare `docker run`
alongside the shipped container so the fix in `docker-compose.llm.yml` was never actually reverted)
requesting `logprobs`/`top_logprobs` on the exact failing calls.

**`PressureDecision` (fields `act, cid, motif, target` under `sort_keys=True`)**: token-by-token
inspection of the raw completion shows the model emitting `{"decisions":[{"act":3,"cid":3,
"motif":306` cleanly (every token argmax at or near 0 logprob — fully confident, correctly
constrained), then at the exact position after `306` closes, the top-2 candidates are bare `\n`
(chosen, logprob **-0.013**, ~98.7% probability) vs. `,\n` — the token that would continue to the
still-required `target` field (logprob **-4.33**, ~1.3%). Not a grammar dead-end: `,\n` was legal
and available, just far less probable in the model's own distribution at that exact branch point.
Once `\n` is chosen, the same pattern repeats at every subsequent step (whitespace token argmax at
~0 logprob, `,\n` still sitting a few logprobs behind as a live but never-taken alternative) —
self-reinforcing under greedy decoding, with nothing in the local context ever making the
comma-continuation the argmax again.

**`CandidacyDecision` (fields `cid, motif, outcome` under `sort_keys=True`)**: same shape,
independently confirmed. Right after `"motif":201` closes, bare `\n` (logprob **-0.010**, ~99%)
beats `,\n` (logprob **-4.57**, ~1%) — the token that would continue to the still-required
`outcome` field. Same self-reinforcing loop afterward.

**What this narrows**: the failure is not a grammar dead-end (both continuations were always
legal) — it's that xgrammar's grammar makes bare trailing whitespace an available continuation at
all at that branch point, and the model's own learned distribution assigns it far more mass than
the correct continuation, right after finishing the *second-to-last* required field in both broken
schemas' alphabetized order. `disable_any_whitespace=True` fixes this not by changing the model's
preference, but by removing the whitespace option from the grammar entirely at that point, forcing
argmax to choose among only the continuations that actually complete the object.

**Correction — the trigger lives in the prompt, not the schema's field names.** An earlier version
of this document speculated the model's own preference for particular field-name/enum-value
combinations was the likely differentiator, since `motif` sits in the same penultimate wire
position for `ReactionDecision`/`CoalitionDecision` too (both clean). Tested directly with a
controlled swap, not assumed: took `pressure_action`'s real system+user prompt verbatim and
re-ran it against a schema whose last field was renamed from `target` to `party_id` — **still
broke, identically** (`finish_reason='length'`, same whitespace loop). Took `coalition_decision`'s
real prompt (always clean) and renamed ITS last field to `target` — **still clean**. The field
name makes no difference in either direction; a bare, generic prompt ("Return a JSON object with
cid=7, motif=305, and `<field>`=5") stays clean regardless of which of the four real field names
is used. **The trigger is something in `pressure_action`'s/`candidacy_considered`'s own real
system/user prompt content** (length, specific instructions, something else) that the shorter or
differently-worded prompts for the other seven decision types don't share — not the schema. What
exactly, in the prompt, causes it was not isolated further (would mean a systematic prompt-
ablation study, its own separate effort) — this correction narrows the search space to the right
place, not to a conclusion.

## Fix and verification

`vllm serve`'s `--structured-outputs-config` accepts this as a JSON CLI arg —
`{"backend": "xgrammar", "disable_any_whitespace": true}`. `backend` must be explicit: passing
`disable_any_whitespace` under vLLM's own default (`backend: auto`) is rejected outright
(`disable_any_whitespace is only supported for xgrammar and guidance backends`) — a real gotcha
worth recording, since the flag looks independent of `backend` until you actually try it.

Re-ran every sort_keys sweep script against this config, both field orderings, all 9 decision
types:

| Decision type | Before (shipped `sort_keys=True`) | After (`disable_any_whitespace=true`), both orderings |
|---|---|---|
| `PressureDecision` | **broken** | clean |
| `CandidacyDecision` | **broken** | clean |
| `PartyNominationDecision` | broken under unsorted order only | clean |
| `VoteCastDecision`, `PositioningDecision`, `ChamberDecision`, `ResponseDecision`, `CoalitionDecision`, `ReactionDecision` | clean | clean (no regression) |

**All 9 decision types clean under both orderings** — not just a fix for the two known-broken
schemas, but a fix that also closes `PartyNominationDecision`'s latent exposure (safe today only
because its shipped order happened not to trigger it).

No regression found on anything else checked:
- Decode correctness, not just "not truncated": `VllmJsonClient.complete_json` +
  `decode_pressure_batch` on the real production path, 5/5 byte-identical
  (`{"decisions": [{"act": 3, "cid": 3, "motif": 306, "target": 5}]}`) at temperature=0.
- `check_vllm_batching_determinism.py`'s full protocol (§15bis.5) — batch sizes 1/5/25/50
  concurrent, 10 sequential calls — still **PASS**, byte-identical, same as before this config
  change.
- `think=True` / `--reasoning-parser qwen3` — reasoning still present, `content` still clean JSON,
  `finish_reason='stop'`. The R1 mechanism (structured-output grammar silently suppressing
  `enable_thinking`) is unaffected by this flag.

## Applied

`docker-compose.llm.yml` now ships `--structured-outputs-config
'{"backend": "xgrammar", "disable_any_whitespace": true}'` permanently, not as an experiment.

## What this does and does not change

This resolves the specific blocker `check_vllm_pressure_action_sort_keys_truncation_results.md`
raised against any `provider: vllm` production switch — the truncation bug that made
`pressure_action`/`candidacy_considered` unreliable no longer reproduces. It does **not** itself
authorize the switch: `provider` stays `ollama`, and axis (b)'s broader caveat still stands — this
fix addresses a structural generation-corruption bug, not a re-verification of every reliability
calibration in the codebase (`_VOTE_CAST_MAX_CHUNK_SIZE`, `recycle_after_n_calls`, etc.) against
AWQ weights, which remains a separate, not-yet-done piece of work. Nor does it explain what,
specifically, in `pressure_action`'s/`candidacy_considered`'s own real prompts triggers the
model's closing preference — narrowed to "the prompt content, not the schema" above, but not
identified further, since the empirical fix already resolves the practical question without
needing that.
