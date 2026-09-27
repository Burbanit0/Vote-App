#!/usr/bin/env python3
"""run_e2e_coverage_server.py — start the FastAPI app under coverage.py and
guarantee the coverage data actually gets written to disk when the server is
stopped (Lot 6, PLAN_SOLIDITE_TECHNIQUE.md — "Couverture runtime": what does
the real e2e suite actually execute in the backend?).

Why `coverage run -m uvicorn api.main:app --port 4434` isn't enough on its
own: uvicorn's graceful-shutdown code (`uvicorn/server.py`'s
`Server.capture_signals()`) captures whatever SIGTERM/SIGINT handler was
already installed, runs its own handler while serving, and once the async
shutdown finishes, RESTORES the original handler and re-raises the captured
signal against the process -- a deliberate, well-known idiom so a process
supervisor sees the real termination signal in the exit status. That
re-raise kills the process via the raw OS signal *after* Python-level
cleanup has already run, which bypasses `atexit` entirely (atexit only
fires on normal interpreter shutdown, e.g. `sys.exit()`, never on death by
an unhandled signal) -- and coverage.py's own data-saving is atexit-based.
Verified directly before writing this workaround: `coverage run -m uvicorn
api.main:app --port 4434` followed by `kill -TERM <pid>` logs a fully
graceful "Application shutdown complete" / "Finished server process" and
still leaves NO coverage data file on disk.

The fix: install our own SIGTERM/SIGINT handler *before* uvicorn installs
its own (via `uvicorn.run()`'s internal `Server`, not `python -m uvicorn`,
so we control setup order). uvicorn's `capture_signals()` captures our
handler as the "original" one and restores + re-raises against exactly that
at the end of its own graceful shutdown -- so our handler fires exactly
once, after uvicorn's async shutdown has already completed, which is
precisely the right moment to persist coverage data before the process
actually terminates.

Usage (see scripts/e2e_coverage.sh at the repo root for the full orchestration):
    cd fast_api_voter
    COVERAGE_FILE=.coverage.e2e python -m coverage run \\
        scripts/run_e2e_coverage_server.py --port 4434
"""
from __future__ import annotations

import argparse
import signal
import sys
from types import FrameType

import coverage
import uvicorn

from api.main import app


def _save_coverage_then_reraise(sig: int, _frame: FrameType | None) -> None:
    cov = coverage.Coverage.current()
    if cov is not None:
        cov.save()
    # Restore the real default action and re-deliver so the process still
    # terminates the normal way (exit status reflects the signal, matching
    # what a process supervisor expects) -- we only needed to get in front
    # of it once to save data first.
    signal.signal(sig, signal.SIG_DFL)
    signal.raise_signal(sig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4434)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, _save_coverage_then_reraise)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
    sys.exit(0)
