# `ResponseDecision` / `CoalitionDecision` vs the `PressureDecision` sort_keys bug — both clean

Follow-up to `check_vllm_pressure_action_sort_keys_truncation_results.md`, which named
`ResponseDecision` and `CoalitionDecision` as the next plausible candidates for the same
`sort_keys=True`-triggered non-terminating whitespace loop found on `PressureDecision`. Checked
both, using each decision type's own real production prompts/schemas, reused directly from
`check_representative_response_collapse_signature.py` and
`check_coalition_decision_collapse_signature.py` (not reconstructed).

## Result: both clean, both orderings, both providers

| Decision type | Fields (declared → alphabetical) | vLLM `sort_keys=False` | vLLM `sort_keys=True` (shipped) | Ollama (both) |
|---|---|---|---|---|
| `ResponseDecision` | `cid, shifts, stance, motif` → `cid, motif, shifts, stance` | OK | OK | OK |
| `CoalitionDecision` | `party_id, action, motif` → `action, motif, party_id` | OK | OK | OK |

Verified across two cases per decision type (`ResponseDecision`: NO-PROBLEM pole cid=1 and CRISIS
pole cid=7; `CoalitionDecision`: JOIN-OBVIOUS party 50 and DECLINE-OBVIOUS party 77) via
`check_vllm_response_coalition_sort_keys_truncation.py`.

## What this narrows, not just confirms

`CoalitionDecision` has the same flat-integer, no-array shape as `PressureDecision`
(`party_id, action, motif` vs. `cid, target, act, motif`) and the same enum-heavy field
constraints — the closest structural match among untested schemas, and the one this
investigation's own prior write-up predicted as most likely to share the bug. It doesn't. Whatever
makes `PressureDecision` specifically vulnerable is narrower than "any small, flat, alphabetically-
reordered integer schema" — plausibly specific to its exact 4-field shape, or to something about
this particular field-name sequence, not investigated further here (would need systematically
varying field count/names on synthetic schemas, out of scope for this comparison pass).

`ResponseDecision`'s clean result is less surprising — it has an array field (`shifts`), closer in
shape to `PositioningDecision`/`ChamberDecision`, both already confirmed clean under vLLM's real
(alphabetized) production schema in `scripts/vllm_switch_results.md`'s axis (b).

## Standing scope note

Every decision type with a real LLM-facing schema in this project has now been checked at least
once for this specific bug: `VoteCastDecision`, `PositioningDecision`, `ChamberDecision`,
`ResponseDecision`, `CoalitionDecision` clean; `PressureDecision` alone affected. Not exhaustively
stress-tested (each got 1-4 sample cases, not a full sweep), and `PartyNominationDecision`/
`CandidacyDecision`/`ReactionDecision` were not checked at all — flagged as a real gap, not
assumed safe, consistent with this investigation's own standing discipline of not over-claiming
from a small sample.
