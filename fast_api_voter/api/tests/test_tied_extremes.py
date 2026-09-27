"""Best / worst method is a SET when methods tie -- and they usually do.

Methods producing the same outcome score exactly the same, so the top of a
per-method score is shared far more often than not: 25-33 of 34 methods on
/interpret's regret, 4 or 5 of 5 on most /jury runs, up to 31 of 34 on
/polarization. Four endpoints used to answer `min(d, key=d.get)`, naming
whichever tied method came first, and /interpret and /jury put that name in
their prose. (/polarization had a "X est la méthode la plus robuste" finding
too, gated on an index above 0.2 that its electorates never exceed -- 0.225 is
the ceiling for a perfect split between the two extremes -- so it was deleted.)
"""
from api.domain.election import jury, multiwinner_compare
from api.domain.election._helpers import prose_list, tied_extremes


def test_tied_extremes_returns_every_tied_key_in_order():
    scores = {"a": 1.0, "b": 3.0, "c": 1.0, "d": 3.0, "e": 2.0}
    assert tied_extremes(scores) == (["a", "c"], ["b", "d"])
    # Reordering the input cannot change who is in either set.
    low, high = tied_extremes(dict(reversed(scores.items())))
    assert set(low) == {"a", "c"} and set(high) == {"b", "d"}


def test_tied_extremes_names_nothing_when_nothing_stands_out():
    assert tied_extremes({"a": 0.5, "b": 0.5}) == ([], [])
    assert tied_extremes({}) == ([], [])


def test_prose_list():
    assert prose_list(["a"]) == "a"
    assert prose_list(["a", "b", "c"]) == "a, b et c"
    assert prose_list(list("abcdef")) == "a, b, c et 3 autres"
    assert prose_list(["a", "b"], conj="and", others="others") == "a and b"


JURY = {"num_voters": 51, "voter_competence": 0.52, "correct_option_index": 0,
        "num_simulations": 60}


def test_jury_names_every_method_tied_at_the_top():
    body, status = jury({**JURY, "num_options": 3, "seed": 3})
    assert status == 200
    assert body["best_method"] == ["plurality", "borda"]
    assert "Plurality et borda atteignent 96.7%" in body["pedagogical_note"]
    assert "Plurality and borda reach 96.7%" in body["pedagogical_note_en"]


def test_jury_singular_when_one_method_leads():
    body, _ = jury({**JURY, "num_options": 3, "seed": 0})
    assert body["best_method"] == ["borda"]
    assert "Borda atteint 100.0%" in body["pedagogical_note"]


def test_jury_crowns_no_method_when_all_five_tie():
    body, _ = jury({**JURY, "num_options": 2, "seed": 1})
    assert body["best_method"] == [] and body["worst_method"] == []
    assert "Toutes les méthodes atteignent" in body["pedagogical_note"]
    assert "Every method reaches" in body["pedagogical_note_en"]


def test_multiwinner_reports_the_tied_sets():
    cands = [{"name": f"C{i}", "x": x, "y": 0.0}
             for i, x in enumerate((-0.8, -0.3, 0.0, 0.3, 0.8, 0.5))]
    body, status = multiwinner_compare(
        {"candidates": cands, "num_voters": 200, "num_seats": 3, "seed": 1}
    )
    assert status == 200
    distortion = {m: md["distortion"] for m, md in body["methods"].items()}
    assert (body["best_method"], body["worst_method"]) == tied_extremes(distortion)


def test_polarization_crowns_no_single_method_from_a_tie(client):
    cands = [{"name": "Alice", "x": -0.5, "y": -0.2}, {"name": "Bob", "x": 0.5, "y": 0.2},
             {"name": "Carol", "x": 0.0, "y": 0.3}, {"name": "Dan", "x": 0.3, "y": -0.6}]
    body = client.post("/api/v2/election/polarization",
                       json={"seed": 0, "candidates": cands}).json()
    for row in body["results"]:
        assert (row["best_method"], row["worst_method"]) == tied_extremes(row["method_regrets"])
