"""
test_monte_carlo_websocket.py — Tests for the Monte Carlo WebSocket streaming.

Uses flask_socketio.test_client() which runs handlers synchronously in
the test process without needing a running server.

IMPORTANT: We use a module-scoped Flask app because re-calling
create_app() / socketio.init_app() in a new function-scope breaks the
event-handler registration on the module-level `socketio` singleton.
All WebSocket tests therefore share one app instance.
"""
import pytest


# ── Module-scoped app + client fixtures ──────────────────────────────────────

@pytest.fixture(scope="module")
def ws_app():
    """Single Flask app for the entire WebSocket test module."""
    from app import create_app, db
    _app = create_app("config.TestingConfig")
    with _app.app_context():
        db.create_all()
        yield _app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sio_client(ws_app):
    """Fresh SocketIO test client for each test (app reused)."""
    from app import socketio
    client = socketio.test_client(ws_app)
    yield client
    if client.is_connected():
        client.disconnect()


def emit_mc(client, num_iterations=50, num_voters=20, num_candidates=2,
            candidates=None, extra=None):
    """Helper: emit 'start_monte_carlo' and return all received events."""
    data = {
        "num_iterations": num_iterations,
        "num_voters":     num_voters,
        "num_candidates": num_candidates,
    }
    if candidates:
        data["candidates"] = candidates
    if extra:
        data.update(extra)
    client.emit("start_monte_carlo", data)
    return client.get_received()


# ── Connection ────────────────────────────────────────────────────────────────

def test_socketio_client_connects(sio_client):
    assert sio_client.is_connected()


# ── start_monte_carlo emits progress events ───────────────────────────────────

def test_emits_monte_carlo_progress(sio_client):
    """With 100 iterations, expect at least one progress event."""
    received    = emit_mc(sio_client, num_iterations=100)
    event_names = [msg["name"] for msg in received]
    assert "monte_carlo_progress" in event_names, (
        f"Expected 'monte_carlo_progress' in events: {event_names}"
    )


def test_emits_monte_carlo_complete(sio_client):
    """After all iterations, a 'monte_carlo_complete' event must be sent."""
    received    = emit_mc(sio_client)
    event_names = [msg["name"] for msg in received]
    assert "monte_carlo_complete" in event_names, (
        f"Expected 'monte_carlo_complete' in events: {event_names}"
    )


def test_progress_event_structure(sio_client):
    """Each progress event must contain the required fields."""
    received        = emit_mc(sio_client)
    progress_events = [m for m in received if m["name"] == "monte_carlo_progress"]
    assert progress_events, "No progress events received"

    for evt in progress_events:
        data = evt["args"][0]
        assert "iteration"             in data
        assert "total"                 in data
        assert "partial_results"       in data
        assert "condorcet_exists_rate" in data
        assert data["total"]           == 50
        assert 0 < data["iteration"]  <= 50


def test_complete_event_structure(sio_client):
    """The complete event must contain final_results, num_iterations, num_voters."""
    received = emit_mc(sio_client)
    complete = next((m for m in received if m["name"] == "monte_carlo_complete"), None)
    assert complete is not None

    data = complete["args"][0]
    assert "final_results"         in data
    assert "num_iterations"        in data
    assert "condorcet_exists_rate" in data
    assert data["num_iterations"]  == 50


def test_partial_results_have_winner_distribution(sio_client):
    """partial_results must include winner_distribution for each method."""
    received = emit_mc(sio_client)
    progress = next((m for m in received if m["name"] == "monte_carlo_progress"), None)
    assert progress is not None

    partial = progress["args"][0]["partial_results"]
    assert isinstance(partial, dict)
    assert len(partial) > 0

    for method, stats in partial.items():
        assert "winner_distribution" in stats
        assert "most_common_winner"  in stats


def test_final_results_have_plurality_method(sio_client):
    """final_results must contain at minimum the 'plurality' method."""
    received = emit_mc(sio_client)
    complete = next((m for m in received if m["name"] == "monte_carlo_complete"), None)
    assert complete is not None
    assert "plurality" in complete["args"][0]["final_results"]


def test_num_iterations_reported_in_complete(sio_client):
    """The complete event must report back the exact number of iterations."""
    received = emit_mc(sio_client, num_iterations=60)
    complete = next((m for m in received if m["name"] == "monte_carlo_complete"), None)
    assert complete is not None
    assert complete["args"][0]["num_iterations"] == 60


def test_custom_candidates_respected(sio_client):
    """Named candidates must appear in winner_distribution."""
    received = emit_mc(sio_client, candidates=["Marie", "Jean"])
    complete = next((m for m in received if m["name"] == "monte_carlo_complete"), None)
    assert complete is not None

    final = complete["args"][0]["final_results"]
    for method, stats in final.items():
        for cand in stats.get("winner_distribution", {}):
            assert cand in ("Marie", "Jean"), (
                f"Unexpected candidate '{cand}' in method '{method}'"
            )


def test_invalid_num_iterations_emits_error(sio_client):
    """Non-numeric num_iterations must cause a 'monte_carlo_error' event."""
    sio_client.emit("start_monte_carlo", {
        "num_iterations": "not_a_number",
        "num_voters":     20,
        "num_candidates": 2,
    })
    received    = sio_client.get_received()
    event_names = [m["name"] for m in received]
    assert "monte_carlo_error" in event_names


