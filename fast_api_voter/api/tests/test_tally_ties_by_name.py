"""An exact tie in an election tally goes to the first name, as the engine's
plurality, approval and Borda break it. These sites used `max(tally)` or
`Counter.most_common`, which pick whichever candidate was listed or counted
first -- so the same profile could get a different winner here than from the
engine. Where the engine elects nobody (an IRV dead tie), so do they."""
from api.domain.election.workers_behavioral import _nota_worker
from api.domain.election.workers_mechanisms import _jury_worker
from api.domain.simulations.compare import _irv_steps, _schulze_matrices
from api.domain.simulations.helpers import _parse_candidate_configs
from api.domain.theory.workers import _identity_plurality
from api.engine.utils.quadratic_voting import apply_quadratic_voting
from api.engine.utils.simulation_ranked_utils import get_irv_winner, get_schulze_winner

# Every candidate beats and loses to the other equally often.
FULL_TIE = [["Bob", "Alice"], ["Alice", "Bob"]]
CYCLE = [["Alice", "Bob", "Carol"], ["Bob", "Carol", "Alice"], ["Carol", "Alice", "Bob"]]


# Alice and Bob are both unbeaten by strongest path; Bob wins more duels.
UNBEATEN_PAIR = ([["Carol", "Alice", "Bob"]] * 5 + [["Bob", "Alice", "Carol"]] * 4
                 + [["Alice", "Bob", "Carol"]] * 3 + [["Bob", "Carol", "Alice"]] * 2
                 + [["Carol", "Bob", "Alice"]])


def test_schulze_steps_elect_whom_the_rule_elects_and_show_its_paths():
    """The animation counted beat-path wins and fell back to the first-listed
    candidate, so it named Bob here where Schulze elects Alice. Its path matrix
    also seeded losing duels, so it could not always explain the winner."""
    for profile, listed in ((FULL_TIE, ["Bob", "Alice"]), (CYCLE, ["Carol", "Bob", "Alice"]),
                            (UNBEATEN_PAIR, ["Alice", "Bob", "Carol"])):
        _, paths, winner = _schulze_matrices(profile, listed)
        assert winner == get_schulze_winner(profile) == "Alice"
        assert all(paths[winner][o] >= paths[o][winner] for o in listed if o != winner)


def test_quadratic_voting_breaks_a_tie_by_name_as_its_comment_says():
    """The comment said "tie -> alphabetical first"; the code took the first key,
    and handed each voter's odd leftover vote to the first-listed of two
    equally rated candidates, so it was Bob 4-3 when Bob was listed first."""
    for voter in ({"Bob": 0.5, "Alice": 0.5}, {"Alice": 0.5, "Bob": 0.5}):
        assert apply_quadratic_voting([voter], budget=30)["winner"] == "Alice"


def test_counted_ties_go_to_the_first_name_not_the_first_counted():
    assert _identity_plurality(["Bob", "Alice"], ["Bob", "Alice"]) == "Alice"


def test_a_tied_election_with_no_shy_voters_is_polled_right():
    """25-25. With the social-desirability factor at 0 the poll is the vote, so
    it can't be wrong -- unless the real and polled winners break the tie
    differently, as they did for one commit of this change."""
    from api.domain.election.workers_behavioral import _shy_voter_worker
    body, _ = _shy_voter_worker({
        "num_voters": 50, "seed": 0, "shy_candidate_idx": 0, "ideology": "centrist", "num_polls": 3,
        "candidates": [{"name": "Bob", "x": 0.3, "y": 0.0}, {"name": "Alice", "x": -0.3, "y": 0.0}],
    })
    assert body["real_results"] == {"Bob": 0.5, "Alice": 0.5} and body["real_winner"] == "Alice"
    assert body["social_desirability_curve"][0]["winner_wrong_pct"] == 0.0


def test_irv_steps_show_a_dead_tie_as_no_winner():
    """25-25: every candidate is tied for last, and get_irv_winner elects nobody.
    The animation used to crown Alice, the first name eliminated."""
    profile = [["Bob", "Alice"]] * 25 + [["Alice", "Bob"]] * 25
    assert _irv_steps(profile, 50)[-1]["winner"] is None is get_irv_winner(profile)


def test_irv_steps_eliminate_a_candidate_nobody_ranks_first():
    """Carol has no first preference. The engine eliminates her first and then
    finds a three-way dead tie; the animation used to protect her and elect her."""
    profile = [["Alice", "Carol", "Bob", "Dave"], ["Bob", "Carol", "Alice", "Dave"],
               ["Dave", "Carol", "Alice", "Bob"]]
    assert _irv_steps(profile, 3)[-1]["winner"] == get_irv_winner(profile)


def test_nota_voids_an_election_only_by_beating_every_candidate():
    """NOTA ties the leader 16-16 here. Whether that voided the election
    depended on how the candidates' names sorted against "NOTA"."""
    for names in (("Alice", "Bob", "Carol"), ("Zoe", "Yann", "Xavier"), ("alice", "bob", "carol")):
        cands = [{"name": n, "x": x, "y": y}
                 for n, (x, y) in zip(names, ((-0.5, -0.2), (0.5, 0.2), (0.0, 0.1)))]
        body, _ = _nota_worker({"num_voters": 50, "seed": 48, "nota_threshold": 0.65, "candidates": cands})
        assert body["election_valid"] is True, names


def test_jury_accuracy_does_not_depend_on_which_option_is_correct():
    """Ten jurors at p=0.5 over two options tie a quarter of the time. Options
    are named in index order and ties went by name, so every tie counted as
    correct when the answer was option 0 (about 0.62) and wrong otherwise (0.38)."""
    for idx in (0, 1):
        body, _ = _jury_worker({"num_voters": 10, "num_options": 2, "voter_competence": 0.5,
                                "num_simulations": 500, "seed": 7, "correct_option_index": idx})
        for m in ("plurality", "approval", "borda", "schulze"):
            assert 0.44 < body["methods"][m]["accuracy"] < 0.56, (idx, m)


def test_candidate_names_are_strings():
    """An int name made the engine return int winners in some runs and str in
    others, and ranking those tallies raised TypeError (a 500)."""
    assert _parse_candidate_configs([{"name": 1}, "Bob"])[0]["name"] == "1"
