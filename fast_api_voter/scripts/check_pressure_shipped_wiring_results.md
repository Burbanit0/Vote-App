# Phase E: calibrated `pressure_action` shipped and live-verified end-to-end

## What changed

`decide_pressure_actions` (`llm_behavior_engine.py`) now calls `build_pressure_system_prompt_calibrated`/
`build_pressure_user_prompt_calibrated` with `PRESSURE_THRESHOLD_SIGNAL` — blank_threshold, the
cheapest of the four calibration signals that cleared the quality bar in Phase C, and the one
Phase D actually measured the cost of — instead of the uncalibrated `build_pressure_system_prompt`/
`build_pressure_user_prompt` pair it used before. It chunks at the new `_PRESSURE_CALIBRATED_CHUNK_SIZE`
(1), overriding `config.llm.max_batch_size` the same way `_vote_cast_chunk_size`/`_chamber_chunk_size`
already override it for their own decision types — one HTTP call per consulted citizen, never a
larger batch, because no batch size other than 1 has ever cleared the quality bar.

Only the threshold signal ships. `PRESSURE_HISTORY_SIGNAL`/`_PERCENTILE_SIGNAL`/`_PLEDGE_SIGNAL` also
scored 100% in Phase C but were never carried through Phase D's own cost measurement — shipping them
would extrapolate a quality result onto an unmeasured cost, exactly what Phase D's "measure, don't
model" mandate exists to prevent.

## Offline verification

14 tests changed or added in `test_polity_llm_behavior_engine.py`:
- Three `decide_pressure_actions` tests rewritten because their premise (one call per cohort, sized by
  `config.llm.max_batch_size`) no longer holds: sort-order, cohort-of-three, and large-cohort chunking
  now assert one call per citizen regardless of `max_batch_size`.
- One test (`..._propagates_llm_response_error_on_count_mismatch`) needed a different fault injection —
  a fixed too-few-decisions reply no longer misaligns a singleton chunk (one decision *is* a correct
  reply to a chunk of one), and an empty list fails `PressureBatch`'s own min-length schema check before
  the misalignment path runs. A response carrying a cid that can never match any real chunk's own
  `expected_cids` still reliably misaligns regardless of chunk size.
- New: `..._sends_blank_threshold_as_the_shipped_calibration_signal`, checking the signal's own
  definition text and the `blank_threshold` value both reach the real prompts `decide_pressure_actions`
  builds, not just the standalone calibrated builders' own unit tests.

`mypy api/` clean (same pre-existing, unrelated `workers_playground.py` numpy-stub artifact noted
throughout this session), `ruff check .` clean, full polity suite 1379/1379 passing (41 skipped,
719 deselected — unchanged skip/deselect counts from before this change).

## Live verification

`check_pressure_shipped_wiring.py` calls `decide_pressure_actions` itself — not its prompt builders in
isolation — against the real vLLM server, with a 12-citizen cohort carrying 12 distinct
`blank_threshold` values and `self_gap` alternating unambiguously below/above each citizen's own
threshold (the pre-registered `plan-decision-quality-validation.md` criterion: `gap < 0.5×bt` or
`gap > 1.5×bt`).

```
HTTP calls made: 12 (expect 12, one per citizen)
blank_threshold present in every wire payload: OK
decoded cleanly: 12/12, all acts legal
agreement with the pre-registered unambiguous criterion: 12/12
```

Confirms three things the offline tests can't: the real client receives exactly one call per
citizen (not a mocked assumption), `blank_threshold` actually reaches the wire through the real
code path `decide_pressure_actions` runs (not just the calibrated builders' own direct unit
tests), and the live model's real decisions agree with the unambiguous criterion at 12/12 — one
more real data point consistent with, not a replacement for, `check_pressure_calibration_matrix.py`'s
own 9-trial (45/45) result for this exact signal at this exact batch size.

## Disposition

**Shipped.** `pressure_action` is now a well-posed decision per polity-decision-contracts.md's own
5-clause contract: goal and rules of the game were already stated, state is now perceptible
(blank_threshold, on `self_gap`'s own scale), nothing prescriptive was added (no `gap < blank_threshold`
rule ever appears in the prompt — enforced structurally by
`test_every_calibration_signal_definition_contains_no_if_then_wording`), and it is scored on the scale
it is shown. Cost is measured, not modelled: +0.85h over the ~35.6h flagship baseline (Phase D),
accepted as the price of a decision type that previously collapsed to a content-blind constant
regardless of input.

This closes the plan (`lets-build-a-solid-spicy-otter.md`, Phases A–E) for `pressure_action` — the
pilot Phase A/B/C/D/E worked through. The specification and the audit of the other 8 decision types
(Phase A) remain the reusable artifact for any future decision type found to fail the same C3 clause;
none of those other types were touched by this change.
