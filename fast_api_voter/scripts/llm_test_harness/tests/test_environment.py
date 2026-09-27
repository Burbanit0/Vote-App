from __future__ import annotations

import json
from collections.abc import Sequence

from llm_test_harness import environment


def _fake_runner(responses: dict[tuple[str, ...], str]) -> environment.CommandRunner:
    def runner(command: Sequence[str]) -> str:
        return responses.get(tuple(command), "")
    return runner


def test_capture_parses_all_fields_from_a_fake_runner():
    responses = {
        ("docker", "inspect", "--format", "{{.State.StartedAt}}", "ollama-polity"):
            "2026-08-19T11:45:29.262742763Z",
        ("docker", "logs", "--tail", "200", "ollama-polity"):
            "some log line\ncache state: 4 prompts\nanother line",
        ("nvidia-smi", "--query-gpu=utilization.gpu,memory.used,temperature.gpu",
         "--format=csv,noheader,nounits"): "12, 9717, 46",
        ("nvidia-smi", "--query-compute-apps=process_name", "--format=csv,noheader"):
            "ollama.exe\nbrave.exe",
        ("git", "rev-parse", "HEAD"): "abc123def456",
    }
    snap = environment.capture(
        "ollama-polity",
        inference_backend="ollama",
        inference_config={"OLLAMA_CONTEXT_LENGTH": "16384"},
        runner=_fake_runner(responses),
    )
    assert snap.container_name == "ollama-polity"
    assert snap.cached_prompts_count == 4
    assert snap.gpu_utilization_percent == 12.0
    assert snap.gpu_memory_used_mib == 9717.0
    assert snap.gpu_temperature_c == 46.0
    assert snap.concurrent_processes == ("ollama.exe", "brave.exe")
    assert snap.git_commit == "abc123def456"
    assert snap.inference_backend == "ollama"
    assert snap.inference_config == {"OLLAMA_CONTEXT_LENGTH": "16384"}
    assert snap.container_uptime_seconds is not None
    assert snap.container_uptime_seconds > 0


def test_capture_degrades_gracefully_when_every_command_fails():
    snap = environment.capture("missing-container", runner=lambda cmd: "")
    assert snap.container_uptime_seconds is None
    assert snap.cached_prompts_count is None
    assert snap.gpu_utilization_percent is None
    assert snap.gpu_memory_used_mib is None
    assert snap.gpu_temperature_c is None
    assert snap.concurrent_processes == ()
    assert snap.git_commit == "unknown"


def test_capture_never_raises_on_malformed_runner_output():
    snap = environment.capture("x", runner=lambda cmd: "not,even,close,to,valid,csv,data")
    assert snap.gpu_utilization_percent is None


def test_parse_cached_prompts_takes_the_most_recent_line():
    logs = "cache state: 2 prompts\nsome noise\ncache state: 7 prompts"
    assert environment._parse_cached_prompts(logs) == 7


def test_parse_cached_prompts_none_when_absent():
    assert environment._parse_cached_prompts("nothing relevant here") is None


def test_environment_snapshot_to_json_round_trips_the_fields():
    snap = environment.capture("x", runner=lambda cmd: "")
    payload = json.loads(snap.to_json())
    assert payload["container_name"] == "x"
    assert payload["git_commit"] == "unknown"


def test_real_runner_never_raises_on_a_nonexistent_command():
    # exercises the actual subprocess path (no mock) against a command
    # that cannot exist, proving the "never fatal" contract holds for real
    # subprocess failures too, not just for a fake runner returning "".
    result = environment._real_runner(["this-command-does-not-exist-anywhere", "--flag"])
    assert result == ""
