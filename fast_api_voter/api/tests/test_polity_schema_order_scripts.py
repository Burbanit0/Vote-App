"""The two ADR-030 scripts' own logic: scripts/schema_order_live_report.py (the live pass/fail) and
scripts/check_schema_order.py (which arms run, the restart between controls, the report header)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


live = _load("schema_order_live_report")
check = _load("check_schema_order")


# ── schema_order_live_report.py ────────────────────────────────────────────

def test_a_behaviour_measure_must_stay_inside_the_two_controls() -> None:
    assert live.verdict("pressure 'nothing' share", [0.546, 0.693], 0.553) == (0.546, 0.693, True)
    assert live.verdict("pressure 'nothing' share", [0.546, 0.693], 0.0)[2] is False  # the motif-first collapse
    assert live.verdict("forum mind-shift rate", [0.039, 0.050], 0.006)[2] is False


def test_controls_that_agree_exactly_widen_to_half_and_twice_and_a_zero_gets_its_floor() -> None:
    assert live.verdict("elections per run", [2.0, 2.0], 3.9) == (1.0, 4.0, True)
    assert live.verdict("elections per run", [2.0, 2.0], 4.1)[2] is False
    assert live.verdict("recalls per run", [0.0, 0.0], 1.0) == (0.0, 1.0, True)  # FLOOR
    assert live.verdict("recalls per run", [0.0, 0.0], 1.5)[2] is False


def test_failures_are_one_sided_so_fewer_retries_or_fallbacks_never_fail() -> None:
    # 2026-10-20: the first table had fewer retries than both controls, and a two-sided range failed it
    assert live.verdict("retry rate", [0.0137, 0.0160], 0.0127)[2] is True
    assert live.verdict("retry rate", [0.0137, 0.0160], 0.03)[2] is False
    assert live.verdict("fallbacks", [0.0, 15.0], 0.0)[2] is True
    assert live.verdict("fallbacks", [0.0, 15.0], 16.0)[2] is False


def _run_dir(root: Path, arm: str, seed: int, *, acts: list[int], shifts: list[int], fallbacks: int,
             retried: int, outcome: str = "completed") -> None:
    run = root / arm / f"sweep-4y-p100-seed{seed}" / "run" / f"sweep-4y-p100-seed{seed}"
    run.mkdir(parents=True)
    (run / "digest.json").write_text(json.dumps({"outcome": outcome, "office_occupancy": 0.9, "llm_fallbacks": fallbacks}))
    events = [{"event_type": "elected"}] * 2 + [{"event_type": "pressure_action", "payload": {"act": a}} for a in acts]
    (run / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events))
    calls = [{"kind": "decision", "decision_type": "forum_post", "attempt": 0,
              "content": json.dumps({"shift_issue": s})} for s in shifts]
    calls += [{"kind": "decision", "decision_type": "vote_cast", "attempt": 1}] * retried
    (run / "llm_calls.jsonl").write_text("\n".join(json.dumps(c) for c in calls))


def test_measures_read_acts_from_the_payload_forum_shifts_from_the_content_and_retries_from_attempts(tmp_path: Path) -> None:
    _run_dir(tmp_path, "ctl-a", 1, acts=[0, 0, 3, 1], shifts=[-1, 4, -1, -1], fallbacks=2, retried=4)
    m = live.measures(live.runs(str(tmp_path), "ctl-a"))
    assert m["elections per run"] == 2 and m["recalls per run"] == 0 and m["office occupancy"] == 0.9
    assert m["pressure 'nothing' share"] == 0.5 and m["forum mind-shift rate"] == 0.25
    assert m["fallbacks"] == 2 and m["retry rate"] == 0.5  # 4 retried decisions of 8


def test_the_report_passes_a_candidate_inside_the_controls_and_refuses_an_incomplete_arm(tmp_path: Path, capsys: Any) -> None:
    for arm, acts in (("ctl-a", [0, 0, 3, 1]), ("ctl-b", [0, 0, 0, 3]), ("new", [0, 0, 3, 3])):
        _run_dir(tmp_path, arm, 1, acts=acts, shifts=[-1, 4], fallbacks=0, retried=0)
    assert live.main(str(tmp_path)) == 0 and "PASS" in capsys.readouterr().out
    _run_dir(tmp_path, "new", 2, acts=[3, 3, 3, 3], shifts=[-1, 4], fallbacks=0, retried=0)  # inaction falls to 25%
    assert live.main(str(tmp_path)) == 1 and "FAIL" in capsys.readouterr().out
    _run_dir(tmp_path, "ctl-b", 2, acts=[0], shifts=[], fallbacks=0, retried=0, outcome="crashed")
    assert live.main(str(tmp_path)) == 1 and "incomplete arms: ctl-b" in capsys.readouterr().out


# ── check_schema_order.py ──────────────────────────────────────────────────

def test_the_candidates_are_every_arm_whose_table_is_not_the_controls() -> None:
    from api.domain.polity.schema_order import RULES, rule_table

    assert check.candidate_arms({}) == [f"order_{rule}" for rule in RULES]  # alphabetical is the control
    assert check.candidate_arms(rule_table("xdm")) == ["alphabetical_order", *(f"order_{r}" for r in RULES if r != "xdm")]


def test_the_report_says_what_the_controls_sent_and_when_it_is_not_today_s_wire_order() -> None:
    header = check.report([], "0" * 64, {}).splitlines()[2]
    assert header.startswith("The controls sent WIRE_ORDER empty (all alphabetical).")
    assert ("They differ" in header) == bool(check.WIRE_ORDER)


def test_the_health_probe_speaks_http_only_and_gives_up_on_a_dead_server() -> None:
    assert check._healthy("file:///etc/passwd", timeout_s=0.5) is False
    assert check._healthy("http://127.0.0.1:9/v1", timeout_s=0.5) is False


def _fake_run(monkeypatch: Any, tmp_path: Path, *, restart_code: int = 0) -> list[Any]:
    calls: list[Any] = []
    monkeypatch.setattr(check, "candidate_arms", lambda control: ["order_dxm"])
    monkeypatch.setattr(check, "_healthy", lambda base_url: True)
    monkeypatch.setattr(check.run_bakeoff, "main", lambda argv: calls.append(("session", argv[1])) or 0)

    def restart(argv: Any, **kwargs: Any) -> Any:
        calls.append(("restart", argv, kwargs))
        return type("Done", (), {"returncode": restart_code})()
    monkeypatch.setattr(check.subprocess, "run", restart)
    return calls


def test_the_server_restarts_once_between_the_controls_without_a_shell(monkeypatch: Any, tmp_path: Path) -> None:
    calls = _fake_run(monkeypatch, tmp_path)
    assert check._run(tmp_path, None, "docker compose -f docker-compose.llm.yml restart vllm; rm -rf /") == 0
    assert [c[0] if c[0] == "restart" else c[1] for c in calls] == ["control-a", "restart", "control-b", "order_dxm"]
    _, argv, kwargs = calls[1]
    assert argv == ["docker", "compose", "-f", "docker-compose.llm.yml", "restart", "vllm;", "rm", "-rf", "/"]
    assert "shell" not in kwargs  # an argument list: the `;` is an argument, never a command separator


def test_a_resume_with_control_b_complete_does_not_restart_the_shared_server(monkeypatch: Any, tmp_path: Path) -> None:
    (tmp_path / "control-b").mkdir()
    (tmp_path / "control-b" / check.GATES_FILENAME).write_text("{}")
    calls = _fake_run(monkeypatch, tmp_path)
    assert check._run(tmp_path, None, "docker compose restart vllm") == 0
    assert [c[0] for c in calls] == ["session"] * 3


def test_a_failed_restart_stops_the_run_before_control_b(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    calls = _fake_run(monkeypatch, tmp_path, restart_code=1)
    assert check._run(tmp_path, None, "docker compose restart vllm") == 1
    assert [c[0] if c[0] == "restart" else c[1] for c in calls] == ["control-a", "restart"]
    assert "did not come back" in capsys.readouterr().out


@pytest.mark.parametrize("missing", ["control-b", "order_dxm"])
def test_decide_refuses_to_run_without_its_sessions(monkeypatch: Any, tmp_path: Path, capsys: Any, missing: str) -> None:
    monkeypatch.setattr(check, "candidate_arms", lambda control: ["order_dxm"])
    for label in ("control-a", "control-b", "order_dxm"):
        if label != missing:
            (tmp_path / label).mkdir()
            (tmp_path / label / check.RESULTS_FILENAME).write_text("")
    assert check._decide(tmp_path) == 1 and "missing" in capsys.readouterr().out
