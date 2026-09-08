"""viz_export.py — post-run UI-ready artifacts (Phase 6,
plan-flagship-30y-run.md, design doc §14). Hand-built event lists for the
pure-reshaping functions, same direct-call register `test_polity_indexer.py`
already uses -- the one exception is the headline end-to-end test, which
runs a real (deterministic) simulation and exports its real journal.
"""
import dataclasses
import json

from api.domain.polity.config import load_config
from api.domain.polity.indexer import index_events
from api.domain.polity.run_polity_simulation import run_simulation
from api.domain.polity.viz_export import (
    export_institutional,
    export_macro,
    export_metadata,
    export_run,
    export_social_graph,
)


def _e(tick, event_type, payload, citizen_id=None, motif=None, codebook_version=""):
    return {
        "tick": tick, "event_type": event_type, "payload": payload,
        "citizen_id": citizen_id, "motif": motif, "codebook_version": codebook_version,
    }


# ── export_macro ─────────────────────────────────────────────────────────

def test_export_macro_is_a_faithful_passthrough_of_run_metrics():
    config = load_config()
    events = [_e(0, "elected", {"winner": 5}, citizen_id=5)]
    metrics = index_events(events, config, run_id="r")

    macro = export_macro(metrics)

    assert macro["run_id"] == "r"
    assert macro["total_ticks"] == metrics.total_ticks
    assert macro["terms"][0]["holder_id"] == 5


def test_export_macro_keeps_none_for_a_disabled_metric_flag():
    config = load_config()  # legitimacy off by default
    events = [_e(0, "elected", {"winner": 5}, citizen_id=5)]
    metrics = index_events(events, config, run_id="r")

    macro = export_macro(metrics)

    assert macro["mean_legitimacy"] is None  # not [] -- "not tracked", not "tracked, empty"


def test_export_macro_is_json_serializable():
    config = load_config()
    events = [_e(0, "elected", {"winner": 5}, citizen_id=5)]
    metrics = index_events(events, config, run_id="r")

    json.dumps(export_macro(metrics))  # must not raise


# ── export_institutional ─────────────────────────────────────────────────

def test_export_institutional_includes_only_institutional_event_types():
    events = [
        _e(0, "elected", {"winner": 5}, citizen_id=5),
        _e(0, "vote_cast", {"blank": 0, "ranking": [1]}, citizen_id=1),  # not institutional
        _e(4, "coalition_formed", {"party_id": 1}),
        _e(4, "candidacy_considered", {"outcome": 1}, citizen_id=2),  # not institutional
    ]
    timeline = export_institutional(events)

    assert [e["event_type"] for e in timeline] == ["elected", "coalition_formed"]


def test_export_institutional_preserves_journal_order():
    events = [
        _e(8, "recalled", {"trigger": "legitimacy_floor"}, citizen_id=3),
        _e(0, "elected", {"winner": 5}, citizen_id=5),
        _e(4, "scandal_occurred", {"target": 5}),
    ]
    timeline = export_institutional(events)

    assert [e["tick"] for e in timeline] == [8, 0, 4]  # NOT re-sorted -- journal order is call order


def test_export_institutional_carries_citizen_id_motif_and_payload():
    events = [_e(0, "elected", {"winner": 5}, citizen_id=5, motif="301")]
    timeline = export_institutional(events)

    assert timeline == [{"tick": 0, "event_type": "elected", "citizen_id": 5, "motif": "301", "payload": {"winner": 5}}]


def test_export_institutional_empty_journal_gives_empty_timeline():
    assert export_institutional([]) == []


# ── export_social_graph ──────────────────────────────────────────────────

def test_export_social_graph_none_when_disabled():
    config = load_config()  # social_graph off by default
    assert export_social_graph(config) is None


def test_export_social_graph_returns_nodes_and_deduplicated_edges():
    config = load_config()
    config = dataclasses.replace(
        config,
        social_graph=dataclasses.replace(config.social_graph, enabled=True, topology="erdos_renyi", mean_degree=4),
        run=dataclasses.replace(config.run, population_size=20),
    )

    graph = export_social_graph(config)

    assert graph is not None
    assert graph["nodes"] == list(range(20))
    for edge in graph["edges"]:
        assert len(edge) == 2
        assert edge[0] < edge[1]  # canonical (a, b) with a < b -- proves dedup, not just presence


def test_export_social_graph_is_deterministic():
    config = load_config()
    config = dataclasses.replace(
        config,
        social_graph=dataclasses.replace(config.social_graph, enabled=True, topology="watts_strogatz", mean_degree=4),
        run=dataclasses.replace(config.run, population_size=20, seed=7),
    )

    assert export_social_graph(config) == export_social_graph(config)


# ── export_metadata ──────────────────────────────────────────────────────

def test_export_metadata_empty_when_llm_disabled():
    config = load_config()  # llm.enabled=False by default
    metadata = export_metadata(config)

    assert metadata == {"unverified_decision_types": [], "unverified_fields": {}}


def test_export_metadata_names_the_two_still_collapsing_decision_types_when_llm_enabled():
    config = load_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))

    metadata = export_metadata(config)

    assert set(metadata["unverified_decision_types"]) == {"representative_response", "coalition_decision"}
    assert metadata["unverified_fields"]["mandate_deviation"] == "representative_response"
    assert metadata["unverified_fields"]["cohabitation_rate"] == "coalition_decision"


def test_export_metadata_does_not_name_the_cleared_decision_type():
    # reaction_to_event's SCANDAL branch was re-tested and cleared (Phase 1)
    # -- it must never appear as unverified.
    config = load_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))

    metadata = export_metadata(config)

    assert "reaction_to_event" not in metadata["unverified_decision_types"]
    assert "reaction_to_event" not in metadata["unverified_fields"].values()


# ── export_run (end to end, a real deterministic simulation) ─────────────

def test_export_run_end_to_end_on_a_real_journal(tmp_path):
    config = load_config()
    config = dataclasses.replace(
        config,
        journal=dataclasses.replace(config.journal, output_dir=str(tmp_path), index_after_run=False),
        run=dataclasses.replace(config.run, population_size=25, duration_years=2),
        candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0),
    )
    journal_path = run_simulation(config, run_id="run")

    output_path = export_run(journal_path, config)

    assert output_path == journal_path.with_name("viz_export.json")
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "run"
    assert "macro" in payload
    assert "institutional" in payload
    assert payload["social_graph"] is None  # off by default
    assert payload["metadata"] == {"unverified_decision_types": [], "unverified_fields": {}}
    assert any(e["event_type"] == "elected" or e["event_type"] == "election_no_winner" for e in payload["institutional"])


def test_export_run_writes_to_an_explicit_output_path(tmp_path):
    config = load_config()
    config = dataclasses.replace(
        config,
        journal=dataclasses.replace(config.journal, output_dir=str(tmp_path), index_after_run=False),
        run=dataclasses.replace(config.run, population_size=25, duration_years=1),
    )
    journal_path = run_simulation(config, run_id="run")
    custom_path = tmp_path / "custom_export.json"

    result = export_run(journal_path, config, output_path=custom_path)

    assert result == custom_path
    assert custom_path.exists()
