"""Tests for api.domain.election.workers_behavioral — per-method winner fallbacks."""
import api.domain.election.workers_behavioral as workers_behavioral
from api.engine.utils import method_registry


def _boom(*a, **kw):
    raise RuntimeError("method exploded")


def _break(monkeypatch, *methods: str) -> None:
    """Make each named rule raise, wherever `winner_from_utilities` looks it up.

    The dispatchers used to re-import their rules per call, so a test could
    patch the source module; they now go through the registry, which binds the
    functions once at import. Patching `simulation_score_utils` from here would
    silently no-op -- the registry entry is the live lookup.
    """
    for method in methods:
        table = (method_registry.SCORE_RULES if method in method_registry.SCORE_RULES
                 else method_registry.RANKED_RULES)
        monkeypatch.setitem(table, method, _boom)


def test_behavioral_biases_worker_falls_back_and_logs_on_method_failures(monkeypatch, caplog):
    _break(monkeypatch, "plurality", "star_voting", "majority_judgment")

    with caplog.at_level("WARNING"):
        body, status = workers_behavioral._behavioral_biases_worker(
            {"num_voters": 50, "seed": 1},
        )

    assert status == 200
    log_text = caplog.text
    assert log_text.count("workers_behavioral.method_failed") >= 6  # 3 methods x 2 calls (sincere + biased)
    assert "method=plurality" in log_text
    assert "method=star_voting" in log_text
    assert "method=majority_judgment" in log_text


def test_nota_worker_falls_back_and_logs_on_mj_failure(monkeypatch, caplog):
    _break(monkeypatch, "majority_judgment")

    with caplog.at_level("WARNING"):
        body, status = workers_behavioral._nota_worker(
            {"num_voters": 50, "seed": 1, "method": "majority_judgment"},
        )

    assert status == 200
    assert "workers_behavioral.method_failed" in caplog.text
    assert "method=majority_judgment" in caplog.text


def test_ballot_complexity_worker_falls_back_and_logs_on_method_failures(monkeypatch, caplog):
    _break(monkeypatch, "star_voting", "majority_judgment")

    with caplog.at_level("WARNING"):
        body, status = workers_behavioral._ballot_complexity_worker({
            "num_voters": 50, "seed": 1,
            "methods_to_compare": ["star_voting", "majority_judgment"],
        })

    assert status == 200
    log_text = caplog.text
    assert "workers_behavioral.method_failed" in log_text
    assert "method=star_voting" in log_text
    assert "method=majority_judgment" in log_text


def test_co_majority_judgment_falls_back_and_logs_on_failure(monkeypatch, caplog):
    # Imported at module level in workers_behavioral.py (unlike the other
    # sites' local per-call imports), so it must be patched on this module,
    # not on its source module.
    monkeypatch.setattr(workers_behavioral, "get_majority_judgment_winner", _boom)

    v_list = [{"id": 1}, {"id": 2}]
    utils = {1: {"Alice": 0.9, "Bob": 0.4}, 2: {"Alice": 0.3, "Bob": 0.8}}
    rnk = [["Alice", "Bob"], ["Bob", "Alice"]]
    cnames = ["Alice", "Bob"]

    with caplog.at_level("WARNING"):
        winner = workers_behavioral._co_majority_judgment(v_list, utils, rnk, cnames)

    assert winner in ("Alice", "Bob")  # falls back to plurality
    assert "workers_behavioral.method_failed" in caplog.text
    assert "method=majority_judgment" in caplog.text
