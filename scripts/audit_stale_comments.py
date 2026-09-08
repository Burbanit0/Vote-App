#!/usr/bin/env python3
"""Heuristic staleness scan for comments and docstrings — Lot 6.1, phase 1.

Comments are the one part of this repo no gate looks at: not compiled, not
type-checked, not run. This script is the first of the two tooling approaches
the plan proposes for finding candidates worth a human/LLM triage pass (the
second — a batched LLM read of (comment, code) pairs — is a separate item to
compare it against).

Heuristic: `git blame` each comment/docstring block and the code line right
after it. When the code was touched significantly more recently than the
comment above it, the comment likely still describes an earlier version of
that code — it's a candidate, not a verdict. Categorising the output into the
plan's four buckets (périmé / redondant / archéologique / pourquoi) is manual
work for the next phase; this script only ranks where to start looking.

Default threshold is 1 day: on this repo's full history (1553 commits back to
2025-03-01 — see EXP-001 in docs/exploration/ for how a shallow/truncated
clone can make it look otherwise), that already surfaces ~330 candidates with
real gaps up to a year, roughly 6% of scanned blocks. A tighter threshold
would just add noise from ordinary same-week edits; a much looser one would
mostly drop candidates rather than add signal, since the distribution is
already sparse above a few weeks.

Precision caveat (see docs/comment-audit/README.md): on a 5-candidate manual
check spanning the top of the ranking, all 5 were genuine time-skew but none
were an actually-stale comment — the code nearby had changed for unrelated
reasons (a type annotation, reformatting) while the comment stayed accurate.
Treat this script's output as a search-space reduction for a content-aware
triage pass, not as a staleness verdict on its own.

Usage (from repo root):
    python scripts/audit_stale_comments.py
    python scripts/audit_stale_comments.py --threshold-days 90 --top 300
"""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_TARGETS = ["fast_api_voter/api", "voter-app/src"]

# Generated artifacts (Lot 12.2): auditing their "comments" is meaningless.
EXCLUDE_SUFFIXES = (".gen.ts", ".gen.json", ".d.ts")
EXCLUDE_NAMES = {"engineParity.json", "package-lock.json"}
EXCLUDE_DIR_PARTS = {"node_modules", "__pycache__", ".venv", "dist", "build", "__fixtures__"}

SOURCE_EXTENSIONS = {".py", ".ts", ".tsx"}

BLAME_HEADER_RE = re.compile(r"^([0-9a-f]{40}) \d+ (\d+)")
ZERO_SHA = "0" * 40


@dataclass
class Candidate:
    path: Path
    start_line: int
    end_line: int
    snippet: str
    comment_date: datetime
    anchor_line: int
    anchor_date: datetime

    @property
    def gap_days(self) -> int:
        return (self.anchor_date - self.comment_date).days


