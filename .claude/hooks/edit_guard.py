#!/usr/bin/env python3
"""PreToolUse hook on Edit / Write / MultiEdit (CI hardening plan, phase 4).

Asks the owner before an edit that:
  - adds a way to silence a check: skipped/focused/xfail tests, `# noqa`,
    `type: ignore`, `pragma: no cover`, `eslint-disable`, `@ts-ignore` /
    `@ts-expect-error`, `as any`. Each can be legitimate; none should arrive
    unnoticed in an agent's diff;
  - lowers a numeric threshold (coverage floors, type-coverage `atLeast`,
    Stryker thresholds, `fail_under`, perf ceilings raised);
  - touches a guardrail file (workflows, merge rules, these hooks and their
    settings, gate scripts and configs, scanner allowlists, baselines,
    regenerated oracles; see guardlib.GUARDRAIL_PATTERNS).
"ask", not "deny": the owner sees the reason and decides.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guardlib import ROOT, decide, is_guardrail, read_payload, rel_path  # noqa: E402

SILENCERS = {
    # Kept in step with scripts/check_test_integrity.py's JS_DISABLER / PY_DISABLERS.
    "skipped/focused test": r"(?<![\w.$])(?:it|test|describe|suite)(?:\.\w+)*?\.(?:skip|only|todo|fixme|fails|skipIf|runIf)\b"
                            r"|(?<![\w.$])x(?:it|describe|test)\s*\(|(?<![\w.$])f(?:it|describe)\s*\(",
    "pytest skip/xfail": r"pytest\.mark\.(?:skip|skipif|xfail)\b|\bpytest\.(?:skip|xfail|importorskip)\s*\(",
    "`# noqa`": r"#\s*noqa\b",
    "`type: ignore`": r"#\s*type:\s*ignore\b",
    "`pragma: no cover`": r"pragma:\s*no\s*cover",
    "`eslint-disable`": r"eslint-disable",
    "`@ts-ignore` / `@ts-expect-error`": r"@ts-(?:ignore|expect-error|nocheck)\b",
    "`as any`": r"\bas\s+any\b",
}
_SILENCERS = {k: re.compile(v) for k, v in SILENCERS.items()}
CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}

# key -> direction that weakens the gate ("down" = lowering it is the risk).
THRESHOLD_KEYS = {
    r"fail[_-]under": "down", r"cov-fail-under": "down", r"atLeast": "down",
    r"\"?(?:break|high|low)\"?\s*:": "down",  # Stryker thresholds
    r"\b(?:branches|functions|lines|statements)\s*:": "down",  # vitest coverage thresholds
    r"_CEILING_S\b": "up",  # engine perf ceilings
    r"\"?limit\"?\s*:": "up",  # size-limit budget
}
_NUM = r"(-?\d+(?:\.\d+)?)"


def edits_of(tool: str, tin: dict, current: str) -> list[tuple[str, str]]:
    if tool == "Write":
        return [(current, str(tin.get("content") or ""))]
    if tool == "MultiEdit":
        return [(str(e.get("old_string") or ""), str(e.get("new_string") or "")) for e in tin.get("edits") or []]
    return [(str(tin.get("old_string") or ""), str(tin.get("new_string") or ""))]


def added_silencers(old: str, new: str) -> list[str]:
    return [name for name, rx in _SILENCERS.items() if len(rx.findall(new)) > len(rx.findall(old))]


def weakened_thresholds(old: str, new: str) -> list[str]:
    found = []
    for key, direction in THRESHOLD_KEYS.items():
        rx = re.compile(key + r"[^\n\d-]{0,12}" + _NUM)
        before = [float(m) for m in rx.findall(old)]
        after = [float(m) for m in rx.findall(new)]
        for b, a in zip(before, after):
            if (direction == "down" and a < b) or (direction == "up" and a > b):
                found.append(f"{key.strip(chr(92))}: {b:g} -> {a:g}")
    return found


def main() -> None:
    payload = read_payload()
    tool = str(payload.get("tool_name") or "")
    tin = payload.get("tool_input") or {}
    rel = rel_path(str(tin.get("file_path") or ""))
    if not rel:
        return
    reasons = []
    if is_guardrail(rel):
        reasons.append(f"`{rel}` is part of the CI/guardrail safety net (workflows, merge rules, hooks, gate configs, "
                       "baselines, allowlists or regenerated oracles).")
    current = ""
    if tool == "Write":
        try:
            current = (ROOT / rel).read_text(encoding="utf-8")
        except OSError:
            current = ""
    pairs = edits_of(tool, tin, current)
    if Path(rel).suffix in CODE_SUFFIXES:
        silencers = sorted({s for old, new in pairs for s in added_silencers(old, new)})
        if silencers:
            reasons.append("this edit adds " + ", ".join(silencers)
                           + ": a way to make a check pass without fixing what it checks. Justify it, or fix the cause.")
    weakened = [w for old, new in pairs for w in weakened_thresholds(old, new)]
    if weakened:
        reasons.append("this edit weakens a threshold (" + "; ".join(weakened) + "). Ratchets only move the safe way.")
    if reasons:
        decide("ask", " ".join(reasons))


if __name__ == "__main__":
    main()
