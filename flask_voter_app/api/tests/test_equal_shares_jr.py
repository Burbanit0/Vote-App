"""Method of Equal Shares (Rule X) + Justified Representation axiom verifier."""

from api.engine.utils.simulation_multiwinner_utils import (
    get_equal_shares_result,
    check_justified_representation,
)

# A textbook proportionality instance: a 4-voter bloc approves only A; an 8-voter
# bloc approves {B,C,D,E}. With k=3 seats (quota = 12/3 = 4), a proportional
# committee gives the small bloc one seat (A) and the large bloc two.
BALLOTS = [["A"]] * 4 + [["B", "C", "D", "E"]] * 8


def test_equal_shares_is_proportional_and_deterministic():
    a = get_equal_shares_result(BALLOTS, 3)
    b = get_equal_shares_result(BALLOTS, 3)
    assert a == b
    assert len(a["elected"]) == 3
    # The 4-voter bloc earns its single proportional seat (A).
    assert "A" in a["elected"]
    # The other two seats come from the large bloc's candidates.
    assert sum(1 for c in a["elected"] if c in {"B", "C", "D", "E"}) == 2


def test_equal_shares_satisfies_ejr():
    elected = get_equal_shares_result(BALLOTS, 3)["elected"]
    jr = check_justified_representation(BALLOTS, elected, 3)
    assert jr == {"jr": True, "pjr": True, "ejr": True}


def test_empty_or_zero_seats():
    assert get_equal_shares_result([], 3)["elected"] == []
    assert get_equal_shares_result(BALLOTS, 0)["elected"] == []


def test_jr_detects_an_unrepresented_cohesive_bloc():
    # Ignoring the 4-voter A-bloc (= exactly one quota) violates JR.
    bad = check_justified_representation(BALLOTS, ["B", "C", "D"], 3)
    assert bad["jr"] is False
    # JR ⊆ PJR ⊆ EJR — failing JR forces the stronger axioms to fail too.
    assert bad["pjr"] is False and bad["ejr"] is False


def test_jr_holds_when_every_bloc_is_represented():
    good = check_justified_representation(BALLOTS, ["A", "B", "C"], 3)
    assert good == {"jr": True, "pjr": True, "ejr": True}


def test_jr_implications_are_consistent():
    # Across a few committees, the output never claims EJR without PJR, etc.
    for committee in (["A", "B", "C"], ["B", "C", "D"], ["A", "B", "D"]):
        r = check_justified_representation(BALLOTS, committee, 3)
        if r["ejr"]:
            assert r["pjr"]
        if r["pjr"]:
            assert r["jr"]
