"""Zip the engine for the browser (api/browser.py, EXP-023, PLAN_BEYOND_CI W6).

The zip holds the `api` modules that `api.browser` can reach, and the pure-Python packages
it needs that Pyodide does not provide, copied from this environment so the browser runs
the server's own versions. Both lists follow the code: the `api` modules from every import
statement, at module level or inside a function (a worker importing lazily is still
shipped), and the third-party packages from those statements plus what importing
`api.browser` loads. Both are checked by distribution, file by file: the build fails on
a file whose distribution is neither provided by Pyodide nor bundled, and a bundled
distribution ships exactly its own `.py` files.

Usage, from fast_api_voter/:  python scripts/build_browser_engine.py OUT.zip
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import zipfile
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Distributions the worker loads from Pyodide's own build (`pyodide.loadPackage`).
PYODIDE = {"numpy", "pydantic", "pydantic-core", "annotated-types", "typing-inspection"}
#: Pure Python, bundled at this environment's versions. typing-extensions too: anyio needs
#: a newer one than Pyodide's, and the bundle comes first on sys.path. opentelemetry-api:
#: FastAPI imports it since 0.142, for its native telemetry, which nothing turns on here.
BUNDLED = {"fastapi", "starlette", "anyio", "annotated-doc", "structlog", "typing-extensions",
           "opentelemetry-api"}
#: Imported only on a path the browser never takes, or only because they happen to be
#: installed here, with importers that do without them: the result cache's Redis (only
#: when REDIS_URL is set), Starlette's form parser (python-multipart), structlog's greenlet
#: support and console renderer (greenlet, rich, colorama, pygments), and what rich
#: imports (attrs...).
OPTIONAL = {"redis", "python-multipart", "greenlet", "rich", "colorama", "pygments", "attrs",
            "markdown-it-py", "mdurl", "cffi"}


def _canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _files(module: str) -> list[Path]:
    """The files a dotted `api` name may be: its module or package, and its packages' inits."""
    parts = module.split(".")
    found = [ROOT.joinpath(*parts[:i], "__init__.py") for i in range(1, len(parts))]
    found += [ROOT.joinpath(*parts).with_suffix(".py"), ROOT.joinpath(*parts, "__init__.py")]
    return [p for p in found if p.is_file()]


def _imported(path: Path) -> list[str]:
    """Every dotted name an import statement in `path` may refer to, anywhere in the file."""
    package = list(path.relative_to(ROOT).parts[:-1])  # a module's package, an __init__'s own
    names: list[str] = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = ".".join(package[: len(package) - node.level + 1]) if node.level else ""
            base = ".".join(p for p in (base, node.module or "") if p)
            names += [base] + [f"{base}.{a.name}" for a in node.names]
    return names


def api_closure() -> tuple[list[Path], set[str]]:
    """The `api` files reachable from api/browser.py through any import statement, and the
    top-level packages those files import."""
    todo, seen, packages = [ROOT / "api" / "browser.py"], set(), set()
    while todo:
        path = todo.pop()
        if path not in seen:
            seen.add(path)
            for name in _imported(path):
                top = name.split(".")[0]
                todo += _files(name) if top == "api" else []
                packages.add(top)
    return sorted(seen), packages - set(sys.stdlib_module_names) - {"__future__", "", "api"}


def closure() -> list[str]:
    """The files of everything `import api.browser` loads, in a fresh interpreter (without
    coverage, which a test run would otherwise start in it)."""
    code = "import json, sys, api.browser; print(json.dumps([getattr(m, '__file__', None) for m in list(sys.modules.values())]))"
    env = {k: v for k, v in os.environ.items() if not k.startswith(("COV_CORE_", "COVERAGE_"))}
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    files: list[str] = [f for f in json.loads(out.stdout.strip().splitlines()[-1]) if f]
    return files


def distributions(loaded: list[str], tops: set[str]) -> set[str]:
    """The installed distributions behind the loaded files, and behind the top-level names
    the `api` code imports (a standard-library name has none)."""
    owner = {Path(str(d.locate_file(f))).resolve(): _canonical(d.metadata["Name"])
             for d in metadata.distributions() for f in d.files or []}
    found = {owner[p] for f in loaded if (p := Path(f).resolve()) in owner}
    by_top = metadata.packages_distributions()
    return found | {_canonical(d) for top in tops for d in by_top.get(top, [])}


def bundled() -> dict[str, Path]:
    """Archive name -> source, for every `.py` file of the BUNDLED distributions."""
    entries: dict[str, Path] = {}
    for name in sorted(BUNDLED):
        dist = metadata.distribution(name)
        for f in dist.files or []:
            if f.suffix in {".so", ".pyd"}:
                raise SystemExit(f"{name} is not pure Python ({f}): Pyodide cannot load it from the zip")
            if f.suffix == ".py":
                entries[f.as_posix()] = Path(str(dist.locate_file(f)))
    return entries


def build(out: Path) -> list[str]:
    files, tops = api_closure()
    unexpected = distributions(closure(), tops) - PYODIDE - BUNDLED - OPTIONAL
    if unexpected:
        raise SystemExit(f"api.browser imports packages the browser has no copy of: {sorted(unexpected)}")
    entries = {path.relative_to(ROOT).as_posix(): path for path in files} | bundled()
    # What the worker loads from Pyodide before importing api.browser
    # (voter-app/src/workers/engine.worker.ts reads it), so the list lives here only.
    contents = {name: path.read_bytes() for name, path in entries.items()}
    contents["engine.json"] = json.dumps({"packages": sorted(PYODIDE)}).encode()
    # Sorted, with a fixed date: the same sources give the same zip, byte for byte.
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for arcname in sorted(contents):
            z.writestr(zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0)), contents[arcname],
                       compress_type=zipfile.ZIP_DEFLATED)
    return sorted(contents)


if __name__ == "__main__":
    names = build(Path(sys.argv[1]))
    print(f"{len(names)} files")
