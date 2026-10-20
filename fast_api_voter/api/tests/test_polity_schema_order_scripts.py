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

def test_the_p_value_is_exact_one_flip_in_two_to_the_k() -> None:
    # new above ctl by the same amount in all 5 seeds: only "all plus" (and, two-sided, "all minus") reach it
    effect, p = live.sign_flip_p([1.0] * 5, one_sided=False)
    assert effect == 1.0 and p == pytest.approx(2 / 2**5)
    assert live.sign_flip_p([1.0] * 5, one_sided=True)[1] == pytest.approx(1 / 2**5)
    assert live.smallest_p([1.0] * 5, one_sided=False) == pytest.approx(2 / 2**5)


def test_a_seed_where_both_runs_agree_cannot_vote() -> None:
    assert live.sign_flip_p([1.0, 1.0, 0.0], one_sided=True) == (pytest.approx(2 / 3), 0.25)
    assert live.smallest_p([1.0, 1.0, 0.0, 0.0], one_sided=True) == 0.25
    assert live.sign_flip_p([0.0] * 6, one_sided=False) == (0.0, 1.0)


def test_failures_are_one_sided_so_fewer_retries_or_fallbacks_never_fail() -> None:
    # 2026-10-20: the first table had fewer retries than both controls, and a two-sided range failed it
    assert live.sign_flip_p([-5.0] * 6, one_sided=True)[1] == 1.0
    assert live.sign_flip_p([-5.0] * 6, one_sided=False)[1] == pytest.approx(2 / 2**6)


def test_holm_steps_down_and_stops_at_the_first_p_that_holds() -> None:
    assert live.holm({"a": 0.001, "b": 0.02, "c": 0.06}) == {"a", "b"}  # 0.001 < .05/3, 0.02 < .05/2, 0.06 >= .05
    assert live.holm({"a": 0.03, "b": 0.001, "c": 0.9}) == {"b"}  # 0.03 >= .05/2 stops it
    assert live.holm({"a": 0.5}) == set()


def test_a_measure_too_sparse_to_test_leaves_the_family_and_frees_the_others() -> None:
    six = [0.1, -0.1, 0.1, -0.1, 0.1, -0.1]  # every seed differs: smallest two-sided p 2/64 = 0.031
    diffs = {"pressure 'nothing' share": six, "fallbacks": [5.0, 0, 0, 0, 0, 5.0], "elections per run": [0.0] * 6}
    # with fallbacks in, the bar is 0.05/2 = 0.025 and both fail it; fallbacks (1/4) leaves first, then 0.031 < 0.05
    assert live.testable(diffs) == ({"pressure 'nothing' share"}, {"fallbacks"})
    assert live.testable({"pressure 'nothing' share": six[:3]}) == (set(), {"pressure 'nothing' share"})


def test_the_family_does_not_depend_on_the_order_of_ties_or_on_a_hopeless_measure() -> None:
    # 8 seeds and all seven measures differing in every seed: all seven can be tested (1/256 and 2/256 pass Holm)
    every = {name: [1.0] * 8 for name in live.MEASURES}
    assert live.testable(every) == (set(live.MEASURES), set())
    # a hopeless measure (fallbacks in 2 seeds) does not block the ones that could pass without it
    # (7 seeds: 2/128 passes 0.05/2; at 6, 2/64 = 0.031 would not)
    mixed = {"pressure 'nothing' share": [1.0] * 7, "forum mind-shift rate": [1.0] * 7, "fallbacks": [5.0, 5.0, 0, 0, 0, 0, 0]}
    assert live.testable(mixed) == ({"pressure 'nothing' share", "forum mind-shift rate"}, {"fallbacks"})


def _run_dir(root: Path, arm: str, seed: int, *, acts: list[int], shifts: list[int], fallbacks: int,
             retried: int, outcome: str = "completed", years: int = 4) -> None:
    run = root / arm / f"sweep-{years}y-p100-seed{seed}" / "run" / f"sweep-{years}y-p100-seed{seed}"
    run.mkdir(parents=True)
    (run / "digest.json").write_text(json.dumps({"outcome": outcome, "office_occupancy": 0.9, "llm_fallbacks": fallbacks}))
    events = [{"event_type": "elected"}] * 2 + [{"event_type": "pressure_action", "payload": {"act": a}} for a in acts]
    (run / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events))
    calls = [{"kind": "decision", "decision_type": "forum_post", "attempt": 0,
              "content": json.dumps({"shift_issue": s})} for s in shifts]
    calls += [{"kind": "decision", "decision_type": "vote_cast", "attempt": 1}] * retried
    (run / "llm_calls.jsonl").write_text("\n".join(json.dumps(c) for c in calls))


def test_measures_read_acts_from_the_payload_forum_shifts_from_the_content_and_retries_from_attempts(tmp_path: Path) -> None:
    _run_dir(tmp_path, "ctl", 1, acts=[0, 0, 3, 1], shifts=[-1, 4, -1, -1], fallbacks=2, retried=4)
    m = live.measures(list(live.runs(str(tmp_path), "ctl").values()))
    assert m["elections per run"] == 2 and m["recalls per run"] == 0 and m["office occupancy"] == 0.9
    assert m["pressure 'nothing' share"] == 0.5 and m["forum mind-shift rate"] == 0.25
    assert m["fallbacks"] == 2 and m["retry rate"] == 0.5  # 4 retried decisions of 8
    empty = live.measures([{"digest": {}, "events": [], "calls": []}])
    assert empty["pressure 'nothing' share"] is None and empty["forum mind-shift rate"] is None


