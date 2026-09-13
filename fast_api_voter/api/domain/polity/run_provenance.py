"""What a run ran under: the code, the prompt source, the inference server and
weights, and the run's shape. Written beside the journal as `run_metadata.json`,
never into it -- the journal's bytes are what reproducibility is asserted over.

The journal says what happened; this says under what, so two runs can be told
apart or matched without the terminal they ran in. Every probe is best-effort:
describing a run must never abort it, so a probe that cannot answer records null,
and a field that does not apply to this run (anything LLM-side on a deterministic
run) is null rather than absent, so a reader never has to guess which it is.

Server fields describe the server the run actually talked to (vLLM's own `/version`
and `/v1/models`, the running container's own command line), not the compose file's
pin -- a pin only says what should be running.
"""
from __future__ import annotations

import dataclasses
import functools
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from api.domain.polity.config import PolityConfig, load_config

_POLITY_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _POLITY_DIR.parents[2]

# Every module whose source can change a prompt's bytes or the schema sent with it.
PROMPT_SOURCE_FILES = ("llm_behavior_engine.py", "codebook.py", "llm_schemas.py", "llm_toon_encoding.py")

_PROBE_TIMEOUT_SECONDS = 5.0
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}

SERVER_FIELDS = (
    "vllm_version", "vllm_image", "vllm_image_id", "served_model_name", "served_model_repo", "served_model_revision",
)


def _run_command(args: list[str], cwd: Path | None = None) -> str | None:
    try:
        completed = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=_PROBE_TIMEOUT_SECONDS, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout if completed.returncode == 0 else None


@functools.lru_cache(maxsize=1)
def git_provenance() -> dict[str, Any]:
    """Commit, branch, and the paths under fast_api_voter/ that differ from it.

    Scoped to fast_api_voter/ because the commit-capture hook stages
    docs/journal/commits.jsonl after every commit: a repo-wide flag would read
    dirty on every run and say nothing. Cached per process: a process runs the
    modules it imported, so re-asking git between runs of a batch would describe
    edits the process never loaded."""
    sha = _run_command(["git", "rev-parse", "HEAD"], cwd=_BACKEND_DIR)
    branch = _run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=_BACKEND_DIR)
    status = _run_command(["git", "status", "--porcelain", "--", "."], cwd=_BACKEND_DIR)
    dirty_paths = None if status is None else sorted(line[3:] for line in status.splitlines() if line.strip())
    return {
        "git_sha": sha.strip() if sha else None,
        "git_branch": branch.strip() if branch else None,
        "git_dirty": None if dirty_paths is None else bool(dirty_paths),
        "git_dirty_paths": dirty_paths,
    }


@functools.lru_cache(maxsize=1)
def prompt_source_sha256() -> str:
    digest = hashlib.sha256()
    for name in PROMPT_SOURCE_FILES:
        digest.update(name.encode("utf-8") + b"\0" + (_POLITY_DIR / name).read_bytes() + b"\0")
    return digest.hexdigest()


def _get_json(url: str) -> Any:
    try:
        response = httpx.get(url, timeout=_PROBE_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError):
        return None


def _flag_value(command: list[str], flag: str) -> str | None:
    if flag in command and command.index(flag) + 1 < len(command):
        return command[command.index(flag) + 1]
    return None


def _container_provenance(port: int) -> dict[str, Any]:
    """The image and weights of the one running container publishing `port`."""
    ids = (_run_command(["docker", "ps", "--filter", f"publish={port}", "--format", "{{.ID}}"]) or "").split()
    if len(ids) != 1:
        return {}
    raw = _run_command(["docker", "inspect", ids[0], "--format", "{{json .}}"])
    try:
        inspected = json.loads(raw) if raw else {}
    except ValueError:
        return {}
    command = [str(token) for token in (inspected.get("Config") or {}).get("Cmd") or []]
    return {
        "vllm_image": (inspected.get("Config") or {}).get("Image"),
        "vllm_image_id": inspected.get("Image"),
        "served_model_repo": _flag_value(command, "--model"),
        "served_model_revision": _flag_value(command, "--revision"),
    }


def vllm_server_provenance(base_url: str) -> dict[str, Any]:
    """Asks the server itself, then the local container serving it. The model
    repo falls back to `/v1/models`' `root` (the `--model` vLLM was launched
    with) when docker cannot be asked; the revision has no HTTP source."""
    fields: dict[str, Any] = dict.fromkeys(SERVER_FIELDS)
    api_root = base_url.rstrip("/")
    version = _get_json(f"{api_root.removesuffix('/v1')}/version")
    fields["vllm_version"] = version.get("version") if isinstance(version, dict) else None
    models = _get_json(f"{api_root}/models")
    served = (models.get("data") or [{}])[0] if isinstance(models, dict) else {}
    fields["served_model_name"] = served.get("id")
    fields["served_model_repo"] = served.get("root")
    parsed = urlsplit(api_root)
    if parsed.hostname in _LOCAL_HOSTS and parsed.port is not None:
        fields.update({k: v for k, v in _container_provenance(parsed.port).items() if v is not None})
    return fields


def typed_config_mapping(config: PolityConfig) -> dict[str, Any]:
    """The config as plain data, minus `raw`: `raw` is the YAML before overrides,
    so keeping it would put two disagreeing answers in one file. (First written
    on feat/polity-live-ui, 5d713eff.)"""
    return {
        field.name: dataclasses.asdict(getattr(config, field.name))
        for field in dataclasses.fields(config)
        if field.name != "raw"
    }


def _flatten(mapping: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in mapping.items():
        path = f"{prefix}{key}"
        flat.update(_flatten(value, f"{path}.") if isinstance(value, dict) else {path: value})
    return flat


@functools.lru_cache(maxsize=1)
def _shipped_config_flat() -> dict[str, Any]:
    return _flatten(typed_config_mapping(load_config()))


def config_overrides(config: PolityConfig) -> dict[str, Any]:
    """Every setting that differs from the shipped polity_config.yaml, by dotted
    path -- the run's override flags, readable without diffing two configs."""
    shipped = _shipped_config_flat()
    missing = object()
    return {
        path: value
        for path, value in sorted(_flatten(typed_config_mapping(config)).items())
        if shipped.get(path, missing) != value
    }


def run_shape(config: PolityConfig) -> dict[str, Any]:
    return {
        "engine": "llm" if config.llm.enabled else "deterministic",
        "seed": config.run.seed,
        "duration_years": config.run.duration_years,
        "ticks_per_year": config.run.ticks_per_year,
        "total_ticks": config.run.total_ticks,
        "population_size": config.run.population_size,
        "assembly_seats": config.institutions.assembly_seats,
        "sortition_seats": config.sortition_chamber.seats if config.sortition_chamber.enabled else None,
    }


def code_and_server_provenance(config: PolityConfig, *, llm_client: object | None) -> dict[str, Any]:
    """The part of the record that can change between a run and its resume.

    The server is probed only when the run builds its own client from config: an
    injected client (a test fake, a replay) never talks to that server, and
    recording it would claim the run used weights it never saw."""
    llm = config.llm.enabled
    probe_server = llm and llm_client is None and config.llm.provider == "vllm"
    return {
        **git_provenance(),
        "prompt_source_sha256": prompt_source_sha256() if llm else None,
        "llm_client_injected": type(llm_client).__name__ if llm and llm_client is not None else None,
        **(vllm_server_provenance(config.llm.base_url) if probe_server else dict.fromkeys(SERVER_FIELDS)),
    }
