"""Read a polity run's LLM exchanges as a conversation: who was asked, what they were
told, what they thought and what they answered. Works on a finished run, or live with
--follow while the run is writing (it waits for a run that has not started writing yet).

    python scripts/show_llm_exchanges.py <run dir> [--follow] [--tick N] [--type president_turn]
                                         [--citizen 197 | --party 2] [--no-system] [--all-kinds]

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
from typing import Any, BinaryIO, TextIO

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.llm_call_log import CALL_LOG_FILENAME, PROMPT_LOG_FILENAME  # noqa: E402

# The decisions whose unit_ids are party ids (llm_behavior_engine: party nomination,
# coalition); every other decision's are citizen ids.
PARTY_DECISIONS = frozenset({"party_nomination_choice", "coalition_decision"})


def _rows(handle: BinaryIO) -> Iterator[tuple[int, dict[str, Any]]]:
    """(byte offset, record) for the complete JSON lines written so far. A half-written last
    line waits for the next read; a damaged one (a run killed mid-write, then resumed) is
    skipped with a warning."""
    while True:
        pos = handle.tell()
        line = handle.readline()
        if not line.endswith(b"\n"):
            handle.seek(pos)
            return
        if not line.strip():
            continue
        try:
            yield pos, json.loads(line)
        except ValueError:
            print(
                f"skipped a damaged line at byte {pos} of {handle.name}",
                file=sys.stderr,
            )


class Prompts:
    """The prompts sidecar (the format llm_call_log.PromptLogWriter writes), read as it
    grows. A blob is kept as its line's offset and read back when shown, so a long run's
    prompts are not all held in memory."""

    def __init__(self, path: Path) -> None:
        self.handle: BinaryIO | None = path.open("rb") if path.exists() else None
        self.blobs: dict[str, int] = {}
        self.calls: dict[str, dict[str, Any]] = {}

    def get(self, call_id: str) -> dict[str, str | None] | None:
        if self.handle is not None:
            for pos, row in _rows(self.handle):
                if "blob" in row:
                    self.blobs[row["blob"]] = pos
                else:
                    self.calls[row["call_id"]] = row
        refs = self.calls.get(call_id)
        return (
            None if refs is None else {"system": refs["system"], "user": refs["user"]}
        )

    def text(self, blob: str) -> str:
        assert self.handle is not None
        end = self.handle.tell()
        self.handle.seek(self.blobs[blob])
        text = str(json.loads(self.handle.readline())["text"])
        self.handle.seek(end)
        return text

    def close(self) -> None:
        if self.handle is not None:
            self.handle.close()


def _answer(content: str | None) -> str:
    try:
        return json.dumps(json.loads(content or ""), indent=2, ensure_ascii=False)
    except ValueError:
        return content or "(no answer)"


def _who(call: dict[str, Any]) -> str:
    units = ", ".join(str(u) for u in call.get("unit_ids") or []) or "-"
    return f"{'party' if call.get('decision_type') in PARTY_DECISIONS else 'citizen'} {units}"


def render(
    call: dict[str, Any],
    prompts: Prompts,
    last_system: dict[tuple[Any, ...], tuple[str, Any]],
    show_system: bool,
) -> str:
    who = _who(call)
    head = [
        f"tick {call.get('tick')}",
        str(call.get("decision_type") or call.get("kind")),
        who,
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
        if (
            prompts.handle is not None and call.get("kind") == "decision"
        ):  # probes and warm-up never log theirs
            out.append("── (no prompt recorded for this call)")
    else:
        system, user = refs["system"], refs["user"]
        if system is not None and show_system:
            key = (call.get("decision_type"), who)
            previous = last_system.get(key)
            if previous is not None and previous[0] == system:
                out.append(
                    f"── system: unchanged since this {who.split()[0]}'s call at tick {previous[1]}"
                )
            else:
                last_system[key] = (system, call.get("tick"))
                out += ["── system", prompts.text(system)]
        if user is not None:
            out += ["── user", prompts.text(user)]
    if call.get("reasoning"):
        out += ["── reasoning", call["reasoning"].strip()]
    if call.get("error"):
        out += ["── error", call["error"]]
    out += ["── answer", _answer(call.get("content")), ""]
    return "\n".join(out)


def wanted(call: dict[str, Any], args: argparse.Namespace) -> bool:
    units = call.get("unit_ids") or []
    party = call.get("decision_type") in PARTY_DECISIONS
    return (
        (args.all_kinds or call.get("kind") == "decision")
        and (args.tick is None or call.get("tick") == args.tick)
        and (args.type is None or call.get("decision_type") == args.type)
        and (args.citizen is None or (not party and args.citizen in units))
        and (args.party is None or (party and args.party in units))
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
    who = parser.add_mutually_exclusive_group()
    who.add_argument("--citizen", type=int, help="calls that include this citizen")
    who.add_argument(
        "--party",
        type=int,
        help="party nominations and coalition calls that include this party",
    )
    parser.add_argument("--no-system", action="store_true", help="hide system prompts")
    parser.add_argument(
        "--all-kinds", action="store_true", help="also warm-up and token-budget probes"
    )
    args = parser.parse_args(argv)

    calls_path = args.run_dir / CALL_LOG_FILENAME
    if not calls_path.exists():
        if not args.follow:
            print(
                f"no {CALL_LOG_FILENAME} in {args.run_dir} (a deterministic run, or not started yet)",
                file=sys.stderr,
            )
            return 1
        print(f"waiting for {calls_path} ...", file=sys.stderr)
        while not calls_path.exists():
            time.sleep(1)
    # The run opens the prompts sidecar before its first call is logged, so once the
    # calls log exists, a missing sidecar means prompts are not being kept.
    prompts = Prompts(args.run_dir / PROMPT_LOG_FILENAME)
    if prompts.handle is None:
        print(
            f"no {PROMPT_LOG_FILENAME}: start the run with POLITY_LOG_PROMPTS=1 to keep the prompts",
            file=sys.stderr,
        )
    last_system: dict[tuple[Any, ...], tuple[str, Any]] = {}
    try:
        with calls_path.open("rb") as calls:
            while True:
                for _, call in _rows(calls):
                    if wanted(call, args):
                        print(
                            render(call, prompts, last_system, not args.no_system),
                            file=out,
                            flush=True,
                        )
                if not args.follow:
                    return 0
                time.sleep(
                    1
                )  # ponytail: polls once a second; inotify if a live view ever needs less lag
    finally:
        prompts.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:  # piped into head/less and closed: not an error
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        raise SystemExit(0) from None
    except KeyboardInterrupt:
        raise SystemExit(0) from None
