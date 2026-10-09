"""reseat: a run's recorded legislative votes re-allocated at another threshold (PLAN_BEYOND_CI W2.2)."""
from __future__ import annotations

import dataclasses
import json

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


def test_an_amended_threshold_applies_from_the_next_election():
    founding = {"run": {"seed": 1}, "institutions": {"electoral_threshold": 0.05, "seat_allocation": "dhondt", "assembly_seats": 10}}
    votes = {"0": 60.0, "1": 36.0, "2": 4.0}  # party 2 has 4%
    events = [
        _legislative(4, votes, {"0": 6, "1": 4, "2": 0}),
        {"tick": 6, "event_type": "constitution_amended",
         "payload": {"article": "institutions.electoral_threshold", "old": 0.05, "new": 0.03, "version": 1, "source": "vote"}},
        _legislative(12, votes, {"0": 6, "1": 4, "2": 0}),
    ]
    first, second = reseat(events, founding)
    assert first["threshold_in_force"] == 0.05 and second["threshold_in_force"] == 0.03
    assert first["reseated_seats"]["2"] == 0  # below 5%
    assert second["reseated_parties_seated"] == first["reseated_parties_seated"]  # 4% of 10 seats rounds to 0 under D'Hondt
    assert reseat(events, founding, threshold=0.0)[0]["threshold_applied"] == 0.0
