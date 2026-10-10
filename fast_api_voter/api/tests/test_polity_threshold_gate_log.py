"""The W2.1 threshold gate's per-founder log and its reading (OBS-045): scripts/check_agent_prompt_neutrality.py
writes the answers, scripts/check_observations.py founders reads them."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from api.domain.polity.citizen import generate_population
from api.domain.polity.llm_schemas import ForumTurn

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _turn(rationale: str, move: str = "found") -> ForumTurn:
    return ForumTurn(rationale=rationale, post="", note_to_self="", shift_issue=-1, shift_direction="none",
                     party_move=move, party_id=-1)


def test_founding_is_tallied_per_backing_count_at_each_bar(neutrality: Any) -> None:
    lines = neutrality._by_backing([6, 5, 6, 9], [True, True, True, True], [True, False, False, True])
    assert lines[1:] == [
        "        5   1            1            0",
        "        6   2            2            1",
        "        9   1            1            1",
    ]


def test_the_gate_logs_every_answer_and_the_count_wording_drops_the_founding_percentage(
    neutrality: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    config = neutrality._config()
    citizens = generate_population(config.citizens, 100, 7)
    prompts: list[str] = []

    def answer(citizen: Any, *, system_prompt: str, **_: Any) -> SimpleNamespace:
        prompts.append(system_prompt)
        return SimpleNamespace(turn=_turn("meets the founding threshold"))

    monkeypatch.setattr(neutrality, "decide_forum", answer)
    monkeypatch.setattr(neutrality, "_split_by_backing", lambda *_: {"enough would co-found": citizens[:2]})
    monkeypatch.setattr(neutrality, "cofounders", lambda *_: [0] * 6)
    monkeypatch.setattr(neutrality, "party_roll", lambda *_: "")
    monkeypatch.setattr(neutrality, "stand_line", lambda *_: "")
    log = tmp_path / "answers.jsonl"

    assert neutrality._threshold_gate(citizens, [], 2, config, None, log, "count") is False  # all found: STOP
    rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert [(row["citizen"], row["backing"], row["told"]) for row in rows] == [
        (citizens[0].citizen_id, 6, 0.03), (citizens[0].citizen_id, 6, 0.07),
        (citizens[1].citizen_id, 6, 0.03), (citizens[1].citizen_id, 6, 0.07),
    ]
    assert {row["rationale"] for row in rows} == {"meets the founding threshold"}
    assert len(prompts) == 4
    assert all("at least 5 of the 100 citizens" in p and "at least 5% of the citizens" not in p for p in prompts)


def test_founders_reads_which_rule_the_answers_cite(tmp_path: Path) -> None:
    def row(told: float, backing: int, rationale: str, move: str = "found") -> str:
        return json.dumps({"citizen": 0, "backing": backing, "told": told, "party_move": move,
                           "rationale": rationale, "note_to_self": "", "post": ""}) + "\n"

    log = tmp_path / "shipped.jsonl"
    log.write_text(
        row(0.07, 6, "Founding meets the 5% threshold with 6 citizens.")
        + row(0.07, 8, "8% support meets the threshold.")
        + row(0.07, 6, "6 citizens closer to me; founding meets the threshold.")
        + row(0.07, 9, "Below 7% we would win no seat.", "none")
        + '{"torn',
        encoding="utf-8",
    )
    out = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_observations.py"), "founders", str(log)],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert out[1].split() == ["shipped", "7%", "4", "3", "2", "of", "2", "1", "1", "1", "1", "1"]


def test_the_gate_flags_are_refused_without_the_gate_and_before_any_call(neutrality: Any, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        neutrality.main(["--probe", "forum", "--gate-wording", "count"])
    with pytest.raises(SystemExit):
        neutrality.main(["--probe", "threshold", "--gate-log", str(tmp_path / "missing" / "answers.jsonl")])
