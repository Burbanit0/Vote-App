"""scripts/show_llm_exchanges.py: a run's LLM calls read back as prompt, reasoning and answer."""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
from types import ModuleType

import pytest

from api.domain.polity.llm_call_log import (
    CALL_LOG_FILENAME,
    PROMPT_LOG_FILENAME,
    PromptLogWriter,
)

BACKEND = Path(__file__).resolve().parents[2]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "show_llm_exchanges", BACKEND / "scripts" / "show_llm_exchanges.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


show = _load()


def _call(
    call_id: str,
    tick: int,
    decision_type: str,
    units: list[int],
    answer: dict[str, object],
    **extra: object,
) -> str:
    record = {
        "call_id": call_id,
        "kind": "decision",
        "decision_type": decision_type,
        "tick": tick,
        "unit_ids": units,
        "attempt": 0,
        "completion_tokens": 10,
        "latency_ms": 1500,
        "finish_reason": "stop",
        "content": json.dumps(answer),
        **extra,
    }
    return json.dumps(record) + "\n"


def _run(tmp_path: Path) -> Path:
    prompts = PromptLogWriter(tmp_path / PROMPT_LOG_FILENAME)
    prompts.write(
        "a1",
        system_prompt="You are Remy Silva, president.",
        user_prompt="Tick 0: state your positions.",
        json_schema=None,
    )
    prompts.write(
        "a2",
        system_prompt="You are Remy Silva, president.",
        user_prompt="Tick 1: a bill is due.",
        json_schema=None,
    )
    prompts.close()
    (tmp_path / CALL_LOG_FILENAME).write_text(
        json.dumps(
            {"call_id": "w0", "kind": "warm_up", "decision_type": None, "tick": None}
        )
        + "\n"
        + _call(
            "a1",
            0,
            "president_turn",
            [197],
            {"speech": "climate first"},
            reasoning="I care about the climate.",
        )
        + _call(
            "p1", 0, "pressure_action", [9, 12], {"decisions": [{"cid": 9, "act": 0}]}
        )
        + _call("a2", 1, "president_turn", [197], {"bill": []})
        + _call(
            "c1",
            1,
            "coalition_decision",
            [12],
            {"decisions": [{"party_id": 12, "join": 1}]},
        )
    )
    return tmp_path


def _out(argv: list[str]) -> str:
    buf = io.StringIO()
    assert show.main(argv, out=buf) == 0
    return buf.getvalue()


def test_a_call_reads_as_prompt_reasoning_and_answer(tmp_path: Path) -> None:
    text = _out([str(_run(tmp_path)), "--type", "president_turn"])
    first, second = text.split("━━ ")[1:]
    assert first.startswith("tick 0 · president_turn · citizen 197 · 10 tokens, 1.5 s")
    for part in (
        "── system\nYou are Remy Silva, president.",
        "── user\nTick 0: state your positions.",
        "── reasoning\nI care about the climate.",
        '"speech": "climate first"',
    ):
        assert part in first
    assert (
        "── system: unchanged since this citizen's call at tick 0" in second
        and "Tick 1: a bill is due." in second
    )
    assert "pressure_action" not in text and "warm_up" not in text


def test_the_filters_pick_by_tick_and_citizen(tmp_path: Path) -> None:
    run = _run(tmp_path)
    assert (
        _out([str(run), "--citizen", "12"]).count("━━ ") == 1
    )  # the pressure call, not party 12's
    party = _out([str(run), "--party", "12"])
    assert party.count("━━ ") == 1 and "coalition_decision · party 12 ·" in party
    assert _out([str(run), "--tick", "1"]).count("━━ ") == 2
    assert "warm_up" in _out([str(run), "--all-kinds"])
    assert "── system\n" not in _out([str(run), "--no-system"])


def test_without_prompts_the_answers_still_show(tmp_path: Path) -> None:
    run = _run(tmp_path)
    (run / PROMPT_LOG_FILENAME).unlink()
    text = _out([str(run)])
    assert text.count("━━ ") == 4 and "── user" not in text and "climate first" in text


def test_a_line_still_being_written_waits_for_its_end(tmp_path: Path) -> None:
    path = tmp_path / "log.jsonl"
    path.write_text('{"a": 1}\n{"b":')
    with path.open("rb") as handle:
        assert [row for _, row in show._rows(handle)] == [{"a": 1}]
        with path.open("a", encoding="utf-8") as writer:
            writer.write(" 2}\n")
        assert [row for _, row in show._rows(handle)] == [{"b": 2}]


def test_a_damaged_line_is_skipped_not_fatal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run = _run(tmp_path)
    calls = run / CALL_LOG_FILENAME
    calls.write_text(
        '{"call_id": "x", "kind": "deci' + calls.read_text()
    )  # a killed run's fragment, resumed
    text = _out([str(run)])
    assert (
        text.count("━━ ") == 4
        and "skipped a damaged line at byte 0" in capsys.readouterr().err
    )
