"""run_polity_flagship.py's --threshold and --freeze-amendments (PLAN_BEYOND_CI W2.1/W2.2 item 3)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from api.domain.polity.config import validate_config

def _config(flagship: Any, tmp_path: Path, **overrides: Any) -> Any:
    return flagship._flagship_config(
        engine="llm", years=2, population=50, seats=8, seed=1, output_dir=tmp_path,
        max_batch_replays=0, provider=None, workers=1, profile="exploration", **overrides,
    )


def test_the_knobs_survive_the_exploration_profile_and_validate(flagship: Any, tmp_path: Path) -> None:
    plain = _config(flagship, tmp_path)
    # The exploration profile turns amendments and regime acts on for the LLM engine...
    assert plain.agents.amendments and plain.regime.enabled
    assert plain.institutions.electoral_threshold == 0.05
    # ...and the experiment's overrides are applied after it, so they stick.
    arm = _config(flagship, tmp_path, threshold=0.03, freeze_amendments=True)
    assert arm.institutions.electoral_threshold == 0.03
    assert not arm.agents.amendments and not arm.regime.enabled and arm.constitution.referendum == "never"
    validate_config(arm)  # regime needs amendments: off together, so the config stays legal
    # Everything else is the profile's own.
    assert arm.agents.forum == plain.agents.forum and arm.parties == plain.parties


def test_without_the_knobs_nothing_changes(flagship: Any, tmp_path: Path) -> None:
    assert _config(flagship, tmp_path, threshold=None, freeze_amendments=False) == _config(flagship, tmp_path)


def test_a_threshold_outside_the_articles_range_is_refused(flagship: Any, tmp_path: Path) -> None:
    for bad in (3.0, -0.01, 0.2, float("nan")):
        with pytest.raises(ValueError, match="the article allows"):
            _config(flagship, tmp_path, threshold=bad)


def test_freezing_also_drops_scripted_amendments(flagship: Any, tmp_path: Path) -> None:
    import dataclasses

    from api.domain.polity.config import ScriptedAmendment

    base = _config(flagship, tmp_path)
    scripted = dataclasses.replace(base, constitution=dataclasses.replace(
        base.constitution, scripted=(ScriptedAmendment(tick=40, article="institutions.electoral_threshold", value=0.07),),
    ))
    frozen = flagship._experiment_overrides(scripted, threshold=0.03, freeze_amendments=True)
    assert frozen.constitution.scripted == () and frozen.institutions.electoral_threshold == 0.03
    kept = flagship._experiment_overrides(scripted, threshold=0.03, freeze_amendments=False)
    assert len(kept.constitution.scripted) == 1  # without the freeze, a scripted amendment is the run's own


def test_the_sweep_passes_the_arms_flags_and_one_directory_holds_one_arm(tmp_path: Path) -> None:
    import argparse
    import importlib.util
    import sys

    script = Path(__file__).resolve().parents[2] / "scripts" / "run_polity_seed_sweep.py"
    spec = importlib.util.spec_from_file_location("run_polity_seed_sweep", script)
    assert spec is not None and spec.loader is not None
    sweep = importlib.util.module_from_spec(spec)
    sys.modules["run_polity_seed_sweep"] = sweep
    spec.loader.exec_module(sweep)

    args = argparse.Namespace(engine="llm", profile="exploration", threshold=0.03, freeze_amendments=True)
    flags = sweep._run_flags(args)
    assert flags == ["--engine", "llm", "--profile", "exploration", "--threshold", "0.03", "--freeze-amendments"]
    sweep._claim_output_dir(tmp_path, flags)
    sweep._claim_output_dir(tmp_path, flags)  # the same arm resumes
    with pytest.raises(SystemExit, match="use another --output-dir"):
        sweep._claim_output_dir(tmp_path, sweep._run_flags(argparse.Namespace(
            engine="llm", profile="exploration", threshold=0.05, freeze_amendments=True)))

