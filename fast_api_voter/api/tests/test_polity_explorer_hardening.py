"""What the run explorer does with a run root it does not own.

A run root is a directory some batch wrote: files can be symlinks out of it, a config can
hold a word where a number belongs, a checkpoint can come from another engine version, and
one damaged run must not cost every other run its listing. Each test here pins one of
those, and the concurrency and staleness of the run cache alongside them.
"""
from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.core.config import get_settings
from api.domain.polity import run_catalog
from api.domain.polity.explorer_paths import inside
from api.domain.polity.run_catalog import (
    _LOADED_FILES,
    DEFAULT_RUN_ROOT,
    LoadedRun,
    RunCache,
    RunRoot,
    RunRootsError,
    list_runs,
    run_key,
)
from api.domain.polity.explorer_workers import ExplorerContext, polity_run_overview
from api.main import fastapi_app
from api.routes import polity as polity_routes

BASE = "/api/v2/polity"
FIXTURE = DEFAULT_RUN_ROOT / "explorer-fixture"
BIG = 64_000_000


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


def _root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *names: str) -> dict[str, Path]:
    """A run root holding a copy of the fixture run under each given name."""
    runs = {name: Path(shutil.copytree(FIXTURE, tmp_path / "root" / name)) for name in names}
    monkeypatch.setenv("POLITY_RUN_ROOTS", f"lab={tmp_path / 'root'}")
    get_settings.cache_clear()
    return runs


def _listed(client: TestClient, tmp_path: Path) -> dict[str, dict[str, Any]]:
    response = client.get(f"{BASE}/runs")
    assert response.status_code == 200, response.text
    assert str(tmp_path) not in response.text  # no absolute path, even for a run it refuses
    return {run["relative_path"]: run for run in response.json()["runs"]}


# ── A file that escapes its root ───────────────────────────────────────────────

@pytest.mark.parametrize("escaping", ["run_metadata.json", "checkpoint.json", "digest.json", "progress.json"])
def test_a_run_whose_file_symlinks_out_of_its_root_is_not_listed(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, escaping: str,
) -> None:
    outside = tmp_path / "outside" / "host.json"
    outside.parent.mkdir(parents=True)
    outside.write_text(json.dumps({"run_id": "LEAKED-FROM-OUTSIDE", "engine": "secret-engine", "seed": 13579}))
    runs = _root(tmp_path, monkeypatch, "escaping", "contained")

    target = runs["escaping"] / escaping
    target.unlink(missing_ok=True)
    target.symlink_to(outside)

    listed = _listed(client, tmp_path)
    assert set(listed) == {"contained"}  # the whole run is refused, not just that file
    assert "LEAKED-FROM-OUTSIDE" not in json.dumps(listed)
    key = run_key("lab", "escaping")
    assert client.get(f"{BASE}/runs/{key}").status_code == 404


