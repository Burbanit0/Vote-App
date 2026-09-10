# Logprob calibration — plan-llm-protocol-and-theory-program.md §5.C

## The two problems this closes

`complete_with_logprobs`'s own docstring (2026-09-09) named a real, unattacked gap: its
live verification used a bare forced-choice probe (P(yes)=0.962), where the answer token is
the FIRST generated token by construction. A real production decision is not shaped that
way — the field-relevant value (`"blank":1` here) sits deep inside an xgrammar-constrained
JSON object, generated under `think=True`, with a `<think>...</think>` reasoning block in
front of it that the reasoning parser strips out of `message.content` but NOT out of the raw
per-token `logprobs.content` the API also returns. Two separate alignment problems, both
solved before this could be tried against a real decision:

1. **`VllmJsonClient.complete_json_with_logprobs`** (`llm_client.py`) — the real production
   call shape (`response_format`/xgrammar, `think=True` default) plus `logprobs`/
   `top_logprobs`, so the SAME completion a `decide_*` function would decode also carries its
   own per-token probabilities. A distinct method from `complete_with_logprobs`, not a
   parameter on it — same "one call shape, no hidden branching" discipline this class
   already applies everywhere else.
2. **`llm_logprob_instrumentation.py`** (new module) — `locate_decision_field_logprobs`
   reconstructs the FULL raw generation by concatenating every returned token in order, finds
   `content` as a (possibly non-zero-offset) substring of it — the fix for the reasoning-
   parser split — then locates each decision's own field-value token by walking cumulative
   token-character offsets in that raw space, zipping the result against `json.loads(content)`
   in document order to attach each token to its own `cid`. `binary_probability` reads a
   normalized P(true_value) off `TokenLogprob.alternatives` for a two-outcome field.

## Offline-verified first

13 new tests in `test_polity_llm_logprob_instrumentation.py` exercise the alignment logic
against hand-built `TokenLogprob` sequences with deliberately adversarial token boundaries —
including one that straddles `</think>` itself, reproducing the exact misalignment this
module exists to fix. 4 new tests in `test_polity_llm_client.py` cover
`complete_json_with_logprobs`'s request shape (schema dereferencing, `think=True` default,
override), all offline/mocked. mypy + flake8 clean on both new/changed source files (tests
directory is excluded from the mypy gate, `pyproject.toml`).

## Live-verified against a real production, ground-truth-bearing decision

Per §5.C's own stated Verification bar ("validate against the one decision type with real
ground truth ... before licensing the signal on types that have no ground truth"):
`check_logprob_blank_calibration.py` ran `vote_cast`'s real `build_system_prompt`/
`build_user_prompt` (chunk_size=3, the shipped vLLM value, `think=True`, the real
`VOTE_CAST_JSON_SCHEMA`) through `complete_json_with_logprobs`, located each voter's own
`"blank"` field token via `locate_decision_field_logprobs`, and read P(blank=1) via
`binary_probability`. Ground truth: `simple_rules.build_ranking(voter, nominees)[0] ==
BLANK_LABEL`.

16 real voters (8 ground-truth blank, 8 ground-truth non-blank, selected from a 200-citizen
pool by ground-truth outcome — never hand-placed):

| | |
|---|---|
| Field-locator alignment | **16/16** — zero `LogprobAlignmentError`, across 6 real chunked completions, each with its own real `<think>` block of unpredictable length |
| Threshold-call accuracy (P(blank=1)>0.5 vs ground truth) | **16/16** |
| Mean P(blank=1) \| ground-truth blank | **0.9969** (n=8) |
| Mean P(blank=1) \| ground-truth non-blank | **0.0494** (n=8) |
| Separation | **+0.948** |

Every aligned decision's `blank` field also matched the model's own generated `blank`
token exactly (no `finish_reason` or JSON-decode failures across the run).

**Caveat, stated plainly:** this sample was selected for ground-truth balance, not for
difficulty — none of these 16 voters sit near their own `blank_threshold` boundary, where a
genuinely graded/ambiguous P(blank=1) would be the more interesting case. The clean
separation measured here validates the ALIGNMENT technique (the previously-unsolved problem)
and the DIRECTION of the correlation unambiguously; it does not yet demonstrate the graded
signal's value on a hard, boundary-adjacent case. A follow-up sample deliberately drawn near
the threshold is the natural next probe of that specific claim, not attempted here.

## Disposition

**Both primitives shipped and live-verified.** §5.C's own Verification bar is now met:
the technique is licensed for use on decision types with no ground truth (starting with
`pressure_action`'s `act` field, §5.C's own named target). Not yet applied there in this
pass — a separate, deliberate next step, not assumed to transfer by analogy.
