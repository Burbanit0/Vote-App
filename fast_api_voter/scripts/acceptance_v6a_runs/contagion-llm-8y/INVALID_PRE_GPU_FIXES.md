# Flagged: predates the bug 1-4 GPU/LLM reliability fixes

This run (v6a Lot 4's own acceptance run, cited in `THEORY.md` §10.8 and
`scripts/acceptance_v6a_results.md`) completed 2026-08-16, **before**
every one of the reliability fixes this repo's own bug 1-4 investigation
(2026-08-17 through 2026-08-22) produced:

- `d115705` (2026-08-18) — GPU cold-start non-determinism (a first
  post-cold-load call could silently return `cid` values equal to `motif`
  codes instead of real citizen ids). Fixed by a warm-up call, added
  **after** this run.
- `49e3631` / `a87efdd` (2026-08-20) — bug 4, cache-recycling mitigation
  for prompt-cache exhaustion (`finish_reason='length'` truncation
  correlating with cache saturation).
- `ca02344` (2026-08-22) — `vote_cast`'s own deterministic, per-voter
  `blank`/`ranking` schema-incoherence failure mode (a byte-identical
  temperature=0 retry reproduces the identical wrong output rather than
  resampling past it — silent, not a crash). This run's own `pressure_action`
  (dt=10) decisions are the ones most directly exercised by the same
  underlying reliability class, though the specific incoherence found was
  isolated to `vote_cast`.

**Not marked invalid because of an observed defect in this run's own
data** — a spot check found `replays.log` empty and the journal complete
(1204 events, no crash). Marked because the risk this investigation
identified is **silent by construction**: a run produced before the fix
can complete cleanly, with a schema-valid journal, while still containing
individual decisions this project's own later work found were sometimes
wrong.

**Do not use this run as a clean baseline for a future cross-run
sensitivity analysis (§11) without first checking whether re-running it
under the current, fixed code changes its result.** The run itself is
preserved, unmodified, alongside this note — nothing has been deleted or
altered.

Added 2026-08-22, as part of `prompt-sequencement-post-harnais.md`'s own
étape 3.2 (auditing pre-fix runs), following the same day's completion of
the v6b Lot 4 acceptance run and the chunk-size/temperature fixes that
motivated this audit.
