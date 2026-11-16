"""api.core.cancellation — stopping a worker whose request has timed out or gone away.

Python cannot kill a thread. `worker_dispatch` therefore runs each heavy worker on a thread of its
own and, when the request times out (or the client leaves), does two things to it:

1. `Job.cancel()` sets a flag the worker can read with `cancel_check()`, and
2. raises `WorkCancelled` inside the thread (`PyThreadState_SetAsyncExc`), which stops pure-Python
   work at its next bytecode. A long C call (one large numpy operation) finishes first.

Work that fans out to threads of its own (the Monte Carlo's pool) is not reached by (2): it takes
`cancel_check()` in the parent thread and calls the result from the children.

`WorkCancelled` derives from BaseException, not Exception, so a worker's own `except Exception`
cannot swallow it.
"""
from __future__ import annotations

import contextvars
import ctypes
import threading
from typing import Callable


#: Raise `WorkCancelled` into a cancelled worker's thread (the hard stop). False: only the flag
#: is set, and a worker stops only where it polls `cancel_check()`. The hard stop is an
#: asynchronous exception: it can land between any two bytecodes, so in principle inside library
#: code that holds a lock (logging, a cache) at that instant. It is raised only into a worker whose
#: request already timed out or went away; turn it off if that trade is not wanted.
RAISE_INTO_THREAD = True


class WorkCancelled(BaseException):
    """Raised inside a worker whose request no longer wants its result."""


class Job:
    """One dispatched worker: its thread, and whether it has been told to stop."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ident: int | None = None
        self.cancelled = threading.Event()

    def attach(self) -> None:
        """Called on the worker's own thread, as it starts. A job cancelled before its thread got
        here never starts: WorkCancelled."""
        with self._lock:
            if self.cancelled.is_set():
                raise WorkCancelled
            self._ident = threading.get_ident()

    def detach(self) -> None:
        """Called on the worker's own thread, once the work has returned: after this no
        exception is raised into the thread, which may by then be doing something else."""
        with self._lock:
            self._ident = None

    def cancel(self) -> None:
        self.cancelled.set()
        with self._lock:
            if RAISE_INTO_THREAD and self._ident is not None:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(
                    ctypes.c_ulong(self._ident), ctypes.py_object(WorkCancelled)
                )


_current: contextvars.ContextVar[Job | None] = contextvars.ContextVar("worker_job", default=None)


def bind(job: Job) -> None:
    """Make `job` the current one for this context (the dispatcher's, on the worker thread)."""
    _current.set(job)


def cancel_check() -> Callable[[], None]:
    """A function that raises `WorkCancelled` once the current job has been cancelled, safe to
    call from any thread. Take it in the worker's own thread, before fanning out. A no-op outside
    a dispatched worker."""
    job = _current.get()
    if job is None:
        return lambda: None

    def check() -> None:
        if job.cancelled.is_set():
            raise WorkCancelled

    return check
