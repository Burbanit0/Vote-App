"""GET /api/v2/polity/* — the run explorer's routes, against the committed fixture run
and against configured run roots."""
from __future__ import annotations

import asyncio
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.core.config import get_settings
from api.domain.polity.run_catalog import DEFAULT_RUN_ROOT, run_key
from api.main import fastapi_app
from api.routes import polity as polity_routes

FIXTURE_KEY = run_key("fixture", "explorer-fixture")
BASE = "/api/v2/polity"


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("POLITY_RUN_ROOTS", raising=False)
    get_settings.cache_clear()
    polity_routes._cache.cache_clear()
    yield
    get_settings.cache_clear()
    polity_routes._cache.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(fastapi_app)


def _ok(client: TestClient, path: str) -> Any:
    response = client.get(path)
    assert response.status_code == 200, response.text
    assert all(leak not in response.text for leak in (str(Path.home()), tempfile.gettempdir(), str(DEFAULT_RUN_ROOT)))
    return response.json()


def test_without_configured_roots_the_fixture_run_is_the_one_listed(client: TestClient) -> None:
    [run] = _ok(client, f"{BASE}/runs")["runs"]
    assert (run["key"], run["label"], run["relative_path"], run["run_id"]) == (FIXTURE_KEY, "fixture", "explorer-fixture", "explorer-fixture")
    assert (run["engine"], run["population"], run["years"], run["ticks_planned"]) == ("llm", 40, 3, 12)


def test_the_overview_carries_the_map_and_the_institutional_story(client: TestClient) -> None:
    overview = _ok(client, f"{BASE}/runs/{FIXTURE_KEY}")
    assert (overview["population"], overview["ticks_per_year"], overview["last_tick"], overview["vote_coverage"]) == (40, 4, 12, "all")
    projection = overview["projection"]
    assert projection["method"] == "latent" and len(projection["axes"]) == 2
    assert [len(census["xy"]) for census in projection["citizens"]] == [40]
    assert len(overview["citizen_parties"]) == 40 and {p["party_id"] for p in overview["parties"]} == set(overview["citizen_parties"])
    assert len(overview["standings"]) == 13 and [e["outcome"] for e in overview["elections"]] == ["elected"] * 3
    assert {t["ended_by"] for t in overview["terms"]} >= {"legitimacy_floor"}
    assert any(entry["event_type"] == "recalled" for entry in overview["timeline"])
    assert {"code": 105, "label": "ACCEPTABLE_MATCH"} in overview["motifs"]


def test_frames_come_in_chunks_of_at_most_forty_ticks(client: TestClient) -> None:
    whole = _ok(client, f"{BASE}/runs/{FIXTURE_KEY}/frames")
    assert (whole["from_tick"], whole["to_tick"], len(whole["frames"])) == (0, 12, 13)
    frame = whole["frames"][0]
    assert len(frame["status"]) == len(frame["act"]) == len(frame["vote"]) == len(frame["candidacy"]) == len(frame["chamber"]) == 40
    assert frame["president"]["citizen_id"] == 2 and len(frame["president"]["xy"]) == 2
    assert 2 in frame["status"] and 1 in frame["vote"]

    part = _ok(client, f"{BASE}/runs/{FIXTURE_KEY}/frames?from_tick=9&to_tick=30")
    assert (part["from_tick"], part["to_tick"], [f["tick"] for f in part["frames"]]) == (9, 12, [9, 10, 11, 12])
    assert part["frames"][0]["president"] is None  # recalled at tick 9

    for query, message in [("from_tick=0&to_tick=40", "at most 40 ticks per request"),
                           ("from_tick=5&to_tick=4", "to_tick is before from_tick"),
                           ("from_tick=13", "from_tick 13 is past the run's last tick, 12")]:
        response = client.get(f"{BASE}/runs/{FIXTURE_KEY}/frames?{query}")
        assert (response.status_code, response.json()) == (400, {"detail": message})


def test_a_citizen_biography_is_served_and_an_unknown_citizen_is_not(client: TestClient) -> None:
    biography = _ok(client, f"{BASE}/runs/{FIXTURE_KEY}/citizens/2")
    assert biography["citizen_id"] == 2 and any(e["event_type"] == "elected" for e in biography["sections"]["roles"])
    assert biography["received"] and [c["year"] for c in biography["census"]] == [0, 1, 2, 3]
    response = client.get(f"{BASE}/runs/{FIXTURE_KEY}/citizens/40")
    assert (response.status_code, response.json()) == (404, {"detail": "citizen not found"})


def test_an_unknown_or_malformed_run_key_is_refused(client: TestClient) -> None:
    for path in ("", "/frames", "/citizens/0"):
        response = client.get(f"{BASE}/runs/0123456789abcdef{path}")
        assert (response.status_code, response.json()) == (404, {"detail": "run not found"})
    assert client.get(f"{BASE}/runs/not-a-run-key").status_code == 422
    assert client.get(f"{BASE}/runs/..%2F..%2Fetc").status_code in (404, 422)


def test_configured_roots_replace_the_fixture_and_an_unexplorable_run_is_a_400(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    shutil.copytree(DEFAULT_RUN_ROOT / "explorer-fixture", tmp_path / "batch" / "good")
    broken = Path(shutil.copytree(DEFAULT_RUN_ROOT / "explorer-fixture", tmp_path / "batch" / "broken"))
    lines = (broken / "snapshots.jsonl").read_text().splitlines(keepends=True)
    (broken / "snapshots.jsonl").write_text("".join(lines[:10]))
    monkeypatch.setenv("POLITY_RUN_ROOTS", f"lab={tmp_path}")
    get_settings.cache_clear()

    keys = {run["relative_path"]: run["key"] for run in _ok(client, f"{BASE}/runs")["runs"]}
    assert keys == {"batch/broken": run_key("lab", "batch/broken"), "batch/good": run_key("lab", "batch/good")}
    assert _ok(client, f"{BASE}/runs/{keys['batch/good']}")["run_id"] == "explorer-fixture"
    response = client.get(f"{BASE}/runs/{keys['batch/broken']}")
    assert (response.status_code, response.json()) == (400, {"detail": "run cannot be explored: no complete year-0 census"})
    assert client.get(f"{BASE}/runs/{FIXTURE_KEY}").status_code == 404

    (tmp_path / "batch" / "good" / "checkpoint.json").unlink()  # a run killed before its first checkpoint
    get_settings.cache_clear()
    polity_routes._cache.cache_clear()
    assert _ok(client, f"{BASE}/runs/{keys['batch/good']}")["parties"] == []


def test_a_worker_that_runs_too_long_is_a_503(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def too_slow(*args: Any, **kwargs: Any) -> Any:
        raise asyncio.TimeoutError

    monkeypatch.setattr(polity_routes, "run_bounded", too_slow)
    response = client.get(f"{BASE}/runs")
    assert (response.status_code, response.json()) == (503, {"detail": "Request took too long to process"})