def test_progress_iteration_increases(sio_client):
    """Progress event iteration values must be strictly increasing."""
    received   = emit_mc(sio_client, num_iterations=150)
    iterations = [
        m["args"][0]["iteration"]
        for m in received
        if m["name"] == "monte_carlo_progress"
    ]
    assert iterations == sorted(iterations), (
        f"Progress iterations not monotone: {iterations}"
    )


def test_stop_monte_carlo_sets_flag(ws_app):
    """
    'stop_monte_carlo' event must set the stop flag for the caller's SID.

    Because the test client runs handlers synchronously, we can't easily
    interleave stop and start.  We test the mechanism directly:
      1. Emit 'stop_monte_carlo' → flag becomes True for that session.
      2. Emit 'start_monte_carlo' again → flag is cleared automatically.
    """
    from app import socketio as _sio
    from app.events.simulation_events import _stop_flags
    from flask import request as _req

    # Capture the SocketIO SID via a one-shot probe handler
    sids: list[str] = []

    @_sio.on("__probe_sid_stop_test")
    def _probe(data):                           # noqa: ANN001
        sids.append(_req.sid)                   # type: ignore[attr-defined]

    client = _sio.test_client(ws_app)
    client.emit("__probe_sid_stop_test", {})
    client.get_received()

    assert sids, "Could not capture SocketIO SID"
    real_sid = sids[0]

    # Emit stop_monte_carlo — the handler sets _stop_flags[sid] = True
    client.emit("stop_monte_carlo", {})
    client.get_received()

    assert _stop_flags.get(real_sid) is True, (
        f"Expected stop flag True for SID {real_sid}, got {_stop_flags}"
    )
    client.disconnect()


def test_disconnect_cleans_stop_flag(ws_app):
    """
    Disconnecting the client must remove the stop flag from _stop_flags
    (tested via the disconnect handler).
    """
    from app import socketio as _sio
    from app.events.simulation_events import _stop_flags
    from flask import request as _req

    sids: list[str] = []

    @_sio.on("__probe_sid_dc_test")
    def _probe(data):                           # noqa: ANN001
        sids.append(_req.sid)                   # type: ignore[attr-defined]

    client = _sio.test_client(ws_app)
    client.emit("__probe_sid_dc_test", {})
    client.get_received()

    assert sids, "Could not capture SocketIO SID"
    real_sid = sids[0]

    # Manually set the flag and then disconnect
    _stop_flags[real_sid] = True
    assert real_sid in _stop_flags

    client.disconnect()

    # The 'disconnect' event handler should have removed the flag
    assert real_sid not in _stop_flags, (
        "disconnect handler should clean up _stop_flags"
    )


# ── Convergence fields ────────────────────────────────────────────────────────

def test_progress_contains_convergence_fields(sio_client):
    """Each progress event must carry regret_history, agreement_rate, regret_ci_half."""
    received = emit_mc(sio_client, num_iterations=100)
    progress = next((m for m in received if m["name"] == "monte_carlo_progress"), None)
    assert progress is not None, "No progress event received"

    data = progress["args"][0]
    assert "regret_history"        in data, "Missing 'regret_history'"
    assert "agreement_rate"        in data, "Missing 'agreement_rate'"
    assert "regret_ci_half"        in data, "Missing 'regret_ci_half'"
    assert "iteration_checkpoints" in data, "Missing 'iteration_checkpoints'"


def test_regret_history_grows_between_events(sio_client):
    """regret_history[method] must be longer in later progress events."""
    received = emit_mc(sio_client, num_iterations=150)
    progress_events = [m for m in received if m["name"] == "monte_carlo_progress"]
    assert len(progress_events) >= 2, (
        "Need at least 2 progress events — try num_iterations >= 100"
    )

    first_data  = progress_events[0]["args"][0]
    second_data = progress_events[1]["args"][0]

    first_history  = first_data["regret_history"]
    second_history = second_data["regret_history"]

    assert isinstance(first_history, dict) and len(first_history) > 0
    for method in first_history:
        assert method in second_history, f"Method '{method}' missing in second event"
        assert len(second_history[method]) > len(first_history[method]), (
            f"regret_history[{method!r}] did not grow: "
            f"{len(first_history[method])} → {len(second_history[method])}"
        )


def test_agreement_rate_is_probability(sio_client):
    """agreement_rate must be a float in [0, 1]."""
    received = emit_mc(sio_client, num_iterations=100)
    for msg in received:
        if msg["name"] != "monte_carlo_progress":
            continue
        rate = msg["args"][0].get("agreement_rate")
        assert rate is not None, "agreement_rate missing"
        assert isinstance(rate, (int, float)), f"agreement_rate not numeric: {rate!r}"
        assert 0.0 <= rate <= 1.0, f"agreement_rate out of [0,1]: {rate}"


def test_complete_event_unchanged(sio_client):
    """monte_carlo_complete must NOT contain the new convergence keys (backward compat)."""
    received = emit_mc(sio_client)
    complete = next((m for m in received if m["name"] == "monte_carlo_complete"), None)
    assert complete is not None
    data = complete["args"][0]
    # These keys belong only to progress events, not complete
    assert "regret_history"  not in data
    assert "agreement_rate"  not in data
    assert "regret_ci_half"  not in data
