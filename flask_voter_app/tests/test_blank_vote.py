"""
Tests for the blank-vote feature.

Three scenarios:
  1. Blank wins a plurality election (heavily dissatisfied electorate).
  2. IRV paradox: all real candidates are eliminated successively;
     blank survives and wins the final round.
  3. BlankVoteRule transitions on the same raw result.

Pure logic tests — no Flask app context required.
"""

import pytest
from app.utils.simulation_ranked_utils import (
    get_plurality_winner,
    get_irv_winner,
    get_condorcet_winner,
    get_borda_winner,
    get_schulze_winner,
)
from app.utils.blank_vote_rules import BlankVoteRule, apply_blank_rule
from app.utils.simulation_metrics import _insert_blank


# ── Helpers ────────────────────────────────────────────────────────────────

BLANK = "Blank"


# ── 1. _insert_blank ────────────────────────────────────────────────────────

class TestInsertBlank:
    def test_blank_inserted_at_threshold_boundary(self):
        utils = {"Alice": 0.7, "Bob": 0.4, "Carol": 0.2}
        sorted_names = ["Alice", "Bob", "Carol"]
        result = _insert_blank(sorted_names, utils, blank_threshold=0.5, blank_name=BLANK)
        assert result == ["Alice", BLANK, "Bob", "Carol"]

    def test_blank_first_when_all_below_threshold(self):
        utils = {"Alice": 0.3, "Bob": 0.2}
        result = _insert_blank(["Alice", "Bob"], utils, blank_threshold=0.8, blank_name=BLANK)
        assert result[0] == BLANK

    def test_blank_last_when_all_above_threshold(self):
        utils = {"Alice": 0.9, "Bob": 0.8}
        result = _insert_blank(["Alice", "Bob"], utils, blank_threshold=0.1, blank_name=BLANK)
        assert result[-1] == BLANK

    def test_blank_inserted_exactly_once(self):
        utils = {"Alice": 0.6, "Bob": 0.5, "Carol": 0.4}
        result = _insert_blank(["Alice", "Bob", "Carol"], utils, 0.45, BLANK)
        assert result.count(BLANK) == 1


# ── 2. Blank wins plurality ─────────────────────────────────────────────────

class TestBlankWinsPlurality:
    """
    60 voters so dissatisfied they rank Blank first.
    25 voters prefer Alice.
    15 voters prefer Bob.
    Plurality first-choice count: Blank=60, Alice=25, Bob=15 → Blank wins.
    """

    @pytest.fixture
    def rankings(self):
        return (
            [[BLANK, "Alice", "Bob"]] * 60
            + [["Alice", BLANK, "Bob"]] * 25
            + [["Bob", "Alice", BLANK]] * 15
        )

    def test_blank_wins_plurality(self, rankings):
        assert get_plurality_winner(rankings, blank_candidate_name=BLANK) == BLANK

    def test_alice_wins_without_blank(self):
        # Same dissatisfied voters but without blank in rankings
        rankings_no_blank = (
            [["Alice", "Bob"]] * 60  # their "sincere" preference among real candidates
            + [["Alice", "Bob"]] * 25
            + [["Bob", "Alice"]] * 15
        )
        assert get_plurality_winner(rankings_no_blank) == "Alice"

    def test_blank_also_wins_condorcet(self, rankings):
        # Blank beats Alice (60+15=75 vs 25) and beats Bob (60+25=85 vs 15)
        assert get_condorcet_winner(rankings, blank_candidate_name=BLANK) == BLANK

    def test_blank_pct_calculation(self, rankings):
        blank_first = sum(1 for r in rankings if r[0] == BLANK)
        assert blank_first == 60
        assert round(blank_first / len(rankings), 4) == 0.6


# ── 3. IRV paradox: blank wins last round ──────────────────────────────────

