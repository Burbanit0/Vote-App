"""Run provenance (S0.4): run_metadata.json records what a run ran under.
See api/domain/polity/run_provenance.py."""
from __future__ import annotations

import dataclasses
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import httpx
import pytest

from api.domain.polity import run_provenance
from api.domain.polity.config import PolityConfig, load_config
from api.domain.polity.run_polity_simulation import run_simulation
from api.tests.polity_golden import golden_config
from api.tests.test_polity_run_simulation import _config_with_llm_enabled, _config_with_output_dir, _FakeLlmClient

# The command line of the real vllm-polity container, from `docker inspect` (2026-09-13).
_VLLM_CONTAINER_CMD = [
    "--model", "Qwen/Qwen3-8B-AWQ", "--revision", "4da05a8edb55c6046cce958586c33b61da07bb79",
    "--quantization", "awq_marlin", "--served-model-name", "qwen3:8b", "--reasoning-parser", "qwen3",
    "--max-model-len", "16384", "--port", "8000", "--seed", "42",
]

_LLM_ONLY_FIELDS = (
    "llm_provider", "llm_base_url", "llm_model", "llm_client_injected", "prompt_source_sha256", "model_profile",
    "gpu_driver_version", "gpu_cuda_version", *run_provenance.SERVER_FIELDS,
)

_EVERY_FIELD = {
    "run_id", "started_at", "resumes", "llm_enabled", *_LLM_ONLY_FIELDS,
    "git_sha", "git_branch", "git_dirty", "git_dirty_paths",
    "engine", "seed", "duration_years", "ticks_per_year", "total_ticks", "population_size",
    "assembly_seats", "sortition_seats", "config_hash", "config_overrides",
}


def _metadata(journal_path: Path) -> dict[str, Any]:
    return dict(json.loads((journal_path.parent / "run_metadata.json").read_text(encoding="utf-8")))


def _one_year_population_30(output_dir: Path) -> PolityConfig:
    config = _config_with_output_dir(output_dir)
    return dataclasses.replace(config, run=dataclasses.replace(config.run, duration_years=1, population_size=30))


def test_a_deterministic_run_records_every_field_with_llm_fields_null(tmp_path: Path) -> None:
    config = _one_year_population_30(tmp_path)
    metadata = _metadata(run_simulation(config, run_id="prov"))

    assert set(metadata) == _EVERY_FIELD
    assert metadata["engine"] == "deterministic"
    assert {field: metadata[field] for field in _LLM_ONLY_FIELDS} == dict.fromkeys(_LLM_ONLY_FIELDS)
    assert (metadata["seed"], metadata["duration_years"], metadata["population_size"]) == (config.run.seed, 1, 30)
    assert metadata["total_ticks"] == config.run.ticks_per_year
    assert metadata["sortition_seats"] is None  # the chamber ships disabled
    assert metadata["config_overrides"]["run.population_size"] == 30
    assert metadata["resumes"] == []
    assert metadata["started_at"]


def test_the_git_fields_describe_this_checkout(tmp_path: Path) -> None:
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    metadata = _metadata(run_simulation(_one_year_population_30(tmp_path), run_id="git"))
    assert metadata["git_sha"] == head
    assert isinstance(metadata["git_dirty"], bool)
    assert metadata["git_dirty"] == bool(metadata["git_dirty_paths"])


