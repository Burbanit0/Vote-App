"""CI facts the docs restate, read from the files that own them.

Used by the cog blocks in CONTRIBUTING.md and .claude/skills/voter-ci/SKILL.md
(scripts/check_generated_docs.sh). Those counts drifted by hand twice: 11 then 21
workflows, 15 then 16 required checks.
"""
from __future__ import annotations

import re
from pathlib import Path

from check_ci_health import parse_setup_script_expectations

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
BRANCHES = ("polity", "develop", "main", "polity-ui")

# A table row whose first cell names a workflow: "| `e2e.yml` (E2E Tests) | ...",
# with or without the .github/workflows/ prefix.
_ROW = re.compile(r"^\|\s*`(?:\.github/workflows/)?([\w.-]+\.ya?ml)`")


def workflow_files() -> list[str]:
    return sorted(p.name for p in WORKFLOWS.iterdir() if p.suffix in {".yml", ".yaml"})


def required_contexts(branch: str) -> list[str]:
    """What setup-branch-protection.sh applies to `branch` (its own --print-contexts,
    read the same way the ci-health drift check reads it)."""
    return parse_setup_script_expectations(branch)[0]


def workflow_table_drift(doc: str | Path) -> list[str]:
    """How the doc's workflow table disagrees with .github/workflows/: a file with
    no row, a row for a file that's gone, a file with two rows."""
    rows: list[str] = []
    for line in Path(doc).read_text(encoding="utf-8").splitlines():
        m = _ROW.match(line)
        if m:
            rows.append(m.group(1))
    files = workflow_files()
    problems = [f"no row for {f}" for f in files if f not in rows]
    problems += [f"a row for {r}, which is not in .github/workflows/" for r in sorted(set(rows)) if r not in files]
    problems += [f"two rows for {r}" for r in sorted(set(rows)) if rows.count(r) > 1]
    return problems


def require_workflow_table_in_sync(doc: str | Path) -> None:
    problems = workflow_table_drift(doc)
    if problems:
        raise SystemExit(f"{doc}, workflow table: " + "; ".join(problems))
