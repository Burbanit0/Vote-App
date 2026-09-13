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

Usage:
    python fast_api_voter/scripts/check_llm_stack_versions.py
    python fast_api_voter/scripts/check_llm_stack_versions.py --strict  # exit 1 on any drift
    python fast_api_voter/scripts/check_llm_stack_versions.py --json

Network access to registry-1.docker.io, hub.docker.com, huggingface.co and
registry.ollama.ai is required; any single failed lookup is reported inline
as "could not verify" rather than aborting the rest of the report.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
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
        resp = client.get(url, timeout=_TIMEOUT)
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


def _run_checks() -> tuple[list[ImageCheck], list[ModelCheck], list[OllamaModelCheck]]:
    image_pins, model_pins = _collect_pins(_FAST_API_DIR)
    image_checks: list[ImageCheck] = []
    model_checks: list[ModelCheck] = []
    ollama_checks: list[OllamaModelCheck] = []
    with httpx.Client(transport=_TRANSPORT, timeout=_TIMEOUT) as client:
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
    return image_checks, model_checks, ollama_checks


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


def _to_jsonable(checks: list[Any]) -> list[dict[str, Any]]:
    return [dataclasses.asdict(c) | {"up_to_date": c.up_to_date} for c in checks]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON instead of the text report")
    parser.add_argument("--strict", action="store_true", help="exit 1 if anything checked is not up to date")
    args = parser.parse_args(argv)

    image_checks, model_checks, ollama_checks = _run_checks()

    if args.json:
        print(
            json.dumps(
                {
                    "images": _to_jsonable(image_checks),
                    "models": _to_jsonable(model_checks),
                    "ollama_models": _to_jsonable(ollama_checks),
                },
                indent=2,
            )
        )
    else:
        _print_report(image_checks, model_checks, ollama_checks)

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
