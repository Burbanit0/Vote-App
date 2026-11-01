"""The decision audit of finished (or running) runs: plumbing per decision type, the vote and the pressure
decisions scored against the kernel's own rules. A sweep's summary carries the same section; this reads any
run directory without running a sweep.

Usage (from fast_api_voter/):
    python scripts/audit_decisions.py ~/Documents/Dev/polity-runs/rtxpro6000-8b-baseline
    python scripts/audit_decisions.py <run_dir> <run_dir> ...

Every argument is a run directory (the one holding events.jsonl) or a root searched for them. The vote needs
llm_prompts.jsonl (POLITY_LOG_PROMPTS=1, now the flagship's default); a run without it is still audited for the rest.
"""
from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.decision_audit import audit_run, render_audit  # noqa: E402


def run_dirs(roots: Sequence[Path]) -> list[Path]:
    return sorted({journal.parent for root in roots for journal in [*root.rglob("events.jsonl")]})


def labelled(runs: Sequence[Path]) -> dict[Path, str]:
    """A run's directory name, or the tail of its path when two runs share one (a replay of the same id)."""
    names = [run.name for run in runs]
    return {run: run.name if names.count(run.name) == 1 else "/".join(run.parts[-4:]) for run in runs}


def main(argv: Sequence[str] | None = None) -> int:
    roots = [Path(a).expanduser() for a in (argv if argv is not None else sys.argv[1:])]
    if not roots:
        print(__doc__, file=sys.stderr)
        return 2
    runs = run_dirs(roots)
    if not runs:
        print("no events.jsonl under: " + ", ".join(map(str, roots)), file=sys.stderr)
        return 1
    print("\n".join(render_audit({label: audit_run(run) for run, label in labelled(runs).items()})))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
