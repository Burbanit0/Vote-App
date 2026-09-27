"""Ballot format equivalence: a ranking may arrive as a plain list
(`["A", "B", "C"]`) or as a dict with a "ranking" key
(`{"ranking": ["A", "B", "C"]}`) — every ordinal rule must treat the two
identically. `_is_dict_format`/`_get_ranking` exist specifically to unwrap
the dict form.

CORRECTION (found by `/code-review ultra`, verified by tracing every real
caller): an earlier version of this docstring claimed
`api/domain/simulations/base.py` produces dict-formatted ballots in real,
non-test code. That's wrong — base.py's `"ranking"` dict keys are on
per-voter EXPORT records (paired with `"voter_id"`, for CSV/audit output),
not the shape fed into these rules. Every actual caller, traced end to
end (`simul.py`'s `simulate_ranked_voters`, `real_election_data.py`'s
`convert_to_rankings` — explicitly typed `-> List[List[str]]` — and every
`compare_all_methods`/`get_*_winner` call site under `api/domain/`),
extracts `voter["ranking"]` into a plain list BEFORE calling any rule.
No schema under `api/schemas/` models a ranking as a dict either. So the
dict-format branch these 19+ functions share currently has no live
caller anywhere in this backend (`api/domain/polity/` is a different,
separately-developed subsystem, out of scope here).

That doesn't make the branch pointless to test: it's real code, in the
functions' own accepted `Any`-typed contract, reachable by any future
caller (or direct API/script use outside this backend) without anyone
touching simulation_ranked_utils.py itself — a silent break there would
have zero warning today. It does mean the honest framing is "protects an
existing, currently-unexercised contract branch," not "closes a live
production gap."

WHY THIS FILE EXISTS. mutmut 3.8.0's first real (uncrashed) run found that
`is_dict = _is_dict_format(votes)` mutated to `is_dict = None` survives on
every single rule that reads it — 19+ functions sharing the exact same
gap, because nothing in this suite has ever called a rule with
dict-formatted ballots. Same shape of bug as test_anonymity.py's: a real
code path with zero direct test pressure, found by a mutation tool
rather than by reading the code. See
docs/plan/vote-app/PLAN_REMEDIATION_CI_CD.md §2.1 for the mutation-score
investigation this came out of.
"""

import pytest

from api.engine.utils import simulation_ranked_utils as ranked

# Every public rule in the module, discovered rather than listed — same
# convention as test_anonymity.py's RULE_NAMES, for the same reason: a rule
# added later is covered without anyone remembering to add it here.
RULE_NAMES = sorted(
    name
    for name in dir(ranked)
    if name.startswith("get_") and name.endswith("_winner")
)

# A small spread, not exhaustive: a Condorcet cycle (exercises pairwise
# comparisons), an unambiguous single winner (3 first-choices to 1 and 1 —
# verified via get_plurality_winner, not assumed: an earlier version of
# this profile was actually a 2-2 tie resolved only by the alphabetical
# tie-break, which meant two of the three profiles below exercised
# tie-break code and none exercised a genuine single-winner path), and an
# exact tie (exercises tie-break code deliberately, on the unwrapped
# rankings just as much as the main path).
PROFILES = [
    [["A", "B", "C"], ["B", "C", "A"], ["C", "A", "B"]],
    [["A", "B", "C"], ["A", "C", "B"], ["A", "B", "C"], ["B", "A", "C"], ["C", "A", "B"]],
    [["A", "B"], ["B", "A"]],
]


def _as_dict_ballots(ballots: list[list[str]]) -> list[dict[str, list[str]]]:
    return [{"ranking": ballot} for ballot in ballots]


def test_the_rule_list_is_not_empty():
    """A discovery bug that silently found no rules would make every test
    below pass vacuously."""
    assert len(RULE_NAMES) >= 20


@pytest.mark.parametrize("rule_name", RULE_NAMES)
def test_dict_and_list_ballots_produce_the_same_winner(rule_name):
    rule = getattr(ranked, rule_name)
    for ballots in PROFILES:
        list_result = rule(ballots)
        dict_result = rule(_as_dict_ballots(ballots))
        assert dict_result == list_result, (
            f"{rule_name} disagrees between list- and dict-formatted "
            f"ballots for the same profile: list -> {list_result!r}, "
            f"dict -> {dict_result!r}.\n  ballots: {ballots}"
        )

