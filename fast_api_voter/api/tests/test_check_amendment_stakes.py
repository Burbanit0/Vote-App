"""OBS-049's count in scripts/check_amendment_stakes.py: what a proposed voting method changes for the president."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_amendment_stakes.py"
_spec = importlib.util.spec_from_file_location("check_amendment_stakes", SCRIPT)
assert _spec is not None and _spec.loader is not None
probe = importlib.util.module_from_spec(_spec)
_saved_path = sys.path[:]
_spec.loader.exec_module(probe)
sys.path[:] = _saved_path  # the script puts scripts/ on the path: keep it from leaking into later tests

_BALLOTS = [["A", "B", "C"]] * 4 + [["B", "C", "A"]] * 3 + [["C", "B", "A"]] * 2  # plurality elects A, Borda B


def test_a_proposed_method_is_judged_from_the_presidents_side() -> None:
    assert probe._gain(_BALLOTS, "plurality", "borda", "B") == "gain"
    assert probe._gain(_BALLOTS, "plurality", "borda", "A") == "loss"
    assert probe._gain(_BALLOTS, "plurality", "borda", "C") == "shift"  # another winner, still not them
    assert probe._gain(_BALLOTS, "borda", "irv", "B") == "nothing"  # two methods, one winner
