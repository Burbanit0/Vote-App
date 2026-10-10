"""The W2.1 threshold gate's breakdown by backing (OBS-045): scripts/check_agent_prompt_neutrality.py."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def test_founding_is_tallied_per_backing_count_at_each_bar() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "check_agent_prompt_neutrality.py"
    spec = importlib.util.spec_from_file_location("check_agent_prompt_neutrality", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_agent_prompt_neutrality"] = module
    spec.loader.exec_module(module)

    lines = module._by_backing([6, 5, 6, 9], [True, True, True, True], [True, False, False, True])
    assert lines[1:] == [
        "        5   1            1            0",
        "        6   2            2            1",
        "        9   1            1            1",
    ]
