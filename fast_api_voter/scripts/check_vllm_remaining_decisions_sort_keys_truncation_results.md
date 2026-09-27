# Completing the sort_keys truncation sweep — 2 more findings, all 9 decision types now checked

Follow-up to `check_vllm_pressure_action_sort_keys_truncation_results.md` (found the bug on
`PressureDecision`) and `check_vllm_response_coalition_sort_keys_truncation_results.md`
(`ResponseDecision`/`CoalitionDecision` clean). Checks the 3 remaining decision types —
`CandidacyDecision`, `PartyNominationDecision`, `ReactionDecision` — completing coverage of all 9
decision types in the engine.

## Result

| Decision type | Fields (declared → alphabetical) | vLLM `sort_keys=False` | vLLM `sort_keys=True` (shipped) |
|---|---|---|---|
| `CandidacyDecision` | `cid, outcome, motif` → `cid, motif, outcome` | OK | **FAILED (whitespace loop)** |
| `PartyNominationDecision` | `party_id, winner_position, motif` → `motif, party_id, winner_position` | **FAILED (whitespace loop)** | OK |
| `ReactionDecision` | `cid, salience_delta, motif` → `cid, motif, salience_delta` | OK | OK |

Each pattern reproduced identically across 2 independent cases (different citizens/ambition
scores/party compositions). Ollama: all 3 clean, both orderings, both cases.

## `candidacy_considered` is a second real production bug

Same signature as `PressureDecision`: clean under the natural (declared) field order, fails under
the shipped `sort_keys=True` alphabetization — `\n   ` repeated hundreds of times after partial
valid output, never terminating, burning the whole token budget. **This is a second decision
type where vLLM cannot reliably serve production traffic as currently wired**, not an isolated
`pressure_action` quirk.

## `party_nomination_choice` is the mirror image — informative, not a production bug

Here the *unsorted* order fails and the *shipped, alphabetized* order is the one that works.
Production is safe as currently configured. But this is a real caution for any future `sort_keys`
remediation (the kind `plan-pressure-action-resolution.md` §4 explicitly declines to attempt
without its own separate scoping): a fix that stops alphabetizing and instead preserves
declaration order — the natural-seeming "fix" — **would silently break `party_nomination_choice`
while fixing `PressureDecision`/`CandidacyDecision`**. There is no single field-ordering rule that
is safe for every decision type on this backend; any future scoping work needs to check all 9
schemas under whatever new ordering it proposes, not just the ones known broken today.

## Final coverage: all 9 decision types checked

| Decision type | Under shipped `sort_keys=True` |
|---|---|
| `VoteCastDecision` | clean |
| `PositioningDecision` | clean |
| `ChamberDecision` | clean |
| `ResponseDecision` | clean |
| `CoalitionDecision` | clean |
| `ReactionDecision` | clean |
| `PartyNominationDecision` | clean (would break under a naive "un-sort" fix) |
| `PressureDecision` | **broken** (85.7% truncation, measured) |
| `CandidacyDecision` | **broken** (this document) |

2 of 9 decision types fail outright under vLLM's shipped configuration. No systematic property
distinguishes the broken pair from the clean seven that this investigation identified: field
count doesn't (`CandidacyDecision`=3 fields fails, `CoalitionDecision`=3 fields clean;
`PressureDecision`=4 fields fails, none of the other 4-plus-field schemas do), and neither does
"has an array field" (both broken schemas are array-free, but so are 2 of the clean ones).
Whatever the underlying vLLM/xgrammar mechanism is, it was not isolated by this comparison pass —
only its footprint was mapped, empirically, schema by schema.

`sort_keys` itself is not touched — same standing discipline as every other document in this
investigation.

## Resolved, 2026-09-06

The vLLM/xgrammar mechanism this document left unisolated is now identified and fixed:
`scripts/check_vllm_disable_any_whitespace_fix_results.md`. All 9 decision types, including
`PartyNominationDecision`'s previously-broken unsorted ordering, are clean afterward.
