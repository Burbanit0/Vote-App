# A small real run: pressure_action's calibration fix in a genuine multi-tick simulation

Every prior check of Phase E (`check_pressure_shipped_wiring.py`, the pytest live tests in
`test_polity_vllm_live.py`) called `decide_pressure_actions` directly against a hand-built cohort.
This is the first check to run the actual `run_simulation()` tick loop end to end against the real
vLLM server and look at what pressure_action does across a real run.

## Setup

`scripts/check_pressure_small_run.py`: the shipped config (`load_config()`, vLLM already the
default provider), with `llm.enabled=True`, `candidacy.ambition_threshold=0.1` (needed for any
candidacy to occur at all — ADR-002/ADR-003), `run.population_size=20` (down from the shipped 100,
purely to bound wall-clock — `_PRESSURE_CALIBRATED_CHUNK_SIZE=1` makes population size the
dominant cost lever now), `run.duration_years=4`.

**First attempt produced zero `pressure_action` events despite 2 real elections.** Root cause:
`config.awakening.enabled` and `config.legitimacy.enabled` are both `false` in the shipped yaml —
`awakening` is pressure_action's own consultation gate ("PORTE d'échantillonnage, jamais une
décision", §7bis.9d), and the accountability phase's own docstring notes pressure levers require
`legitimacy.enabled` too. Both are off by default; a real flagship run must turn them on
explicitly (the only way `check_pressure_batch_size_cost_results.md`'s "137 real decisions/tick"
anchor could ever have been measured). Corrected by enabling both, matching the overrides
`test_pressure_action_wiring_against_the_real_client_in_a_live_tick` already uses.
`pressure_menu.electoral_only` stays at its shipped `true` — the closed-menu regime Phase E
actually calibrated and shipped for.

## Result

```
run completed in 285.3s -> events.jsonl
total events: 203
  pressure_action: 64
  candidacy_considered: 40
  vote_cast: 40
  legitimacy_updated: 17
  ... (9 other event types)

pressure_action events: 64
act histogram: {4: 22, 0: 42}
LLM-decided (carries ctx.self_gap): 64/64
mean self_gap by chosen act:
  act=0 (nothing):            n=42, mean self_gap=0.2336
  act=4 (wait for election):  n=22, mean self_gap=0.3820
```

All 64 pressure_action decisions across the run were LLM-decided (none fell back to the
deterministic proxy). Not a collapsed constant — both legal acts occur, in a realistic split
(42/22, not 64/0). The direction is the one the calibration fix targeted: citizens who chose the
more assertive act (4, wait-for-election) have a materially higher mean self_gap (0.382) than
those who chose nothing (0.234) — real, if noisy, sensitivity to the citizen's own discontent,
which is exactly what `check_pressure_calibration_matrix_results.md`'s own controlled matrix
already established at batch size 1 and what the earlier isolated checks confirmed in miniature.
This is the same finding surfacing a third way, in a run nobody hand-tuned the inputs for.

Two vote_cast batches fell back to the deterministic sincere ranking mid-run (one hit the
already-documented `blank=1` / non-empty-ranking §3.6.1 hard-rule violation, ~6.7% of vote_cast
batches historically; one hit `finish_reason='length'`). Both are the existing retry-exhaustion
safety net working as designed, not a crash and not related to pressure_action — noted, not
investigated further here.

## Disposition

Confirms Phase E's fix in the one setting none of the prior checks used: a real, unscripted,
multi-tick run where the model has to get the input right on citizens whose exact state nobody
chose to be unambiguous. Combined with the offline suite, the standalone live script, and the two
pytest live tests, `pressure_action`'s calibration fix is now verified at four independent levels.
