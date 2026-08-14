"""Lot 1 — config.py: typed loading + validation of polity_config.yaml.

Contract (dev-plan-v0-worktree.md §3, Lot 1): an invalid config file fails
explicitly, never silently.
"""
import copy

import pytest
import yaml

from api.domain.polity.config import PolityConfigError, load_config


def test_loads_the_real_polity_config_with_expected_v0_values():
    config = load_config()
    assert config.run.seed == 42
    assert config.run.ticks_per_year == 4
    assert config.run.duration_years == 30
    assert config.run.total_ticks == 120
    assert config.run.population_size == 100
    assert config.institutions.presidential_method == "two_round"
    assert config.institutions.assembly_seats == 100
    assert config.institutions.seat_allocation == "dhondt"
    assert config.institutions.president_term_limit is None
    assert config.parties.initial_count == 5
    assert config.parties.coalition_tiebreak == ("seats", "votes", "party_id")
    assert config.citizens.issue_count == 20
    assert config.legitimacy.enabled is False
    assert config.journal.enabled is True
    assert config.metrics.effective_parties is True
    assert config.metrics.mandate_deviation is True
    assert config.metrics.lame_duck_deviation_delta is True
    assert config.metrics.inaction_rate is True
    assert config.metrics.pressure_lever_mix is True
    assert config.metrics.petition_success_rate is True
    assert config.metrics.stance_distribution is True
    assert config.llm.max_batch_replays == 0
    assert config.llm.enabled is False
    assert config.llm.provider == "ollama"
    assert config.llm.base_url == "http://localhost:11434/v1"
    assert config.llm.model == "qwen3:8b"
    assert config.llm.temperature == 0.0
    assert config.llm.max_batch_size == 25
    assert config.llm.batch_sharding == "static"
    assert config.llm.codebook_version == "1.3"
    assert config.llm.personas_count == 30
    assert config.campaign.max_positioning_delta == 0.3
    assert config.campaign.max_positioning_shifts == 3
    assert config.parallel.runs_in_parallel == 1
    assert config.parallel.intra_run_workers == 1


def test_missing_file_raises_explicitly(tmp_path):
    with pytest.raises(PolityConfigError, match="not found"):
        load_config(tmp_path / "does_not_exist.yaml")


def test_malformed_yaml_raises_explicitly(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("run: [unclosed", encoding="utf-8")
    with pytest.raises(PolityConfigError, match="invalid YAML"):
        load_config(bad)


def test_top_level_must_be_a_mapping(tmp_path):
    bad = tmp_path / "list.yaml"
    bad.write_text("- 1\n- 2\n", encoding="utf-8")
    with pytest.raises(PolityConfigError, match="mapping"):
        load_config(bad)


def _valid_dict() -> dict:
    return copy.deepcopy(load_config().raw)


def _write(tmp_path, mutate):
    data = _valid_dict()
    mutate(data)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_missing_required_key_raises_and_names_it(tmp_path):
    path = _write(tmp_path, lambda d: d["run"].pop("seed"))
    with pytest.raises(PolityConfigError, match="run.seed"):
        load_config(path)


def test_wrong_type_raises_and_names_it(tmp_path):
    path = _write(tmp_path, lambda d: d["run"].__setitem__("seed", "not-an-int"))
    with pytest.raises(PolityConfigError, match="run.seed"):
        load_config(path)


def test_bool_is_rejected_where_int_is_expected(tmp_path):
    """bool is a subclass of int in Python — a plain isinstance(x, int) check
    would silently accept `seed: true`. Must be rejected explicitly."""
    path = _write(tmp_path, lambda d: d["run"].__setitem__("seed", True))
    with pytest.raises(PolityConfigError, match="run.seed"):
        load_config(path)


def test_unknown_enum_value_raises(tmp_path):
    path = _write(
        tmp_path, lambda d: d["institutions"].__setitem__("presidential_method", "coin_flip")
    )
    with pytest.raises(PolityConfigError, match="presidential_method"):
        load_config(path)


def test_ratio_out_of_range_raises(tmp_path):
    path = _write(
        tmp_path, lambda d: d["institutions"].__setitem__("electoral_threshold", 1.5)
    )
    with pytest.raises(PolityConfigError, match="electoral_threshold"):
        load_config(path)


def test_coalition_tiebreak_rejects_unknown_key(tmp_path):
    path = _write(
        tmp_path,
        lambda d: d["parties"].__setitem__("coalition_tiebreak", ["seats", "coin_flip"]),
    )
    with pytest.raises(PolityConfigError, match="coalition_tiebreak"):
        load_config(path)


def test_coalition_tiebreak_rejects_duplicates(tmp_path):
    path = _write(
        tmp_path,
        lambda d: d["parties"].__setitem__("coalition_tiebreak", ["seats", "seats"]),
    )
    with pytest.raises(PolityConfigError, match="coalition_tiebreak"):
        load_config(path)


def test_coalition_tiebreak_rejects_empty(tmp_path):
    path = _write(tmp_path, lambda d: d["parties"].__setitem__("coalition_tiebreak", []))
    with pytest.raises(PolityConfigError, match="coalition_tiebreak"):
        load_config(path)


# ── llm / parallel (v2 increment 1) ──────────────────────────────────────

def test_llm_model_without_a_tag_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("model", "qwen3"))
    with pytest.raises(PolityConfigError, match="llm.model"):
        load_config(path)


