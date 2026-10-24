"""plan-scenarios-v1 step 6: the catalogue's Latin hypercube, its configs and its PRIM boxes."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from api.domain.polity.catalogue import DIMENSIONS, Dimension, apply_point, prim, sample
from api.domain.polity.config import validate_config

N = 200


# ── the sample ────────────────────────────────────────────────────────────

def test_every_range_has_one_point_in_each_stratum_and_every_level_comes_up_equally_often() -> None:
    points = sample(N, seed=3)
    assert len(points) == N
    for dim in DIMENSIONS:
        values = [p[dim.name] for p in points]
        if dim.categorical:
            counts = {level: values.count(level) for level in dim.levels}
            assert set(counts) == set(dim.levels) and max(counts.values()) - min(counts.values()) <= 2
        else:
            strata = np.floor((np.array(values, dtype=float) - dim.low) / (dim.high - dim.low) * N).astype(int)
            assert sorted(strata.tolist()) == list(range(N))  # a Latin hypercube: one per stratum


def test_the_same_seed_gives_the_same_points_and_another_seed_other_ones() -> None:
    assert sample(20, seed=1) == sample(20, seed=1) != sample(20, seed=2)


def test_a_point_sets_every_dimension_in_the_config_and_the_result_is_valid(flagship: Any, tmp_path: Path) -> None:
    base = flagship._flagship_config(
        engine="deterministic", years=3, population=40, seats=6, seed=1, output_dir=tmp_path, max_batch_replays=0, provider=None, workers=1,
        profile="scenario",
    )
    point = {dim.name: (dim.levels[-1] if dim.categorical else dim.high) for dim in DIMENSIONS}
    config = apply_point(base, point)
    assert config.institutions.presidential_method == DIMENSIONS[0].levels[-1]
    assert config.institutions.electoral_threshold == 0.10 and config.legitimacy.recall_floor == 0.4
    assert config.petition.signature_threshold == 0.40 and config.events.scandal_rate_per_tick == 0.15
    assert config.events.economy_ar1_sigma == 0.30 and config.constitution.amendment_threshold == 0.9
    assert config.citizens.ambition_dist == "beta(1,1)" and config.institutions.seat_allocation == "largest_remainder"
    assert base.institutions.electoral_threshold != 0.10  # the base is not changed
    validate_config(config)  # the extremes of every range are legal


# ── PRIM ──────────────────────────────────────────────────────────────────

_TWO = (Dimension("x", "a.x", 0.0, 1.0), Dimension("noise", "a.noise", 0.0, 1.0), Dimension("kind", "a.kind", levels=("a", "b", "c")))


def _rows(n: int = 600) -> list[dict[str, Any]]:
    rng = np.random.default_rng(0)
    return [{"x": float(rng.random()), "noise": float(rng.random()), "kind": str(rng.choice(["a", "b", "c"]))} for _ in range(n)]


def test_prim_finds_the_box_that_makes_the_target_and_leaves_an_irrelevant_dimension_alone() -> None:
    rows = _rows()
    target = [r["x"] > 0.7 and r["kind"] == "a" for r in rows]
    box = prim(rows, target, _TWO, alpha=0.1, min_support=0.03)
    assert box is not None
    assert box.density > 0.85 and box.coverage > 0.6  # most of the class, almost nothing else
    assert "noise" not in box.restrictions  # the dimension that does nothing is not cut
    assert box.restrictions["kind"] == ("a",) and box.restrictions["x"][0] > 0.6 and box.restrictions["x"][1] == float("inf")  # open above
    assert box.support >= 0.03 and box.path[0] == (1.0, pytest.approx(sum(target) / len(target)))


def test_prim_with_no_target_or_nothing_to_peel_returns_none() -> None:
    rows = _rows(50)
    assert prim(rows, [False] * 50, _TWO) is None  # no positives
    assert prim([], [], _TWO) is None
    assert prim(rows, [True] * 50, _TWO) is None  # everything is the target: no peel improves on the whole


def test_the_box_never_holds_less_than_the_support_asked() -> None:
    rows = _rows()
    box = prim(rows, [r["x"] > 0.9 for r in rows], _TWO, alpha=0.2, min_support=0.25)
    assert box is not None and box.support >= 0.25


def test_prim_stops_when_no_cut_can_take_a_point_out() -> None:
    same = [{"x": 0.5, "noise": 0.5, "kind": "a"}] * 10
    assert prim(same, [True] * 5 + [False] * 5, _TWO, min_support=0.01) is None  # nothing separates them


# ── one point through the runner ──────────────────────────────────────────

@pytest.fixture(scope="module")
def runner(flagship: Any) -> Any:
    script = Path(__file__).resolve().parents[2] / "scripts" / "run_polity_catalogue.py"
    spec = importlib.util.spec_from_file_location("run_polity_catalogue", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_polity_catalogue"] = module
    spec.loader.exec_module(module)
    return module


def test_a_point_runs_into_a_row_and_leaves_no_run_directory(runner: Any, tmp_path: Path) -> None:
    point = sample(1, seed=1)[0]
    row = runner.run_point((7, point, 5, 3, 40, str(tmp_path)))
    assert "error" not in row, row.get("trace")
    assert row["index"] == 7 and row["point"] == point and row["archetype"]
    from api.domain.polity.trajectory import PLAUSIBILITY_BAND

    assert set(row["failed"]) <= set(PLAUSIBILITY_BAND)  # only checks the digest knows
    assert row["max_shift"] >= 0.0 and row["max_rel_shift"] >= 0.0 and row["max_volatility"] >= 0.0
    assert not (tmp_path / "runs" / "7").exists()


def test_a_point_that_cannot_run_is_a_row_with_its_error_not_a_crash(runner: Any, tmp_path: Path) -> None:
    point = dict(sample(1, seed=1)[0], method="star")  # needs a cardinal ballot the rule path does not build
    row = runner.run_point((0, point, 1, 3, 40, str(tmp_path)))
    assert "NotImplementedError" in row["error"] and "archetype" not in row


def test_the_report_counts_archetypes_and_reads_a_box_only_for_the_frequent_ones(runner: Any, tmp_path: Path) -> None:
    import argparse
    import json

    rng = np.random.default_rng(1)
    rows = []
    for i in range(80):
        high = float(rng.random())
        point = {d.name: (d.levels[0] if d.categorical else d.low) for d in DIMENSIONS} | {"polarization_pressure": high}
        archetype = "realignment" if high > 0.5 else ("churn" if i % 20 == 0 else "stasis")
        rows.append({"index": i, "seed": i, "point": point, "archetype": archetype, "failed": [] if i % 2 else ["turnout"]})
    rows.append({"index": 99, "seed": 99, "point": rows[0]["point"], "error": "ValueError: boom"})
    (tmp_path / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert runner.report(argparse.Namespace(out=tmp_path)) == 0
    text = (tmp_path / "report.md").read_text()
    assert "81 runs (80 read, 1 errored)" in text and "ValueError: boom" in text
    assert "realignment" in text and "polarization_pressure" in text  # the box that explains it
    assert "Inside the plausibility band there are 40 runs, under 60" in text
    assert runner.report(argparse.Namespace(out=tmp_path / "missing")) == 1  # nothing to read


def test_prim_does_not_take_a_box_of_a_few_lucky_points() -> None:
    rows = _rows(400)
    rare = [i in (3, 90, 200) for i in range(400)]  # three target points scattered at random
    box = prim(rows, rare, _TWO, alpha=0.1, min_support=0.05, min_hits=3)
    assert box is None or box.coverage == pytest.approx(1.0)  # a box has all three, or there is none


def test_resume_runs_an_errored_point_again_and_refuses_other_settings(runner: Any, tmp_path: Path) -> None:
    import argparse
    import json

    args = argparse.Namespace(out=tmp_path, runs=2, seed=1, years=2, population=30, workers=2)
    (tmp_path / "rows.jsonl").write_text(json.dumps({"index": 0, "seed": 1, "point": {}, "error": "OSError: disk full"}) + "\n")
    (tmp_path / "settings.json").write_text(json.dumps({"runs": 2, "seed": 1, "years": 2, "population": 30}))
    assert runner.run(args) == 0  # point 0 errored before: it is run again, with point 1
    rows = runner.load_rows(tmp_path)
    assert [r["index"] for r in rows] == [0, 1] and all("error" not in r for r in rows)
    assert runner.run(argparse.Namespace(out=tmp_path, runs=2, seed=1, years=5, population=30, workers=2)) == 2  # other settings: refused


def test_the_runner_wants_a_positive_number_of_workers(runner: Any) -> None:
    with pytest.raises(SystemExit):
        runner.main(["report", "--out", "/nonexistent", "--workers", "0"])
