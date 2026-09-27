#!/usr/bin/env python3
"""check_llm_stack_versions.py — report whether the pinned LLM-stack versions
(Docker images, served models) are still current against their real upstream
source, before a long/expensive run.

This project pins everything on purpose (docker-compose.ollama.yml's own
module comment: "a pinned version tag, not `latest`" -- a bump must be a
deliberate, reviewable edit, never a side effect of a bare `pull`/`up`) and
every existing pin was verified directly against the source API at pin time,
never guessed or copied from a webpage (see the `--revision` comments in
docker-compose.llm*.yml). This script automates exactly that verification
step. It only ever REPORTS a diff between what's pinned and what upstream
says is current -- it never edits a compose file or triggers a pull itself.
"Latest" for a Docker image means the newest tag matching a plain stable
semver pattern (`vX.Y.Z[.postN]`), explicitly excluding `latest`/rc/alpha/
beta/dev/nightly floating or pre-release tags. There is no equivalent
"stable" concept for a Hugging Face model revision -- for those this reports
whether the pinned commit SHA still matches the repo's current default-branch
HEAD, and leaves the judgment call (worth re-verifying behaviour before
moving to a new commit) to whoever reads the report, exactly as
plan-vllm-switch-readiness.md already treats a weights change as a
confounding variable requiring its own re-verification, not a drop-in.

Checks, read directly out of the compose files (not hand-maintained here, so
this stays accurate as those files change):
  - every `image:` in docker-compose.llm.yml / .llm-4b.yml / .llm-nvfp4.yml /
    .ollama.yml, against the full tag list on Docker Hub's own OCI registry
    (registry-1.docker.io, the plain protocol `docker pull` itself uses --
    NOT hub.docker.com's REST API, which caps anonymous pagination depth
    short of a repo the size of ollama/ollama; see _registry_list_all_tags).
  - every `--model`/`--revision` pair in each vLLM service's `command`,
    against the Hugging Face Hub API.
  - the one Ollama library model this project ships (`qwen3:8b`), against
    the Ollama registry's own manifest digests -- the closest thing Ollama's
    library has to a by-digest pin (docker-compose.ollama.yml's own comment).
    The baseline digests below are hand-copied from that comment; update
    them there and here together on a deliberate re-pin, not automatically.

`--discover` answers a different question: not "has my pinned repo moved?" but
"has a NEWER model been released that I should evaluate?" It lists official
releases from the org behind each pinned model's base, newer than the newest
model already pinned, and runs each survivor through two gates this project
actually depends on:
  - fits the card: real weight-file bytes + a KV cache sized for one
    `--max-model-len` sequence + an overhead allowance, against nvidia-smi's
    VRAM x `--gpu-memory-utilization` (both read from the compose files).
    The pinned models go through the same estimator first, as a calibration
    check -- they run today, so if they did not "fit", the estimator is wrong.
  - honors `enable_thinking`: this engine toggles thinking per decision type,
    so a model without the toggle is not a drop-in even within the same
    family. Measured 2026-09-13: the Qwen3-4B "2507" refresh split into an
    Instruct model that never thinks and a Thinking model that always does.
Passing both gates earns "worth evaluating" -- necessary, not sufficient. A
weights change is a confounded variable in this project
(plan-vllm-switch-readiness.md); decision quality and throughput still have
to be measured on this project's own probes before anything is switched.
Discovery never affects `--strict`: a newer model existing is not drift.

Usage:
    python fast_api_voter/scripts/check_llm_stack_versions.py
    python fast_api_voter/scripts/check_llm_stack_versions.py --strict  # exit 1 on any drift
    python fast_api_voter/scripts/check_llm_stack_versions.py --json
    python fast_api_voter/scripts/check_llm_stack_versions.py --discover
    python fast_api_voter/scripts/check_llm_stack_versions.py --discover --discover-orgs google,mistralai

Network access to registry-1.docker.io, hub.docker.com, huggingface.co and
registry.ollama.ai is required; any single failed lookup is reported inline
as "could not verify" rather than aborting the rest of the report. `--discover`
also needs docker (to ask the pinned vLLM image what it can load -- never
pulls) and nvidia-smi (or --vram-gib). Set HF_TOKEN to probe gated repos.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import httpx
import yaml

_SCRIPTS_DIR = Path(__file__).resolve().parent
_FAST_API_DIR = _SCRIPTS_DIR.parent
_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=15.0, pool=15.0)

# `local_address="0.0.0.0"` forces IPv4: httpx/httpcore has no Happy-Eyeballs
# fallback the way curl does, so a broken/black-holed IPv6 route (observed in
# this project's own sandbox -- SYN-SENT that never completes) would otherwise
# eat the full connect timeout on every single call, serially.
_TRANSPORT = httpx.HTTPTransport(local_address="0.0.0.0")

_COMPOSE_FILES = [
    "docker-compose.llm.yml",
    "docker-compose.llm-4b.yml",
    "docker-compose.llm-nvfp4.yml",
    "docker-compose.ollama.yml",
]

# vX.Y.Z or vX.Y.Z.postN only -- excludes `latest`, rc/alpha/beta/dev/nightly
# tags and platform-variant suffixes (e.g. `-cpu`) by simply not matching them.
_STABLE_TAG_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:\.post(\d+))?$")

# Baseline from docker-compose.ollama.yml's own module comment (measured live
# 2026-09-05). Ollama's library has no by-digest pull, so this is the
# strongest available guarantee: flag drift against a manually recorded pin,
# not silently assume the tag still means the same weights.
_OLLAMA_LIBRARY_MODELS = {
    "qwen3:8b": {
        "weight_digest": "sha256:a3de86cd1c132c822487ededd47a324c50491393e6565cd14bafa40d0b8e686f",
        "config_digest": "sha256:05a61d37b08453e59290add468e3bb2f688e23a01e967fecb0e2fa41218cea76",
    },
}


def _tag_sort_key(tag: str) -> tuple[int, int, int, int] | None:
    m = _STABLE_TAG_RE.match(tag)
    if not m:
        return None
    major, minor, patch, post = m.groups()
    return (int(major), int(minor), int(patch), int(post) if post else 0)


@dataclasses.dataclass
class ImageCheck:
    source_files: list[str]
    repository: str
    pinned_tag: str
    pinned_pushed_at: str | None
    latest_tag: str | None
    latest_pushed_at: str | None
    error: str | None

    @property
    def up_to_date(self) -> bool | None:
        if self.error or self.latest_tag is None:
            return None
        pinned_key, latest_key = _tag_sort_key(self.pinned_tag), _tag_sort_key(self.latest_tag)
        if pinned_key is None or latest_key is None:
            return None
        return pinned_key >= latest_key


@dataclasses.dataclass
class ModelCheck:
    source_files: list[str]
    repo_id: str
    pinned_revision: str
    head_revision: str | None
    head_last_modified: str | None
    error: str | None

    @property
    def up_to_date(self) -> bool | None:
        if self.error or self.head_revision is None:
            return None
        return self.pinned_revision == self.head_revision


@dataclasses.dataclass
class OllamaModelCheck:
    tag: str
    pinned: dict[str, str]
    live: dict[str, str] | None
    error: str | None

    @property
    def up_to_date(self) -> bool | None:
        if self.error or self.live is None:
            return None
        return self.pinned == self.live


def _load_compose(path: Path) -> dict[str, Any]:
    with path.open() as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)
    return data


def _extract_model_revision_pairs(command: list[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    current_model: str | None = None
    for i, token in enumerate(command):
        if token == "--model" and i + 1 < len(command):
            current_model = command[i + 1]
        elif token == "--revision" and i + 1 < len(command) and current_model:
            pairs.append((current_model, command[i + 1]))
            current_model = None
    return pairs


def _collect_pins(
    fast_api_dir: Path,
) -> tuple[dict[tuple[str, str], list[str]], dict[tuple[str, str], list[str]]]:
    """Returns ({(repository, tag): [source files]}, {(repo_id, revision): [source files]})."""
    images: dict[tuple[str, str], list[str]] = {}
    models: dict[tuple[str, str], list[str]] = {}
    for name in _COMPOSE_FILES:
        path = fast_api_dir / name
        if not path.exists():
            continue
        compose = _load_compose(path)
        for service in (compose.get("services") or {}).values():
            image = service.get("image")
            if image and ":" in image:
                repository, tag = image.rsplit(":", 1)
                sources = images.setdefault((repository, tag), [])
                if name not in sources:
                    sources.append(name)
            command = service.get("command") or []
            for repo_id, revision in _extract_model_revision_pairs(command):
                sources = models.setdefault((repo_id, revision), [])
                if name not in sources:
                    sources.append(name)
    return images, models


_REGISTRY_MAX_PAGES = 50  # n=100/page -> up to 5000 tags; both repos this
# project pins (vllm/vllm-openai ~600, ollama/ollama ~1200, measured
# 2026-09-13) fit in well under 15 pages. A safety bound against a runaway
# repo, not a shortcut -- see _registry_list_all_tags for why a partial scan
# is not acceptable here.

_LINK_NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


def _registry_get(client: httpx.Client, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
    """GET against a plain OCI Distribution v2 endpoint (docker.io,
    registry.ollama.ai, ...), transparently handling the anonymous
    bearer-token challenge every one of them requires even for public reads
    -- the same flow `docker pull` itself uses, discovered from the 401's own
    `Www-Authenticate` header rather than hardcoded per registry."""
    headers = dict(headers or {})
    resp = client.get(url, headers=headers, timeout=_TIMEOUT)
    if resp.status_code == 401:
        challenge = resp.headers.get("Www-Authenticate", "")
        params = dict(re.findall(r'(\w+)="([^"]*)"', challenge))
        realm = params.get("realm")
        if realm is None:
            resp.raise_for_status()  # a 401 always raises here; this is just for mypy's narrowing
            raise AssertionError("unreachable")
        token_resp = client.get(
            realm, params={k: v for k, v in params.items() if k != "realm"}, timeout=_TIMEOUT
        )
        token_resp.raise_for_status()
        token = token_resp.json().get("token") or token_resp.json().get("access_token")
        headers["Authorization"] = f"Bearer {token}"
        resp = client.get(url, headers=headers, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp


def _registry_list_all_tags(client: httpx.Client, registry: str, repository: str) -> tuple[list[str], str | None]:
    """Returns (all_tags, error) via the registry's own `tags/list` endpoint
    (paginated through the `Link` header), NOT hub.docker.com's REST API.

    Tried hub.docker.com's `/v2/repositories/<repo>/tags` first: it caps
    anonymous pagination depth well short of a 1000+-tag repo (measured live
    2026-09-13 against ollama/ollama: 403 at page 11, body "pagination
    offset too large for anonymous requests; sign in to page further").
    Worse, sorting that API by recency to stay under the cap silently
    returned a STALE "latest" (0.5.5, over a year old) because heavy
    multi-arch/rebuild tag churn buried the real latest release outside the
    first few hundred "recently updated" entries. The plain registry API
    used here is the same one `docker pull` itself relies on for anonymous
    public repos and has no such business-tier limit.
    """
    tags: list[str] = []
    path = f"/v2/{repository}/tags/list?n=100"
    try:
        for _ in range(_REGISTRY_MAX_PAGES):
            resp = _registry_get(client, f"https://{registry}{path}")
            payload = resp.json()
            tags.extend(payload.get("tags") or [])
            m = _LINK_NEXT_RE.search(resp.headers.get("link", ""))
            if not m:
                break
            path = m.group(1)
        return tags, None
    except httpx.HTTPError as exc:
        return tags, str(exc)


def _docker_hub_latest_stable_tag(
    client: httpx.Client, repository: str
) -> tuple[str | None, str | None, str | None]:
    """Returns (latest_stable_tag, pushed_at, error) -- the true max stable
    semver tag across the repository's ENTIRE tag list."""
    tags, error = _registry_list_all_tags(client, "registry-1.docker.io", repository)
    if error:
        return None, None, error
    best: tuple[int, int, int, int] | None = None
    best_tag: str | None = None
    for name in tags:
        key = _tag_sort_key(name)
        if key is not None and (best is None or key > best):
            best, best_tag = key, name
    if best_tag is None:
        return None, None, "no tag matched the stable semver pattern"
    return best_tag, _docker_hub_tag_pushed_at(client, repository, best_tag), None


def _docker_hub_tag_pushed_at(
    client: httpx.Client, repository: str, tag: str
) -> str | None:
    """A single, non-paginated lookup -- not subject to the anonymous
    pagination-depth limit _registry_list_all_tags works around."""
    url = f"https://hub.docker.com/v2/repositories/{repository}/tags/{tag}"
    try:
        resp = client.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
        payload: dict[str, Any] = resp.json()
        result = payload.get("tag_last_pushed") or payload.get("last_updated")
        return str(result) if result is not None else None
    except httpx.HTTPError:
        return None


def _hf_model_head(
    client: httpx.Client, repo_id: str
) -> tuple[str | None, str | None, str | None]:
    """Returns (head_sha, last_modified, error)."""
    url = f"https://huggingface.co/api/models/{repo_id}"
    try:
        resp = client.get(url, headers=_hf_headers(), timeout=_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("sha"), payload.get("lastModified"), None
    except httpx.HTTPError as exc:
        return None, None, str(exc)


def _ollama_repo_and_reference(tag: str) -> tuple[str, str]:
    name, _, reference = tag.partition(":")
    repo = name if "/" in name else f"library/{name}"
    return repo, reference or "latest"


def _ollama_manifest_digests(
    client: httpx.Client, tag: str
) -> tuple[dict[str, str] | None, str | None]:
    """Returns ({"config_digest", "weight_digest"}, error)."""
    repo, reference = _ollama_repo_and_reference(tag)
    accept = "application/vnd.docker.distribution.manifest.v2+json"
    url = f"https://registry.ollama.ai/v2/{repo}/manifests/{reference}"
    try:
        resp = _registry_get(client, url, headers={"Accept": accept})
        manifest = resp.json()
        config_digest = manifest.get("config", {}).get("digest", "")
        weight_digest = next(
            (
                layer.get("digest")
                for layer in manifest.get("layers", [])
                if "model" in layer.get("mediaType", "")
            ),
            None,
        )
        return {"config_digest": config_digest, "weight_digest": weight_digest}, None
    except httpx.HTTPError as exc:
        return None, str(exc)


# ── --discover: newer official models worth evaluating ─────────────────────

_GIB = 1024**3
# vLLM's KV cache dtype follows the model's activation dtype unless
# --kv-cache-dtype is set; no compose file here sets it, and every pinned
# model runs fp16/bf16 activations.
_KV_BYTES_PER_ELEMENT = 2
# CUDA graphs, sampler, activations. docker-compose.llm.yml's own
# --max-model-len history is the evidence this is not free: a config with
# 37 MiB left died during CUDA-graph/sampler warmup, not under load. 1.5 GiB
# is an allowance, not a measurement -- the calibration rows exist to catch it
# being wrong.
_OVERHEAD_GIB = 1.5
# The most aggressive quantization any candidate could plausibly ship in, used
# only to discard models that could not fit even then, before spending HTTP
# calls probing them. A floor, so it never wrongly excludes a model that fits.
_FOUR_BIT_BYTES_PER_PARAM = 0.5
_DISCOVER_MAX_PAGES = 20
_UNSERVABLE_FORMAT_RE = re.compile(r"\b(mlx|gguf)\b", re.IGNORECASE)
_NON_CHAT_NAME_RE = re.compile(r"(embedding|reranker|guard)", re.IGNORECASE)
# pipeline_tag -> is it multimodal. image-text-to-text is NOT optional here:
# measured 2026-09-13, every newer Qwen generation (Qwen3.5, 3.6, 3.8) ships as
# image-text-to-text. Filtering to text-generation alone reported only
# same-generation siblings as "newer" -- silently hiding the entire mainline.
_CHAT_PIPELINES = {"text-generation": False, "image-text-to-text": True}
_WORTH_EVALUATING = "worth evaluating"


@dataclasses.dataclass
class ModelCandidate:
    repo_id: str
    revision: str
    created_at: str | None
    pinned: bool
    multimodal: bool = False
    architecture: str | None = None
    arch_supported: bool | None = None
    quant: str | None = None
    weights_gib: float | None = None
    kv_gib: float | None = None
    est_total_gib: float | None = None
    fits: bool | None = None
    thinking_toggle: bool | None = None
    error: str | None = None

    @property
    def verdict(self) -> str:
        if self.error:
            return f"could not probe: {self.error}"
        # Before any size question: a model the pinned server cannot load is a
        # non-starter at any size, and no quantization changes that.
        if self.arch_supported is False:
            return f"the pinned vLLM cannot load {self.architecture}"
        if self.fits is None:
            return "size unknown"
        if not self.fits:
            if self.pinned:
                return "estimator says it does NOT fit, yet it runs today -- do not trust the fit verdicts"
            return "too big for this card"
        if self.thinking_toggle is None:
            return "fits; no chat template found -- check thinking support by hand"
        if not self.thinking_toggle:
            return "fits, but NOT a drop-in: no enable_thinking toggle"
        if self.pinned:
            return "fits (consistent with it running today)"
        return _WORTH_EVALUATING


@dataclasses.dataclass
class ModelDiscovery:
    since_by_org: dict[str, str | None]
    vram_gib: float | None
    gpu_memory_utilization: float | None
    max_model_len: int | None
    budget_gib: float | None
    vllm_image: str | None
    vllm_arch_count: int | None
    calibration: list[ModelCandidate]
    candidates: list[ModelCandidate]
    excluded: dict[str, int]
    notes: list[str]


def _extract_flag_values(command: list[str], flag: str) -> list[str]:
    return [command[i + 1] for i, token in enumerate(command) if token == flag and i + 1 < len(command)]


def _collect_serving_limits(fast_api_dir: Path) -> tuple[float | None, int | None]:
    """(tightest --gpu-memory-utilization, largest --max-model-len) across every
    vLLM service -- the most conservative pair, so "fits" means fits every arm."""
    utilizations: list[float] = []
    max_lens: list[int] = []
    for name in _COMPOSE_FILES:
        path = fast_api_dir / name
        if not path.exists():
            continue
        for service in (_load_compose(path).get("services") or {}).values():
            command = service.get("command") or []
            utilizations += [float(v) for v in _extract_flag_values(command, "--gpu-memory-utilization")]
            max_lens += [int(v) for v in _extract_flag_values(command, "--max-model-len")]
    return (min(utilizations) if utilizations else None, max(max_lens) if max_lens else None)


def _gpu_total_gib() -> float | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    mib = [float(line) for line in out.splitlines() if line.strip()]
    return max(mib) / 1024 if mib else None


def _hf_headers() -> dict[str, str]:
    """HF_TOKEN, if set, for gated repos (Gemma variants, all of Llama). Passed
    per request and only on huggingface.co calls -- never set on the shared
    client, which also talks to Docker Hub and the Ollama registry. httpx drops
    Authorization on the cross-origin redirect to HF's CDN, which is what those
    pre-signed CDN URLs expect."""
    token = os.environ.get("HF_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _hf_api(client: httpx.Client, path: str, params: Any = None) -> Any:
    resp = client.get(f"https://huggingface.co/api/{path}", params=params, headers=_hf_headers(), timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _hf_file(client: httpx.Client, repo_id: str, revision: str, filename: str) -> str | None:
    """A raw repo file, or None if the repo does not ship it. `resolve/`
    redirects to a CDN, and httpx does not follow redirects by default -- the
    first probe of this returned nothing for every model because of that."""
    resp = client.get(
        f"https://huggingface.co/{repo_id}/resolve/{revision}/{filename}",
        headers=_hf_headers(), timeout=_TIMEOUT, follow_redirects=True,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.text


def _weights_gib(client: httpx.Client, repo_id: str, revision: str) -> float | None:
    """Real bytes of the safetensors files. NOT `safetensors.parameters` from
    the model API: for a quantized model that counts packed int4 tensors in
    their I32 storage dtype, which sizes Qwen3-8B-AWQ at ~30 GB when its files
    are 6.1 GB."""
    info = _hf_api(client, f"models/{repo_id}/revision/{revision}", params={"blobs": "true"})
    sizes = [
        sibling.get("size") or 0
        for sibling in info.get("siblings", [])
        if str(sibling.get("rfilename", "")).endswith(".safetensors")
    ]
    return sum(sizes) / _GIB if sizes else None


def _kv_cache_gib(config: dict[str, Any], max_model_len: int) -> float | None:
    """KV cache for ONE max-length sequence (this client never issues concurrent
    requests): 2 (K,V) x kv_heads x head_dim x bytes x tokens-held, summed over
    the layers that actually hold a KV cache. Multimodal configs nest the
    language model under `text_config`.

    `layer_types` matters and is not an edge case: Qwen3.5/3.6 run linear
    attention on 24 of 32 layers (a fixed-size recurrent state, no per-token
    cache), so counting every layer overestimated their KV by 4x -- 2.0 GiB
    instead of 0.5 GiB for Qwen3.5-4B at 16384 tokens, which on a larger model
    is enough to mark a real candidate "too big".
    Linear-attention state is left to the overhead allowance; sliding-window
    layers hold at most `sliding_window` tokens; any unrecognized layer type is
    counted as full attention, so an unknown architecture errs toward "too
    big" rather than toward an out-of-memory crash."""
    text = config if "num_hidden_layers" in config else config.get("text_config")
    if not isinstance(text, dict):
        return None
    layers = text.get("num_hidden_layers")
    heads = text.get("num_attention_heads")
    kv_heads = text.get("num_key_value_heads") or heads
    hidden = text.get("hidden_size")
    head_dim = text.get("head_dim") or (hidden // heads if hidden and heads else None)
    if not (layers and kv_heads and head_dim):
        return None
    layer_types = text.get("layer_types")
    if not (isinstance(layer_types, list) and layer_types):
        layer_types = ["full_attention"] * int(layers)
    window = text.get("sliding_window")
    tokens_held = 0
    for layer_type in layer_types:
        if layer_type == "linear_attention":
            continue
        if layer_type == "sliding_attention" and window:
            tokens_held += min(int(window), max_model_len)
        else:
            tokens_held += max_model_len
    return float(2 * kv_heads * head_dim * _KV_BYTES_PER_ELEMENT * tokens_held) / _GIB


def _vllm_supported_archs(image: str | None) -> tuple[frozenset[str] | None, str | None]:
    """Asks the pinned vLLM image itself which architectures it can load -- the
    exact server version that would serve the model, not a docs page for some
    other release. No GPU needed (measured 2026-09-13: ~12 s, 378
    architectures). `--pull=never` because this must not turn into a 28 GB
    download just to answer a question, and `--network none` because the
    container has no reason to talk to anything."""
    if image is None:
        return None, "no pinned vllm/vllm-openai image in the compose files: architecture support unchecked"
    script = (
        "import json; from vllm.model_executor.models import ModelRegistry; "
        "print(json.dumps(sorted(ModelRegistry.get_supported_archs())))"
    )
    try:
        proc = subprocess.run(
            ["docker", "run", "--rm", "--pull=never", "--network", "none", "--entrypoint", "python3", image, "-c", script],
            capture_output=True, text=True, timeout=300, check=True,
        )
        archs = json.loads(proc.stdout.strip().splitlines()[-1])
    except (OSError, subprocess.SubprocessError, ValueError, IndexError) as exc:
        return None, f"could not ask {image} for its supported architectures (is it pulled?): {exc}"
    return frozenset(str(a) for a in archs), None


def _quant_label(config: dict[str, Any]) -> str:
    """quant_method if quantized, else the dtype. Newer configs say `dtype`
    rather than `torch_dtype`, and multimodal ones keep it under `text_config`
    (Qwen3.5: `text_config.dtype`) -- all four spellings are checked."""
    for scope in (config, config.get("text_config")):
        if not isinstance(scope, dict):
            continue
        quant = scope.get("quantization_config")
        if isinstance(quant, dict) and quant.get("quant_method"):
            return str(quant["quant_method"])
    for scope in (config, config.get("text_config")):
        if isinstance(scope, dict) and (dtype := scope.get("torch_dtype") or scope.get("dtype")):
            return str(dtype)
    return "unknown"


def _has_thinking_toggle(client: httpx.Client, repo_id: str, revision: str) -> bool | None:
    """Does the chat template accept `enable_thinking`? None when no template
    exists at all -- that is "cannot tell", not "no"."""
    templates: list[str] = []
    raw = _hf_file(client, repo_id, revision, "tokenizer_config.json")
    if raw is not None:
        loaded = json.loads(raw)
        chat_template = loaded.get("chat_template") if isinstance(loaded, dict) else None
        if isinstance(chat_template, str):
            templates.append(chat_template)
        elif isinstance(chat_template, list):
            templates += [str(t.get("template", "")) for t in chat_template if isinstance(t, dict)]
    if not templates:
        jinja = _hf_file(client, repo_id, revision, "chat_template.jinja")
        if jinja is not None:
            templates.append(jinja)
    if not templates:
        return None
    return any("enable_thinking" in template for template in templates)


def _probe_model(
    client: httpx.Client,
    repo_id: str,
    revision: str,
    created_at: str | None,
    *,
    pinned: bool,
    budget_gib: float | None,
    max_model_len: int | None,
    supported_archs: frozenset[str] | None,
    multimodal: bool = False,
) -> ModelCandidate:
    candidate = ModelCandidate(
        repo_id=repo_id, revision=revision, created_at=created_at, pinned=pinned, multimodal=multimodal,
    )
    try:
        raw_config = _hf_file(client, repo_id, revision, "config.json")
        loaded = json.loads(raw_config) if raw_config is not None else {}
        config: dict[str, Any] = loaded if isinstance(loaded, dict) else {}
        architectures = config.get("architectures")
        if isinstance(architectures, list) and architectures:
            candidate.architecture = str(architectures[0])
            if supported_archs is not None:
                candidate.arch_supported = candidate.architecture in supported_archs
        candidate.quant = _quant_label(config)
        candidate.weights_gib = _weights_gib(client, repo_id, revision)
        if max_model_len is not None:
            candidate.kv_gib = _kv_cache_gib(config, max_model_len)
        if candidate.weights_gib is not None and candidate.kv_gib is not None:
            candidate.est_total_gib = candidate.weights_gib + candidate.kv_gib + _OVERHEAD_GIB
            if budget_gib is not None:
                candidate.fits = candidate.est_total_gib <= budget_gib
        candidate.thinking_toggle = _has_thinking_toggle(client, repo_id, revision)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (401, 403):
            candidate.error = (
                "gated repo, and HF_TOKEN lacks access to it" if os.environ.get("HF_TOKEN")
                else "gated repo: accept its license on huggingface.co, then set HF_TOKEN"
            )
        else:
            candidate.error = str(exc)
    except (httpx.HTTPError, ValueError) as exc:  # ValueError covers a malformed JSON file
        candidate.error = str(exc)
    return candidate


def _pinned_lineage(
    client: httpx.Client, model_pins: Iterable[tuple[str, str]]
) -> tuple[dict[str, str | None], dict[str, str | None], list[str]]:
    """(org -> newest pinned createdAt, repo -> createdAt, notes).

    The org searched is the one behind each pinned model's BASE, so a
    community requant (ELVISIO/Qwen3-8B-NVFP4A16) points discovery at Qwen,
    not at ELVISIO's unrelated uploads. A requant's own upload date says
    nothing about which generation it is, so only official pins in an org set
    its "since" -- falling back to the base model's date if an org has none."""
    since: dict[str, str | None] = {}
    created: dict[str, str | None] = {}
    orphan_bases: dict[str, str] = {}
    notes: list[str] = []
    for repo_id, _revision in model_pins:
        try:
            info = _hf_api(client, f"models/{repo_id}", params=[("expand[]", "createdAt"), ("expand[]", "cardData")])
        except httpx.HTTPError as exc:
            notes.append(f"{repo_id}: could not read lineage: {exc}")
            continue
        repo_created = info.get("createdAt")
        created[repo_id] = repo_created
        base = (info.get("cardData") or {}).get("base_model")
        if isinstance(base, list):
            base = base[0] if base else None
        own_org = repo_id.split("/")[0]
        org = base.split("/")[0] if isinstance(base, str) and "/" in base else own_org
        current = since.setdefault(org, None)
        if org == own_org:
            if repo_created and (current is None or repo_created > current):
                since[org] = repo_created
        elif isinstance(base, str):
            orphan_bases.setdefault(org, base)
    for org, base in orphan_bases.items():
        if since.get(org) is None:
            try:
                since[org] = _hf_api(client, f"models/{base}", params=[("expand[]", "createdAt")]).get("createdAt")
            except httpx.HTTPError as exc:
                notes.append(f"{org}: could not date lineage base {base}: {exc}")
    return since, created, notes


def _list_org_models_since(
    client: httpx.Client, org: str, since: str | None
) -> tuple[list[dict[str, Any]], list[str]]:
    """Newest first, stopping once past `since`. That early stop leans on the
    server's createdAt sort, so the order is checked page by page rather than
    trusted -- the Docker Hub half of this script already learned that a
    trusted server ordering can silently hide the real answer. If the order is
    ever seen to break, listing continues to the page cap instead."""
    url = "https://huggingface.co/api/models"
    params: Any = [
        ("author", org), ("sort", "createdAt"), ("direction", "-1"), ("limit", "100"),
        ("expand[]", "createdAt"), ("expand[]", "safetensors"), ("expand[]", "tags"), ("expand[]", "pipeline_tag"),
    ]
    items: list[dict[str, Any]] = []
    notes: list[str] = []
    previous: str | None = None
    ordered = True
    for _ in range(_DISCOVER_MAX_PAGES):
        resp = client.get(url, params=params, headers=_hf_headers(), timeout=_TIMEOUT)
        resp.raise_for_status()
        reached_older = False
        for item in resp.json():
            item_created = item.get("createdAt") or ""
            if previous is not None and item_created > previous:
                ordered = False
            previous = item_created
            if since is not None and item_created <= since:
                reached_older = True
                continue
            items.append(item)
        m = _LINK_NEXT_RE.search(resp.headers.get("link", ""))
        if not m or (reached_older and ordered):
            break
        if not m.group(1).startswith("https://huggingface.co/"):
            # The next URL comes from the server and the request carries HF_TOKEN.
            notes.append(f"{org}: refused a pagination link off huggingface.co, listing may be incomplete")
            break
        url, params = m.group(1), None
    else:
        notes.append(f"{org}: stopped at the {_DISCOVER_MAX_PAGES}-page cap, listing may be incomplete")
    if not ordered:
        notes.append(f"{org}: server createdAt order was not monotonic, so early stopping was disabled")
    return items, notes


def _exclusion_reason(item: dict[str, Any], budget_gib: float | None) -> str | None:
    """Cheap, listing-data-only reasons to skip a model before probing it. Every
    skip is counted and reported, so nothing disappears silently. The pipeline
    filter is client-side and deliberately wide -- see `_CHAT_PIPELINES` for the
    newer generations a narrow one hid."""
    repo_id = str(item.get("id", ""))
    if _UNSERVABLE_FORMAT_RE.search(" ".join([repo_id, *map(str, item.get("tags") or [])])):
        return "MLX/GGUF build (not this project's vLLM-on-NVIDIA path)"
    if item.get("pipeline_tag") not in _CHAT_PIPELINES:
        return "not a chat model (speech, image generation, classification...)"
    if _NON_CHAT_NAME_RE.search(repo_id):
        return "embedding / reranker / guard model"
    total_params = (item.get("safetensors") or {}).get("total")
    if not total_params:
        return "no safetensors metadata to size it"
    if budget_gib is not None and total_params * _FOUR_BIT_BYTES_PER_PARAM / _GIB > budget_gib:
        return "too large for this card even at 4-bit"
    return None


def _discover(
    client: httpx.Client,
    model_pins: Iterable[tuple[str, str]],
    *,
    override_orgs: list[str] | None,
    vram_gib_override: float | None,
    vllm_image: str | None,
) -> ModelDiscovery:
    pins = sorted(model_pins)
    since_by_org, created, notes = _pinned_lineage(client, pins)
    if override_orgs:
        newest = max((s for s in since_by_org.values() if s), default=None)
        since_by_org = {org: newest for org in override_orgs}

    utilization, max_model_len = _collect_serving_limits(_FAST_API_DIR)
    vram_gib = vram_gib_override if vram_gib_override is not None else _gpu_total_gib()
    if vram_gib is None:
        notes.append("nvidia-smi unavailable and no --vram-gib given: fit verdicts skipped")
    budget = vram_gib * utilization if vram_gib is not None and utilization is not None else None
    supported_archs, arch_note = _vllm_supported_archs(vllm_image)
    if arch_note:
        notes.append(arch_note)

    calibration = [
        _probe_model(
            client, repo, rev, created.get(repo), pinned=True,
            budget_gib=budget, max_model_len=max_model_len, supported_archs=supported_archs,
        )
        for repo, rev in pins
    ]

    pinned_ids = {repo for repo, _ in pins}
    candidates: list[ModelCandidate] = []
    excluded: Counter[str] = Counter()
    for org, since in sorted(since_by_org.items()):
        try:
            items, list_notes = _list_org_models_since(client, org, since)
        except httpx.HTTPError as exc:
            notes.append(f"{org}: listing failed: {exc}")
            continue
        notes += list_notes
        for item in items:
            if item.get("id") in pinned_ids:
                continue
            reason = _exclusion_reason(item, budget)
            if reason:
                excluded[reason] += 1
                continue
            candidates.append(_probe_model(
                client, str(item["id"]), "main", item.get("createdAt"),
                pinned=False, budget_gib=budget, max_model_len=max_model_len,
                supported_archs=supported_archs, multimodal=_CHAT_PIPELINES[str(item.get("pipeline_tag"))],
            ))
    # "worth evaluating" first, and within it the largest model that fits --
    # the most capability this card can hold. Newest-first was tried and buried
    # Qwen3.5-4B under the 0.8B/2B releases dated one day later. Base models
    # sort after their instruct twin; every other group stays newest first.
    def order(c: ModelCandidate) -> tuple[bool, float, bool]:
        worth = c.verdict == _WORTH_EVALUATING
        return (not worth, -(c.weights_gib or 0.0) if worth else 0.0, c.repo_id.endswith("-Base"))

    candidates.sort(key=lambda c: c.created_at or "", reverse=True)
    candidates.sort(key=order)  # stable, so newest-first survives as the final tie-break

    return ModelDiscovery(
        since_by_org=since_by_org, vram_gib=vram_gib, gpu_memory_utilization=utilization,
        max_model_len=max_model_len, budget_gib=budget, vllm_image=vllm_image,
        vllm_arch_count=len(supported_archs) if supported_archs is not None else None,
        calibration=calibration, candidates=candidates, excluded=dict(excluded.most_common()), notes=notes,
    )


def _run_checks(
    *,
    discover: bool = False,
    discover_orgs: list[str] | None = None,
    vram_gib: float | None = None,
) -> tuple[list[ImageCheck], list[ModelCheck], list[OllamaModelCheck], ModelDiscovery | None]:
    image_pins, model_pins = _collect_pins(_FAST_API_DIR)
    image_checks: list[ImageCheck] = []
    model_checks: list[ModelCheck] = []
    ollama_checks: list[OllamaModelCheck] = []
    discovery: ModelDiscovery | None = None
    # One client for everything: _TRANSPORT is a single shared instance, and
    # closing the client closes it, so discovery cannot open a second client
    # after this block ends.
    with httpx.Client(transport=_TRANSPORT, timeout=_TIMEOUT) as client:
        if discover:
            # The production arm's image, since that is the server a switch would land on.
            vllm_image = next(
                (f"{repo}:{tag}" for (repo, tag), sources in sorted(image_pins.items())
                 if repo == "vllm/vllm-openai" and "docker-compose.llm.yml" in sources),
                None,
            )
            discovery = _discover(
                client, model_pins.keys(), override_orgs=discover_orgs,
                vram_gib_override=vram_gib, vllm_image=vllm_image,
            )
        for (repository, tag), sources in sorted(image_pins.items()):
            latest_tag, latest_pushed_at, error = _docker_hub_latest_stable_tag(client, repository)
            pinned_pushed_at = None if error else _docker_hub_tag_pushed_at(client, repository, tag)
            image_checks.append(
                ImageCheck(sources, repository, tag, pinned_pushed_at, latest_tag, latest_pushed_at, error)
            )
        for (repo_id, revision), sources in sorted(model_pins.items()):
            head_sha, last_modified, error = _hf_model_head(client, repo_id)
            model_checks.append(ModelCheck(sources, repo_id, revision, head_sha, last_modified, error))
        for tag, pinned in sorted(_OLLAMA_LIBRARY_MODELS.items()):
            live, error = _ollama_manifest_digests(client, tag)
            ollama_checks.append(OllamaModelCheck(tag, pinned, live, error))
    return image_checks, model_checks, ollama_checks, discovery


def _short(revision: str) -> str:
    return revision[:12] if len(revision) > 12 else revision


def _print_report(
    image_checks: list[ImageCheck], model_checks: list[ModelCheck], ollama_checks: list[OllamaModelCheck]
) -> None:
    print("## Docker images\n")
    for image_check in image_checks:
        print(f"- {image_check.repository} ({', '.join(image_check.source_files)})")
        print(
            f"    pinned: {image_check.pinned_tag}"
            + (f"  (pushed {image_check.pinned_pushed_at})" if image_check.pinned_pushed_at else "")
        )
        if image_check.error:
            print(f"    could not verify against Docker Hub: {image_check.error}")
        else:
            print(
                f"    latest stable: {image_check.latest_tag}"
                + (f"  (pushed {image_check.latest_pushed_at})" if image_check.latest_pushed_at else "")
            )
            print(
                "    -> "
                + ("up to date" if image_check.up_to_date else "NEWER VERSION AVAILABLE -- review before bumping")
            )
        print()

    print("## Hugging Face models\n")
    for model_check in model_checks:
        print(f"- {model_check.repo_id} ({', '.join(model_check.source_files)})")
        print(f"    pinned revision: {_short(model_check.pinned_revision)}")
        if model_check.error:
            print(f"    could not verify against Hugging Face Hub: {model_check.error}")
        else:
            print(
                f"    HEAD revision:   {_short(model_check.head_revision or '')}"
                f"  (last modified {model_check.head_last_modified})"
            )
            print(
                "    -> "
                + (
                    "up to date"
                    if model_check.up_to_date
                    else "HEAD has moved -- treat a bump as a weights change, re-verify before switching"
                )
            )
        print()

    print("## Ollama library models\n")
    for ollama_check in ollama_checks:
        print(f"- {ollama_check.tag}")
        print(
            f"    pinned: config={_short(ollama_check.pinned['config_digest'])}"
            f" weight={_short(ollama_check.pinned['weight_digest'] or '')}"
        )
        if ollama_check.error:
            print(f"    could not verify against registry.ollama.ai: {ollama_check.error}")
        else:
            live = ollama_check.live or {}
            print(
                f"    live:   config={_short(live.get('config_digest', ''))} weight={_short(live.get('weight_digest') or '')}"
            )
            print(
                "    -> "
                + (
                    "up to date"
                    if ollama_check.up_to_date
                    else "MANIFEST DRIFT -- same tag now serves different weights, re-verify before trusting"
                )
            )
        print()


def _format_candidate(candidate: ModelCandidate) -> str:
    created = (candidate.created_at or "")[:10] or "?"
    if candidate.weights_gib is not None and candidate.kv_gib is not None and candidate.est_total_gib is not None:
        size = (
            f"{candidate.weights_gib:.2f} weights + {candidate.kv_gib:.2f} KV + {_OVERHEAD_GIB:.1f} overhead"
            f" = {candidate.est_total_gib:.2f} GiB"
        )
    elif candidate.weights_gib is not None:
        size = f"{candidate.weights_gib:.2f} GiB weights, KV unknown"
    else:
        size = "size unknown"
    yes_no = {True: "yes", False: "NO", None: "?"}
    kind = ", multimodal" if candidate.multimodal else ""
    return (
        f"- {candidate.repo_id}  [created {created}, {candidate.quant or '?'}{kind}]\n"
        f"    {size}\n"
        f"    enable_thinking: {yes_no[candidate.thinking_toggle]}  |  "
        f"pinned vLLM loads {candidate.architecture or '?'}: {yes_no[candidate.arch_supported]}\n"
        f"    -> {candidate.verdict}"
    )


def _print_discovery(discovery: ModelDiscovery) -> None:
    print("## Model candidates (--discover)\n")
    if discovery.budget_gib is not None:
        print(
            f"Budget: {discovery.vram_gib:.2f} GiB VRAM x {discovery.gpu_memory_utilization:.2f} "
            f"--gpu-memory-utilization = {discovery.budget_gib:.2f} GiB for vLLM, against weights + a KV cache"
        )
        print(f"        for one --max-model-len {discovery.max_model_len} sequence + {_OVERHEAD_GIB} GiB overhead.")
    if discovery.vllm_arch_count is not None:
        print(f"Loadable: checked against {discovery.vllm_image} itself ({discovery.vllm_arch_count} architectures).")
    for org, since in sorted(discovery.since_by_org.items()):
        print(f"Searched: {org}, releases after {since[:10] if since else '(the beginning)'}")

    print("\nCalibration: the pinned models through the same estimator. These run today, so they must fit --")
    print("if one does not, trust none of the fit verdicts below.\n")
    for candidate in discovery.calibration:
        print(_format_candidate(candidate))

    print("\nCandidates:\n")
    if not discovery.candidates:
        print("- nothing newer passed the filters")
    for candidate in discovery.candidates:
        print(_format_candidate(candidate))

    if discovery.excluded:
        print(f"\nSkipped before probing ({sum(discovery.excluded.values())}):")
        for reason, count in discovery.excluded.items():
            print(f"  {count:>4}  {reason}")
    for note in discovery.notes:
        print(f"\nnote: {note}")
    print(
        f"\n'{_WORTH_EVALUATING}' means: fits this card, the pinned vLLM loads its architecture, and it honors\n"
        "enable_thinking. Necessary, not sufficient: a weights change is a confounded variable here\n"
        "(plan-vllm-switch-readiness.md), so decision quality and throughput still have to be measured on this\n"
        "project's own probes before switching anything. Multimodal models also load a vision tower (counted\n"
        "in the weights above) and have never been served text-only in this project."
    )
    print()


def _to_jsonable(checks: list[Any]) -> list[dict[str, Any]]:
    return [dataclasses.asdict(c) | {"up_to_date": c.up_to_date} for c in checks]


def _discovery_jsonable(discovery: ModelDiscovery) -> dict[str, Any]:
    def with_verdicts(candidates: list[ModelCandidate]) -> list[dict[str, Any]]:
        return [dataclasses.asdict(c) | {"verdict": c.verdict} for c in candidates]

    return dataclasses.asdict(discovery) | {
        "calibration": with_verdicts(discovery.calibration),
        "candidates": with_verdicts(discovery.candidates),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON instead of the text report")
    parser.add_argument("--strict", action="store_true", help="exit 1 if anything checked is not up to date")
    parser.add_argument(
        "--discover", action="store_true",
        help="also list newer official models that fit this card and honor enable_thinking (slower; never affects --strict)",
    )
    parser.add_argument(
        "--discover-orgs", default=None,
        help="comma-separated Hugging Face orgs to search instead of the pinned models' own lineage (e.g. google,mistralai)",
    )
    parser.add_argument("--vram-gib", type=float, default=None, help="total GPU memory, if nvidia-smi is unavailable")
    args = parser.parse_args(argv)

    orgs = [org.strip() for org in args.discover_orgs.split(",") if org.strip()] if args.discover_orgs else None
    image_checks, model_checks, ollama_checks, discovery = _run_checks(
        discover=args.discover or orgs is not None, discover_orgs=orgs, vram_gib=args.vram_gib,
    )

    if args.json:
        payload: dict[str, Any] = {
            "images": _to_jsonable(image_checks),
            "models": _to_jsonable(model_checks),
            "ollama_models": _to_jsonable(ollama_checks),
        }
        if discovery is not None:
            payload["model_discovery"] = _discovery_jsonable(discovery)
        print(json.dumps(payload, indent=2))
    else:
        _print_report(image_checks, model_checks, ollama_checks)
        if discovery is not None:
            _print_discovery(discovery)

    if args.strict:
        any_drift = (
            any(c.up_to_date is False for c in image_checks)
            or any(c.up_to_date is False for c in model_checks)
            or any(c.up_to_date is False for c in ollama_checks)
        )
        if any_drift:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
