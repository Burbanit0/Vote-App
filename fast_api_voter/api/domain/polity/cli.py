"""
api.domain.polity.cli — the run entrypoint the engine never had.

Until now `run_simulation` was reachable only from Python: every launch in
this project goes through a bespoke `scripts/run_*_acceptance.py` that
hard-codes its own arm's overrides. That is fine for a fixed experiment and
useless for anything that has to launch a run it didn't write the script for
-- a supervisor answering an HTTP request, a CI job building a fixture, or a
second terminal. This module is that missing seam and nothing more: parse
arguments, apply overrides, call `run_simulation`, record how it ended.

It holds NO simulation logic of its own. Any behaviour here that isn't
argument handling or status bookkeeping is a bug.

    python -m api.domain.polity.cli --run-id demo --output-dir runs \\
        --set run.duration_years=8 --set llm.enabled=true

Overrides are validated against the typed config's own fields, so a typo
(`--set run.duraton_years=8`) fails at startup with the offending key named,
rather than being silently dropped and discovered three hours later in a
run that quietly used the default.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import signal
import sys
import types
import typing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from api.domain.polity.config import PolityConfig, PolityConfigError, load_config
from api.domain.polity.run_polity_simulation import run_simulation

STATUS_FILENAME = "run_status.json"

# The four terminal-or-not states a run directory can report. `running` is
# written before the first tick and is the only one a reader must not trust
# on its own: nothing can update it if the process is killed with a signal
# it cannot handle (Windows `TerminateProcess`, SIGKILL), so a consumer
# reconciles it against pid liveness -- see `RUNNING`'s note in read_status.
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
INTERRUPTED = "interrupted"


class CliError(ValueError):
    """A usage problem worth reporting as a clean message, not a traceback."""


# ── override parsing ──────────────────────────────────────────────────────

def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    """(base_type, is_optional) for `X` and for `X | None`.

    config.py uses `from __future__ import annotations`, so its field types
    arrive here as strings and are resolved by `typing.get_type_hints`. In
    3.10+ that turns `int | None` into a `types.UnionType`, NOT a
    `typing.Union`, so both spellings are accepted rather than assuming
    whichever one this file happened to be written against.
    """
    args = typing.get_args(annotation)
    if args and type(None) in args:
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1:
            return non_none[0], True
    return annotation, False


def _coerce(raw: str, annotation: Any, key: str) -> Any:
    """Turn one `--set` string into the type the target field declares.

    Strict on bools on purpose. `bool("false")` is `True`, so a permissive
    cast here would turn `--set llm.enabled=false` into an LLM run -- the
    single most expensive way this could fail, three hours of GPU time
    spent proving the opposite of what was asked.
    """
    base, optional = _unwrap_optional(annotation)
    if optional and raw.lower() in {"null", "none"}:
        return None
    if base is bool:
        if raw.lower() in {"true", "1", "yes"}:
            return True
        if raw.lower() in {"false", "0", "no"}:
            return False
        raise CliError(f"--set {key}: expected a boolean (true/false), got {raw!r}")
    if base is int:
        try:
            return int(raw)
        except ValueError:
            raise CliError(f"--set {key}: expected an integer, got {raw!r}") from None
    if base is float:
        try:
            return float(raw)
        except ValueError:
            raise CliError(f"--set {key}: expected a number, got {raw!r}") from None
    if base is str:
        return raw
    raise CliError(f"--set {key}: unsupported field type {base!r} -- edit the config file instead")


def parse_overrides(pairs: Sequence[str]) -> dict[str, dict[str, Any]]:
    """`["run.seed=7", "llm.enabled=true"]` -> `{"run": {"seed": 7}, ...}`.

    Only `section.field` is accepted. A few fields are not scalars --
    `awakening.context_modulation` is a nested dataclass,
    `parties.coalition_tiebreak` a tuple, `parties.manual_platforms` a list
    -- and none of them are reachable this way: `_coerce` refuses them by
    type with a message pointing at the config file. That is the intended
    ceiling, not an oversight. `--set` exists to vary the handful of
    scalars an experiment sweeps (seed, duration, an enabled flag); a
    config whose structure is being changed wants a YAML file that can be
    read back, diffed, and committed.
    """
    parsed: dict[str, dict[str, Any]] = {}
    for pair in pairs:
        if "=" not in pair:
            raise CliError(f"--set {pair!r}: expected section.field=value")
        key, _, raw_value = pair.partition("=")
        key = key.strip()
        if key.count(".") != 1:
            raise CliError(f"--set {key!r}: expected exactly one dot, as section.field")
        section, _, field_name = key.partition(".")
        parsed.setdefault(section, {})[field_name] = (raw_value, key)
    return parsed


def apply_overrides(config: PolityConfig, pairs: Sequence[str]) -> PolityConfig:
    """Apply `--set` overrides to a loaded config, or raise naming the key.

    Deliberately built on `dataclasses.fields`, which sees declared fields
    and not properties -- so `--set run.total_ticks=40` is rejected as
    unknown. It is derived (`ticks_per_year * duration_years`), and letting
    it be set would create a config that disagrees with itself.
    """
    sections = {field.name for field in dataclasses.fields(config)} - {"raw"}
    updates: dict[str, Any] = {}
    for section, assignments in parse_overrides(pairs).items():
        if section not in sections:
            raise CliError(f"--set {section}.*: unknown config section (known: {', '.join(sorted(sections))})")
        current = getattr(config, section)
        hints = typing.get_type_hints(type(current))
        known = {field.name for field in dataclasses.fields(current)}
        replacements: dict[str, Any] = {}
        for field_name, (raw_value, key) in assignments.items():
            if field_name not in known:
                raise CliError(f"--set {key}: unknown field on '{section}' (known: {', '.join(sorted(known))})")
            replacements[field_name] = _coerce(raw_value, hints[field_name], key)
        updates[section] = dataclasses.replace(current, **replacements)
    return dataclasses.replace(config, **updates)


# ── status file ───────────────────────────────────────────────────────────

def write_status(run_dir: Path, run_id: str, status: str, **extra: Any) -> None:
    """Overwrite `run_status.json`. Never raises into the caller's `finally`.

    A failure to describe the run must not become the reason the run is
    reported as failed, so an OSError here is swallowed: the consumer's
    pid-liveness reconciliation already covers "the file says running and
    isn't", which is the same state a failed write leaves behind.
    """
    payload: dict[str, Any] = {
        "run_id": run_id,
        "status": status,
        "pid": os.getpid(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(extra)
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / STATUS_FILENAME).write_text(
            json.dumps(payload, sort_keys=True, indent=2, default=str), encoding="utf-8"
        )
    except OSError:
        pass


class _Terminated(BaseException):
    """SIGTERM, raised so the `finally` that records the status still runs.

    BaseException, not Exception: it must pass straight through the
    `except Exception` that classifies a run as `failed`. A stop requested
    by an operator is not a failure, and reporting it as one would make the
    UI's stop button look like it broke the run every single time.
    """


def _install_sigterm_handler() -> None:
    """Best-effort: turn SIGTERM into `_Terminated`.

    Effective on POSIX. On Windows `Popen.terminate()` is `TerminateProcess`,
    which no Python handler can observe, so a stopped run there leaves the
    status at `running` and the reader's pid check is what resolves it. The
    handler is still installed on Windows because `signal.SIGTERM` exists
    and `os.kill(pid, SIGTERM)` from another Python process does deliver it.
    """
    def _handler(_signum: int, _frame: types.FrameType | None) -> None:
        raise _Terminated()

    try:
        signal.signal(signal.SIGTERM, _handler)
    except (ValueError, OSError):  # pragma: no cover - non-main thread only
        pass


# ── entrypoint ────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m api.domain.polity.cli",
        description="Run one polity simulation and record how it ended.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", type=Path, default=None, help="polity_config.yaml (default: the shipped one)")
    parser.add_argument("--run-id", default=None, help="run directory name (default: config's run.run_label)")
    parser.add_argument("--output-dir", type=Path, default=None, help="override journal.output_dir")
    parser.add_argument(
        "--set", dest="overrides", action="append", default=[], metavar="section.field=value",
        help="override one typed config field; repeatable",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        config = load_config(args.config)
        if args.output_dir is not None:
            config = dataclasses.replace(
                config, journal=dataclasses.replace(config.journal, output_dir=str(args.output_dir))
            )
        config = apply_overrides(config, args.overrides)
    except (CliError, PolityConfigError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    run_id = args.run_id or config.run.run_label
    run_dir = Path(config.journal.output_dir) / run_id
    started_at = datetime.now(timezone.utc).isoformat()

    _install_sigterm_handler()
    write_status(run_dir, run_id, RUNNING, started_at=started_at, finished_at=None, exit_code=None, error=None)
    try:
        journal_path = run_simulation(config, run_id=run_id)
    except _Terminated:
        write_status(
            run_dir, run_id, INTERRUPTED, started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(), exit_code=130, error=None,
        )
        return 130
    except KeyboardInterrupt:
        write_status(
            run_dir, run_id, INTERRUPTED, started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(), exit_code=130, error=None,
        )
        return 130
    except Exception as exc:  # noqa: BLE001 - the status file is the report
        write_status(
            run_dir, run_id, FAILED, started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(), exit_code=1,
            error=f"{type(exc).__name__}: {exc}",
        )
        print(f"error: run {run_id} failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    write_status(
        run_dir, run_id, COMPLETED, started_at=started_at,
        finished_at=datetime.now(timezone.utc).isoformat(), exit_code=0, error=None,
        journal_path=str(journal_path),
    )
    print(str(journal_path))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via main()
    sys.exit(main())
