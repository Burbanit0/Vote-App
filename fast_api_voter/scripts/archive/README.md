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
  `stage4_llm_*`, …). Apart from their own `_results.md` and the journal, nothing refers to them.

Other files still mention these scripts. Where a path was written out (`scripts/<name>.py`),
it now reads `scripts/archive/<name>.py`. Where only the file name is given (in docstrings,
ADRs, plan docs and `_results.md` files), it stays as written: look for it here. The journal
keeps its dated paths.

They are not maintained:

- Nothing imports them.
- The import smoke test (`api/tests/test_scripts_import.py`) and the `mypy_scripts` ratchet only
  cover `scripts/*.py`.
- They are not type-checked.
- They were written against the `api/` of their day, and most of them add `parents[1]` to
  `sys.path`, so they no longer run from this folder.

To rerun one, check out the commit **before** the one that moved it:

```bash
moved=$(git log -1 --diff-filter=D --format=%H -- fast_api_voter/scripts/<name>.py)
git switch --detach "$moved^"   # the script is back at fast_api_voter/scripts/<name>.py
```

Any rerun command still quoted in a `_results.md` (for example
`ollama_structured_output_results.md`) works only from that commit.