def test_llm_model_pinned_to_latest_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("model", "qwen3:latest"))
    with pytest.raises(PolityConfigError, match="llm.model"):
        load_config(path)


def test_llm_provider_unknown_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("provider", "openai"))
    with pytest.raises(PolityConfigError, match="provider"):
        load_config(path)


def test_llm_batch_sharding_unknown_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("batch_sharding", "round_robin"))
    with pytest.raises(PolityConfigError, match="batch_sharding"):
        load_config(path)


def test_llm_max_batch_size_must_be_positive(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("max_batch_size", 0))
    with pytest.raises(PolityConfigError, match="max_batch_size"):
        load_config(path)


def test_llm_enabled_with_nonzero_temperature_raises(tmp_path):
    def mutate(d):
        d["llm"]["enabled"] = True
        d["llm"]["temperature"] = 0.7

    path = _write(tmp_path, mutate)
    with pytest.raises(PolityConfigError, match="temperature"):
        load_config(path)


def test_llm_disabled_with_nonzero_temperature_is_allowed(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("temperature", 0.7))
    config = load_config(path)
    assert config.llm.temperature == 0.7
    assert config.llm.enabled is False


def test_llm_base_url_without_scheme_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("base_url", "localhost:11434/v1"))
    with pytest.raises(PolityConfigError, match="base_url"):
        load_config(path)


def test_llm_base_url_trailing_slash_is_stripped(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("base_url", "http://localhost:11434/v1/"))
    config = load_config(path)
    assert config.llm.base_url == "http://localhost:11434/v1"


def test_parallel_intra_run_workers_must_be_positive(tmp_path):
    path = _write(tmp_path, lambda d: d["parallel"].__setitem__("intra_run_workers", 0))
    with pytest.raises(PolityConfigError, match="intra_run_workers"):
        load_config(path)


# ── campaign (v2 increment 4) ─────────────────────────────────────────────

def test_campaign_max_positioning_delta_out_of_range_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["campaign"].__setitem__("max_positioning_delta", 1.5))
    with pytest.raises(PolityConfigError, match="max_positioning_delta"):
        load_config(path)


def test_campaign_max_positioning_shifts_must_be_positive(tmp_path):
    path = _write(tmp_path, lambda d: d["campaign"].__setitem__("max_positioning_shifts", 0))
    with pytest.raises(PolityConfigError, match="max_positioning_shifts"):
        load_config(path)


# ── v4 Lot 1: legitimacy/pressure/mandate/petition/street_pressure/awakening ──

