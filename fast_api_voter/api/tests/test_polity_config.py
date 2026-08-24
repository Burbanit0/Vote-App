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
    assert config.journal.index_after_run is True
    assert config.journal.decode_codebook_on_index is True
    assert config.metrics.effective_parties is True
    assert config.metrics.mandate_deviation is True
    assert config.metrics.lame_duck_deviation_delta is True
    assert config.metrics.inaction_rate is True
    assert config.metrics.pressure_lever_mix is True
    assert config.metrics.petition_success_rate is True
    assert config.metrics.stance_distribution is True
    assert config.llm.max_batch_replays == 0
    assert config.llm.recycle_after_n_calls is None
    assert config.llm.enabled is False
    assert config.llm.provider == "ollama"
    assert config.llm.base_url == "http://localhost:11434/v1"
    assert config.llm.model == "qwen3:8b"
    assert config.llm.temperature == 0.0
    assert config.llm.max_batch_size == 25
    assert config.llm.batch_sharding == "static"
    assert config.llm.codebook_version == "1.6"
    assert config.sortition_chamber.enabled is False
    assert config.sortition_chamber.seats == 30
    assert config.sortition_chamber.term_years == 1
    assert config.sortition_chamber.renewable is False
    assert config.sortition_chamber.selection == "uniform_random"
    assert config.sortition_chamber.overlaps_with_assembly is False
    assert config.sortition_chamber.veto_power == "suspensive_limited"
    assert config.sortition_chamber.veto_delay_ticks == 2
    assert config.sortition_chamber.max_deliberation_delta == 0.3
    assert config.sortition_chamber.max_deliberation_shifts == 3
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


def test_blank_vote_competitive_without_blank_vote_enabled_raises(tmp_path):
    def mutate(d):
        d["institutions"]["blank_vote_enabled"] = False
        d["institutions"]["blank_vote_competitive"] = True

    path = _write(tmp_path, mutate)
    with pytest.raises(PolityConfigError, match="blank_vote_competitive"):
        load_config(path)


def test_reelection_delay_ticks_zero_raises(tmp_path):
    path = _write(
        tmp_path, lambda d: d["institutions"].__setitem__("reelection_delay_ticks", 0)
    )
    with pytest.raises(PolityConfigError, match="reelection_delay_ticks"):
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


def test_llm_provider_vllm_is_accepted(tmp_path):
    # v4 vLLM switch (§15bis.6): "vllm" is a legal config.py value even
    # though the shipped default stays "ollama" -- nothing pinned this
    # loading successfully before this lot.
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("provider", "vllm"))
    config = load_config(path)
    assert config.llm.provider == "vllm"


def test_llm_model_bare_hf_repo_id_is_rejected(tmp_path):
    # Pins a genuine v4 vLLM-switch blocker, not just the pre-existing
    # pinning rule: vLLM's natural model id (e.g. "Qwen/Qwen3-8B") has no
    # colon, so it fails llm.model's pinning check exactly like an
    # unpinned Ollama tag would. This is why the vLLM deployment plan
    # requires launching the server with `--served-model-name qwen3:8b`
    # rather than relaxing this rule -- llm.model, and every prompt/journal
    # byte downstream of it, stays identical across providers.
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("model", "Qwen/Qwen3-8B"))
    with pytest.raises(PolityConfigError, match="llm.model"):
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


# ── llm.recycle_after_n_calls (bug 4 investigation, 2026-08-19/20) ────────

def test_llm_recycle_after_n_calls_null_is_legal(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("recycle_after_n_calls", None))
    assert load_config(path).llm.recycle_after_n_calls is None


def test_llm_recycle_after_n_calls_positive_is_legal(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("recycle_after_n_calls", 6))
    assert load_config(path).llm.recycle_after_n_calls == 6


def test_llm_recycle_after_n_calls_zero_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("recycle_after_n_calls", 0))
    with pytest.raises(PolityConfigError, match="recycle_after_n_calls"):
        load_config(path)


def test_llm_recycle_after_n_calls_negative_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("recycle_after_n_calls", -1))
    with pytest.raises(PolityConfigError, match="recycle_after_n_calls"):
        load_config(path)


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


# ── journal.decode_codebook_on_index (v4 storage lot, §16.6/§3.7.4) ───────

def test_missing_decode_codebook_on_index_raises_and_names_it(tmp_path):
    path = _write(tmp_path, lambda d: d["journal"].pop("decode_codebook_on_index"))
    with pytest.raises(PolityConfigError, match="journal.decode_codebook_on_index"):
        load_config(path)


