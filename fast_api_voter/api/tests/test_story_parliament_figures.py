"""The parliament stories' figures, checked on the backend that computes them (PLAN_BEYOND_CI W1.3).

The guided stories' copy states seat counts and shares for three parliament stories (seuil,
structures, diviseur). Their seats are allocated here, by /api/v2/election/assembly, so the
client-side claim table (voter-app/src/lib/storyClaims.ts) cannot check them. These requests
are the ones the browser sends for each beat (voter-app/src/services/assemblyApi.ts): the
story's parties and electorate from voter-app/src/lib/stories.ts (PARL, PARL_ELECTORATE),
the beat's assembly settings, the default full turnout. Change a story there, change it here.
"""
from __future__ import annotations

from typing import Any

import pytest

PARL = [
    {"name": "Gauche", "x": -0.55, "y": -0.2},
    {"name": "Verts", "x": -0.35, "y": 0.45},
    {"name": "Centre", "x": 0.0, "y": 0.0},
    {"name": "Droite", "x": 0.5, "y": 0.15},
    {"name": "Souverainistes", "x": 0.85, "y": 0.75},
]


def _assembly(client: Any, **beat: Any) -> dict[str, Any]:
    body = {"parties": PARL, "num_voters": 1000, "ideology": "random", "seed": 17, "structure": "pr",
            "seats": 100, "threshold": 0.05, "apportionment": "dhondt", "strategic_desertion": False,
            "turnout": {"model": "full", "intensity": 0}, **beat}
    response = client.post("/api/v2/election/assembly", json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    result["by_name"] = {p["name"]: p for p in result["parties"]}
    return result


def _pct(share: float) -> int:
    return round(100 * share)


def test_seuil_the_threshold_removes_a_party_then_moves_its_votes(client: Any) -> None:
    pur = _assembly(client, threshold=0.0)
    # "the Sovereignists -- 3.4 % of the vote -- take 3 seats"
    assert pur["by_name"]["Souverainistes"]["seats"] == 3
    assert round(100 * pur["by_name"]["Souverainistes"]["vote_share"], 1) == 3.4
    barre = _assembly(client, threshold=0.05)
    # "the Sovereignists drop to zero seats. Their 3.4 % becomes wasted votes"
    assert barre["by_name"]["Souverainistes"]["seats"] == 0
    assert round(100 * barre["wasted_vote_share"], 1) == 3.4
    desertion = _assembly(client, threshold=0.05, strategic_desertion=True)
    # "the Right, which climbs from 21 % to 25 %"
    assert _pct(barre["by_name"]["Droite"]["vote_share"]) == 21
    assert _pct(desertion["by_name"]["Droite"]["vote_share"]) == 25


def test_structures_one_vote_three_parliaments(client: Any) -> None:
    pr = _assembly(client, structure="pr")
    fptp = _assembly(client, structure="fptp")
    mmp = _assembly(client, structure="mmp")
    # "The Gallagher index ... is very low" under PR
    assert pr["gallagher_index"] < 0.05
    # "the Centre, on 35 % of the vote, takes 44 % of the seats, while the Greens -- on 19 % -- fall to 9 %"
    assert _pct(fptp["by_name"]["Centre"]["vote_share"]) == 35
    assert _pct(fptp["by_name"]["Centre"]["seat_share"]) == 44
    assert _pct(fptp["by_name"]["Verts"]["vote_share"]) == 19
    assert _pct(fptp["by_name"]["Verts"]["seat_share"]) == 9
    # "Nearly a third of all votes now count for nothing"
    assert 0.28 <= fptp["wasted_vote_share"] < 1 / 3
    # MMP "restore[s] the proportions"
    assert mmp["gallagher_index"] < 0.05


@pytest.mark.parametrize(("apportionment", "centre", "souverainistes"), [("dhondt", 8, 0), ("sainte_lague", 7, 1)])
def test_diviseur_only_the_rounding_formula_changes(client: Any, apportionment: str, centre: int, souverainistes: int) -> None:
    # "A 21-seat assembly, no threshold ... the Centre takes 8 seats and the Sovereignists none" /
    # "Sainte-Lague: the Centre falls back to 7 seats and the Sovereignists gain 1"
    result = _assembly(client, seats=21, threshold=0.0, apportionment=apportionment)
    assert result["by_name"]["Centre"]["seats"] == centre
    assert result["by_name"]["Souverainistes"]["seats"] == souverainistes
