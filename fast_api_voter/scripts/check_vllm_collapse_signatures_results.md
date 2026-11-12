# Phase 1 (plan-flagship-30y-run.md): the 3 collapse-flagged decision types, re-tested under vLLM

`representative_response` (dt=6), `reaction_to_event` (dt=8, scandal branch) and `coalition_decision`
(dt=9) each carry a `RELIABILITY WARNING` in this project's own documentation: two structurally
opposite input poles produced byte-identical decisions (4/4, 6/6, 6/6) — all three measurements
were on Ollama only. The flagship run targets vLLM/AWQ; the truncation bug already proved
backend-specific behaviour is real, so this re-runs the exact same protocol (same poles, same
citizens/parties, same schema, same `think=False`), unmodified except for the client, before
committing days of GPU to a run that would otherwise silently inherit an unverified assumption
either way.

Scripts: `check_vllm_representative_response_collapse_signature.py`,
`check_vllm_reaction_to_event_collapse_signature.py`,
`check_vllm_coalition_decision_collapse_signature.py` — each a direct diff of its Ollama
counterpart (client class only).

## Result: 2 of 3 still collapse. 1 of 3 does not.

| Decision type | Ollama (documented) | vLLM/AWQ (this check) | Verdict |
|---|---|---|---|
| `representative_response` | 6/6 identical (CONCESSION) | **6/6 identical (CONCESSION)** | Collapse **confirmed**, stays `unverified` |
| `coalition_decision` | 6/6 identical (JOIN) | **6/6 identical (JOIN)** | Collapse **confirmed**, stays `unverified` |
| `reaction_to_event` (SCANDAL) | 6/6 identical | **VARIES**: salience_delta=0.20 (low-salience pole) vs 0.15 (high-salience pole), both poles internally consistent across all 3 reactors | Collapse **not reproduced** — warning **dropped** |

## What this does and does not license

**`reaction_to_event` (SCANDAL)**: the warning is dropped for this specific branch. The vLLM/AWQ
response is directionally sensible too — a citizen already sensitized to past events
(`event_salience=0.9`) shows a *smaller* incremental salience_delta (0.15) than one previously
untouched (`event_salience=0.0`, delta 0.20), consistent with a saturating/diminishing-returns
reading of event salience, not an arbitrary flip. Not proof of correctness against any ground
truth (none exists for this decision type, per the original script's own documented
justification for using the collapse-signature method instead of an accuracy check) — only that
the specific byte-identical-regardless-of-input failure mode this warning names does not
reproduce here.

**`representative_response` and `coalition_decision`**: both collapse identically to their Ollama
behaviour, on a different serving stack and a different (AWQ) quantization. This rules out
"an Ollama-specific serving artifact" as the explanation — whatever drives these two collapses
survives a full backend change, which points toward the model's own learned behaviour on these
two prompt shapes (or a shared structural property of how they're framed) rather than an
infrastructure quirk. Neither is root-caused further here — same scope discipline as every other
document in this investigation: this measures whether the warning still applies, not why.

## Per the plan's own decision gate

- `representative_response`, `coalition_decision`: **stay `unverified`** in any exported
  flagship artifact — the UI must not present metrics derived from these two as trustworthy
  findings.
- `reaction_to_event` (SCANDAL): **warning dropped**. Note this covers the SCANDAL branch only,
  the one this check (and the original Ollama one) actually exercises — `ECONOMIC_SHOCK`'s
  impersonal, no-target branch was never in scope for either version of this check.
