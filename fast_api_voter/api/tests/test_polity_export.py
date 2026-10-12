"""Polity's run explorer on the static site (W6, step 4): scripts/export_polity_runs.py writes
the explorer's answers ahead, and voter-app/src/api/staticPolity.ts serves them. The export
must answer as the server does, and the committed one (voter-app/polity-export/, made from
runs on the owner's disk) must still fit today's response schemas, or the page breaks."""
from __future__ import annotations

import gzip
import importlib.util
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from api.core.config import get_settings
from api.routes import polity as polity_routes
from api.schemas.polity import PolityCitizen, PolityFrames, PolityRunList, PolityRunOverview

REPO = Path(__file__).resolve().parents[3]
COMMITTED = REPO / "voter-app" / "polity-export"


@pytest.fixture(autouse=True)
def _fixture_roots(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The server serves the fixture run too, whatever the shell's POLITY_RUN_ROOTS."""
    monkeypatch.delenv("POLITY_RUN_ROOTS", raising=False)
    get_settings.cache_clear()
    polity_routes._cache.cache_clear()
    yield
    get_settings.cache_clear()
    polity_routes._cache.cache_clear()


def _export_script() -> Any:
    spec = importlib.util.spec_from_file_location("export_polity_runs", REPO / "fast_api_voter" / "scripts" / "export_polity_runs.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read(path: Path) -> Any:
    return json.loads(gzip.decompress(path.read_bytes()))


def _citizens(run_dir: Path) -> dict[str, Any]:
    citizens: dict[str, Any] = {}
    for path in run_dir.glob("citizens-*.json.gz"):
        citizens.update(_read(path))
    return citizens


def test_the_export_answers_as_the_server_does(client, tmp_path):
    """The committed fixture run (POLITY_RUN_ROOTS unset), exported, against its routes."""
    keys = _export_script().export(tmp_path, "")
    assert keys
    assert json.loads((tmp_path / "runs.json").read_text()) == client.get("/api/v2/polity/runs").json()
    for key in keys:
        base = f"/api/v2/polity/runs/{key}"
        run = _read(tmp_path / key / "run.json.gz")
        assert run["overview"] == client.get(base).json()
        last = run["overview"]["last_tick"]
        assert run["frames"]
        for span, frames in run["frames"].items():
            start, end = span.split("-")
            assert frames == client.get(f"{base}/frames", params={"from_tick": start, "to_tick": end}).json()
        # Every tick is in one chunk, as the page cuts them (lib/polity/ticks.ts).
        assert [t for frames in run["frames"].values() for t in range(frames["from_tick"], frames["to_tick"] + 1)] == list(range(last + 1))
        citizens = _citizens(tmp_path / key)
        population = run["overview"]["population"]
        assert sorted(citizens, key=int) == [str(i) for i in range(population)]
        for i in range(population):
            assert citizens[str(i)] == client.get(f"{base}/citizens/{i}").json()
        assert client.get(f"{base}/citizens/{population}").status_code == 404


def test_a_new_export_replaces_the_old_runs_folders(tmp_path):
    stale = tmp_path / "0123456789abcdef"
    stale.mkdir(parents=True)
    (stale / "citizens-9.json.gz").write_bytes(b"old")
    keys = _export_script().export(tmp_path, "")
    assert not stale.exists()
    assert sorted(p.name for p in tmp_path.iterdir() if p.is_dir()) == keys


def test_a_file_over_the_repo_limit_stops_the_export_before_it_writes(tmp_path, monkeypatch):
    script = _export_script()
    monkeypatch.setattr(script, "MAX_FILE_BYTES", 100)
    with pytest.raises(SystemExit, match="over the repo's 500 KB"):
        script.export(tmp_path / "out", "")
    assert not (tmp_path / "out").exists()


def test_the_committed_export_fits_todays_schemas():
    """Re-export when this fails (the module docstring of scripts/export_polity_runs.py)."""
    runs = PolityRunList.model_validate_json((COMMITTED / "runs.json").read_text())
    assert runs.runs
    for summary in runs.runs:
        run = _read(COMMITTED / summary.key / "run.json.gz")
        overview = PolityRunOverview.model_validate(run["overview"])
        for frames in run["frames"].values():
            PolityFrames.model_validate(frames)
        citizens = _citizens(COMMITTED / summary.key)
        assert len(citizens) == overview.population
        for citizen in citizens.values():
            PolityCitizen.model_validate(citizen)