def iter_source_files(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        base = ROOT / target
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix not in SOURCE_EXTENSIONS or not path.is_file():
                continue
            if EXCLUDE_DIR_PARTS & set(path.relative_to(ROOT).parts):
                continue
            if path.name in EXCLUDE_NAMES or path.name.endswith(EXCLUDE_SUFFIXES):
                continue
            files.append(path)
    return sorted(files)


def git_blame_dates(path: Path) -> dict[int, datetime]:
    """Map 1-based line number -> commit author date, for the current HEAD."""
    result = subprocess.run(
        ["git", "blame", "--line-porcelain", "HEAD", "--", str(path.relative_to(ROOT))],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    line_sha: dict[int, str] = {}
    sha_time: dict[str, int] = {}
    current_sha: str | None = None
    for raw_line in result.stdout.splitlines():
        header = BLAME_HEADER_RE.match(raw_line)
        if header:
            current_sha = header.group(1)
            line_sha[int(header.group(2))] = current_sha
            continue
        if raw_line.startswith("author-time ") and current_sha is not None:
            sha_time[current_sha] = int(raw_line.split(" ", 1)[1])
    return {
        line_no: datetime.fromtimestamp(sha_time[sha], tz=timezone.utc)
        for line_no, sha in line_sha.items()
        if sha != ZERO_SHA and sha in sha_time
    }


def classify_python(lines: list[str]) -> list[bool]:
    """True per line if it's a `#` comment or a standalone docstring statement."""
    is_comment = [False] * len(lines)
    in_triple: str | None = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if in_triple is not None:
            is_comment[i] = True
            if in_triple in stripped:
                in_triple = None
            continue
        if stripped.startswith("#"):
            is_comment[i] = True
            continue
        for quote in ('"""', "'''"):
            if stripped.startswith(quote):
                is_comment[i] = True
                if stripped.count(quote) < 2:
                    in_triple = quote
                break
    return is_comment


def classify_ts(lines: list[str]) -> list[bool]:
    """True per line if it's a `//` line comment or inside a `/* */` block."""
    is_comment = [False] * len(lines)
    in_block = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if in_block:
            is_comment[i] = True
            if "*/" in stripped:
                in_block = False
            continue
        if stripped.startswith("//"):
            is_comment[i] = True
            continue
        if stripped.startswith("/*"):
            is_comment[i] = True
            if "*/" not in stripped[2:]:
                in_block = True
    return is_comment


def comment_blocks(is_comment: list[bool]) -> list[tuple[int, int]]:
    """Contiguous runs of comment lines, as 0-based (start, end-inclusive)."""
    blocks: list[tuple[int, int]] = []
    start: int | None = None
    for i, flag in enumerate(is_comment):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            blocks.append((start, i - 1))
            start = None
    if start is not None:
        blocks.append((start, len(is_comment) - 1))
    return blocks


def find_candidates(path: Path, threshold_days: int) -> list[Candidate]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    lines = text.splitlines()
    if not lines:
        return []

    is_comment = classify_python(lines) if path.suffix == ".py" else classify_ts(lines)
    blame = git_blame_dates(path)

    candidates: list[Candidate] = []
    for start, end in comment_blocks(is_comment):
        block_dates = [blame[i + 1] for i in range(start, end + 1) if (i + 1) in blame]
        if not block_dates:
            continue
        comment_date = max(block_dates)

        anchor = next(
            (i for i in range(end + 1, len(lines)) if lines[i].strip() and not is_comment[i]),
            None,
        )
        if anchor is None or (anchor + 1) not in blame:
            continue
        anchor_date = blame[anchor + 1]

        if (anchor_date - comment_date).days >= threshold_days:
            candidates.append(
                Candidate(
                    path=path,
                    start_line=start + 1,
                    end_line=end + 1,
                    snippet=lines[start].strip()[:100],
                    comment_date=comment_date,
                    anchor_line=anchor + 1,
                    anchor_date=anchor_date,
                )
            )
    return candidates


def write_report(candidates: list[Candidate], output: Path, threshold_days: int, top: int) -> None:
    candidates.sort(key=lambda c: c.gap_days, reverse=True)
    shown, hidden = candidates[:top], candidates[top:]

    lines = [
        "# Candidats à commentaires périmés (généré)",
        "",
        f"Généré par `scripts/audit_stale_comments.py` — heuristique (a) du Lot 6.1 :"
        f" `git blame` sur chaque bloc de commentaire vs. la ligne de code qui le suit,"
        f" seuil de {threshold_days} jours d'écart.",
        "",
        "**Ceci est une liste de candidats, pas un verdict.** Chaque ligne est à trier"
        " manuellement (ou via l'approche (b), passe LLM) dans une des quatre catégories"
        " du Lot 6.1 avant toute correction.",
        "",
        f"{len(candidates)} candidats au-dessus du seuil"
        + (f", {len(shown)} affichés ci-dessous" if hidden else "")
        + ".",
        "",
        "| Fichier | Lignes | Écart (j) | Commentaire touché | Code touché | Aperçu |",
        "|---|---|---|---|---|---|",
    ]
    for c in shown:
        rel = c.path.relative_to(ROOT)
        lines.append(
            f"| `{rel}` | {c.start_line}-{c.end_line} | {c.gap_days} "
            f"| {c.comment_date.date()} | {c.anchor_date.date()} "
            f"| {c.snippet.replace('|', chr(92) + '|')} |"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", nargs="+", default=DEFAULT_TARGETS)
    parser.add_argument("--threshold-days", type=int, default=1)
    parser.add_argument("--top", type=int, default=150)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "docs" / "comment-audit" / "candidates.md"
    )
    args = parser.parse_args()

    all_candidates: list[Candidate] = []
    for path in iter_source_files(args.targets):
        all_candidates.extend(find_candidates(path, args.threshold_days))

    write_report(all_candidates, args.output, args.threshold_days, args.top)
    try:
        shown_path = args.output.relative_to(ROOT)
    except ValueError:
        shown_path = args.output
    print(f"{len(all_candidates)} candidates written to {shown_path}")


if __name__ == "__main__":
    main()
