"""Exports finished polity runs for the static site (PLAN_BEYOND_CI W6, option A, step 4).

The static build has no server to read run files from, so the run explorer's answers are
written ahead, by its own workers (api/domain/polity/explorer_workers.py), into <out_dir>:

- runs.json: GET /api/v2/polity/runs;
- <key>/run.json.gz: the run's overview, its frames in the chunks the page asks for (from
  each multiple of MAX_FRAME_SPAN; voter-app/src/lib/polity/ticks.ts), and how many
  citizens each citizens file holds;
- <key>/citizens-<n>.json.gz: by id, the biographies from citizen n * CITIZENS_PER_FILE.

Gzipped and split so that no file passes the repo's 500 KB limit (checked here), and a
biography loads only its own file. voter-app/src/api/staticPolity.ts answers from them.
Everything is computed before anything is written: a run that cannot be explored stops
the export with <out_dir> untouched. The runs' folders already there are replaced.

Usage, from fast_api_voter/, with the roots as POLITY_RUN_ROOTS spells them (empty: the
committed fixture run):

    python scripts/export_polity_runs.py <out_dir> <label=path,...>
"""

from __future__ import annotations

import gzip
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.core.config import get_settings  # noqa: E402
from api.domain.polity.explorer_workers import (  # noqa: E402
    MAX_FRAME_SPAN,
    ExplorerContext,
    explorer_roots,
    list_polity_runs,
    polity_citizen,
    polity_run_frames,
    polity_run_overview,
)
from api.domain.polity.run_catalog import RunCache  # noqa: E402

#: A 30-year run's 100 biographies gzip to about 190 KB.
CITIZENS_PER_FILE = 100
#: pre-commit's check-added-large-files (--maxkb=500).
MAX_FILE_BYTES = 500 * 1024


def _ok(answer: tuple[dict[str, Any], int], what: str) -> dict[str, Any]:
    body, status = answer
    if status != 200:
        raise SystemExit(f"{what}: {status} {body}")
    return body


def _encode(name: str, value: Any) -> bytes:
    data = json.dumps(value, separators=(",", ":")).encode()
    data = gzip.compress(data, mtime=0) if name.endswith(".gz") else data + b"\n"
    if len(data) > MAX_FILE_BYTES:
        raise SystemExit(f"{name}: {len(data)} bytes, over the repo's 500 KB: lower CITIZENS_PER_FILE")
    return data


def _frames(context: ExplorerContext, key: str, last: int) -> dict[str, Any]:
    spans = [(start, min(start + MAX_FRAME_SPAN - 1, last)) for start in range(0, last + 1, MAX_FRAME_SPAN)]
    return {f"{a}-{b}": _ok(polity_run_frames(context, key, a, b), f"{key} frames {a}-{b}") for a, b in spans}


def _citizens(context: ExplorerContext, key: str, first: int, population: int) -> dict[str, Any]:
    ids = range(first, min(first + CITIZENS_PER_FILE, population))
    return {str(i): _ok(polity_citizen(context, key, i), f"{key} citizen {i}") for i in ids}


def _files(context: ExplorerContext) -> dict[str, bytes]:
    """Every file of the export, by its path in it."""
    runs = _ok(list_polity_runs(context), "runs")
    files = {"runs.json": _encode("runs.json", runs)}
    for key in (run["key"] for run in runs["runs"]):
        overview = _ok(polity_run_overview(context, key), key)
        files[f"{key}/run.json.gz"] = _encode(f"{key}/run.json.gz", {
            "overview": overview,
            "frames": _frames(context, key, overview["last_tick"]),
            "citizens_per_file": CITIZENS_PER_FILE,
        })
        for n, first in enumerate(range(0, overview["population"], CITIZENS_PER_FILE)):
            name = f"{key}/citizens-{n}.json.gz"
            files[name] = _encode(name, _citizens(context, key, first, overview["population"]))
    return files


def export(out: Path, spec: str) -> list[str]:
    """Writes every run under the roots `spec` names into `out`; returns their keys."""
    context = ExplorerContext(
        roots=explorer_roots(spec),
        max_journal_bytes=get_settings().polity_explorer_max_journal_bytes,
        cache=RunCache(1),
    )
    files = _files(context)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.iterdir():
        if old.is_dir() and re.fullmatch(r"[0-9a-f]{16}", old.name):
            shutil.rmtree(old)
    for name, data in files.items():
        (out / name).parent.mkdir(exist_ok=True)
        (out / name).write_bytes(data)
    return sorted({name.split("/")[0] for name in files if "/" in name})


if __name__ == "__main__":
    export(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "")