def test_git_provenance_lists_dirty_paths_and_degrades_to_null_without_git(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = {
        "rev-parse HEAD": "3593e65b4edf7828c9d5c555ed302593c3f9da31\n",
        "rev-parse --abbrev-ref HEAD": "feat/x\n",
        "status --porcelain -- .": " M fast_api_voter/api/domain/polity/config.py\n?? fast_api_voter/new.py\n",
    }
    monkeypatch.setattr(run_provenance, "_run_command", lambda args, cwd=None: answers.get(" ".join(args[1:])))
    assert run_provenance.git_provenance.__wrapped__() == {
        "git_sha": "3593e65b4edf7828c9d5c555ed302593c3f9da31",
        "git_branch": "feat/x",
        "git_dirty": True,
        "git_dirty_paths": ["fast_api_voter/api/domain/polity/config.py", "fast_api_voter/new.py"],
    }
    monkeypatch.setattr(run_provenance, "_run_command", lambda args, cwd=None: None)
    assert run_provenance.git_provenance.__wrapped__() == dict.fromkeys(
        ("git_sha", "git_branch", "git_dirty", "git_dirty_paths")
    )


def test_an_injected_client_is_named_and_no_server_is_probed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A fake or replay client never talks to the configured server, so recording
    # that server's weights would claim the run used them.
    def must_not_probe(base_url: str) -> dict[str, Any]:
        raise AssertionError(f"probed {base_url} for a run that never used it")

    monkeypatch.setattr(run_provenance, "vllm_server_provenance", must_not_probe)
    metadata = _metadata(run_simulation(_config_with_llm_enabled(tmp_path), run_id="fake", llm_client=_FakeLlmClient()))
    assert metadata["engine"] == "llm"
    assert metadata["llm_client_injected"] == "_FakeLlmClient"
    assert re.fullmatch(r"[0-9a-f]{64}", metadata["prompt_source_sha256"])
    assert metadata["model_profile"]["weights"] == "Qwen/Qwen3-8B-AWQ"
    assert metadata["model_profile"]["vote_cast_chunk_size"] == 3
    assert all(metadata[field] is None for field in run_provenance.SERVER_FIELDS)


def test_a_run_that_builds_its_own_vllm_client_records_the_server(monkeypatch: pytest.MonkeyPatch) -> None:
    config = load_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True, provider="vllm"))
    probed: list[str] = []
    monkeypatch.setattr(
        run_provenance, "vllm_server_provenance",
        lambda base_url: probed.append(base_url) or {**dict.fromkeys(run_provenance.SERVER_FIELDS), "vllm_version": "0.28.0"},
    )
    provenance = run_provenance.code_and_server_provenance(config, llm_client=None)
    assert probed == [config.llm.base_url]
    assert provenance["vllm_version"] == "0.28.0"
    assert provenance["llm_client_injected"] is None


class _FakeResponse:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._payload


def _fake_server(monkeypatch: pytest.MonkeyPatch, commands: list[list[str]]) -> None:
    pages = {
        "http://localhost:8000/version": {"version": "0.28.0"},
        "http://localhost:8000/v1/models": {"data": [{"id": "qwen3:8b", "root": "Qwen/Qwen3-8B-AWQ"}]},
    }
    monkeypatch.setattr(httpx, "get", lambda url, timeout: _FakeResponse(pages[url]))
    inspected = {"Image": "sha256:4f3c", "Config": {"Image": "vllm/vllm-openai:v0.28.0", "Cmd": _VLLM_CONTAINER_CMD}}

    def run_command(args: list[str], cwd: Path | None = None) -> str | None:
        commands.append(args)
        if args[:2] == ["docker", "ps"]:
            return "c0ffee\n"
        return json.dumps(inspected) if args[:2] == ["docker", "inspect"] else None

    monkeypatch.setattr(run_provenance, "_run_command", run_command)


