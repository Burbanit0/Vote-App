"""Read a polity run's LLM exchanges as a conversation: who was asked, what they were
told, what they thought and what they answered. Works on a finished run, or live with
--follow while the run is writing.

    python scripts/show_llm_exchanges.py <run dir> [--follow] [--tick N] [--type president_turn]
                                         [--citizen 197] [--no-system] [--all-kinds]

`llm_calls.jsonl`, written by every LLM run, holds each call's reasoning and answer. The
prompts are in `llm_prompts.jsonl` only when the run was started with POLITY_LOG_PROMPTS=1;
without it the reader says so and shows the rest.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TextIO

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.llm_call_log import CALL_LOG_FILENAME, PROMPT_LOG_FILENAME  # noqa: E402


def _rows(handle: TextIO) -> Iterator[dict[str, Any]]:
    """The complete JSON lines written so far; a half-written last line waits for the next read."""
    while True:
        pos = handle.tell()
        line = handle.readline()
        if not line.endswith("\n"):
            handle.seek(pos)
            return
        if line.strip():
            yield json.loads(line)


class Prompts:
    """The prompts sidecar read incrementally (the format of llm_call_log.PromptLogWriter)."""

    def __init__(self, path: Path) -> None:
        self.handle = path.open(encoding="utf-8") if path.exists() else None
        self.blobs: dict[str, str] = {}
        self.calls: dict[str, dict[str, Any]] = {}

    def get(self, call_id: str) -> dict[str, str | None] | None:
        if self.handle is not None:
            for row in _rows(self.handle):
                if "blob" in row:
                    self.blobs[row["blob"]] = row["text"]
                else:
                    self.calls[row["call_id"]] = row
        refs = self.calls.get(call_id)
        if refs is None:
            return None
        return {field: refs[field] for field in ("system", "user")}


def _answer(content: str | None) -> str:
    try:
        return json.dumps(json.loads(content or ""), indent=2, ensure_ascii=False)
    except ValueError:
        return content or "(no answer)"


def render(
    call: dict[str, Any],
    prompts: Prompts,
    seen_system: dict[str, int | None],
    show_system: bool,
) -> str:
    who = ", ".join(str(u) for u in call.get("unit_ids") or []) or "-"
    head = [
        f"tick {call.get('tick')}",
        str(call.get("decision_type") or call.get("kind")),
        f"citizen {who}",
    ]
    if call.get("attempt"):
        head.append(f"retry {call['attempt']}")
    head.append(
        f"{call.get('completion_tokens', '?')} tokens, {(call.get('latency_ms') or 0) / 1000:.1f} s"
    )
    if call.get("finish_reason") not in (None, "stop"):
        head.append(f"finish: {call['finish_reason']}")
    out = ["━━ " + " · ".join(head)]
    refs = prompts.get(call["call_id"])
    if refs is None:
        if prompts.handle is not None:
            out.append("── (no prompt recorded for this call)")
    else:
        system, user = refs["system"], refs["user"]
        if system is not None and show_system:
            if system in seen_system:
                out.append(f"── system: unchanged since tick {seen_system[system]}")
            else:
                seen_system[system] = call.get("tick")
                out += ["── system", prompts.blobs[system]]
        if user is not None:
            out += ["── user", prompts.blobs[user]]
    if call.get("reasoning"):
        out += ["── reasoning", call["reasoning"].strip()]
    if call.get("error"):
        out += ["── error", call["error"]]
    out += ["── answer", _answer(call.get("content")), ""]
    return "\n".join(out)


def wanted(call: dict[str, Any], args: argparse.Namespace) -> bool:
    return (
        (args.all_kinds or call.get("kind") == "decision")
        and (args.tick is None or call.get("tick") == args.tick)
        and (args.type is None or call.get("decision_type") == args.type)
        and (args.citizen is None or args.citizen in (call.get("unit_ids") or []))
    )


def main(argv: list[str] | None = None, out: TextIO = sys.stdout) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("run_dir", type=Path)
    parser.add_argument(
        "--follow", action="store_true", help="keep reading as the run writes"
    )
    parser.add_argument("--tick", type=int)
    parser.add_argument(
        "--type",
        help="a decision type, e.g. president_turn, pressure_action, vote_cast",
    )
    parser.add_argument("--citizen", type=int, help="calls that include this citizen")
    parser.add_argument("--no-system", action="store_true", help="hide system prompts")
    parser.add_argument(
        "--all-kinds", action="store_true", help="also warm-up and token-budget probes"
    )
    args = parser.parse_args(argv)

    calls_path = args.run_dir / CALL_LOG_FILENAME
    if not calls_path.exists():
        print(
            f"no {CALL_LOG_FILENAME} in {args.run_dir} (a deterministic run, or not started yet)",
            file=sys.stderr,
        )
        return 1
    prompts = Prompts(args.run_dir / PROMPT_LOG_FILENAME)
    if prompts.handle is None:
        print(
            f"no {PROMPT_LOG_FILENAME}: start the run with POLITY_LOG_PROMPTS=1 to keep the prompts",
            file=sys.stderr,
        )
    seen_system: dict[str, int | None] = {}
    with calls_path.open(encoding="utf-8") as calls:
        while True:
            for call in _rows(calls):
                if wanted(call, args):
                    print(
                        render(call, prompts, seen_system, not args.no_system),
                        file=out,
                        flush=True,
                    )
            if not args.follow:
                return 0
            time.sleep(
                1
            )  # ponytail: polls once a second; inotify if a live view ever needs less lag


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:  # piped into head/less and closed: not an error
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        raise SystemExit(0) from None
    except KeyboardInterrupt:
        raise SystemExit(0) from None
