"""reseat: a run's recorded legislative votes re-allocated at another threshold (PLAN_BEYOND_CI W2.2)."""
from __future__ import annotations

import dataclasses
import json
import random

from api.domain.polity.ballot_and_aggregation import allocate_seats
from api.domain.polity.config import load_config
from api.domain.polity.reseat import reseat
from api.domain.polity.run_polity_simulation import run_simulation


def _legislative(tick, votes, seats):
    return {"tick": tick, "event_type": "legislative_result", "payload": {"votes": votes, "seats": seats, "blank_count": 0}}


def test_a_real_run_is_reproduced_at_its_own_threshold_and_moves_at_another(tmp_path):
    config = load_config()
    config = dataclasses.replace(config, journal=dataclasses.replace(config.journal, output_dir=str(tmp_path)))
    config = dataclasses.replace(config, run=dataclasses.replace(config.run, population_size=40, duration_years=2))
    journal = run_simulation(config, run_id="reseat")
    events = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines() if line.strip()]
    founding = dataclasses.asdict(config)

    rows = reseat(events, founding)
    assert rows and all(row["reseated_seats"] == row["recorded_seats"] for row in rows)
    unreachable = reseat(events, founding, threshold=1.01)  # no party can clear it
    assert all(row["reseated_enp"] is None and row["reseated_parties_seated"] == 0 for row in unreachable)


def test_an_amended_threshold_governs_every_election_journaled_after_it_its_own_tick_included():
    founding = {"run": {"seed": 1}, "institutions": {"electoral_threshold": 0.05, "seat_allocation": "dhondt", "assembly_seats": 100}}
    votes = {"0": 60.0, "1": 36.0, "2": 4.0}  # party 2 has 4%: out at 5%, in at 3%
    amend = {"tick": 12, "event_type": "constitution_amended",
             "payload": {"article": "institutions.electoral_threshold", "old": 0.05, "new": 0.03, "version": 1, "source": "vote"}}
    events = [_legislative(4, votes, {}), amend, _legislative(12, votes, {})]  # same tick: amendment first
    first, second = reseat(events, founding)
    assert (first["threshold_in_force"], second["threshold_in_force"]) == (0.05, 0.03)
    assert first["reseated_seats"]["2"] == 0 and second["reseated_seats"]["2"] > 0  # the amendment moves the seats
    fixed = reseat(events, founding, threshold=0.05)  # a fixed bar overrides the amendment
    assert fixed[1]["threshold_applied"] == 0.05 and fixed[1]["reseated_seats"]["2"] == 0


def test_amended_seat_method_and_assembly_size_are_followed():
    founding = {"run": {"seed": 1}, "institutions": {"electoral_threshold": 0.0, "seat_allocation": "dhondt", "assembly_seats": 5}}
    votes = {"0": 70.0, "1": 18.0, "2": 12.0}  # 5 seats: D'Hondt 4/1/0, Sainte-Lague 3/1/1

    def amend(tick, article, old, new):
        return {"tick": tick, "event_type": "constitution_amended",
                "payload": {"article": article, "old": old, "new": new, "version": 1, "source": "vote"}}

    events = [
        _legislative(4, votes, {}),
        amend(10, "institutions.seat_allocation", "dhondt", "sainte_lague"),
        _legislative(20, votes, {}),
        amend(30, "institutions.assembly_seats", 5, 10),
        _legislative(36, votes, {}),
    ]
    first, second, third = reseat(events, founding)
    assert first["reseated_seats"] == {"0": 4, "1": 1, "2": 0}
    assert second["reseated_seats"] == {"0": 3, "1": 1, "2": 1}
    assert sum(third["reseated_seats"].values()) == 10


def test_seat_ties_are_drawn_from_the_simulations_own_lot():
    # Two parties tied, three seats: the third is a coin toss, seeded exactly as
    # run_polity_simulation seeds it. Twelve elections: a wrong seed string would
    # have to land on the same side twelve times to pass.
    founding = {"run": {"seed": 7}, "institutions": {"electoral_threshold": 0.0, "seat_allocation": "dhondt", "assembly_seats": 3}}
    votes = {"0": 50.0, "1": 50.0}
    rows = reseat([_legislative(tick, votes, {}) for tick in range(1, 13)], founding)
    expected = [
        allocate_seats(votes, total_seats=3, method="dhondt", electoral_threshold=0.0,
                       rng=random.Random(f"legislative-seats:7:{tick}"))
        for tick in range(1, 13)
    ]
    assert [row["reseated_seats"] for row in rows] == expected
    assert len({tuple(sorted(seats.items())) for seats in expected}) == 2  # both sides do come up
