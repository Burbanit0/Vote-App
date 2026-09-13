"""
Shared `except Exception` boilerplate (CODE_AUDIT.md §7 item 5).

Lot 2 (`.semgrep/vote-app-rules.yml`'s `except-exception-without-log`) already
closed the *dangerous* version of this pattern across api/ — a bare
`except Exception` with no log call at all. Every remaining site already logs;
this module centralises the *shape* of what commonly follows the log call, to
cut the boilerplate duplication, not to fix an observability gap.

Two shapes cover most of the corpus:

  - "Compute with fallback": a value is computed, and on failure a default is
    used instead while the caller keeps running (or returns the default
    itself). Use `safe_call`.
  - "Handler wrapping": a route/worker step's contract is `(body, status)`
    (see the `voter-api` conventions), and on failure both become the error
    response. Use `log_and_error_response` — called *from inside* the
    existing `except Exception as exc:` block, not as a replacement for the
    try/except itself. Many call sites parse/validate input *outside* the
    guarded region (a separate `except (TypeError, ValueError)` above, or
    code that runs after), so a decorator wrapping the whole function would
    silently widen what gets caught — an actual behaviour change, not just a
    refactor. This only replaces the log-call + return-tuple tail.

Not every `except Exception` site reduces to either shape — a fire-and-forget
best-effort retry with no return value in play, a per-iteration
partial-result accumulator inside a loop (append a bespoke fallback item and
`continue`), or an async handler that also emits a client notification, don't
fit cleanly. Those are intentionally left as plain try/except at the call
site rather than forced through here.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Tuple, TypeVar

T = TypeVar("T")

ErrorBody = Dict[str, Any]


def safe_call(
    fn: Callable[[], T],
    fallback: Callable[[], T],
    *,
    log: Any,
    event: str,
    level: str = "warning",
    **log_kwargs: Any,
) -> T:
    """Run `fn()`; on any Exception, log it and run `fallback()` instead.

    Centralises:

        try:
            x = fn()
        except Exception:
            log.<level>(event, ..., exc_info=True)
            x = fallback()

    Both `fn` and `fallback` are zero-arg callables (typically `lambda:`), so
    the fallback is only ever evaluated when actually needed — several real
    call sites compute a non-trivial fallback (another engine call) that the
    original code also only ran on the failure path.

    `log` is the caller's own module logger (`get_logger(__name__)`), so the
    emitted event still carries the calling module's name. `**log_kwargs` are
    forwarded as structured fields (e.g. `method=method_name`).
    """
    try:
        return fn()
    except Exception:
        getattr(log, level)(event, exc_info=True, **log_kwargs)
        return fallback()


def log_and_error_response(
    log: Any,
    event: str,
    body: ErrorBody,
    *,
    level: str = "error",
    status: int = 500,
    **log_kwargs: Any,
) -> Tuple[ErrorBody, int]:
    """Log `event` (with `exc_info=True`) and return `(body, status)`.

    Centralises the tail of the "handler wrapping" shape. Called from
    *inside* the existing `except Exception as exc:` block:

        except Exception as exc:
            return log_and_error_response(
                log, "simulation.compare.failed", {"error": str(exc)},
            )

    It does not build `body` for the caller — error bodies vary per site (a
    bare `{"error": ...}`, a `{"success": False, "error": ..., "message":
    ...}` triple, ...) — so the caller builds the exact dict it already
    built, and this just logs it and wires up the `(body, status)` return
    contract worker functions already use.
    """
    getattr(log, level)(event, exc_info=True, **log_kwargs)
    return body, status
