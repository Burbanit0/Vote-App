"""run_polity_flagship.py's --threshold and --freeze-amendments (PLAN_BEYOND_CI W2.1/W2.2 item 3)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

from api.domain.polity.config import validate_config

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_polity_flagship.py"


@pytest.fixture(scope="module")
def flagship() -> Any:
    spec = importlib.util.spec_from_file_location("run_polity_flagship", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_polity_flagship"] = module
    spec.loader.exec_module(module)
    return module


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
