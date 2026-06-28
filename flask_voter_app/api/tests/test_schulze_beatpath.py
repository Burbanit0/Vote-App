"""Schulze must use the strongest-path (widest-path) beatpath correctly.

The old implementation had the Floyd–Warshall intermediate node as the INNER loop
(it must be the outer loop), kept both pairwise directions instead of zeroing the
losing one, and picked "most beatpath-wins" instead of the candidate whose path
dominates every rival. This pins the corrected method against the canonical
Wikipedia Schulze example, whose winner is E.
"""

from api.engine.utils.simulation_ranked_utils import get_schulze_winner


def test_schulze_wikipedia_example():
    groups = [
        (5, ["A", "C", "B", "E", "D"]),
        (5, ["A", "D", "E", "C", "B"]),
        (8, ["B", "E", "D", "A", "C"]),
        (3, ["C", "A", "B", "E", "D"]),
        (7, ["C", "A", "E", "B", "D"]),
        (2, ["C", "B", "A", "D", "E"]),
        (7, ["D", "C", "E", "B", "A"]),
        (8, ["E", "B", "A", "D", "C"]),
    ]
    votes = [ballot for count, ballot in groups for _ in range(count)]
    assert len(votes) == 45
    assert get_schulze_winner(votes) == "E"
