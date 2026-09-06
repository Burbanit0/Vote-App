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
AWQ weights, which remains a separate, not-yet-done piece of work. It also doesn't explain why
xgrammar's default whitespace flexibility specifically corrupts THESE schemas and not the other
six — that would need vLLM-internals-level tracing (token-by-token logprob inspection at the
failure point) this investigation didn't attempt, since the empirical fix already resolves the
practical question without it.
