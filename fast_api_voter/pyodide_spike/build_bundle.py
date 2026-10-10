"""Zip the engine for Pyodide: `api/` without its web, socket, polity and test layers,
this spike's dispatcher, and structlog (pure Python, a hard import of the engine's
logger). Usage, from fast_api_voter/: python -m pyodide_spike.build_bundle OUT.zip"""

import sys
import zipfile
from pathlib import Path

import structlog

SKIP = {"tests", "routes", "sockets", "polity", "__pycache__"}
ROOT = Path(__file__).resolve().parent.parent


def add_tree(z: zipfile.ZipFile, src: Path, arc: str) -> None:
    for p in sorted(src.rglob("*.py")):
        rel = p.relative_to(src)
        if SKIP.intersection(rel.parts) or rel.name == "main.py":
            continue
        z.write(p, f"{arc}/{rel}")


with zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED) as z:
    add_tree(z, ROOT / "api", "api")
    add_tree(z, ROOT / "pyodide_spike", "pyodide_spike")
    add_tree(z, Path(structlog.__file__).parent, "structlog")
    print(len(z.namelist()), "files")