def test_loads_the_real_config_with_expected_v4_lot1_values():
    config = load_config()
    assert config.citizens.base_threshold_dist == "beta(3,5)"
    assert config.legitimacy.recall_floor_indexed_on_l0 is False
    assert config.legitimacy.recall_cooldown_ticks == 4
    assert config.legitimacy.passive_erosion_weight == 0.0
    assert config.pressure_menu.petition_enabled is False
    assert config.pressure_menu.mobilization_enabled is False
    assert config.pressure_menu.electoral_only is True
    assert config.mandate.pledge_scope == "top_k_priorities"
    assert config.mandate.pledge_top_k == 5
    assert config.mandate.max_response_delta == 0.3
    assert config.mandate.max_response_shifts == 3
    assert config.petition.signature_threshold == 0.25
    assert config.petition.concurrent_allowed is False
    assert config.petition.weight_in_ecart == 0.5
    assert config.street_pressure.decay == 0.85
    assert config.street_pressure.weight_in_ecart == 0.5
    assert config.awakening.source == "persona_base_threshold"
    assert config.awakening.context_modulation.mandate_deviation is True
    assert config.awakening.context_modulation.neighbors_acting is False
    assert config.awakening.modulation_amplitude == 0.5
    assert config.awakening.no_consultation_cap is True


def test_legitimacy_recall_floor_indexed_on_l0_true_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["legitimacy"].__setitem__("recall_floor_indexed_on_L0", True))
    with pytest.raises(PolityConfigError, match="recall_floor_indexed_on_L0"):
        load_config(path)


def test_awakening_no_consultation_cap_false_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["awakening"].__setitem__("no_consultation_cap", False))
    with pytest.raises(PolityConfigError, match="no_consultation_cap"):
        load_config(path)


def test_petition_concurrent_allowed_true_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["petition"].__setitem__("concurrent_allowed", True))
    with pytest.raises(PolityConfigError, match="concurrent_allowed"):
        load_config(path)


# ── metrics.* [v2]/[v6] TRANCHÉ guards (v4 Lot 8: not implemented yet) ────

def test_metrics_platform_convergence_true_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["metrics"].__setitem__("platform_convergence", True))
    with pytest.raises(PolityConfigError, match="platform_convergence"):
        load_config(path)


def test_metrics_mobilization_nonlinearity_true_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["metrics"].__setitem__("mobilization_nonlinearity", True))
    with pytest.raises(PolityConfigError, match="mobilization_nonlinearity"):
        load_config(path)


def test_metrics_polarization_true_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["metrics"].__setitem__("polarization", True))
    with pytest.raises(PolityConfigError, match="polarization"):
        load_config(path)


# ── llm.max_batch_replays (v4 Lot 8) ──────────────────────────────────────

def test_llm_max_batch_replays_negative_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("max_batch_replays", -1))
    with pytest.raises(PolityConfigError, match="max_batch_replays"):
        load_config(path)


def test_llm_max_batch_replays_zero_is_legal(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("max_batch_replays", 0))
    assert load_config(path).llm.max_batch_replays == 0


def test_llm_max_batch_replays_positive_is_legal(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("max_batch_replays", 2))
    assert load_config(path).llm.max_batch_replays == 2


def test_mandate_unknown_pledge_scope_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["mandate"].__setitem__("pledge_scope", "everything"))
    with pytest.raises(PolityConfigError, match="pledge_scope"):
        load_config(path)


def test_awakening_unknown_source_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["awakening"].__setitem__("source", "random"))
    with pytest.raises(PolityConfigError, match="source"):
        load_config(path)


def test_electoral_only_with_petition_enabled_raises(tmp_path):
    def mutate(d):
        d["pressure_menu"]["electoral_only"] = True
        d["pressure_menu"]["petition_enabled"] = True
        d["petition"]["enabled"] = True
        d["legitimacy"]["enabled"] = True

    path = _write(tmp_path, mutate)
    with pytest.raises(PolityConfigError, match="electoral_only"):
        load_config(path)


def test_electoral_only_with_mobilization_enabled_raises(tmp_path):
    def mutate(d):
        d["pressure_menu"]["electoral_only"] = True
        d["pressure_menu"]["mobilization_enabled"] = True
        d["street_pressure"]["enabled"] = True
        d["legitimacy"]["enabled"] = True

    path = _write(tmp_path, mutate)
    with pytest.raises(PolityConfigError, match="electoral_only"):
        load_config(path)