# ── events (v5 Lot 1, §8) ──────────────────────────────────────────────────

def test_shipped_default_events_config_is_reachable_and_off():
    config = load_config()
    assert config.events.enabled is False
    assert config.events.scandal_enabled is False
    assert config.events.scandal_rate_per_tick == 0.05
    assert config.events.scandal_magnitude == 0.3
    assert config.events.economic_shock_enabled is False
    assert config.events.economy_ar1_phi == 0.8
    assert config.events.economy_ar1_sigma == 0.1
    assert config.events.economy_shock_threshold == 0.5
    assert config.events.salience_decay == 0.85
    assert config.events.max_reaction_delta == 0.3
    assert config.awakening.context_modulation.event_salience is False


def test_events_enabled_disagreeing_with_both_subtoggles_raises(tmp_path):
    # enabled=True but neither scandal_enabled nor economic_shock_enabled --
    # the two must describe the same fact (§8), mirroring the
    # pressure_menu/petition drift-prevention rule.
    path = _write(tmp_path, lambda d: d["events"].__setitem__("enabled", True))
    with pytest.raises(PolityConfigError, match="events.enabled"):
        load_config(path)


def test_events_enabled_false_with_a_subtoggle_true_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["events"].__setitem__("scandal_enabled", True))
    with pytest.raises(PolityConfigError, match="events.enabled"):
        load_config(path)


def test_events_enabled_without_awakening_enabled_raises(tmp_path):
    def mutate(d):
        d["events"]["enabled"] = True
        d["events"]["scandal_enabled"] = True
        d["awakening"]["context_modulation"]["event_salience"] = True
        # awakening.enabled deliberately left False.

    path = _write(tmp_path, mutate)
    with pytest.raises(PolityConfigError, match="awakening.enabled"):
        load_config(path)


def test_events_enabled_without_event_salience_modulation_raises(tmp_path):
    def mutate(d):
        d["events"]["enabled"] = True
        d["events"]["scandal_enabled"] = True
        d["awakening"]["enabled"] = True
        # awakening.context_modulation.event_salience deliberately left False.

    path = _write(tmp_path, mutate)
    with pytest.raises(PolityConfigError, match="event_salience"):
        load_config(path)


def test_events_enabled_economic_shock_only_is_accepted(tmp_path):
    def mutate(d):
        d["events"]["enabled"] = True
        d["events"]["economic_shock_enabled"] = True
        d["awakening"]["enabled"] = True
        d["awakening"]["context_modulation"]["event_salience"] = True

    path = _write(tmp_path, mutate)
    config = load_config(path)
    assert config.events.enabled is True
    assert config.events.scandal_enabled is False
    assert config.events.economic_shock_enabled is True


def test_missing_event_salience_modulation_flag_raises_and_names_it(tmp_path):
    path = _write(tmp_path, lambda d: d["awakening"]["context_modulation"].pop("event_salience"))
    with pytest.raises(PolityConfigError, match="event_salience"):
        load_config(path)


# ── social_graph (v6 Lot 1, §5) ────────────────────────────────────────────

def test_shipped_default_social_graph_config_is_reachable_and_off():
    config = load_config()
    assert config.social_graph.enabled is False
    assert config.social_graph.topology == "watts_strogatz"
    assert config.social_graph.mean_degree == 8
    assert config.social_graph.rewiring_prob == 0.1
    assert config.social_graph.evolving is False
    assert config.awakening.context_modulation.neighbors_acting is False


def test_social_graph_unknown_topology_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["social_graph"].__setitem__("topology", "random_forest"))
    with pytest.raises(PolityConfigError, match="social_graph.topology"):
        load_config(path)


def test_social_graph_evolving_true_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["social_graph"].__setitem__("evolving", True))
    with pytest.raises(PolityConfigError, match="social_graph.evolving"):
        load_config(path)


def test_social_graph_mean_degree_zero_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["social_graph"].__setitem__("mean_degree", 0))
    with pytest.raises(PolityConfigError, match="social_graph.mean_degree"):
        load_config(path)


def test_social_graph_rewiring_prob_out_of_range_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["social_graph"].__setitem__("rewiring_prob", 1.5))
    with pytest.raises(PolityConfigError, match="social_graph.rewiring_prob"):
        load_config(path)


def test_neighbors_acting_modulation_without_social_graph_enabled_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["awakening"]["context_modulation"].__setitem__("neighbors_acting", True))
    with pytest.raises(PolityConfigError, match="social_graph.enabled"):
        load_config(path)


