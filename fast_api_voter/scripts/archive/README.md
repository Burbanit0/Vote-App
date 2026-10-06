# Archived scripts

Scripts whose work is finished. Each one produced a result that is already written down: in its
own `_results.md` (still in `scripts/`, next to the live scripts), in a plan doc, or in an ADR.
They stay here, rather than being deleted, so that those results keep pointing at the code that
produced them.

What is here:

- **The acceptance runners** of polity v5–v7 (`run_v5/v6a/v6b/v7_acceptance`,
  `run_cascade_acceptance`, `run_acceptance_comparison`) and `ollama_uptime_guard` (only
  `run_v6b_acceptance` used it). These come from the Ollama and pre-GPU era, and
  `run_polity_flagship.py` has replaced them.
- **The pressure_action resolution experiments** (`resolution_2_*`), dated 2026-08-31. Their
  results are in `docs/plan/polity/plan-pressure-action-resolution.md`.
- **The Lot 0 Ollama structured-output spike** (`check_ollama_structured_output`).
- **The one-off LLM spikes and calibrations** (`check_vllm_*`, `check_pressure_*`,
  `stage4_llm_*`, …). Nothing outside their own `_results.md` refers to them.

They are not maintained:

- Nothing imports them.
- The import smoke test (`api/tests/test_scripts_import.py`) and the `mypy_scripts` ratchet only
  cover `scripts/*.py`.
- They are not type-checked.
- They were written against the `api/` of their day, and most of them add `parents[1]` to
  `sys.path`, so they no longer run from this folder.

To rerun one, go back to the commit before it moved: `git log -- fast_api_voter/scripts/<name>.py`
gives that commit.
