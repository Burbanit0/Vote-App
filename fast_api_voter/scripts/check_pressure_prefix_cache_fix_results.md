# Prefix-cache continuity fix, pressure_action — plan-llm-protocol-and-theory-program.md §3.B.7

Third and final application of the fix already shipped for `vote_cast`
(`check_vote_cast_prefix_cache_fix_results.md`) and `chamber_deliberation`
(`check_chamber_prefix_cache_fix_results.md`).

## The fix

Identical pattern: the per-chunk `cid_list`, previously embedded near the end of
`build_pressure_system_prompt`'s output, is gone; the closing paragraph now references
`expected_cids` by name, and `build_pressure_user_prompt` carries that field instead. The
diagnostic `build_pressure_*_prompt_calibrated` builders (Phase B) inherited the same fix in the
same pass, since they were originally written by copying the pre-fix body.

`pressure_action`'s own version is the most complete of the three: `build_pressure_system_prompt`
no longer reads its `consulted` parameter **at all** — confirmed structurally by
`test_pressure_system_prompt_is_identical_across_different_chunks` (two disjoint citizen sets,
byte-identical output). Its output is a pure function of `config`: a constant for the entire run
at a fixed config, not merely stable within one tick's chunks the way `chamber_deliberation`'s fix
already was.

## Verified live — correctness unaffected

`check_pressure_prefix_cache_fix.py`, 6 consecutive chunks of 5 (30 citizens total, self_gap
spanning 0.05→2.2 across the burst so real content varies, not one constant input): **30/30
decoded cleanly**, every `act` within the legal `{0,4}` menu. Agreement with the deterministic
proxy: 23/30 — consistent with, not worse than, the already-known collapse (act=4 dominant
regardless of self_gap; this run used the unmodified production prompt, so the collapse itself
is expected and unrelated to this fix, per `check_pressure_calibration_matrix_results.md`).

## Verified live — the actual cache-hit signal

One real measurement landed during the burst: **45.7%** (vLLM's own periodic log line, read
directly via `docker logs`, not estimated). Only one sample, not a rising sequence the way
`vote_cast`'s 8-call burst produced (65.2%→73.0%): `pressure_action`'s `think=False` calls are
fast enough that all 30 completed inside vLLM's own ~10s logging interval, leaving only one tick
to sample from. Reported as what was actually measured, not extrapolated into a trend that
wasn't observed.

## Disposition

**Shipped**, to both the production and the calibrated diagnostic builders. Closes the loop on
§3.B.7: all three decision types with a per-chunk cid list embedded in their system prompt
(`vote_cast`, `chamber_deliberation`, `pressure_action`) now reference `expected_cids` by name
instead. `pressure_action`'s fix is a prerequisite for Phase D's own cost measurement (next):
without it, batch size 1 would pay the full cost of a system prompt that differs on every call,
which is exactly the scenario the fix removes.
