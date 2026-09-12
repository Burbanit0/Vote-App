"""Tests for api.engine.utils.campaign_dynamics — the balloted-winner fallback."""
import random

from api.engine.utils.campaign_dynamics import _balloted_winner


def test_balloted_winner_falls_back_and_logs_on_method_failure(monkeypatch, caplog):
    def _boom(*a, **kw):
        raise RuntimeError("ranked method exploded")

    monkeypatch.setattr(
        "api.engine.utils.simulation_ranked_utils.get_plurality_winner", _boom,
    )

    utilities = {"Alice": 0.9, "Bob": 0.4, "Carol": 0.2}
    with caplog.at_level("WARNING"):
        winner = _balloted_winner(
            utilities, list(utilities), method="plurality", rng=random.Random(0),
        )

    assert winner == "Alice"  # falls back to the plain utility-max plurality winner
    assert "campaign_dynamics.balloted_winner_failed" in caplog.text


def test_balloted_winner_falls_back_when_method_returns_no_winner(monkeypatch):
    """Distinct from the exception-path test above: here fn(ballots) returns
    cleanly but falsy (None), so `winner or _plurality_winner(utilities)` on
    the try block's own return line takes the fallback -- never raises, never
    logs, no except block involved."""
    monkeypatch.setattr(
        "api.engine.utils.simulation_ranked_utils.get_plurality_winner",
        lambda ballots: None,
    )

    utilities = {"Alice": 0.9, "Bob": 0.4, "Carol": 0.2}
    winner = _balloted_winner(
        utilities, list(utilities), method="plurality", rng=random.Random(0),
    )

    assert winner == "Alice"  # same fallback target, reached via the "or", not an exception