def test_runs_are_paired_by_sweep_and_seed_number_and_one_sweep_size_per_out_dir(tmp_path: Path, capsys: Any) -> None:
    for seed in (1, 2, 10):
        _run_dir(tmp_path, "new", seed, acts=[0] * seed, shifts=[], fallbacks=0, retried=0)
    paired = live.runs(str(tmp_path), "new")
    assert sorted(paired) == [("sweep-4y-p100", 1), ("sweep-4y-p100", 2), ("sweep-4y-p100", 10)]
    assert len(paired[("sweep-4y-p100", 10)]["events"]) == 2 + 10
    for seed in (1, 2, 10):
        _run_dir(tmp_path, "ctl", seed, acts=[0], shifts=[], fallbacks=0, retried=0)
    _run_dir(tmp_path, "ctl", 1, acts=[0], shifts=[], fallbacks=0, retried=0, years=8)  # a linked older sweep
    assert live.main(str(tmp_path)) == 1 and "more than one sweep" in capsys.readouterr().out


def _arms(root: Path, seeds: int, new: Any) -> None:
    """ctl: inaction 4/8 in every seed; new: what `new(seed)` returns over the same base."""
    base = {"acts": [0, 0, 0, 0, 3, 3, 3, 1], "shifts": [-1, 4], "fallbacks": 0, "retried": 0}
    for seed in range(1, seeds + 1):
        _run_dir(root, "ctl", seed, **base)
        _run_dir(root, "new", seed, **{**base, **new(seed)})


def test_the_report_passes_a_candidate_that_moves_both_ways(tmp_path: Path, capsys: Any) -> None:
    _arms(tmp_path, 8, lambda seed: {"acts": [0, 0, 0, 0 if seed % 2 else 3, 0 if seed % 2 else 3, 3, 3, 1]})  # 5/8, 3/8, ...
    assert live.main(str(tmp_path)) == 0
    out = capsys.readouterr().out
    assert "PASS" in out and "Cannot tell" not in out and "| no difference |" in out


def test_a_behaviour_that_moves_in_every_seed_is_changed_not_failed(tmp_path: Path, capsys: Any) -> None:
    _arms(tmp_path, 6, lambda seed: {"acts": [0, 3, 3, 3, 1, 3, 3, 1]})  # inaction 1/8 against 4/8
    assert live.main(str(tmp_path)) == 2
    out = capsys.readouterr().out
    assert "CHANGED" in out and "**changed**" in out and "Holm across the 1 measures" in out


def test_more_fallbacks_fail_and_a_collapse_fails_even_with_too_few_seeds(tmp_path: Path, capsys: Any) -> None:
    _arms(tmp_path / "worse", 6, lambda seed: {"fallbacks": 5})
    assert live.main(str(tmp_path / "worse")) == 1 and "**worse**" in capsys.readouterr().out
    _arms(tmp_path / "collapse", 3, lambda seed: {"acts": [3] * 8})  # the motif-first order: inaction 0%
    out = live.main(str(tmp_path / "collapse")), capsys.readouterr().out
    assert out[0] == 1 and "**collapsed**" in out[1] and "FAIL" in out[1]


def test_too_few_seeds_give_no_verdict_and_an_incomplete_arm_none_either(tmp_path: Path, capsys: Any) -> None:
    _arms(tmp_path, 3, lambda seed: {"acts": [0, 3, 3, 3, 1, 3, 3, 1]})  # 2/8 at most: the smallest p is 2/8
    assert live.main(str(tmp_path)) == 1
    out = capsys.readouterr().out
    assert "no verdict: 3 paired seeds" in out and "Cannot tell: pressure 'nothing' share." in out
    _run_dir(tmp_path, "ctl", 4, acts=[0], shifts=[], fallbacks=0, retried=0, outcome="crashed")
    assert live.main(str(tmp_path)) == 1 and "incomplete arms: ctl" in capsys.readouterr().out


def test_no_verdict_while_a_behaviour_measure_is_untested_even_if_the_failures_were(tmp_path: Path, capsys: Any) -> None:
    base = {"acts": [0, 0, 0, 0, 3, 3, 3, 1], "shifts": [-1, 4], "fallbacks": 0}
    for seed in range(1, 7):
        odd = seed % 2 == 1
        _run_dir(tmp_path, "ctl", seed, **base, retried=1 if odd else 0)
        # retries: one more or one fewer in turn, testable (1/64) and not higher; inaction moves in 4 seeds only
        acts = [0, 0, 0, 0 if odd else 3, 0 if odd else 3, 3, 3, 1] if seed <= 4 else base["acts"]
        _run_dir(tmp_path, "new", seed, **{**base, "acts": acts}, retried=0 if odd else 1)
    assert live.main(str(tmp_path)) == 1
    out = capsys.readouterr().out
    assert "| retry rate |" in out and "(one-sided) | no difference |" in out
    assert "no verdict: 6 paired seeds are too few to test every behaviour measure" in out and "PASS" not in out


def test_a_decision_that_vanishes_under_the_candidate_is_a_collapse(tmp_path: Path, capsys: Any) -> None:
    _arms(tmp_path, 2, lambda seed: {"acts": []})  # no pressure action at all
    assert live.main(str(tmp_path)) == 1 and "**collapsed**" in capsys.readouterr().out
    assert live._diff(None, 0.5) == 0.0 and live._diff(0.25, 0.5) == 0.25


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
