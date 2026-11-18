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

- **The `check_*` experiments of the prompt-and-chunk-size era, archived 2026-11-15** (25 scripts: the
  `check_pressure_action_*` and `*_collapse_signature` studies, the chunk-size and positional-bias checks,
  the vote-cast cache checks). No code, workflow or script referenced them; their results are in their
  `_results.md` and the plan docs. `check_vllm_speculation_ab` was meant to go with them and was kept: it is
  the measuring step of the vLLM bump protocol (the 0.29-0.31 bump notes and EXP-019 all run it).
- **`place_model_runs_on_catalogue.py`** (EXP-028, Stage 2b): places the ten model-led scenario runs on the rule catalogue's
  per-feature envelope. It imports `run_polity_catalogue` from `scripts/`, so it runs from `fast_api_voter/` as its docstring says.
- **`classify_model_leaders_against_rules.py`** (EXP-029, Stage 2c): reads the model's presidents' and nominees' moves in the EXP-028 runs
  against ADR-040's four leader rules, from their journals and snapshots; CPU only.
- **Four prompt builders and their tests, archived 2026-11-16** (`polity_archived_builders.py`,
  `test_archived_prompt_builders.py`): `build_candidacy_system_prompt_toon_calibrated`,
  `build_coalition_system_prompt_calibrated` and the TOON pressure pair, moved out of
  `llm_behavior_engine.py` because no live code calls them. Only the three experiment scripts above
  import them. The 18 tests are not collected by CI: `pytest scripts/archive/test_archived_prompt_builders.py -o addopts=""`.

Other files still mention these scripts. Where a path was written out (`scripts/<name>.py`),
it now reads `scripts/archive/<name>.py`. Where only the file name is given (in docstrings,
ADRs, plan docs and `_results.md` files), it stays as written: look for it here. The journal
keeps its dated paths.

They are not maintained:

- Nothing outside the archive imports them.
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