def test_social_graph_enabled_without_neighbors_acting_modulation_is_accepted(tmp_path):
    # The deliberately-not-enforced reverse direction: the graph can be
    # enabled (feeding pressure_action's ctx.neighbors_acting, once wired)
    # without also modulating the awakening gate -- a real experimental arm,
    # not a degenerate one, so this must NOT raise.
    path = _write(tmp_path, lambda d: d["social_graph"].__setitem__("enabled", True))
    config = load_config(path)
    assert config.social_graph.enabled is True
    assert config.awakening.context_modulation.neighbors_acting is False


def test_missing_social_graph_topology_raises_and_names_it(tmp_path):
    path = _write(tmp_path, lambda d: d["social_graph"].pop("topology"))
    with pytest.raises(PolityConfigError, match="social_graph.topology"):
        load_config(path)


# ── v6b Lot 1: sortition_chamber (§6bis.3) ────────────────────────────────

def test_sortition_selection_stratified_demographic_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["sortition_chamber"].__setitem__("selection", "stratified_demographic"))
    with pytest.raises(PolityConfigError, match="sortition_chamber.selection"):
        load_config(path)


def test_sortition_overlaps_with_assembly_true_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["sortition_chamber"].__setitem__("overlaps_with_assembly", True))
    with pytest.raises(PolityConfigError, match="sortition_chamber.overlaps_with_assembly"):
        load_config(path)


def test_sortition_renewable_true_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["sortition_chamber"].__setitem__("renewable", True))
    with pytest.raises(PolityConfigError, match="sortition_chamber.renewable"):
        load_config(path)


def test_sortition_unknown_veto_power_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["sortition_chamber"].__setitem__("veto_power", "absolute"))
    with pytest.raises(PolityConfigError, match="sortition_chamber.veto_power"):
        load_config(path)


def test_sortition_seats_zero_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["sortition_chamber"].__setitem__("seats", 0))
    with pytest.raises(PolityConfigError, match="sortition_chamber.seats"):
        load_config(path)


def test_sortition_enabled_with_seats_exceeding_population_size_raises(tmp_path):
    def mutate(d: dict) -> None:
        d["sortition_chamber"]["enabled"] = True
        d["sortition_chamber"]["seats"] = d["run"]["population_size"] + 1

    path = _write(tmp_path, mutate)
    with pytest.raises(PolityConfigError, match="sortition_chamber.seats"):
        load_config(path)


def test_sortition_enabled_with_seats_equal_to_population_size_is_accepted(tmp_path):
    # Boundary case: seats == population_size seats exactly one full chamber
    # from the whole population -- legal, not a degenerate arm.
    def mutate(d: dict) -> None:
        d["sortition_chamber"]["enabled"] = True
        d["sortition_chamber"]["seats"] = d["run"]["population_size"]

    path = _write(tmp_path, mutate)
    config = load_config(path)
    assert config.sortition_chamber.enabled is True
    assert config.sortition_chamber.seats == config.run.population_size


def test_missing_sortition_seats_raises_and_names_it(tmp_path):
    path = _write(tmp_path, lambda d: d["sortition_chamber"].pop("seats"))
    with pytest.raises(PolityConfigError, match="sortition_chamber.seats"):
        load_config(path)


# ── v6b Lot 3: max_deliberation_delta/max_deliberation_shifts (§6bis.3, dt=11) ──

def test_sortition_max_deliberation_delta_out_of_range_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["sortition_chamber"].__setitem__("max_deliberation_delta", 1.5))
    with pytest.raises(PolityConfigError, match="sortition_chamber.max_deliberation_delta"):
        load_config(path)


def test_missing_sortition_max_deliberation_delta_raises_and_names_it(tmp_path):
    path = _write(tmp_path, lambda d: d["sortition_chamber"].pop("max_deliberation_delta"))
    with pytest.raises(PolityConfigError, match="sortition_chamber.max_deliberation_delta"):
        load_config(path)


def test_sortition_max_deliberation_shifts_zero_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["sortition_chamber"].__setitem__("max_deliberation_shifts", 0))
    with pytest.raises(PolityConfigError, match="sortition_chamber.max_deliberation_shifts"):
        load_config(path)


def test_missing_sortition_max_deliberation_shifts_raises_and_names_it(tmp_path):
    path = _write(tmp_path, lambda d: d["sortition_chamber"].pop("max_deliberation_shifts"))
    with pytest.raises(PolityConfigError, match="sortition_chamber.max_deliberation_shifts"):
        load_config(path)
