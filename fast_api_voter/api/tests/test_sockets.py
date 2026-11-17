"""Tests for Phase 4.4 — Monte Carlo Socket.IO streaming on FastAPI.

We boot the v2 ASGI app on a free port via uvicorn in a worker thread,
then drive it with python-socketio's AsyncClient. The protocol is the
same as the Flask side (Socket.IO over WebSocket), so this test also
guards against future protocol drift on the client.
"""
from __future__ import annotations

import asyncio
import contextlib
import socket
import threading
import time
from typing import Any

import pytest
import socketio
import uvicorn

import api.sockets as sockets_module


# ── Boot helper: a single shared server for the whole module ──────────────

def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server():
    """Run the FastAPI + Socket.IO ASGI app on a random local port.

    Module-scoped so the heavy uvicorn startup is paid once.
    """
    from api.main import app

    port   = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port,
                            log_level="warning", lifespan="off")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for the server to accept connections.
    deadline = time.time() + 5
    while time.time() < deadline:
        with contextlib.suppress(OSError):
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        time.sleep(0.05)
    else:
        raise RuntimeError("uvicorn did not start in time")

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5)


# ── Client helper ──────────────────────────────────────────────────────────

@contextlib.asynccontextmanager
async def _connected(url: str):
    """Yields a connected python-socketio AsyncClient pointed at our app."""
    client = socketio.AsyncClient()
    await client.connect(url, socketio_path="/api/v2/socket.io",
                         transports=["websocket"])
    try:
        yield client
    finally:
        if client.connected:
            await client.disconnect()


@pytest.fixture(autouse=True)
def _fresh_start_limiter():
    """Every test starts from an empty window: the module's runs all come from 127.0.0.1."""
    sockets_module.start_limiter.clear()
    yield
    sockets_module.start_limiter.clear()


def _slow_runs(monkeypatch, seconds: float = 0.02) -> None:
    """Each iteration takes `seconds` longer, so a 500-iteration run is still live when looked at."""
    real = sockets_module._run_one

    def slow(*args, **kwargs):
        time.sleep(seconds)
        return real(*args, **kwargs)

    monkeypatch.setattr(sockets_module, "_run_one", slow)


async def _until(predicate, tries: int = 100) -> None:
    for _ in range(tries):
        if predicate():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("the condition never became true")


# ── Tests ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_monte_carlo_progress_and_complete(live_server):
    """End-to-end: small run completes with the expected event sequence."""
    progress_events = []
    complete_event  = []

    async with _connected(live_server) as client:
        @client.on("monte_carlo_progress")
        async def _p(data):
            progress_events.append(data)

        @client.on("monte_carlo_complete")
        async def _c(data):
            complete_event.append(data)

        @client.on("monte_carlo_error")
        async def _e(data):
            complete_event.append({"error": data})

        # 50 iterations means exactly one progress emit (_EMIT_EVERY == 50)
        # plus the final one if (i+1) is not a multiple — here both coincide.
        await client.emit("start_monte_carlo", {
            "num_iterations": 50,
            "num_voters":     30,
            "num_candidates": 3,
            "ideology":       "random",
        })
        # Wait up to 10s for completion.
        for _ in range(100):
            if complete_event:
                break
            await asyncio.sleep(0.1)

    assert complete_event, "Server never emitted monte_carlo_complete"
    final = complete_event[0]
    assert "error" not in final, final
    assert final["num_iterations"] == 50
    assert final["num_voters"] == 30
    assert 0.0 <= final["condorcet_exists_rate"] <= 1.0
    assert isinstance(final["final_results"], dict)
    assert progress_events, "Expected at least one progress event"
    # The progress events should be monotonic in iteration number.
    iters = [p["iteration"] for p in progress_events]
    assert iters == sorted(iters)


@pytest.mark.asyncio
async def test_stop_monte_carlo_aborts_loop(live_server, monkeypatch):
    _slow_runs(monkeypatch, 0.01)
    progress_events = []
    stopped_event   = []
    complete_event  = []

    async with _connected(live_server) as client:
        @client.on("monte_carlo_progress")
        async def _p(data):
            progress_events.append(data)

        @client.on("monte_carlo_stopped")
        async def _s(_data):
            stopped_event.append(True)

        @client.on("monte_carlo_complete")
        async def _c(_data):
            complete_event.append(True)

        await client.emit("start_monte_carlo", {
            "num_iterations": 500,       # the most a run may ask for; slowed so it is still going
            "num_voters":     30,
            "num_candidates": 3,
            "ideology":       "random",
        })
        # Wait for the first progress emit (50 iterations) then stop.
        for _ in range(200):
            if progress_events:
                break
            await asyncio.sleep(0.05)
        assert progress_events, "Loop produced no progress before stop"

        await client.emit("stop_monte_carlo", {})

        for _ in range(100):
            if stopped_event or complete_event:
                break
            await asyncio.sleep(0.05)

    assert stopped_event, "Server never emitted monte_carlo_stopped"
    assert not complete_event, "Loop should have aborted before completion"