def test_vllm_server_provenance_reads_the_server_and_the_container_serving_it(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []
    _fake_server(monkeypatch, commands)
    assert run_provenance.vllm_server_provenance("http://localhost:8000/v1") == {
        "vllm_version": "0.28.0",
        "vllm_image": "vllm/vllm-openai:v0.28.0",
        "vllm_image_id": "sha256:4f3c",
        "served_model_name": "qwen3:8b",
        "served_model_repo": "Qwen/Qwen3-8B-AWQ",
        "served_model_revision": "4da05a8edb55c6046cce958586c33b61da07bb79",
    }
    assert ["docker", "ps", "--filter", "publish=8000", "--format", "{{.ID}}"] in commands


def test_a_remote_server_is_asked_over_http_only(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []
    _fake_server(monkeypatch, commands)
    monkeypatch.setattr(
        httpx, "get", lambda url, timeout: _FakeResponse({"version": "0.28.0"} if url.endswith("/version") else {"data": []})
    )
    provenance = run_provenance.vllm_server_provenance("http://gpu-box:8000/v1")
    assert commands == []  # the local docker daemon does not run gpu-box's container
    assert provenance["vllm_version"] == "0.28.0"
    assert provenance["served_model_revision"] is None


@pytest.mark.parametrize(
    ("ps_output", "inspect_output"),
    [
        ("", None),  # no running container publishes the port
        ("c0ffee\nbadd06\n", None),  # two do: which one served the run is unknowable
        ("c0ffee\n", "not json"),
    ],
)
def test_container_fields_stay_null_when_the_container_cannot_be_identified(
    monkeypatch: pytest.MonkeyPatch, ps_output: str, inspect_output: str | None
) -> None:
    _fake_server(monkeypatch, [])
    monkeypatch.setattr(
        run_provenance, "_run_command",
        lambda args, cwd=None: ps_output if args[:2] == ["docker", "ps"] else inspect_output,
    )
    provenance = run_provenance.vllm_server_provenance("http://localhost:8000/v1")
    assert provenance["served_model_repo"] == "Qwen/Qwen3-8B-AWQ"  # still known from /v1/models
    assert (provenance["vllm_image"], provenance["vllm_image_id"], provenance["served_model_revision"]) == (None, None, None)


def test_a_server_launched_without_a_pinned_revision_records_the_revision_as_null(monkeypatch: pytest.MonkeyPatch) -> None:
    unpinned = {"Image": "sha256:4f3c", "Config": {"Image": "vllm/vllm-openai:v0.28.0", "Cmd": ["--model", "Qwen/Qwen3-8B-AWQ"]}}
    _fake_server(monkeypatch, [])
    monkeypatch.setattr(
        run_provenance, "_run_command",
        lambda args, cwd=None: "c0ffee\n" if args[:2] == ["docker", "ps"] else json.dumps(unpinned),
    )
    provenance = run_provenance.vllm_server_provenance("http://localhost:8000/v1")
    assert provenance["vllm_image"] == "vllm/vllm-openai:v0.28.0"
    assert provenance["served_model_revision"] is None  # whatever the hub served at launch: not reconstructible


def test_run_command_returns_null_for_a_missing_binary_or_a_failing_command(tmp_path: Path) -> None:
    assert run_provenance._run_command(["definitely-not-an-installed-binary-s04"]) is None
    assert run_provenance._run_command(["git", "rev-parse", "HEAD"], cwd=tmp_path) is None  # not a repository
    assert run_provenance._run_command(["git", "--version"]) is not None


def test_vllm_server_provenance_is_null_when_nothing_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(url: str, timeout: float) -> Any:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "get", refuse)
    monkeypatch.setattr(run_provenance, "_run_command", lambda args, cwd=None: None)
    assert run_provenance.vllm_server_provenance("http://localhost:8000/v1") == dict.fromkeys(
        run_provenance.SERVER_FIELDS
    )


def test_config_overrides_name_every_setting_changed_from_the_shipped_yaml(tmp_path: Path) -> None:
    assert run_provenance.config_overrides(load_config()) == {}
    overrides = run_provenance.config_overrides(golden_config(tmp_path, llm=True))
    assert overrides["events.scandal_rate_per_tick"] == 0.5
    assert overrides["sortition_chamber.enabled"] is True
    assert overrides["llm.enabled"] is True
    assert "llm.model" not in overrides  # unchanged settings stay out


def test_the_prompt_source_hash_moves_when_a_prompt_module_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in run_provenance.PROMPT_SOURCE_FILES:
        shutil.copy(Path(run_provenance.__file__).parent / name, tmp_path / name)
    monkeypatch.setattr(run_provenance, "_POLITY_DIR", tmp_path)
    before = run_provenance.prompt_source_sha256.__wrapped__()
    schemas = tmp_path / "llm_schemas.py"
    schemas.write_bytes(schemas.read_bytes() + b"\n")
    assert run_provenance.prompt_source_sha256.__wrapped__() != before


def test_a_resume_keeps_the_first_record_and_appends_what_it_ran_under(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _one_year_population_30(tmp_path)
    first = _metadata(run_simulation(config, run_id="resumed"))
    resumed_git = {"git_sha": "f" * 40, "git_branch": "fix/after-crash", "git_dirty": False, "git_dirty_paths": []}
    monkeypatch.setattr(run_provenance, "git_provenance", lambda: resumed_git)

    after = _metadata(run_simulation(config, run_id="resumed", resume=True))

    assert {k: v for k, v in after.items() if k != "resumes"} == {k: v for k, v in first.items() if k != "resumes"}
    assert len(after["resumes"]) == 1
    assert after["resumes"][0]["git_sha"] == "f" * 40
    assert after["resumes"][0]["resumed_at"] >= first["started_at"]


def test_the_resolved_config_is_written_beside_the_journal(tmp_path: Path) -> None:
    config = _one_year_population_30(tmp_path)
    config = dataclasses.replace(config, run=dataclasses.replace(config.run, seed=4321))
    written = json.loads((run_simulation(config, run_id="resolved").parent / "config.json").read_text(encoding="utf-8"))
    assert "raw" not in written
    assert written["run"]["seed"] == 4321  # the override, not the YAML on disk
    for section in ("legitimacy", "petition", "street_pressure", "awakening", "events", "social_graph", "llm"):
        assert "enabled" in written[section]