class TestIRVBlankWinsLastRound:
    """
    Constructed so that every real candidate is eliminated before blank:

    25 voters: [Blank, Alice, Bob, Carol]
    30 voters: [Alice, Blank, Bob, Carol]
    25 voters: [Bob, Blank, Carol, Alice]
    20 voters: [Carol, Blank, Bob, Alice]

    Round 1: Blank=25, Alice=30, Bob=25, Carol=20 → Carol eliminated (fewest)
    Round 2: Blank=25+20=45, Alice=30, Bob=25        → Bob eliminated (fewest)
    Round 3: Blank=45+25=70, Alice=30                → Blank wins majority
    """

    @pytest.fixture
    def rankings(self):
        return (
            [[BLANK, "Alice", "Bob", "Carol"]] * 25
            + [["Alice", BLANK, "Bob", "Carol"]] * 30
            + [["Bob", BLANK, "Carol", "Alice"]] * 25
            + [["Carol", BLANK, "Bob", "Alice"]] * 20
        )

    def test_irv_blank_wins(self, rankings):
        assert get_irv_winner(rankings, blank_candidate_name=BLANK) == BLANK

    def test_irv_alice_wins_without_blank(self):
        """Without blank, Alice should win (most real-candidate support)."""
        rankings_no_blank = (
            [["Alice", "Bob", "Carol"]] * 25
            + [["Alice", "Bob", "Carol"]] * 30
            + [["Bob", "Carol", "Alice"]] * 25
            + [["Carol", "Bob", "Alice"]] * 20
        )
        winner = get_irv_winner(rankings_no_blank)
        assert winner == "Alice"  # 25+30=55 vs Bob/Carol

    def test_borda_treats_blank_as_candidate(self, rankings):
        winner = get_borda_winner(rankings, blank_candidate_name=BLANK)
        # Blank and Alice compete for top; result should be deterministic
        assert winner in {BLANK, "Alice", "Bob", "Carol"}

    def test_schulze_treats_blank_as_candidate(self, rankings):
        winner = get_schulze_winner(rankings, blank_candidate_name=BLANK)
        assert winner is not None


# ── 4. BlankVoteRule transitions ────────────────────────────────────────────

class TestBlankVoteRules:
    """
    Same raw result: Alice wins with 32 % blank vote.
    Each rule produces a different constitutional outcome.
    """

    def _result(self, rule, winner="Alice", blank_pct=0.32, blank_vs_winner_pct=0.35):
        return apply_blank_rule(
            winner=winner,
            blank_pct=blank_pct,
            rule=rule,
            blank_name=BLANK,
            blank_vs_winner_pct=blank_vs_winner_pct,
        )

    def test_symbolic_real_winner_is_kept(self):
        r = self._result(BlankVoteRule.SYMBOLIC)
        assert r["winner"] == "Alice"
        assert r["blank_triggered"] is False

    def test_symbolic_blank_winner_is_annulled(self):
        r = apply_blank_rule(
            winner=BLANK, blank_pct=0.45,
            rule=BlankVoteRule.SYMBOLIC, blank_name=BLANK,
        )
        assert r["winner"] is None
        assert r["blank_triggered"] is True

    def test_competitive_blank_winner_stands(self):
        r = apply_blank_rule(
            winner=BLANK, blank_pct=0.45,
            rule=BlankVoteRule.COMPETITIVE, blank_name=BLANK,
        )
        assert r["winner"] == BLANK
        assert r["blank_triggered"] is True

    def test_competitive_real_winner_stands(self):
        r = self._result(BlankVoteRule.COMPETITIVE)
        assert r["winner"] == "Alice"
        assert r["blank_triggered"] is False

    def test_threshold_30_triggered_at_32_pct(self):
        r = self._result(BlankVoteRule.THRESHOLD_30)
        assert r["blank_triggered"] is True
        assert r["winner"] is None

    def test_threshold_30_not_triggered_at_29_pct(self):
        r = apply_blank_rule(
            winner="Alice", blank_pct=0.29,
            rule=BlankVoteRule.THRESHOLD_30, blank_name=BLANK,
        )
        assert r["blank_triggered"] is False
        assert r["winner"] == "Alice"

    def test_majority_required_not_triggered_when_blank_minority(self):
        # 35% prefer blank over Alice → Alice keeps the win
        r = self._result(BlankVoteRule.MAJORITY_REQUIRED, blank_vs_winner_pct=0.35)
        assert r["blank_triggered"] is False
        assert r["winner"] == "Alice"

    def test_majority_required_triggered_when_blank_majority(self):
        # 51% prefer blank over Alice → mandate contested
        r = apply_blank_rule(
            winner="Alice", blank_pct=0.32,
            rule=BlankVoteRule.MAJORITY_REQUIRED, blank_name=BLANK,
            blank_vs_winner_pct=0.51,
        )
        assert r["blank_triggered"] is True
        assert r["winner"] is None

    def test_result_always_contains_required_keys(self):
        for rule in BlankVoteRule:
            r = self._result(rule)
            assert {"winner", "blank_triggered", "consequence", "blank_pct", "rule"} == set(r.keys())

    def test_consequence_is_non_empty_string(self):
        for rule in BlankVoteRule:
            r = self._result(rule)
            assert isinstance(r["consequence"], str)
            assert len(r["consequence"]) > 0
