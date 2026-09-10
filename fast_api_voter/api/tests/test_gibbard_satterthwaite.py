"""Tests for api.engine.utils.gibbard_satterthwaite — manipulability estimation."""
from api.engine.utils.gibbard_satterthwaite import compute_manipulability_index


def test_manipulability_index_falls_back_and_logs_on_method_failure(monkeypatch, caplog):
    def _boom(*a, **kw):
        raise RuntimeError("ranked method exploded")

    monkeypatch.setattr(
        "api.engine.utils.simulation_ranked_utils.get_plurality_winner", _boom,
    )

    ballots = [
        ["Alice", "Bob", "Carol"],
        ["Bob", "Alice", "Carol"],
        ["Carol", "Bob", "Alice"],
    ]
    with caplog.at_level("WARNING"):
        result = compute_manipulability_index("plurality", ballots, num_trials=3)

    # Every method_fn(...) call raises, so no manipulation is ever detected —
    # the function still returns a well-formed (if degenerate) result rather
    # than propagating the exception.
    assert result["method"] == "plurality"
    assert result["num_manipulators"] == 0
    assert "gibbard_satterthwaite.sincere_winner_failed" in caplog.text
    assert "gibbard_satterthwaite.manipulated_winner_failed" in caplog.text