@pytest.mark.asyncio
async def test_concurrent_sessions_do_not_cross_contaminate(live_server):
    """Two clients running Monte Carlo at once each get their own result —
    _stop_flags is keyed by sid, so this also guards against one session's
    stop request (or disconnect) silently affecting the other."""
    results: dict[str, list[Any]] = {"a": [], "b": []}

    async def _run(key: str, num_voters: int):
        async with _connected(live_server) as client:
            @client.on("monte_carlo_complete")
            async def _c(data):
                results[key].append(data)

            await client.emit("start_monte_carlo", {
                "num_iterations": 50,
                "num_voters":     num_voters,
                "num_candidates": 3,
                "ideology":       "random",
            })
            for _ in range(100):
                if results[key]:
                    break
                await asyncio.sleep(0.1)

    await asyncio.gather(_run("a", 30), _run("b", 40))

    assert results["a"], "Session A never completed"
    assert results["b"], "Session B never completed"
    assert results["a"][0]["num_voters"] == 30
    assert results["b"][0]["num_voters"] == 40


@pytest.mark.asyncio
async def test_disconnect_mid_run_leaves_the_server_healthy(live_server, monkeypatch):
    """Disconnecting before completion must not crash the handler or leak
    state that breaks the next session (api/sockets/__init__.py's disconnect
    handler sets the sid's stop flag for exactly this reason)."""
    _slow_runs(monkeypatch)
    async with _connected(live_server) as client:
        await client.emit("start_monte_carlo", {
            "num_iterations": 500,  # the most a run may ask for, slowed below so it is still running
            "num_voters":     30,
            "num_candidates": 3,
            "ideology":       "random",
        })
        await asyncio.sleep(0.2)  # let it get into the loop
    # `_connected`'s __aexit__ disconnects here, mid-run, on purpose.

    # A fresh session afterwards must behave normally — proves the server
    # (and its shared _stop_flags dict) wasn't left in a broken state.
    complete_event: list[Any] = []
    async with _connected(live_server) as client:
        @client.on("monte_carlo_complete")
        async def _c(data):
            complete_event.append(data)

        await client.emit("start_monte_carlo", {
            "num_iterations": 50,
            "num_voters":     30,
            "num_candidates": 3,
            "ideology":       "random",
        })
        for _ in range(100):
            if complete_event:
                break
            await asyncio.sleep(0.1)

    assert complete_event, "Server did not recover after a mid-run disconnect"


