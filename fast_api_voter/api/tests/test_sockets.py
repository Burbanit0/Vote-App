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
async def test_stop_monte_carlo_aborts_loop(live_server):
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
            "num_iterations": 10_000,    # would take a while
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
async def test_disconnect_mid_run_leaves_the_server_healthy(live_server):
    """Disconnecting before completion must not crash the handler or leak
    state that breaks the next session (api/sockets/__init__.py's disconnect
    handler pops the sid's stop flag for exactly this reason)."""
    async with _connected(live_server) as client:
        await client.emit("start_monte_carlo", {
            "num_iterations": 10_000,  # long enough to still be running
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
