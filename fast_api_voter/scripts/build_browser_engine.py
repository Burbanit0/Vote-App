"""Zip the engine for the browser (api/browser.py, EXP-023, PLAN_BEYOND_CI W6).

The zip holds the `api` modules that `api.browser` can reach, and the pure-Python packages
it needs that Pyodide does not provide, copied from this environment so the browser runs
the server's own versions. Both lists follow the code: the `api` modules from every import
statement, at module level or inside a function (a worker importing lazily is still
shipped), and the third-party packages from those statements plus what importing
`api.browser` loads. The build fails on a package neither provided by Pyodide nor bundled.

Usage, from fast_api_voter/:  python scripts/build_browser_engine.py OUT.zip
"""

from __future__ import annotations

import ast
import importlib
import json
import subprocess
import sys
import sysconfig
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Loaded by the worker from Pyodide's own distribution (`pyodide.loadPackage`).
PYODIDE = {"numpy", "pydantic", "pydantic_core", "annotated_types", "typing_inspection"}
#: Pure Python, bundled at this environment's versions. typing_extensions too: the bundled
#: anyio needs a newer one than Pyodide's, and the bundle comes first on sys.path.
BUNDLED = {"fastapi", "starlette", "anyio", "annotated_doc", "structlog", "typing_extensions"}
#: Imported only on a path the browser never takes, or only because they happen to be
#: installed here, with importers that do without them: the result cache's Redis (only
#: when REDIS_URL is set), Starlette's form parser (python_multipart), structlog's greenlet
#: support and console renderer (greenlet, rich, colorama, pygments), and what rich
#: imports (attr...).
OPTIONAL = {"redis", "python_multipart", "multipart", "greenlet", "rich", "colorama", "pygments",
            "attr", "markdown_it", "mdurl", "_cffi_backend"}


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


def closure() -> dict[str, str | None]:
    """Module name -> file, for everything `import api.browser` loads."""
    code = "import json, sys, api.browser; print(json.dumps({n: getattr(m, '__file__', None) for n, m in list(sys.modules.items())}))"
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    loaded: dict[str, str | None] = json.loads(out.stdout.strip().splitlines()[-1])
    return loaded


def installed(loaded: dict[str, str | None]) -> set[str]:
    """The top-level installed (non-stdlib) packages among the loaded modules."""
    site = {Path(sysconfig.get_paths()[k]).resolve() for k in ("purelib", "platlib")}
    return {name.split(".")[0] for name, file in loaded.items()
            if file and any(Path(file).resolve().is_relative_to(s) for s in site)}


def bundled() -> dict[str, Path]:
    """Archive name -> source, for every file of the BUNDLED packages."""
    entries: dict[str, Path] = {}
    for name in sorted(BUNDLED):
        file = importlib.import_module(name).__file__
        if file is None:
            raise SystemExit(f"{name} has no source file to bundle")
        source = Path(file)
        if source.name != "__init__.py":  # a single-file module
            entries[source.name] = source
            continue
        package = source.parent
        compiled = [p.name for p in package.rglob("*") if p.suffix in {".so", ".pyd"}]
        if compiled:
            raise SystemExit(f"{name} is not pure Python ({compiled[:3]}): Pyodide cannot load it from the zip")
        for path in package.rglob("*.py"):
            entries[(Path(name) / path.relative_to(package)).as_posix()] = path
    return entries


def build(out: Path) -> list[str]:
    files, imported = api_closure()
    packages = imported | installed(closure())
    unexpected = packages - PYODIDE - BUNDLED - OPTIONAL
    if unexpected:
        raise SystemExit(f"api.browser imports packages the browser has no copy of: {sorted(unexpected)}")
    entries = {path.relative_to(ROOT).as_posix(): path for path in files} | bundled()
    # Sorted, with a fixed date: the same sources give the same zip, byte for byte.
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for arcname in sorted(entries):
            z.writestr(zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0)), entries[arcname].read_bytes(),
                       compress_type=zipfile.ZIP_DEFLATED)
    return sorted(entries)


if __name__ == "__main__":
    names = build(Path(sys.argv[1]))
    print(f"{len(names)} files")