def test_pressure_menu_petition_enabled_disagreeing_with_petition_enabled_raises(tmp_path):
    def mutate(d):
        d["pressure_menu"]["electoral_only"] = False
        d["pressure_menu"]["petition_enabled"] = True
        # petition.enabled deliberately left False -- the drift this rule catches.

    path = _write(tmp_path, mutate)
    with pytest.raises(PolityConfigError, match="petition_enabled"):
        load_config(path)


def test_pressure_menu_mobilization_enabled_disagreeing_with_street_pressure_enabled_raises(tmp_path):
    def mutate(d):
        d["pressure_menu"]["electoral_only"] = False
        d["pressure_menu"]["mobilization_enabled"] = True
        # street_pressure.enabled deliberately left False -- the drift this rule catches.

    path = _write(tmp_path, mutate)
    with pytest.raises(PolityConfigError, match="mobilization_enabled"):
        load_config(path)


def test_petition_and_street_pressure_weights_must_sum_to_one(tmp_path):
    path = _write(tmp_path, lambda d: d["petition"].__setitem__("weight_in_ecart", 0.6))
    with pytest.raises(PolityConfigError, match="weight_in_ecart"):
        load_config(path)


def test_petition_enabled_without_legitimacy_enabled_raises(tmp_path):
    def mutate(d):
        d["pressure_menu"]["electoral_only"] = False
        d["pressure_menu"]["petition_enabled"] = True
        d["petition"]["enabled"] = True
        # legitimacy.enabled deliberately left False.

    path = _write(tmp_path, mutate)
    with pytest.raises(PolityConfigError, match="legitimacy.enabled"):
        load_config(path)


def test_street_pressure_enabled_without_legitimacy_enabled_raises(tmp_path):
    def mutate(d):
        d["pressure_menu"]["electoral_only"] = False
        d["pressure_menu"]["mobilization_enabled"] = True
        d["street_pressure"]["enabled"] = True
        # legitimacy.enabled deliberately left False.

    path = _write(tmp_path, mutate)
    with pytest.raises(PolityConfigError, match="legitimacy.enabled"):
        load_config(path)


def test_petition_and_mobilization_enabled_with_legitimacy_enabled_is_allowed(tmp_path):
    def mutate(d):
        d["pressure_menu"]["electoral_only"] = False
        d["pressure_menu"]["petition_enabled"] = True
        d["pressure_menu"]["mobilization_enabled"] = True
        d["petition"]["enabled"] = True
        d["street_pressure"]["enabled"] = True
        d["legitimacy"]["enabled"] = True
        d["awakening"]["enabled"] = True

    path = _write(tmp_path, mutate)
    config = load_config(path)
    assert config.pressure_menu.petition_enabled is True
    assert config.pressure_menu.mobilization_enabled is True
    assert config.legitimacy.enabled is True
    assert config.awakening.enabled is True


def test_street_pressure_enabled_without_awakening_enabled_raises(tmp_path):
    def mutate(d):
        d["pressure_menu"]["electoral_only"] = False
        d["pressure_menu"]["mobilization_enabled"] = True
        d["street_pressure"]["enabled"] = True
        d["legitimacy"]["enabled"] = True
        # awakening.enabled deliberately left False.

    path = _write(tmp_path, mutate)
    with pytest.raises(PolityConfigError, match="awakening.enabled"):
        load_config(path)


def test_petition_enabled_without_awakening_enabled_raises(tmp_path):
    def mutate(d):
        d["pressure_menu"]["electoral_only"] = False
        d["pressure_menu"]["petition_enabled"] = True
        d["petition"]["enabled"] = True
        d["legitimacy"]["enabled"] = True
        # awakening.enabled deliberately left False.

    path = _write(tmp_path, mutate)
    with pytest.raises(PolityConfigError, match="awakening.enabled"):
        load_config(path)