@pytest.mark.asyncio
async def test_disconnect_stops_the_orphaned_run(live_server, monkeypatch):
    """A disconnected client's Monte Carlo loop must actually stop, not run
    to completion with nowhere to send its events (Lot 3,
    PLAN_SOLIDITE_TECHNIQUE.md — the "run orphelin" case). Counts real
    _run_one calls before/after disconnect: unbounded growth after
    disconnect means the loop never noticed the client left."""
    call_count = 0
    real_run_one = sockets_module._run_one

    def _counting_run_one(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        time.sleep(0.02)  # 500 of these outlast the test, so the run is live at the disconnect
        return real_run_one(*args, **kwargs)

    monkeypatch.setattr(sockets_module, "_run_one", _counting_run_one)

    async with _connected(live_server) as client:
        await client.emit("start_monte_carlo", {
            "num_iterations": 500,
            "num_voters":     30,
            "num_candidates": 3,
            "ideology":       "random",
        })
        await asyncio.sleep(0.2)  # let it get into the loop
    # Disconnects here, mid-run, on purpose.

    count_at_disconnect = call_count
    await asyncio.sleep(1.0)  # give the loop a real chance to notice and stop
    count_after_wait = call_count

    # A handful of iterations already dispatched before the disconnect was
    # noticed is fine; thousands more (the un-fixed behaviour: the loop runs
    # to num_iterations regardless) is the orphaned-run bug this pins.
    assert count_after_wait - count_at_disconnect < 20, (
        f"orphaned run kept iterating after disconnect: "
        f"{count_at_disconnect} -> {count_after_wait} _run_one calls"
    )


@pytest.mark.asyncio
async def test_invalid_payload_emits_error(live_server):
    error_event   = []
    complete_event = []

    async with _connected(live_server) as client:
        @client.on("monte_carlo_error")
        async def _e(data):
            error_event.append(data)

        @client.on("monte_carlo_complete")
        async def _c(_d):
            complete_event.append(True)

        # `num_voters` not parseable as int → ValueError in handler → emit error.
        await client.emit("start_monte_carlo", {
            "num_iterations": 10,
            "num_voters":     "not-an-int",
            "num_candidates": 3,
        })
        for _ in range(50):
            if error_event:
                break
            await asyncio.sleep(0.05)

    assert error_event, "Server never emitted monte_carlo_error"
    assert "Invalid parameters" in error_event[0]["message"]
    assert not complete_event


@pytest.mark.asyncio
async def test_run_failure_emits_error_and_logs(live_server, monkeypatch, caplog):
    """A failure *inside* a run (as opposed to bad parameters, covered above)
    — e.g. a numerical edge case in the engine — must still notify the client
    and leave a server-side trail, not fail silently."""
    def _boom(*a, **kw):
        raise RuntimeError("engine exploded mid-run")

    monkeypatch.setattr(sockets_module, "_run_one", _boom)

    error_event = []
    async with _connected(live_server) as client:
        @client.on("monte_carlo_error")
        async def _e(data):
            error_event.append(data)

        with caplog.at_level("WARNING"):
            await client.emit("start_monte_carlo", {
                "num_iterations": 5,
                "num_voters":     50,
                "num_candidates": 3,
            })
            for _ in range(50):
                if error_event:
                    break
                await asyncio.sleep(0.05)

    assert error_event, "Server never emitted monte_carlo_error"
    assert "engine exploded mid-run" in error_event[0]["message"]
    assert "sockets.monte_carlo_run_failed" in caplog.text


@pytest.mark.asyncio
async def test_run_timeout_emits_error_and_logs(live_server, monkeypatch, caplog):
    """Each run now goes through api.core.worker_dispatch.run_bounded (the
    same shared semaphore + timeout every HTTP route uses) instead of a raw
    asyncio.to_thread — PLAN_SURFACE_EXTERIEURE.md §2.A. A timeout from that
    shared bound must surface as a clean client-facing error, not hang."""
    async def _timeout(*a, **kw):
        raise asyncio.TimeoutError

    monkeypatch.setattr(sockets_module, "run_bounded", _timeout)

    error_event = []
    async with _connected(live_server) as client:
        @client.on("monte_carlo_error")
        async def _e(data):
            error_event.append(data)

        with caplog.at_level("ERROR"):
            await client.emit("start_monte_carlo", {
                "num_iterations": 5,
                "num_voters":     50,
                "num_candidates": 3,
            })
            for _ in range(50):
                if error_event:
                    break
                await asyncio.sleep(0.05)

    assert error_event, "Server never emitted monte_carlo_error"
    assert "too long" in error_event[0]["message"]
    assert "sockets.monte_carlo_run_timeout" in caplog.text


class TestMonteCarloParseInputExplicitCandidates:
    """No live_server test exercised the "explicit `candidates` list"
    branch — every one sends `num_candidates` and lets the default
    `_CANDIDATE_NAMES` fallback apply. `_monte_carlo_parse_input` is a pure
    function, so this is a direct unit test rather than a full socket
    round-trip."""

    def test_string_and_dict_entries_both_resolve_to_name_dicts(self):
        _, _, _, _, candidate_configs = sockets_module._monte_carlo_parse_input({
            "candidates": ["Alice", {"name": "Bob"}, {"other_key": "ignored"}],
        })
        assert candidate_configs == [
            {"name": "Alice"}, {"name": "Bob"}, {"name": "Cand2"},
        ]

    def test_truncated_to_eight_candidates(self):
        _, _, _, _, candidate_configs = sockets_module._monte_carlo_parse_input({
            "candidates": [f"C{i}" for i in range(12)],
        })
        assert len(candidate_configs) == 8

    def test_single_candidate_falls_back_to_defaults(self):
        # len(raw_cands) >= 2 is required; a single explicit candidate isn't
        # enough and falls back to the num_candidates/_CANDIDATE_NAMES path.
        _, _, _, _, candidate_configs = sockets_module._monte_carlo_parse_input({
            "candidates": ["Solo"], "num_candidates": 2,
        })
        assert candidate_configs == [{"name": "Alice"}, {"name": "Bob"}]


# ── What one client may ask for, and how often (P4-1) ──────────────────────

def test_the_socket_takes_the_http_bounds():
    """The same numbers as POST /simulations/monte-carlo (api/schemas/simulations.py)."""
    parse = sockets_module._monte_carlo_parse_input
    assert parse({"num_iterations": 500, "num_voters": 1000})[:2] == (500, 1000)
    assert parse({"num_iterations": 1, "num_voters": 10})[:2] == (1, 10)
    assert parse({})[:2] == (100, 150)  # the HTTP defaults for runs; voters 150 as before


@pytest.mark.parametrize("payload,word", [
    ({"num_iterations": 100.5}, "num_iterations"),
    ({"num_iterations": True}, "num_iterations"),
    ({"num_voters": float("inf")}, "num_voters"),
    ({"num_voters": float("nan")}, "num_voters"),
    ({"num_iterations": 501}, "num_iterations"),
    ({"num_iterations": 0}, "num_iterations"),
    ({"num_iterations": 10_000}, "num_iterations"),
    ({"num_voters": 1001}, "num_voters"),
    ({"num_voters": 9}, "num_voters"),
    ({"num_voters": 2_000}, "num_voters"),
])
def test_a_request_outside_the_bounds_is_refused_not_clamped(payload, word):
    with pytest.raises(ValueError, match=word):
        sockets_module._monte_carlo_parse_input(payload)


@pytest.mark.asyncio
async def test_a_request_for_more_than_http_allows_is_refused_and_nothing_runs(
    live_server, monkeypatch
):
    calls = []
    monkeypatch.setattr(sockets_module, "_run_one", lambda *a, **k: calls.append(1))
    errors: list[Any] = []
    async with _connected(live_server) as client:
        @client.on("monte_carlo_error")
        async def _e(data):
            errors.append(data)

        await client.emit("start_monte_carlo", {"num_iterations": 10_000, "num_voters": 2_000})
        await _until(lambda: errors)

    assert errors and "num_iterations must be between 1 and 500" in errors[0]["message"]
    assert not calls
    assert not sockets_module._stop_flags, "a refused request left a live-run flag behind"


@pytest.mark.asyncio
async def test_repeated_starts_from_one_address_are_limited(live_server, monkeypatch):
    monkeypatch.setattr(sockets_module, "start_limiter", sockets_module.StartLimiter(max_starts=2))
    completed: list[Any] = []
    errors: list[Any] = []
    async with _connected(live_server) as client:
        @client.on("monte_carlo_complete")
        async def _c(data):
            completed.append(data)

        @client.on("monte_carlo_error")
        async def _e(data):
            errors.append(data)

        for n in range(3):
            await client.emit("start_monte_carlo", {
                "num_iterations": 1, "num_voters": 10, "num_candidates": 2,
            })
            await _until(lambda n=n: len(completed) + len(errors) > n)

    assert len(completed) == 2
    assert len(errors) == 1 and "Too many runs" in errors[0]["message"]


@pytest.mark.asyncio
async def test_a_second_start_on_a_live_connection_is_refused(live_server, monkeypatch):
    _slow_runs(monkeypatch)
    errors: list[Any] = []
    stopped: list[Any] = []
    async with _connected(live_server) as client:
        @client.on("monte_carlo_error")
        async def _e(data):
            errors.append(data)

        @client.on("monte_carlo_stopped")
        async def _s(data):
            stopped.append(data)

        payload = {"num_iterations": 500, "num_voters": 10, "num_candidates": 2}
        await client.emit("start_monte_carlo", payload)
        await asyncio.sleep(0.2)
        await client.emit("start_monte_carlo", payload)
        await _until(lambda: errors)
        await client.emit("stop_monte_carlo", {})
        await _until(lambda: stopped)

    assert errors and "already in progress" in errors[0]["message"]
    assert stopped, "the first run was not stopped by the stop event"


@pytest.mark.asyncio
async def test_a_failed_run_leaves_no_live_flag_so_the_next_start_is_accepted(
    live_server, monkeypatch
):
    real = sockets_module._run_one
    monkeypatch.setattr(sockets_module, "_run_one", lambda *a, **k: 1 / 0)
    errors: list[Any] = []
    completed: list[Any] = []
    async with _connected(live_server) as client:
        @client.on("monte_carlo_error")
        async def _e(data):
            errors.append(data)

        @client.on("monte_carlo_complete")
        async def _c(data):
            completed.append(data)

        payload = {"num_iterations": 1, "num_voters": 10, "num_candidates": 2}
        await client.emit("start_monte_carlo", payload)
        await _until(lambda: errors)
        monkeypatch.setattr(sockets_module, "_run_one", real)
        await client.emit("start_monte_carlo", payload)
        await _until(lambda: completed)

    assert completed, f"the next start was not accepted: {errors}"


@pytest.mark.asyncio
async def test_stop_and_disconnect_without_a_run_leave_nothing_behind(live_server):
    async with _connected(live_server) as client:
        await client.emit("stop_monte_carlo", {})
        await asyncio.sleep(0.2)
        assert not sockets_module._stop_flags
    await asyncio.sleep(0.2)
    assert not sockets_module._stop_flags


def test_client_address_is_the_scope_client_else_one_shared_unknown(monkeypatch):
    def environ(env):
        monkeypatch.setattr(sockets_module.sio, "get_environ", lambda sid: env)
        return sockets_module._client_address("abc")

    # python-engineio's ASGI driver writes 127.0.0.1 into REMOTE_ADDR for everyone: not read.
    assert environ({"REMOTE_ADDR": "127.0.0.1", "asgi.scope": {"client": ("203.0.113.7", 5000)}}) == "203.0.113.7"
    assert environ({"asgi.scope": {"client": None}}) == "unknown"
    assert environ({"asgi.scope": {}}) == "unknown"
    assert environ({}) == "unknown"

    def _unknown(sid):
        raise KeyError(sid)

    monkeypatch.setattr(sockets_module.sio, "get_environ", _unknown)
    assert sockets_module._client_address("abc") == "unknown"


@pytest.mark.asyncio
async def test_a_live_connection_has_the_address_it_connected_from(live_server):
    """Through the real server: the scope's client, not the 127.0.0.1 the driver writes for all."""
    seen: list[str] = []

    @sockets_module.sio.on("probe_address")
    async def _probe(sid, _data=None):
        seen.append(sockets_module._client_address(sid))

    async with _connected(live_server) as client:
        await client.emit("probe_address", {})
        await _until(lambda: seen)

    assert seen == ["127.0.0.1"]  # the test client's real address (loopback), via the scope


@pytest.mark.asyncio
async def test_a_start_right_after_stop_is_refused_until_the_old_run_is_gone(
    live_server, monkeypatch
):
    _slow_runs(monkeypatch, 0.1)
    events: list[tuple[str, Any]] = []
    async with _connected(live_server) as client:
        for name in ("monte_carlo_error", "monte_carlo_stopped"):
            client.on(name, lambda data, name=name: events.append((name, data)))

        payload = {"num_iterations": 500, "num_voters": 10, "num_candidates": 2}
        await client.emit("start_monte_carlo", payload)
        await asyncio.sleep(0.3)
        await client.emit("stop_monte_carlo", {})
        await client.emit("start_monte_carlo", payload)
        await _until(lambda: {n for n, _ in events} >= {"monte_carlo_error", "monte_carlo_stopped"})

    errors = [d for n, d in events if n == "monte_carlo_error"]
    assert "already in progress" in errors[0]["message"]


@pytest.mark.asyncio
async def test_one_address_cannot_have_more_runs_going_than_the_limit(live_server, monkeypatch):
    _slow_runs(monkeypatch)
    errors: list[Any] = []
    payload = {"num_iterations": 500, "num_voters": 10, "num_candidates": 2}
    async with contextlib.AsyncExitStack() as stack:
        clients = [await stack.enter_async_context(_connected(live_server)) for _ in range(3)]
        clients[2].on("monte_carlo_error", lambda data: errors.append(data))
        for client in clients[:2]:
            await client.emit("start_monte_carlo", payload)
        await asyncio.sleep(0.3)
        await clients[2].emit("start_monte_carlo", payload)
        await _until(lambda: errors)

    assert "still going" in errors[0]["message"]


@pytest.mark.asyncio
async def test_the_payload_the_monte_carlo_page_sends_is_accepted(live_server):
    """What voter-app's MonteCarloResults hands useMonteCarloStream.start (the sliders' smallest
    values: 20 runs, 50 voters; candidates as the page's {name} objects; an ideology). The hook's
    own test mocks socket.io, so this is the one that shows the server takes what the page sends."""
    complete: list[Any] = []
    errors: list[Any] = []
    async with _connected(live_server) as client:
        client.on("monte_carlo_complete", lambda data: complete.append(data))
        client.on("monte_carlo_error", lambda data: errors.append(data))
        await client.emit("start_monte_carlo", {
            "num_iterations": 20,
            "num_voters":     50,
            "candidates":     [{"name": "Alice"}, {"name": "Bob"}, {"name": "Carol"}],
            "ideology":       "random",
        })
        await _until(lambda: complete or errors)

    assert not errors, errors
    assert complete[0]["num_iterations"] == 20 and complete[0]["num_voters"] == 50
