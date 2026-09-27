"""Regenerate the polity golden references (api/tests/golden/polity_golden.json).

Run only when a change to prompts or journal events is intentional, and say in
the commit what changed and why. Prints what moved before overwriting.

Usage (from fast_api_voter/):
    python scripts/gen_polity_golden.py
    python scripts/gen_polity_golden.py --check   # exit 1 if regeneration would change anything
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.tests.polity_golden import GOLDEN_MANIFEST, compute_manifest, describe_drift  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="report drift and exit 1 instead of writing")
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory() as work_dir:
        manifest = compute_manifest(Path(work_dir))

    previous = json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8")) if GOLDEN_MANIFEST.exists() else None
    if previous == manifest:
        print("polity golden references unchanged")
        return 0
    if previous is not None:
        print("changed:\n" + describe_drift(previous, manifest))
    if args.check:
        return 1
    GOLDEN_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {GOLDEN_MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