def test_the_runners_outer_directory_is_not_read_when_it_sits_above_the_root(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`run_registry` reads `<batch>/config.json` and `<batch>/metrics.json` for a run in
    `<batch>/run/<id>`. With the root set to that `run` directory, the batch directory is
    outside it, so those two files are the runner's, not this root's, and go unread."""
    outer = tmp_path / "batch"
    shutil.copytree(FIXTURE, outer / "run" / "seed1")
    (outer / "metrics.json").write_text(json.dumps({"_meta": {"run_id": "OUTER-LEAK", "engine": "outer-engine"}}))
    monkeypatch.setenv("POLITY_RUN_ROOTS", f"lab={outer / 'run'}")
    get_settings.cache_clear()

    [run] = _listed(client, tmp_path).values()
    assert (run["relative_path"], run["run_id"]) == ("seed1", "explorer-fixture")
    assert run["engine"] == "llm" and "OUTER-LEAK" not in json.dumps(run)


def test_a_path_that_cannot_be_resolved_counts_as_outside(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolution itself can fail -- a name too long for the filesystem, a parent that
    denies traversal. What cannot be vouched for is refused, not raised at the caller."""
    assert inside(tmp_path / "events.jsonl", tmp_path) is True

    def refuses(self: Path, strict: bool = False) -> Path:
        raise OSError(40, "Too many levels of symbolic links")

    monkeypatch.setattr(Path, "resolve", refuses)
    assert inside(tmp_path / "events.jsonl", tmp_path) is False


def test_a_file_the_loader_reads_whole_is_refused_when_it_is_larger_than_the_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs = _root(tmp_path, monkeypatch, "fat", "lean")
    root = [RunRoot(label="lab", path=tmp_path / "root")]
    limit = max((runs["lean"] / name).stat().st_size for name in _LOADED_FILES)
    (runs["fat"] / "snapshots.jsonl").write_text("x" * (limit + 1))  # the census, not the journal

    assert {entry.relative_path for entry in list_runs(root, limit)} == {"lean"}
    assert {entry.relative_path for entry in list_runs(root, limit + 1)} == {"fat", "lean"}


def test_a_directory_where_a_read_file_belongs_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runs = _root(tmp_path, monkeypatch, "odd", "plain")
    (runs["odd"] / "digest.json").unlink(missing_ok=True)
    (runs["odd"] / "digest.json").mkdir()
    assert {e.relative_path for e in list_runs([RunRoot(label="lab", path=tmp_path / "root")], BIG)} == {"plain"}


# ── A run whose files are not the shape the replay expects ─────────────────────

@pytest.mark.parametrize(("mangle", "detail"), [
    (lambda config: config.pop("run"), "run cannot be explored: its files are not the shape the replay expects"),
    (lambda config: config["run"].update(population_size="forty"),
     "run cannot be explored: its files are not the shape the replay expects"),
])
def test_a_config_the_replay_cannot_read_is_a_400_not_a_500(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    mangle: Any, detail: str,
) -> None:
    runs = _root(tmp_path, monkeypatch, "mangled")
    config = json.loads((runs["mangled"] / "config.json").read_text())
    mangle(config)
    (runs["mangled"] / "config.json").write_text(json.dumps(config))

    response = client.get(f"{BASE}/runs/{run_key('lab', 'mangled')}")
    assert (response.status_code, response.json()) == (400, {"detail": detail})


def test_a_run_whose_files_cannot_be_read_is_a_400_not_a_500() -> None:
    class Unreadable(RunCache):
        def get(self, run_dir: Path) -> LoadedRun:
            raise PermissionError(13, "Permission denied")

    context = ExplorerContext(roots=(RunRoot(label="fixture", path=DEFAULT_RUN_ROOT),),
                              max_journal_bytes=BIG, cache=Unreadable(capacity=1))
    body, status = polity_run_overview(context, run_key("fixture", "explorer-fixture"))
    assert (status, body) == (400, {"error": "run cannot be explored: its files could not be read"})


def test_one_damaged_run_record_costs_only_that_run_its_shape(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs = _root(tmp_path, monkeypatch, "damaged", "sound")
    metadata = json.loads((runs["damaged"] / "run_metadata.json").read_text())
    metadata["population_size"] = "quarante"
    (runs["damaged"] / "run_metadata.json").write_text(json.dumps(metadata))
    (runs["damaged"] / "digest.json").write_text(json.dumps({"outcome": 5}))  # a number where a word belongs

    listed = _listed(client, tmp_path)
    assert set(listed) == {"damaged", "sound"}  # the listing still stands
    assert (listed["damaged"]["population"], listed["damaged"]["outcome"]) == (None, None)
    assert (listed["sound"]["population"], listed["sound"]["years"]) == (40, 3)


@pytest.mark.parametrize("checkpoint", [
    [{"party_id": 0}],                                   # a list where the state belongs
    {"parties": {"0": []}},                              # parties that are not a list
    {"parties": [{"party_id": 0}, 7]},                   # an entry without a platform, and one that is not one
    {"parties": [{"party_id": 0, "platform": "left"}]},  # a platform that is not numbers
])
def test_a_checkpoint_the_parties_cannot_be_read_from_leaves_the_run_openable(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, checkpoint: Any,
) -> None:
    runs = _root(tmp_path, monkeypatch, "odd")
    (runs["odd"] / "checkpoint.json").write_text(json.dumps(checkpoint))
    overview = client.get(f"{BASE}/runs/{run_key('lab', 'odd')}")
    assert overview.status_code == 200, overview.text
    assert overview.json()["parties"] == []


def test_a_party_platform_the_projection_cannot_place_is_left_off_the_map(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs = _root(tmp_path, monkeypatch, "future")
    checkpoint = json.loads((runs["future"] / "checkpoint.json").read_text())
    kept, unplaceable = checkpoint["parties"][0], dict(checkpoint["parties"][1])
    unplaceable["platform"] = [0.5] * (len(kept["platform"]) + 3)  # another engine version's issues
    checkpoint["parties"] = [kept, unplaceable]
    (runs["future"] / "checkpoint.json").write_text(json.dumps(checkpoint))

    overview = client.get(f"{BASE}/runs/{run_key('lab', 'future')}")
    assert overview.status_code == 200, overview.text
    assert [party["party_id"] for party in overview.json()["parties"]] == [kept["party_id"]]


# ── The run cache ─────────────────────────────────────────────────────────────

def test_a_cached_run_is_reloaded_when_any_file_it_was_read_from_changes(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs = _root(tmp_path, monkeypatch, "written")
    key = run_key("lab", "written")
    assert client.get(f"{BASE}/runs/{key}").json()["parties"]  # the first read fills the cache

    (runs["written"] / "checkpoint.json").unlink()  # the checkpoint goes, the journal does not
    assert client.get(f"{BASE}/runs/{key}").json()["parties"] == []


def test_concurrent_first_readers_of_a_run_wait_for_one_load(monkeypatch: pytest.MonkeyPatch) -> None:
    """Four requests land on a cold run at once (the page asks for the overview, two
    frame chunks and a citizen). A loaded p500 run is several times its journal
    resident, so they share one load instead of building four copies."""
    loads = 0
    first_load_started, release = Event(), Event()
    real_load = run_catalog.load_run

    def counted(run_dir: Path) -> LoadedRun:
        nonlocal loads
        loads += 1
        first_load_started.set()
        assert release.wait(timeout=10)
        return real_load(run_dir)

    monkeypatch.setattr(run_catalog, "load_run", counted)
    cache = RunCache(capacity=2)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(cache.get, FIXTURE) for _ in range(4)]
        assert first_load_started.wait(timeout=10)
        release.set()
        loaded = [future.result(timeout=30) for future in futures]

    assert loads == 1 and len({id(run) for run in loaded}) == 1 and len(cache) == 1


def test_a_run_evicted_from_the_cache_is_loaded_again(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    other = _root(tmp_path, monkeypatch, "other")["other"]
    cache = RunCache(capacity=1)

    first = cache.get(FIXTURE)
    assert cache.get(FIXTURE) is first  # a warm hit, not a second load
    cache.get(other)  # one slot, so the fixture is evicted
    assert len(cache) == 1
    assert cache.get(FIXTURE) is not first  # loaded again, not served from the evicted entry


def test_a_run_whose_file_vanishes_while_the_roots_are_read_is_only_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A run root is written by someone else. A file that goes between the existence
    check and the size check costs that run its place in the listing, not the listing."""
    runs = _root(tmp_path, monkeypatch, "racing", "settled")
    vanishing = runs["racing"] / "progress.json"
    real_stat = Path.stat

    def stat_once_then_vanish(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == vanishing:
            raise FileNotFoundError(2, "No such file or directory")
        return real_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat_once_then_vanish)
    assert {e.relative_path for e in list_runs([RunRoot(label="lab", path=tmp_path / "root")], BIG)} == {"settled"}


# ── The configured roots ──────────────────────────────────────────────────────

def test_a_malformed_run_roots_setting_stops_the_process_at_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLITY_RUN_ROOTS", "/srv/private/simulation-runs")  # no "label="
    get_settings.cache_clear()
    with pytest.raises(RunRootsError, match="is not label=path"):
        with TestClient(fastapi_app):  # entering the client runs the app's lifespan
            pass


def test_a_sound_run_roots_setting_starts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("POLITY_RUN_ROOTS", f"lab={tmp_path}")
    get_settings.cache_clear()
    with TestClient(fastapi_app) as started:
        assert started.get(f"{BASE}/runs").json() == {"runs": []}
