"""The W2.1 threshold gate's per-founder readout (OBS-045): scripts/check_agent_prompt_neutrality.py."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from api.domain.polity.llm_schemas import ForumTurn


def test_founding_is_tallied_per_backing_count_at_each_bar(neutrality: Any) -> None:
    lines = neutrality._by_backing([6, 5, 6, 9], [True, True, True, True], [True, False, False, True])
    assert lines[1:] == [
        "        5   1            1            0",
        "        6   2            2            1",
        "        9   1            1            1",
    ]


def _turn(rationale: str) -> ForumTurn:
    return ForumTurn(rationale=rationale, post="", note_to_self="", shift_issue=-1, shift_direction="none",
                     party_move="found", party_id=-1)


def test_only_the_seat_bar_counts_as_naming_it_not_the_founding_rule(neutrality: Any) -> None:
    assert not neutrality._names_seat_bar(_turn("Founding meets the 5% threshold with 6 citizens."), 0.07)
    assert neutrality._names_seat_bar(_turn("Below 7% we would win no seat."), 0.07)
    assert neutrality._names_seat_bar(_turn("Too few votes for the assembly."), 0.03)


def test_the_gate_flags_are_refused_without_the_gate_and_before_any_call(neutrality: Any, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        neutrality.main(["--probe", "forum", "--gate-wording", "count"])
    with pytest.raises(SystemExit):
        neutrality.main(["--probe", "threshold", "--gate-log", str(tmp_path / "missing" / "answers.jsonl")])
